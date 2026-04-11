import os
import pandas as pd
import json
import numpy as np
from sklearn.metrics import cohen_kappa_score
from src.processors.call2go_detector import (
    detect_call2go, detect_call2go_channel_scraped
)
from src.collectors.channel_link_scraper import load_cached_channel_links


def _bootstrap_ci(y_true, y_pred, metric_fn, n_boot=2000, ci=0.95, seed=42):
    """
    Calcula intervalo de confiança via bootstrap para qualquer métrica.

    Args:
        y_true: array de rótulos verdadeiros (humano)
        y_pred: array de rótulos preditos (detector)
        metric_fn: função(y_true, y_pred) -> float
        n_boot: número de re-amostras bootstrap
        ci: nível de confiança (0.95 = 95%)
        seed: seed para reprodutibilidade

    Returns:
        (point_estimate, lower_bound, upper_bound)
    """
    rng = np.random.RandomState(seed)
    n = len(y_true)
    point = metric_fn(y_true, y_pred)

    boot_scores = []
    for _ in range(n_boot):
        idx = rng.randint(0, n, size=n)
        y_t = [y_true[i] for i in idx]
        y_p = [y_pred[i] for i in idx]
        # Cohen's Kappa pode dar erro se todos os rótulos forem iguais
        try:
            score = metric_fn(y_t, y_p)
            boot_scores.append(score)
        except (ValueError, ZeroDivisionError):
            continue

    if not boot_scores:
        return point, float('nan'), float('nan')

    alpha = 1 - ci
    lower = np.percentile(boot_scores, 100 * alpha / 2)
    upper = np.percentile(boot_scores, 100 * (1 - alpha / 2))
    return point, float(lower), float(upper)


def _map_to_binary(value):
    """
    Mapeia qualquer formato de anotação para labels binários unificados.
    SIM / link_direto / texto_implicito → com_call2go
    NÃO / nenhum → sem_call2go
    """
    v = str(value).strip().upper()
    if v in ('SIM', 'LINK_DIRETO', 'TEXTO_IMPLICITO'):
        return 'com_call2go'
    if v in ('NÃO', 'NAO', 'NENHUM', 'NAO'):
        return 'sem_call2go'
    return None


def _detect_separator(filepath):
    """Auto-detecta separador do CSV (`;` vs `,`) via primeira linha."""
    with open(filepath, 'r', encoding='utf-8') as f:
        first_line = f.readline()
    return ';' if first_line.count(';') > first_line.count(',') else ','


def run_cross_validation(ground_truth_file="data/validation/ground_truth.csv",
                         raw_file="data/raw/youtube_videos_raw.jsonl",
                         output_file="data/validation/cross_validation_report.csv"):
    """
    Validação HUMANO vs. MÁQUINA -- Confiabilidade do detector regex.

    Compara a classificação automatizada (call2go_detector) com a anotação
    manual humana (ground truth), gerando métricas de confiabilidade do
    instrumento de medição.

    Suporta dois formatos de ground truth:
      - Formato novo (blind_annotation): SIM/NÃO binário, separador `;`
        Colunas: manual_call2go_video, manual_call2go_canal, manual_call2go_combinado
      - Formato legado: link_direto/texto_implicito/nenhum, separador `,`
        Colunas: manual_call2go_type, manual_channel_call2go_type

    Ambos são mapeados para labels binários (com_call2go / sem_call2go)
    antes da comparação, pois texto_implicito=0 no dataset real.

    Compara em 3 níveis independentes:
      1. Vídeo: humano vs. detector na descrição do vídeo
      2. Canal: humano vs. detector no perfil do canal (About page)
      3. Combinado: humano vs. detector (vídeo OU canal)
         NOTA: humano usou lógica AND; detector usa OR -- discordância documentada.

    Args:
        ground_truth_file: CSV com anotações manuais.
        raw_file: JSONL bruto para re-executar o detector.
        output_file: CSV do relatório de validação cruzada.
    """
    print("=" * 60)
    print("VALIDAÇÃO CRUZADA -- HUMANO vs. DETECTOR AUTOMATIZADO")
    print("=" * 60)

    # Validação de entrada
    if not os.path.exists(ground_truth_file):
        print(f"[ERRO] Ground truth não encontrado: {ground_truth_file}")
        print("Execute primeiro: python -m src.validation.sample_generator")
        print("Depois anote manualmente e salve como ground_truth.csv")
        return None

    if not os.path.exists(raw_file):
        print(f"[ERRO] Dados brutos não encontrados: {raw_file}")
        return None

    # 1. Carrega ground truth com auto-detecção de separador
    sep = _detect_separator(ground_truth_file)
    df_gt = pd.read_csv(ground_truth_file, sep=sep)
    print(f"  Separador detectado: '{sep}'")
    print(f"  Linhas carregadas: {len(df_gt)}")

    # Detecta formato de colunas e normaliza para formato interno
    if 'manual_call2go_video' in df_gt.columns:
        # Formato novo (blind_annotation) -- 3 colunas separadas, valores SIM/NÃO
        print("  Formato detectado: blind_annotation (SIM/NÃO binário)")
        has_video_gt = True
        has_channel_gt = 'manual_call2go_canal' in df_gt.columns
        has_combined_gt = 'manual_call2go_combinado' in df_gt.columns
    elif 'manual_call2go_type' in df_gt.columns:
        # Formato legado -- coluna única combinada, valores link_direto/texto_implicito/nenhum
        print("  Formato detectado: ground_truth (legado 3-classe)")
        df_gt['manual_call2go_video'] = df_gt['manual_call2go_type']
        has_video_gt = True
        has_channel_gt = 'manual_channel_call2go_type' in df_gt.columns
        if has_channel_gt:
            df_gt['manual_call2go_canal'] = df_gt['manual_channel_call2go_type']
        has_combined_gt = False
    else:
        print("[ERRO] Colunas de anotação manual não encontradas.")
        print("  Esperado: manual_call2go_video ou manual_call2go_type")
        return None

    # Mapeia todas as anotações humanas para binário
    df_gt['manual_video_bin'] = df_gt['manual_call2go_video'].apply(
        _map_to_binary)
    if has_channel_gt:
        df_gt['manual_canal_bin'] = df_gt['manual_call2go_canal'].apply(
            _map_to_binary)
    if has_combined_gt:
        df_gt['manual_combinado_bin'] = df_gt['manual_call2go_combinado'].apply(
            _map_to_binary)

    # Verifica preenchimento
    empty_count = df_gt['manual_video_bin'].isna().sum()
    if empty_count > 0:
        print(
            f"[AVISO] {empty_count} vídeos sem anotação manual válida. Serão ignorados.")
        df_gt = df_gt[df_gt['manual_video_bin'].notna()]

    gt_ids = set(df_gt['video_id'].values)

    # 2. Carrega dados brutos e re-executa o detector
    raw_videos = {}
    with open(raw_file, 'r', encoding='utf-8') as f:
        for line in f:
            video = json.loads(line)
            vid = video.get('video_id')
            if vid in gt_ids:
                raw_videos[vid] = {
                    'description': video.get('description', ''),
                    'channel_description': video.get('channel_description', ''),
                    'channel_id': video.get('channel_id', ''),
                }

    # 2b. Carrega links scrapeados dos canais (About page)
    scraped_data = load_cached_channel_links()
    if scraped_data:
        print(f"  Links scrapeados carregados: {len(scraped_data)} canais")
    else:
        print(
            "  [AVISO] Links scrapeados não encontrados -- detecção de canal será apenas por texto")

    # 3. Comparação lado a lado -- detector vs. humano (tudo em binário)
    results = []
    for _, row in df_gt.iterrows():
        vid = row['video_id']
        raw = raw_videos.get(vid, {})
        description = raw.get('description', '')
        channel_id = raw.get('channel_id', '')

        # Detector no vídeo (Nível 1)
        auto_has_video, auto_type_video = detect_call2go(description)
        auto_video_bin = 'com_call2go' if auto_has_video else 'sem_call2go'

        # Detector no canal -- links estruturados scraped (Nível 2)
        auto_has_channel, auto_type_channel = detect_call2go_channel_scraped(
            channel_id, scraped_data)
        auto_channel_bin = 'com_call2go' if auto_has_channel else 'sem_call2go'

        # Combinado detector: lógica OR (vídeo OU canal)
        auto_has_combined = auto_has_video or auto_has_channel
        auto_combined_bin = 'com_call2go' if auto_has_combined else 'sem_call2go'
        auto_source = ('video' if auto_has_video else
                       'canal' if auto_has_channel else
                       'nenhum')

        result = {
            'video_id': vid,
            'artist_name': row['artist_name'],
            'title': row.get('title', ''),
            # Anotação humana (binário)
            'manual_video': row['manual_video_bin'],
            'manual_canal': row.get('manual_canal_bin', None) if has_channel_gt else None,
            'manual_combinado': row.get('manual_combinado_bin', None) if has_combined_gt else None,
            # Detector (binário)
            'auto_video': auto_video_bin,
            'auto_canal': auto_channel_bin,
            'auto_combinado': auto_combined_bin,
            'auto_source': auto_source,
            # Tipos originais do detector (para análise de discordâncias)
            'auto_video_type_orig': auto_type_video if auto_has_video else 'nenhum',
            'auto_canal_type_orig': auto_type_channel if auto_has_channel else 'nenhum',
            # Match por nível
            'match_video': (row['manual_video_bin'] == auto_video_bin),
            'match_canal': (row.get('manual_canal_bin') == auto_channel_bin) if has_channel_gt else None,
            'match_combinado': (row.get('manual_combinado_bin') == auto_combined_bin) if has_combined_gt else None,
            'description_length': len(description),
        }
        results.append(result)

    df_results = pd.DataFrame(results)

    # 4. Métricas de concordância -- TRÊS NÍVEIS (binário)
    def _calc_metrics(df, manual_col, auto_col, label):
        """Calcula acurácia, precisão, recall, F1, Cohen's Kappa + bootstrap CI (binário)."""
        valid = df[df[manual_col].notna() & df[auto_col].notna()].copy()
        if len(valid) == 0:
            return None

        total = len(valid)
        y_true = valid[manual_col].tolist()
        y_pred = valid[auto_col].tolist()

        matches = sum(1 for a, b in zip(y_true, y_pred) if a == b)
        accuracy = matches / total if total > 0 else 0

        # Cohen's Kappa -- métrica padrão para concordância inter-anotador
        try:
            kappa = cohen_kappa_score(y_true, y_pred)
        except (ValueError, ZeroDivisionError):
            kappa = float('nan')

        # Bootstrap CI 95% para Kappa e Acurácia
        def accuracy_fn(yt, yp):
            return sum(1 for a, b in zip(yt, yp) if a == b) / len(yt)

        kappa_point, kappa_lo, kappa_hi = _bootstrap_ci(
            y_true, y_pred, cohen_kappa_score)
        acc_point, acc_lo, acc_hi = _bootstrap_ci(
            y_true, y_pred, accuracy_fn)

        # Métricas por classe -- binário: com_call2go / sem_call2go
        classes = ['com_call2go', 'sem_call2go']
        per_class = {}
        for c in classes:
            tp = len(valid[(valid[manual_col] == c) & (valid[auto_col] == c)])
            fp = len(valid[(valid[manual_col] != c) & (valid[auto_col] == c)])
            fn = len(valid[(valid[manual_col] == c) & (valid[auto_col] != c)])
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision +
                                             recall) if (precision + recall) > 0 else 0
            per_class[c] = {
                'true_positives': tp, 'false_positives': fp, 'false_negatives': fn,
                'precision': precision, 'recall': recall, 'f1_score': f1
            }

        kappa_interp = (
            "quase perfeito" if kappa >= 0.81 else
            "substancial" if kappa >= 0.61 else
            "moderado" if kappa >= 0.41 else
            "razoavel" if kappa >= 0.21 else
            "fraco" if kappa >= 0.0 else
            "abaixo do acaso"
        )

        print(f"\n{'=' * 50}")
        print(f"  {label}")
        print(f"{'=' * 50}")
        print(f"  Total validados: {total}")
        print(f"  Concordâncias: {matches}")
        print(f"  Discordâncias: {total - matches}")
        print(
            f"  ACURÁCIA: {accuracy:.1%}  IC95%=[{acc_lo:.1%}, {acc_hi:.1%}]")
        print(
            f"  COHEN'S KAPPA: {kappa:.4f}  IC95%=[{kappa_lo:.4f}, {kappa_hi:.4f}]")
        print(f"  Interpretação Kappa (Landis & Koch): {kappa_interp}")
        for c, m in per_class.items():
            print(f"    [{c}] P={m['precision']:.1%} R={m['recall']:.1%} F1={m['f1_score']:.1%} (TP={m['true_positives']} FP={m['false_positives']} FN={m['false_negatives']})")

        return {
            'total_validated': total,
            'matches': int(matches),
            'discordances': int(total - matches),
            'accuracy': round(accuracy, 4),
            'accuracy_ci95': [round(acc_lo, 4), round(acc_hi, 4)],
            'cohens_kappa': round(kappa, 4),
            'kappa_ci95': [round(kappa_lo, 4), round(kappa_hi, 4)],
            'kappa_interpretation': kappa_interp,
            'per_class': {k: {mk: round(mv, 4) if isinstance(mv, float) else mv
                              for mk, mv in v.items()} for k, v in per_class.items()}
        }

    # Nível 1: Vídeo (humano vs. detector na descrição do vídeo)
    metrics_video = _calc_metrics(
        df_results, 'manual_video', 'auto_video',
        'NÍVEL 1 -- VÍDEO (humano vs. regex na descrição)')

    # Nível 2: Canal (humano vs. detector no perfil do canal)
    metrics_channel = None
    if has_channel_gt:
        metrics_channel = _calc_metrics(
            df_results, 'manual_canal', 'auto_canal',
            'NÍVEL 2 -- CANAL (humano vs. regex no perfil About)')

    # Nível 3: Combinado (humano vs. detector vídeo+canal)
    #   NOTA: humano usou AND (vídeo E canal); detector usa OR (vídeo OU canal)
    #   Discordâncias esperadas: canal=SIM mas vídeo=NÃO → humano=NÃO, detector=SIM
    metrics_combined = None
    if has_combined_gt:
        metrics_combined = _calc_metrics(
            df_results, 'manual_combinado', 'auto_combinado',
            'NÍVEL 3 -- COMBINADO (humano AND vs. detector OR)')
    else:
        # Fallback: usa manual_video como combinado (formato legado)
        metrics_combined = _calc_metrics(
            df_results, 'manual_video', 'auto_combinado',
            'NÍVEL 3 -- COMBINADO (humano vs. detector vídeo+canal)')

    # 5. Detalhamento das discordâncias por nível
    for level_name, match_col, manual_col, auto_col in [
        ('VÍDEO', 'match_video', 'manual_video', 'auto_video'),
        ('CANAL', 'match_canal', 'manual_canal', 'auto_canal'),
        ('COMBINADO', 'match_combinado', 'manual_combinado', 'auto_combinado'),
    ]:
        if match_col not in df_results.columns:
            continue
        disc = df_results[df_results[match_col] == False]
        if len(disc) > 0:
            print(f"\n--- DISCORDÂNCIAS -- {level_name} ({len(disc)}) ---")
            for _, d in disc.iterrows():
                print(f"  {d['video_id']} ({d['artist_name']})")
                print(
                    f"    Humano: {d[manual_col]}  |  Máquina: {d[auto_col]}")

    # 6. Salva relatório CSV
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df_results.to_csv(output_file, index=False, encoding='utf-8')

    # 7. Salva métricas resumidas (todos os níveis)
    metrics_file = output_file.replace('.csv', '_metrics.json')
    metrics_summary = {
        'video_only': metrics_video,
        'channel_only': metrics_channel,
        'combined': metrics_combined,
    }
    with open(metrics_file, 'w', encoding='utf-8') as f:
        json.dump(metrics_summary, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Relatório salvo em: {output_file}")
    print(f"[OK] Métricas salvas em: {metrics_file}")
    print(f"[OK] {len(df_results)} vídeos validados em 3 níveis")

    return df_results, metrics_summary


if __name__ == "__main__":
    run_cross_validation()

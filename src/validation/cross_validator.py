import os
import pandas as pd
import json
from src.processors.call2go_detector import (
    detect_call2go, detect_call2go_channel, detect_call2go_channel_scraped
)
from src.collectors.channel_link_scraper import load_cached_channel_links


def run_cross_validation(ground_truth_file="data/validation/ground_truth.csv",
                         raw_file="data/raw/youtube_videos_raw.jsonl",
                         output_file="data/validation/cross_validation_report.csv"):
    """
    Validação HUMANO vs. MÁQUINA — Confiabilidade do detector regex.

    Compara a classificação automatizada (call2go_detector) com a anotação
    manual humana (ground truth), gerando métricas de confiabilidade do
    instrumento de medição.

    NOTA: Para a validação cross-platform bidirecional (YouTube ↔ Spotify),
    use cross_platform_validator.py.

    Fluxo:
        1. Lê o ground truth (anotação manual do aluno)
        2. Re-executa o detector automatizado nos mesmos vídeos
        3. Compara resultado humano vs. máquina
        4. Calcula métricas: acurácia, precisão, recall, F1, concordância
        5. Gera relatório detalhado com cada discordância explicada

    Args:
        ground_truth_file: CSV com anotações manuais.
        raw_file: JSONL bruto para re-executar o detector.
        output_file: CSV do relatório de validação cruzada.
    """
    print("=" * 60)
    print("VALIDAÇÃO CRUZADA — HUMANO vs. DETECTOR AUTOMATIZADO")
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

    # 1. Carrega ground truth (classificação humana)
    df_gt = pd.read_csv(ground_truth_file)

    if 'manual_call2go_type' not in df_gt.columns:
        print("[ERRO] Coluna 'manual_call2go_type' não encontrada no ground truth.")
        return None

    # Verifica se foi preenchido
    empty_count = df_gt['manual_call2go_type'].isna(
    ).sum() + (df_gt['manual_call2go_type'] == '').sum()
    if empty_count > 0:
        print(
            f"[AVISO] {empty_count} vídeos sem anotação manual. Serão ignorados.")
        df_gt = df_gt[df_gt['manual_call2go_type'].notna() & (
            df_gt['manual_call2go_type'] != '')]

    gt_ids = set(df_gt['video_id'].values)

    # 2. Carrega dados brutos (descrição + channel_description) e re-executa o detector
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
            "  [AVISO] Links scrapeados não encontrados — detecção de canal será apenas por texto")

    # Verifica se ground truth tem coluna de canal
    has_channel_gt = 'manual_channel_call2go_type' in df_gt.columns

    # 3. Comparação lado a lado (vídeo + canal texto + canal scraped)
    results = []
    for _, row in df_gt.iterrows():
        vid = row['video_id']
        manual_type = row['manual_call2go_type'].strip().lower()

        raw = raw_videos.get(vid, {})
        description = raw.get('description', '')
        channel_desc = raw.get('channel_description', '')
        channel_id = raw.get('channel_id', '')

        # Detector no vídeo
        auto_has_video, auto_type_video = detect_call2go(description)
        # Detector no canal (texto da channel_description)
        auto_has_channel_text, auto_type_channel_text = detect_call2go_channel(
            channel_desc)
        # Detector no canal (links scrapeados do About)
        auto_has_channel_scraped, auto_type_channel_scraped = detect_call2go_channel_scraped(
            channel_id, scraped_data)

        # Canal combinado: scraped prevalece sobre texto
        if auto_has_channel_scraped:
            auto_has_channel = True
            auto_type_channel = auto_type_channel_scraped
        elif auto_has_channel_text:
            auto_has_channel = True
            auto_type_channel = auto_type_channel_text
        else:
            auto_has_channel = False
            auto_type_channel = 'nenhum'

        # Classificação combinada (mesma lógica do call2go_detector.process_videos)
        if auto_has_video:
            auto_combined_type = auto_type_video
            auto_source = 'video'
        elif auto_has_channel:
            auto_combined_type = auto_type_channel
            auto_source = 'canal'
        else:
            auto_combined_type = 'nenhum'
            auto_source = 'nenhum'

        match_combined = (manual_type == auto_combined_type)
        match_video = (manual_type == auto_type_video)

        result = {
            'video_id': vid,
            'artist_name': row['artist_name'],
            'title': row.get('title', ''),
            'manual_call2go_type': manual_type,
            'auto_video_type': auto_type_video,
            'auto_channel_type': auto_type_channel,
            'auto_combined_type': auto_combined_type,
            'auto_source': auto_source,
            'match_video_only': match_video,
            'match_combined': match_combined,
            'description_length': len(description),
        }

        # Validação de canal (se ground truth inclui coluna de canal)
        if has_channel_gt and pd.notna(row.get('manual_channel_call2go_type')):
            manual_channel = str(
                row['manual_channel_call2go_type']).strip().lower()
            if manual_channel:
                result['manual_channel_type'] = manual_channel
                result['match_channel'] = (manual_channel == auto_type_channel)

        results.append(result)

    df_results = pd.DataFrame(results)

    # 4. Métricas de concordância — TRÊS NÍVEIS
    def _calc_metrics(df, manual_col, auto_col, label):
        """Calcula acurácia, precisão, recall, F1 para um par de colunas."""
        valid = df[df[manual_col].notna() & df[auto_col].notna()].copy()
        if len(valid) == 0:
            return None, {}

        total = len(valid)
        matches = (valid[manual_col] == valid[auto_col]).sum()
        accuracy = matches / total if total > 0 else 0

        types = ['link_direto', 'texto_implicito', 'nenhum']
        per_class = {}
        for t in types:
            tp = len(valid[(valid[manual_col] == t) & (valid[auto_col] == t)])
            fp = len(valid[(valid[manual_col] != t) & (valid[auto_col] == t)])
            fn = len(valid[(valid[manual_col] == t) & (valid[auto_col] != t)])
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision +
                                             recall) if (precision + recall) > 0 else 0
            per_class[t] = {
                'true_positives': tp, 'false_positives': fp, 'false_negatives': fn,
                'precision': precision, 'recall': recall, 'f1_score': f1
            }

        print(f"\n{'=' * 50}")
        print(f"  {label}")
        print(f"{'=' * 50}")
        print(f"  Total validados: {total}")
        print(f"  Concordâncias: {matches}")
        print(f"  Discordâncias: {total - matches}")
        print(f"  ACURÁCIA: {accuracy:.1%}")
        for t, m in per_class.items():
            print(f"    [{t}] P={m['precision']:.1%} R={m['recall']:.1%} F1={m['f1_score']:.1%} (TP={m['true_positives']} FP={m['false_positives']} FN={m['false_negatives']})")

        return {
            'total_validated': total,
            'matches': int(matches),
            'discordances': int(total - matches),
            'accuracy': round(accuracy, 4),
            'per_class': {k: {mk: round(mv, 4) if isinstance(mv, float) else mv
                              for mk, mv in v.items()} for k, v in per_class.items()}
        }, per_class

    # Nível 1: Somente vídeo (humano vs. detector no vídeo)
    metrics_video, _ = _calc_metrics(
        df_results, 'manual_call2go_type', 'auto_video_type',
        'NÍVEL 1 — VÍDEO APENAS (humano vs. regex no vídeo)')

    # Nível 2: Combinado (humano vs. detector vídeo+canal)
    metrics_combined, _ = _calc_metrics(
        df_results, 'manual_call2go_type', 'auto_combined_type',
        'NÍVEL 2 — COMBINADO (humano vs. regex vídeo+canal)')

    # Nível 3: Canal isolado (se ground truth tem coluna de canal)
    metrics_channel = None
    if 'manual_channel_type' in df_results.columns:
        df_channel = df_results[df_results['manual_channel_type'].notna()]
        if len(df_channel) > 0:
            metrics_channel, _ = _calc_metrics(
                df_channel, 'manual_channel_type', 'auto_channel_type',
                'NÍVEL 3 — CANAL ISOLADO (humano vs. regex no perfil do canal)')

    # Detalhamento das discordâncias (nível combinado)
    discordances = df_results[~df_results['match_combined']]
    if len(discordances) > 0:
        print(
            f"\n--- DISCORDÂNCIAS DETALHADAS — NÍVEL COMBINADO ({len(discordances)}) ---")
        for _, d in discordances.iterrows():
            print(f"  Video: {d['video_id']} ({d['artist_name']})")
            print(
                f"    Humano: {d['manual_call2go_type']}  |  Máquina: {d['auto_combined_type']} (fonte: {d['auto_source']})")
            print(
                f"    Vídeo={d['auto_video_type']}  Canal={d['auto_channel_type']}")

    # Salva relatório
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df_results.to_csv(output_file, index=False, encoding='utf-8')

    # Salva métricas resumidas (todos os níveis)
    metrics_file = output_file.replace('.csv', '_metrics.json')
    import json as json_lib
    metrics_summary = {
        'video_only': metrics_video,
        'combined': metrics_combined,
        'channel_only': metrics_channel,
    }
    with open(metrics_file, 'w', encoding='utf-8') as f:
        json_lib.dump(metrics_summary, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Relatório salvo em: {output_file}")
    print(f"✅ Métricas salvas em: {metrics_file}")

    return df_results, metrics_summary


if __name__ == "__main__":
    run_cross_validation()

import os
import pandas as pd
import json
from src.processors.call2go_detector import detect_call2go


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

    # 2. Carrega descrições brutas e re-executa o detector
    descriptions = {}
    with open(raw_file, 'r', encoding='utf-8') as f:
        for line in f:
            video = json.loads(line)
            vid = video.get('video_id')
            if vid in gt_ids:
                descriptions[vid] = video.get('description', '')

    # 3. Comparação lado a lado
    results = []
    for _, row in df_gt.iterrows():
        vid = row['video_id']
        manual_type = row['manual_call2go_type'].strip().lower()

        description = descriptions.get(vid, '')
        auto_has, auto_type = detect_call2go(description)

        match = (manual_type == auto_type)

        results.append({
            'video_id': vid,
            'artist_name': row['artist_name'],
            'title': row.get('title', ''),
            'manual_call2go_type': manual_type,
            'auto_call2go_type': auto_type,
            'match': match,
            'description_length': len(description),
        })

    df_results = pd.DataFrame(results)

    # 4. Métricas de concordância
    total = len(df_results)
    matches = df_results['match'].sum()
    accuracy = matches / total if total > 0 else 0

    # Métricas por classe
    types = ['link_direto', 'texto_implicito', 'nenhum']
    metrics_per_class = {}

    for t in types:
        tp = len(df_results[(df_results['manual_call2go_type'] == t) & (
            df_results['auto_call2go_type'] == t)])
        fp = len(df_results[(df_results['manual_call2go_type'] != t) & (
            df_results['auto_call2go_type'] == t)])
        fn = len(df_results[(df_results['manual_call2go_type'] == t) & (
            df_results['auto_call2go_type'] != t)])

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision +
                                         recall) if (precision + recall) > 0 else 0

        metrics_per_class[t] = {
            'true_positives': tp,
            'false_positives': fp,
            'false_negatives': fn,
            'precision': precision,
            'recall': recall,
            'f1_score': f1
        }

    # 5. Relatório
    print(f"\n--- RESULTADO DA VALIDAÇÃO CRUZADA ---")
    print(f"Total de vídeos validados: {total}")
    print(f"Concordâncias (humano = máquina): {matches}")
    print(f"Discordâncias: {total - matches}")
    print(f"ACURÁCIA GLOBAL: {accuracy:.1%}")

    print(f"\n--- MÉTRICAS POR CLASSE ---")
    for t, m in metrics_per_class.items():
        print(f"\n  [{t}]")
        print(
            f"    Precisão: {m['precision']:.1%}  |  Recall: {m['recall']:.1%}  |  F1: {m['f1_score']:.1%}")
        print(
            f"    TP={m['true_positives']}  FP={m['false_positives']}  FN={m['false_negatives']}")

    # Detalhamento das discordâncias
    discordances = df_results[~df_results['match']]
    if len(discordances) > 0:
        print(f"\n--- DISCORDÂNCIAS DETALHADAS ({len(discordances)}) ---")
        for _, d in discordances.iterrows():
            print(f"  Video: {d['video_id']} ({d['artist_name']})")
            print(
                f"    Humano: {d['manual_call2go_type']}  |  Máquina: {d['auto_call2go_type']}")

    # Salva relatório
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df_results.to_csv(output_file, index=False, encoding='utf-8')

    # Salva métricas resumidas
    metrics_file = output_file.replace('.csv', '_metrics.json')
    import json as json_lib
    metrics_summary = {
        'total_validated': total,
        'matches': int(matches),
        'discordances': int(total - matches),
        'accuracy': round(accuracy, 4),
        'per_class': {k: {mk: round(mv, 4) if isinstance(mv, float) else mv
                          for mk, mv in v.items()}
                      for k, v in metrics_per_class.items()}
    }
    with open(metrics_file, 'w', encoding='utf-8') as f:
        json_lib.dump(metrics_summary, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Relatório salvo em: {output_file}")
    print(f"✅ Métricas salvas em: {metrics_file}")

    return df_results, metrics_summary


if __name__ == "__main__":
    run_cross_validation()

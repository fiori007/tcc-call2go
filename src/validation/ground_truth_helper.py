import os
import json
import re
import pandas as pd
from src.processors.call2go_detector import detect_call2go, detect_call2go_channel


def _find_spotify_evidence(text):
    """
    Busca evidências de menção ao Spotify no texto.
    Retorna uma lista de trechos encontrados (para auditoria humana).
    """
    if not isinstance(text, str) or not text.strip():
        return []

    evidence = []
    text_lower = text.lower()

    # Links diretos
    for match in re.finditer(
        r'(https?://(?:open\.spotify\.com|spoti\.fi|sptfy\.com)[^\s]+)', text_lower
    ):
        evidence.append(f"LINK: {match.group(0)[:80]}")

    # Padrões textuais
    text_patterns = [
        (r'ou[çc]a no spotify', 'ouça no spotify'),
        (r'dispon[ií]vel no spotify', 'disponível no spotify'),
        (r'stream.*spotify', 'stream...spotify'),
        (r'ouvir.*spotify', 'ouvir...spotify'),
        (r'\bspotify\b', 'menção "spotify"'),
    ]
    for pattern, label in text_patterns:
        m = re.search(pattern, text_lower)
        if m:
            start = max(0, m.start() - 20)
            end = min(len(text), m.end() + 20)
            context = text[start:end].replace('\n', ' ').strip()
            evidence.append(f"TEXTO ({label}): ...{context}...")

    return evidence


def prefill_ground_truth(sample_file="data/validation/manual_sample.csv",
                         raw_file="data/raw/youtube_videos_raw.jsonl",
                         output_file="data/validation/ground_truth_prefilled.csv"):
    """
    Pré-preenche o ground truth automaticamente para revisão humana.

    Cruza a amostra de validação com os dados brutos (descrição completa +
    channel_description) e aplica o detector regex para sugerir a classificação.

    O aluno deve revisar o CSV gerado, corrigir classificações incorretas
    (especialmente as de baixa confiança), e salvar como ground_truth.csv.

    Fluxo:
        1. Lê a amostra (manual_sample.csv)
        2. Carrega dados brutos para descrição completa + channel_description
        3. Aplica detector regex no vídeo e no canal
        4. Busca evidências textuais (trechos com Spotify)
        5. Calcula nível de confiança da classificação
        6. Salva CSV pré-preenchido para revisão humana
    """
    print("=" * 60)
    print("PRÉ-ANOTAÇÃO AUTOMÁTICA DO GROUND TRUTH")
    print("(Semi-automático — revisão humana obrigatória)")
    print("=" * 60)

    if not os.path.exists(sample_file):
        print(f"[ERRO] Amostra não encontrada: {sample_file}")
        print("Execute primeiro: python -m src.validation.sample_generator")
        return None

    if not os.path.exists(raw_file):
        print(f"[ERRO] Dados brutos não encontrados: {raw_file}")
        return None

    # 1. Lê a amostra
    df_sample = pd.read_csv(sample_file)
    sample_ids = set(df_sample['video_id'].values)

    # 2. Carrega dados brutos completos para os vídeos da amostra
    raw_data = {}
    with open(raw_file, 'r', encoding='utf-8') as f:
        for line in f:
            video = json.loads(line)
            vid = video.get('video_id')
            if vid in sample_ids:
                raw_data[vid] = video

    # 3. Pré-preenche cada vídeo
    rows = []
    stats = {'link_direto': 0, 'texto_implicito': 0, 'nenhum': 0,
             'high_confidence': 0, 'low_confidence': 0}

    for _, sample_row in df_sample.iterrows():
        vid = sample_row['video_id']
        raw = raw_data.get(vid, {})

        description = raw.get('description', '')
        channel_desc = raw.get('channel_description', '')

        # Aplica detector no vídeo
        video_has, video_type = detect_call2go(description)
        # Aplica detector no canal
        channel_has, channel_type = detect_call2go_channel(channel_desc)

        # Classificação combinada (mesma lógica do call2go_detector.py)
        if video_has:
            suggested_type = video_type
            source = 'video'
        elif channel_has:
            suggested_type = channel_type
            source = 'canal'
        else:
            suggested_type = 'nenhum'
            source = 'nenhum'

        # Busca evidências textuais para auditoria
        video_evidence = _find_spotify_evidence(description)
        channel_evidence = _find_spotify_evidence(channel_desc)
        all_evidence = video_evidence + [f"[CANAL] {e}" for e in channel_evidence]

        # Calcula confiança
        # Alta confiança: descrição vazia + canal sem Spotify → claramente nenhum
        # Alta confiança: link explícito encontrado → claramente link_direto
        # Baixa confiança: texto implícito (pode ter falsos positivos do fallback \bspotify\b)
        # Baixa confiança: canal tem mas vídeo não → depende de contexto
        if not description.strip() and not channel_has:
            confidence = 'ALTA'
        elif video_type == 'link_direto':
            confidence = 'ALTA'
        elif suggested_type == 'nenhum' and not all_evidence:
            confidence = 'ALTA'
        elif source == 'canal' and not video_has:
            confidence = 'MEDIA'
        elif video_type == 'texto_implicito':
            confidence = 'MEDIA'
        else:
            confidence = 'BAIXA'

        # has_spotify_link: sim se há link do Spotify em qualquer evidência
        has_link = 'sim' if any('LINK:' in e for e in all_evidence) else 'nao'
        # has_spotify_text: sim se há menção textual ao Spotify
        has_text = 'sim' if any('TEXTO' in e for e in all_evidence) else 'nao'

        stats[suggested_type] += 1
        if confidence == 'ALTA':
            stats['high_confidence'] += 1
        else:
            stats['low_confidence'] += 1

        rows.append({
            'video_id': vid,
            'artist_name': sample_row['artist_name'],
            'title': sample_row.get('title', ''),
            'description_preview': description[:300] if description else '',
            'full_description_length': len(description),
            'channel_description_preview': channel_desc[:300] if channel_desc else '',
            'has_spotify_link': has_link,
            'has_spotify_text': has_text,
            'manual_call2go_type': suggested_type,
            'manual_channel_call2go_type': channel_type,
            'call2go_source': source,
            'confidence': confidence,
            'evidence': ' | '.join(all_evidence) if all_evidence else '',
            'notes': '',
        })

    df_result = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df_result.to_csv(output_file, index=False, encoding='utf-8')

    # Resumo
    total = len(df_result)
    print(f"\n✅ Ground truth pré-preenchido: {total} vídeos")
    print(f"✅ Arquivo salvo em: {output_file}")

    print(f"\n--- DISTRIBUIÇÃO SUGERIDA ---")
    print(f"  link_direto:      {stats['link_direto']}")
    print(f"  texto_implicito:  {stats['texto_implicito']}")
    print(f"  nenhum:           {stats['nenhum']}")

    print(f"\n--- CONFIANÇA DA PRÉ-ANOTAÇÃO ---")
    print(f"  Alta confiança:   {stats['high_confidence']} (provavelmente correto)")
    print(f"  Média/Baixa:      {stats['low_confidence']} (REVISAR com atenção)")

    low_conf = df_result[df_result['confidence'] != 'ALTA']
    if len(low_conf) > 0:
        print(f"\n--- VÍDEOS QUE PRECISAM DE REVISÃO ({len(low_conf)}) ---")
        for _, row in low_conf.iterrows():
            print(f"  🔍 {row['video_id']} ({row['artist_name']})")
            print(f"     Sugestão: {row['manual_call2go_type']} (fonte: {row['call2go_source']})")
            if row['evidence']:
                print(f"     Evidência: {row['evidence'][:120]}")

    print(f"\n{'=' * 60}")
    print(f"🔴 AÇÃO NECESSÁRIA DO ALUNO:")
    print(f"   1. Abra: {output_file}")
    print(f"   2. Revise as classificações (especialmente confiança MEDIA/BAIXA)")
    print(f"   3. Corrija 'manual_call2go_type' e 'manual_channel_call2go_type' se necessário")
    print(f"   4. Salve como: data/validation/ground_truth.csv")
    print(f"{'=' * 60}")

    return df_result


if __name__ == "__main__":
    prefill_ground_truth()

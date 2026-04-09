"""
Gerador de amostra estratificada adversarial para validação do detector Call2Go.

Diferente do sample_generator.py (amostra aleatória simples), este módulo
garante representação de TODOS os estratos relevantes, incluindo edge cases
que a amostra original de 50 vídeos não cobriu:

  - Vídeos com detecção apenas no vídeo (raro: ~15/980)
  - Vídeos auto-gerados (OAC / Content ID)
  - Vídeos sem descrição ou com descrição muito curta
  - Vídeos com menção narrativa ao Spotify (não deveria ser Call2Go)
  - Vídeos com "spotify" no fallback (potencial falso positivo)

A amostra gerada é para uso com blind_annotator.py -- o anotador humano
recebe apenas os dados brutos, sem sugestões do detector.
"""

import os
import json
import random
import pandas as pd
from src.processors.call2go_detector import (
    detect_call2go, detect_call2go_channel_scraped,
    is_auto_generated, _is_narrative_mention
)
from src.collectors.channel_link_scraper import load_cached_channel_links


# ── Configuração dos estratos ────────────────────────────────
STRATA_CONFIG = {
    # stratum_name: (target_n, description)
    'video_link_direto':    (15, 'Vídeo detectou link_direto (sem canal)'),
    'ambos_link_direto':    (10, 'Vídeo + canal ambos com link_direto'),
    'canal_only':           (20, 'Apenas canal scraped detectou link_direto'),
    'nenhum_limpo':         (15, 'Nenhuma detecção, sem menção ao Spotify'),
    'auto_generated':       (10, 'Vídeos auto-gerados (OAC / Content ID)'),
    'narrativa_spotify':    (5,  'Menciona Spotify mas é narrativa (charts, ranking)'),
    'fallback_spotify':     (5,  'Fallback: "spotify" isolado sem link/CTA'),
    'desc_vazia':           (10, 'Descrição vazia ou None'),
    'desc_curta':           (10, 'Descrição curta (<50 caracteres)'),
}


def _classify_video(video, scraped_data):
    """
    Classifica um vídeo nos possíveis estratos para amostragem.

    Retorna uma lista de estratos aos quais o vídeo pertence
    (um vídeo pode pertencer a mais de um estrato).
    """
    desc = video.get('description', '') or ''
    channel_id = video.get('channel_id', '')

    # Detecção no vídeo
    v_has, v_type = detect_call2go(desc)
    # Detecção no canal (scraped)
    c_has, c_type = detect_call2go_channel_scraped(channel_id, scraped_data)

    strata = []

    # Auto-gerado
    if is_auto_generated(desc):
        strata.append('auto_generated')

    # Descrição vazia
    if len(desc.strip()) == 0:
        strata.append('desc_vazia')
    elif len(desc.strip()) < 50:
        strata.append('desc_curta')

    # Classificação por detecção
    if v_has and c_has:
        strata.append('ambos_link_direto')
    elif v_has and not c_has:
        strata.append('video_link_direto')
    elif not v_has and c_has:
        strata.append('canal_only')
    else:
        # Nenhuma detecção -- verificar se tem menção narrativa
        text_lower = desc.lower()
        if 'spotify' in text_lower:
            if _is_narrative_mention(text_lower):
                strata.append('narrativa_spotify')
            else:
                # Não deveria acontecer (fallback deveria pegar),
                # mas inclui por segurança
                strata.append('fallback_spotify')
        else:
            strata.append('nenhum_limpo')

    # Fallback: vídeos onde o detector usa padrão fallback (\bspotify\b)
    # Detectar se o match é pelo fallback e não por link/CTA explícito
    if v_has and v_type == 'texto_implicito':
        import re
        text_lower = desc.lower()
        # Verifica se algum padrão explícito (ouça, disponível, stream, ouvir) deu match
        explicit = any(re.search(p, text_lower) for p in [
            r'ou[çc]a\b.{0,50}\bspotify',
            r'dispon[ií]vel\b.{0,30}\bspotify',
            r'\bstream\b.{0,50}\bspotify',
            r'\bouvir\b.{0,50}\bspotify',
        ])
        if not explicit:
            strata.append('fallback_spotify')

    return strata


def generate_adversarial_sample(
    raw_file="data/raw/youtube_videos_raw.jsonl",
    output_file="data/validation/adversarial_sample.csv",
    seed=2024
):
    """
    Gera amostra estratificada adversarial para validação cega.

    Garante representação mínima de cada estrato definido em STRATA_CONFIG.
    Vídeos podem pertencer a múltiplos estratos; cada vídeo aparece no máximo uma vez.

    Args:
        raw_file: Caminho do JSONL bruto do YouTube.
        output_file: Caminho do CSV de saída.
        seed: Seed para reprodutibilidade.

    Returns:
        pd.DataFrame com a amostra gerada.
    """
    print("=" * 60)
    print("GERAÇÃO DE AMOSTRA ADVERSARIAL ESTRATIFICADA")
    print("=" * 60)

    if not os.path.exists(raw_file):
        print(f"[ERRO] Arquivo não encontrado: {raw_file}")
        return None

    # Carrega todos os vídeos
    videos = []
    with open(raw_file, 'r', encoding='utf-8') as f:
        for line in f:
            videos.append(json.loads(line))

    print(f"  Total de vídeos no dataset: {len(videos)}")

    # Carrega dados scrapeados
    scraped_data = load_cached_channel_links()
    if scraped_data:
        print(f"  Links scrapeados: {len(scraped_data)} canais")
    else:
        print("  [AVISO] Links scrapeados não encontrados.")

    # Classifica cada vídeo nos estratos
    strata_buckets = {name: [] for name in STRATA_CONFIG}
    for video in videos:
        belonging = _classify_video(video, scraped_data)
        for stratum in belonging:
            if stratum in strata_buckets:
                strata_buckets[stratum].append(video)

    # Mostra distribuição
    print(f"\n  {'Estrato':<25} {'Disponível':>10} {'Alvo':>6}")
    print("  " + "-" * 45)
    for name, (target, desc) in STRATA_CONFIG.items():
        avail = len(strata_buckets[name])
        print(f"  {name:<25} {avail:>10} {target:>6}")

    # Amostragem estratificada
    random.seed(seed)
    selected_ids = set()
    selected_videos = []

    # Prioridade: estratos raros primeiro (para garantir representação)
    sorted_strata = sorted(
        STRATA_CONFIG.items(),
        key=lambda x: len(strata_buckets[x[0]])  # menos disponíveis primeiro
    )

    for name, (target, desc) in sorted_strata:
        bucket = strata_buckets[name]
        # Filtra vídeos já selecionados
        available = [v for v in bucket if v['video_id'] not in selected_ids]
        actual = min(target, len(available))

        if actual < target:
            print(
                f"  [AVISO] Estrato '{name}': {actual}/{target} disponíveis (esgotado)")

        chosen = random.sample(available, actual)
        for v in chosen:
            selected_ids.add(v['video_id'])
            selected_videos.append((v, name))

    # Shuffle final para não revelar estratos na ordem
    random.shuffle(selected_videos)

    # Monta DataFrame -- apenas dados necessários para anotação
    rows = []
    for video, primary_stratum in selected_videos:
        desc = video.get('description', '') or ''
        channel_desc = video.get('channel_description', '') or ''
        rows.append({
            'video_id': video.get('video_id'),
            'artist_name': video.get('artist_name'),
            'title': video.get('title'),
            'description_length': len(desc),
            # Coluna interna (não visível no blind CSV)
            '_stratum': primary_stratum,
        })

    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8')

    total = len(df)
    print(f"\n  Amostra gerada: {total} vídeos")
    print(f"  Distribuição por estrato:")
    for name in STRATA_CONFIG:
        count = len(df[df['_stratum'] == name])
        if count > 0:
            print(f"    {name}: {count}")

    print(f"\n  Arquivo: {output_file}")
    print(f"  Seed: {seed}")
    print(f"\n  Próximo passo: python -m src.validation.blind_annotator")
    return df


if __name__ == "__main__":
    generate_adversarial_sample()

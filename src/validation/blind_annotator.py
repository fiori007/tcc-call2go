"""
Gerador de CSV cego para anotacao humana independente.

Recebe a amostra adversarial (ou qualquer amostra) e gera um CSV
com APENAS os dados brutos -- descricao do video, bio completa do canal
(descricao + links da aba Sobre), titulo, URLs -- sem nenhuma sugestao,
evidencia ou pre-anotacao do detector.

Isso elimina o vies de confirmacao: o anotador humano nao sabe o que
a maquina classificou e precisa ler cada descricao manualmente.

Fluxo de uso:
    1. python run_pipeline.py                          (gera censo completo)
    2. Aluno abre o XLSX e anota manualmente cada video
    3. Salva como data/validation/ground_truth.csv
    4. python -m src.validation.cross_validator        (calcula metricas)
"""

import os
import json
import pandas as pd


def _build_channel_bio(channel_desc, channel_id, artist_name, scraped_data):
    """
    Compoe a bio completa do canal: descricao textual + links da aba Sobre.

    Args:
        channel_desc: Texto da descricao do canal (vindo do JSONL/YouTube API).
        channel_id: ID do canal YouTube para buscar no scraped_data.
        artist_name: Nome do artista (fallback se channel_id nao encontrado).
        scraped_data: Dict {channel_id: {links, official_links, ...}} do scraper.

    Returns:
        String com a bio completa formatada.
    """
    parts = []

    # Parte 1: descricao textual do canal
    desc_text = (channel_desc or '').strip()
    if desc_text:
        parts.append(desc_text)

    # Parte 2: links scrapeados da aba Sobre
    # Busca por channel_id primeiro, fallback por artist_name (mismatch Fase 6)
    channel_info = scraped_data.get(channel_id, {})
    if not channel_info and artist_name:
        for _cid, _info in scraped_data.items():
            if _info.get('artist_name', '').lower() == artist_name.lower():
                channel_info = _info
                break

    links = channel_info.get('links', [])
    official_links = channel_info.get('official_links', [])

    all_links = []
    if links:
        for link in links:
            all_links.append(link)
    if official_links:
        for link in official_links:
            all_links.append(f"[Canal Oficial] {link}")

    if all_links:
        parts.append("---LINKS---")
        parts.extend(all_links)
    elif not channel_info:
        # Canal nao encontrado no scraped data
        parts.append("[links nao disponiveis - canal ausente no scraping]")

    return '\n'.join(parts) if parts else ''


def generate_blind_csv(
    sample_file="data/validation/adversarial_sample.csv",
    raw_file="data/raw/youtube_videos_raw.jsonl",
    scraped_file="data/raw/channel_links_scraped.json",
    output_file="data/validation/blind_annotation.csv"
):
    """
    Gera CSV cego para anotacao humana -- sem output do detector.

    Inclui a descricao completa do video, a bio completa do canal
    (descricao + links da aba Sobre scrapeados) e URLs do video e canal
    para que o anotador possa avaliar corretamente.

    Args:
        sample_file: CSV com video_ids da amostra (adversarial ou outra).
        raw_file: JSONL bruto do YouTube para obter descricoes completas.
        scraped_file: JSON com links scrapeados da aba Sobre dos canais.
        output_file: CSV de saida para anotacao humana cega.

    Returns:
        pd.DataFrame com o CSV gerado, ou None em caso de erro.
    """
    print("=" * 60)
    print("GERADOR DE CSV CEGO PARA ANOTACAO HUMANA")
    print("=" * 60)

    if not os.path.exists(sample_file):
        print(f"[ERRO] Amostra nao encontrada: {sample_file}")
        print("Execute primeiro: python run_pipeline.py")
        return None

    if not os.path.exists(raw_file):
        print(f"[ERRO] Dados brutos nao encontrados: {raw_file}")
        return None

    # 1. Carrega IDs da amostra
    df_sample = pd.read_csv(sample_file)
    sample_ids = set(df_sample['video_id'].values)
    print(f"  Videos na amostra: {len(sample_ids)}")

    # 2. Carrega dados brutos completos
    raw_data = {}
    with open(raw_file, 'r', encoding='utf-8') as f:
        for line in f:
            video = json.loads(line)
            vid = video.get('video_id')
            if vid in sample_ids:
                raw_data[vid] = video

    found = len(raw_data)
    if found < len(sample_ids):
        missing = len(sample_ids) - found
        print(
            f"  [AVISO] {missing} videos da amostra nao encontrados no JSONL")

    # 3. Carrega links scrapeados da aba Sobre dos canais
    scraped_data = {}
    if os.path.exists(scraped_file):
        with open(scraped_file, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)
        print(f"  Canais scrapeados carregados: {len(scraped_data)}")
    else:
        print(f"  [AVISO] Scraped data nao encontrado: {scraped_file}")
        print("  A coluna channel_bio tera apenas a descricao da API (sem links).")

    # 4. Monta CSV cego -- ordem por artista + titulo
    rows = []
    for _, sample_row in df_sample.iterrows():
        vid = sample_row['video_id']
        raw = raw_data.get(vid, {})

        description = raw.get('description', '') or ''
        channel_desc = raw.get('channel_description', '') or ''
        channel_id = raw.get('channel_id', '') or ''

        # Bio completa = descricao + links da aba Sobre
        artist_name = sample_row.get('artist_name', '') or ''
        channel_bio = _build_channel_bio(
            channel_desc, channel_id, artist_name, scraped_data
        )

        rows.append({
            # Identificacao
            'video_id': vid,
            'artist_name': artist_name,
            'title': sample_row.get('title', ''),
            'youtube_url': f'https://www.youtube.com/watch?v={vid}',
            'youtube_channel_url': f'https://www.youtube.com/channel/{channel_id}' if channel_id else '',

            # Dados brutos para analise humana
            'description': description,
            'channel_bio': channel_bio,

            # Colunas para preenchimento humano
            'manual_call2go_video': '',       # link_direto / texto_implicito / nenhum
            'manual_call2go_canal': '',       # link_direto / texto_implicito / nenhum
            'manual_call2go_combinado': '',   # link_direto / texto_implicito / nenhum
            'confianca': '',                  # alta / media / baixa
        })

    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8')

    print(f"\n  CSV cego gerado: {output_file}")
    print(f"  Total de videos: {len(df)}")
    print(f"\n  --- INSTRUCOES PARA O ANOTADOR ---")
    print("  1. Abra o arquivo CSV (blind_annotation.csv) ou XLSX (blind_annotation.xlsx)")
    print("  2. Para CADA video, leia as colunas 'description' e 'channel_bio'")
    print("     - channel_bio inclui descricao do canal + links da aba Sobre")
    print("     - Links apos '---LINKS---' sao os links reais da aba Sobre do YouTube")
    print(
        "     - Links com '[Canal Oficial]' vem do canal oficial (para artistas com OAC)")
    print("  3. Se necessario, abra 'youtube_url' (video) ou 'youtube_channel_url' (canal)")
    print("  4. Preencha as colunas:")
    print("     - manual_call2go_video: classificacao da DESCRICAO DO VIDEO")
    print("       -> 'link_direto'      : contem link do Spotify (open.spotify.com, spoti.fi, etc.)")
    print("       -> 'texto_implicito'  : menciona Spotify como CTA ('ouca no Spotify')")
    print("       -> 'nenhum'           : nao tem Call2Go na descricao do video")
    print("     - manual_call2go_canal: classificacao da BIO DO CANAL (descricao + links)")
    print("       -> mesmas opcoes acima, aplicadas a bio completa do canal")
    print("     - manual_call2go_combinado: classificacao FINAL do video")
    print("       -> se video E canal tem Call2Go, o combinado tambem tem")
    print("       -> tipo prevalece: link_direto > texto_implicito > nenhum")
    print("     - confianca: 'alta', 'media', ou 'baixa'")
    print("  5. Salve como: data/validation/ground_truth.csv")
    print("  6. Execute: python -m src.validation.cross_validator")

    return df


def generate_census_csv(
    raw_file="data/raw/youtube_videos_raw.jsonl",
    scraped_file="data/raw/channel_links_scraped.json",
    output_file="data/validation/blind_annotation_census.csv"
):
    """
    Gera CSV cego com TODOS os videos do JSONL para anotacao humana censitaria.

    Diferente de generate_blind_csv() que filtra por amostra, este funcao
    inclui todos os videos coletados -- permitindo validacao censitaria
    completa do detector.

    Args:
        raw_file: JSONL bruto do YouTube com todos os videos.
        scraped_file: JSON com links scrapeados da aba Sobre dos canais.
        output_file: CSV de saida para anotacao humana cega (todos os videos).

    Returns:
        pd.DataFrame com o CSV gerado, ou None em caso de erro.
    """
    print("=" * 60)
    print("GERADOR DE CSV CEGO -- CENSO COMPLETO (TODOS OS VIDEOS)")
    print("=" * 60)

    if not os.path.exists(raw_file):
        print(f"[ERRO] Dados brutos nao encontrados: {raw_file}")
        return None

    # 1. Carrega TODOS os videos do JSONL
    all_videos = []
    with open(raw_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                all_videos.append(json.loads(line))
    print(f"  Videos carregados do JSONL: {len(all_videos)}")

    # 2. Carrega links scrapeados da aba Sobre dos canais
    scraped_data = {}
    if os.path.exists(scraped_file):
        with open(scraped_file, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)
        print(f"  Canais scrapeados carregados: {len(scraped_data)}")
    else:
        print(f"  [AVISO] Scraped data nao encontrado: {scraped_file}")
        print("  A coluna channel_bio tera apenas a descricao da API (sem links).")

    # 3. Monta CSV cego com todos os videos
    rows = []
    for video in all_videos:
        vid = video.get('video_id', '')
        artist_name = video.get('artist_name', '')
        title = video.get('title', '')
        description = video.get('description', '') or ''
        channel_desc = video.get('channel_description', '') or ''
        channel_id = video.get('channel_id', '') or ''

        # Bio completa = descricao + links da aba Sobre
        channel_bio = _build_channel_bio(
            channel_desc, channel_id, artist_name, scraped_data
        )

        rows.append({
            'video_id': vid,
            'artist_name': artist_name,
            'title': title,
            'youtube_url': f'https://www.youtube.com/watch?v={vid}',
            'youtube_channel_url': f'https://www.youtube.com/channel/{channel_id}' if channel_id else '',
            'description': description,
            'channel_bio': channel_bio,
            # Colunas para preenchimento humano (SIM / NAO)
            'manual_call2go_video': '',
            'manual_call2go_canal': '',
            'manual_call2go_combinado': '',
            'confianca': '',
        })

    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8')

    print(f"\n  CSV censo gerado: {output_file}")
    print(f"  Total de videos: {len(df)}")
    artistas_unicos = df['artist_name'].nunique()
    print(f"  Artistas unicos: {artistas_unicos}")
    print(f"\n  --- INSTRUCOES PARA O ANOTADOR ---")
    print("  1. Abra o arquivo XLSX (blind_annotation_census.xlsx)")
    print("  2. Para CADA video, leia as colunas 'description' e 'channel_bio'")
    print("  3. Preencha as colunas com SIM ou NAO:")
    print("     - manual_call2go_video: a DESCRICAO DO VIDEO contem Call2Go?")
    print("       -> SIM = contem link Spotify ou mencao tipo CTA")
    print("       -> NAO = nao tem Call2Go na descricao")
    print("     - manual_call2go_canal: a BIO DO CANAL contem Call2Go?")
    print("       -> mesma logica, aplicada a bio do canal")
    print("     - manual_call2go_combinado: AMBAS as fontes tem Call2Go?")
    print("       -> SIM se video E canal = SIM")
    print("     - confianca: 'alta', 'media', ou 'baixa'")
    print("  4. Salve como: data/validation/ground_truth.csv")
    print("  5. Execute: python -m src.validation.cross_validator")

    return df


def generate_detector_answers(
    raw_file="data/raw/youtube_videos_raw.jsonl",
    scraped_file="data/raw/channel_links_scraped.json",
    output_file="data/validation/detector_answers_census.csv"
):
    """
    Gera CSV com as respostas do detector regex para TODOS os videos.

    Usa as mesmas funcoes do detector (detect_call2go,
    detect_call2go_channel_scraped) para classificar cada video
    automaticamente, servindo como referencia/regressao para comparar
    com a anotacao humana.

    Args:
        raw_file: JSONL bruto do YouTube com todos os videos.
        scraped_file: JSON com links scrapeados da aba Sobre dos canais.
        output_file: CSV de saida com respostas do detector.

    Returns:
        pd.DataFrame com o CSV gerado, ou None em caso de erro.
    """
    from src.processors.call2go_detector import (
        detect_call2go, detect_call2go_channel, detect_call2go_channel_scraped
    )
    from src.collectors.channel_link_scraper import load_cached_channel_links

    print("=" * 60)
    print("RESPOSTAS DO DETECTOR -- CENSO COMPLETO (TODOS OS VIDEOS)")
    print("=" * 60)

    if not os.path.exists(raw_file):
        print(f"[ERRO] Dados brutos nao encontrados: {raw_file}")
        return None

    # 1. Carrega TODOS os videos do JSONL
    all_videos = []
    with open(raw_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                all_videos.append(json.loads(line))
    print(f"  Videos carregados do JSONL: {len(all_videos)}")

    # 2. Carrega links scrapeados da aba Sobre dos canais
    scraped_data = load_cached_channel_links(scraped_file)
    print(f"  Canais scrapeados carregados: {len(scraped_data)}")

    # 3. Carrega scraped_data original para _build_channel_bio
    scraped_data_bio = {}
    if os.path.exists(scraped_file):
        with open(scraped_file, 'r', encoding='utf-8') as f:
            scraped_data_bio = json.load(f)

    # 3b. Carrega mapeamento artist_name -> seed channel_id (normalizacao)
    seed_channels = {}
    seed_file = "data/seed/artistas.csv"
    if os.path.exists(seed_file):
        import pandas as _pd_seed
        df_seed = _pd_seed.read_csv(seed_file)
        if 'youtube_channel_id' in df_seed.columns:
            seed_channels = dict(
                zip(df_seed['artist_name'], df_seed['youtube_channel_id']))
    print(f"  Seed channels carregados: {len(seed_channels)} artistas")

    # 4. Executa detector para cada video e preenche respostas
    rows = []
    count_video_sim = 0
    count_canal_sim = 0
    count_combinado_sim = 0

    for video in all_videos:
        vid = video.get('video_id', '')
        artist_name = video.get('artist_name', '')
        title = video.get('title', '')
        description = video.get('description', '') or ''
        channel_desc = video.get('channel_description', '') or ''
        channel_id = video.get('channel_id', '') or ''

        # Bio completa para contexto visual
        channel_bio = _build_channel_bio(
            channel_desc, channel_id, artist_name, scraped_data_bio
        )

        # Detector: nivel video
        has_video, _ = detect_call2go(description)
        # Detector: nivel canal (links scrapeados)
        # Prioridade: canal oficial do seed, fallback pelo channel_id do JSONL
        seed_ch = seed_channels.get(artist_name, '')
        if seed_ch:
            has_channel, _ = detect_call2go_channel_scraped(
                seed_ch, scraped_data
            )
        else:
            has_channel, _ = detect_call2go_channel_scraped(
                channel_id, scraped_data
            )
        # Fallback: tenta channel_id do JSONL se diferente do seed
        if not has_channel and channel_id and channel_id != seed_ch:
            has_channel, _ = detect_call2go_channel_scraped(
                channel_id, scraped_data
            )
        # Fallback: se scraped não detectou, aplica regex na bio do canal
        if not has_channel and channel_desc:
            has_channel, _ = detect_call2go_channel(channel_desc)
        # Detector: nivel combinado (AND -- video E canal)
        has_combined = has_video and has_channel

        video_label = 'SIM' if has_video else 'NAO'
        canal_label = 'SIM' if has_channel else 'NAO'
        combinado_label = 'SIM' if has_combined else 'NAO'

        if has_video:
            count_video_sim += 1
        if has_channel:
            count_canal_sim += 1
        if has_combined:
            count_combinado_sim += 1

        rows.append({
            'video_id': vid,
            'artist_name': artist_name,
            'title': title,
            'youtube_url': f'https://www.youtube.com/watch?v={vid}',
            'youtube_channel_url': f'https://www.youtube.com/channel/{channel_id}' if channel_id else '',
            'description': description,
            'channel_bio': channel_bio,
            'manual_call2go_video': video_label,
            'manual_call2go_canal': canal_label,
            'manual_call2go_combinado': combinado_label,
            'confianca': 'alta',
        })

    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8')

    total = len(df)
    print(f"\n  CSV detector gerado: {output_file}")
    print(f"  Total de videos: {total}")
    print(f"  Artistas unicos: {df['artist_name'].nunique()}")
    print(f"\n  --- DISTRIBUICAO DETECTOR ---")
    print(f"  Video:     {count_video_sim} SIM ({count_video_sim*100/total:.1f}%) | {total - count_video_sim} NAO ({(total - count_video_sim)*100/total:.1f}%)")
    print(f"  Canal:     {count_canal_sim} SIM ({count_canal_sim*100/total:.1f}%) | {total - count_canal_sim} NAO ({(total - count_canal_sim)*100/total:.1f}%)")
    print(f"  Combinado: {count_combinado_sim} SIM ({count_combinado_sim*100/total:.1f}%) | {total - count_combinado_sim} NAO ({(total - count_combinado_sim)*100/total:.1f}%)")

    return df


if __name__ == "__main__":
    import sys
    if '--detector-answers' in sys.argv:
        generate_detector_answers()
    elif '--census' in sys.argv:
        generate_census_csv()
    else:
        generate_blind_csv()

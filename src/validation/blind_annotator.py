"""
Gerador de CSV cego para anotacao humana independente.

Recebe a amostra adversarial (ou qualquer amostra) e gera um CSV
com APENAS os dados brutos -- descricao do video, bio completa do canal
(descricao + links da aba Sobre), titulo, URLs -- sem nenhuma sugestao,
evidencia ou pre-anotacao do detector.

Isso elimina o vies de confirmacao: o anotador humano nao sabe o que
a maquina classificou e precisa ler cada descricao manualmente.

Fluxo de uso:
    1. python -m src.validation.adversarial_sampler   (gera amostra)
    2. python -m src.validation.blind_annotator       (gera CSV cego)
    3. Aluno abre o CSV/XLSX e anota manualmente cada video
    4. Salva como data/validation/ground_truth.csv
    5. python -m src.validation.cross_validator        (calcula metricas)
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
        print("Execute primeiro: python -m src.validation.adversarial_sampler")
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

    # 4. Monta CSV cego -- ordem aleatorizada (ja vem do adversarial_sampler)
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
            'notas': '',                      # observacoes do anotador
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
    print("       -> se video OU canal tem Call2Go, o combinado tambem tem")
    print("       -> tipo prevalece: link_direto > texto_implicito > nenhum")
    print("     - confianca: 'alta', 'media', ou 'baixa'")
    print("     - notas: qualquer observacao relevante")
    print("  5. Salve como: data/validation/ground_truth.csv")
    print("  6. Execute: python -m src.validation.cross_validator")

    return df


if __name__ == "__main__":
    generate_blind_csv()

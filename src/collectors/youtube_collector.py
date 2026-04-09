import os
import pandas as pd
import json
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Carrega as chaves do arquivo .env
load_dotenv()


def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("Chave do YouTube não encontrada no .env")
    return build('youtube', 'v3', developerKey=api_key)


def get_channel_id_by_name(youtube, artist_name):
    # Busca dinamicamente o ID do canal oficial pelo nome do artista
    res = youtube.search().list(
        q=artist_name,
        part='snippet',
        type='channel',
        maxResults=1
    ).execute()

    if res.get('items'):
        return res['items'][0]['snippet']['channelId']
    raise ValueError(
        f"Nenhum canal encontrado na busca para o nome: {artist_name}")


def get_channel_about(youtube, channel_id):
    """Coleta a descrição e metadados do perfil do canal (seção 'Sobre')."""
    res = youtube.channels().list(
        id=channel_id,
        part='snippet,brandingSettings'
    ).execute()

    if not res.get('items'):
        return {'channel_description': '', 'channel_keywords': ''}

    item = res['items'][0]
    snippet_desc = item.get('snippet', {}).get('description', '')
    branding_desc = item.get('brandingSettings', {}).get(
        'channel', {}).get('description', '')
    keywords = item.get('brandingSettings', {}).get(
        'channel', {}).get('keywords', '')

    # Usa a descrição mais completa entre snippet e branding
    channel_desc = branding_desc if len(
        branding_desc) > len(snippet_desc) else snippet_desc

    return {
        'channel_description': channel_desc,
        'channel_keywords': keywords
    }


def get_channel_videos(youtube, channel_id, max_results=20):
    """
    Busca os vídeos MAIS VISUALIZADOS do canal.

    Estratégia otimizada para quota:
        1. Usa playlistItems.list (1 unit/call) para listar IDs de vídeos recentes
           do canal (playlist de uploads = UC->UU).
        2. Usa videos.list (1 unit/call por 50 vídeos) para obter viewCount.
        3. Ordena localmente por viewCount (descendente).
        4. Retorna os top N vídeos mais visualizados.

    Custo: ~3-5 units por artista (vs 100+ com search.list).
    Limitação: busca nos últimos ~200 vídeos do canal. Para canais com
    milhares de vídeos, a amostra pode não incluir os vídeos mais antigos
    e mais visualizados, mas 200 é suficiente para a vasta maioria.
    """
    # Passo 1: Listar IDs via playlist de uploads (UC->UU)
    uploads_playlist = 'UU' + channel_id[2:]
    video_ids = []
    next_page_token = None
    max_scan = 200  # Escaneia até 200 vídeos para encontrar os top N

    while len(video_ids) < max_scan:
        try:
            res = youtube.playlistItems().list(
                playlistId=uploads_playlist,
                part='contentDetails',
                maxResults=50,
                pageToken=next_page_token
            ).execute()
        except Exception:
            break

        for item in res.get('items', []):
            vid = item.get('contentDetails', {}).get('videoId')
            if vid:
                video_ids.append(vid)

        next_page_token = res.get('nextPageToken')
        if not next_page_token:
            break

    if not video_ids:
        return []

    # Passo 2: Obter viewCount de todos os vídeos (1 call por 50 vídeos)
    videos_with_views = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        try:
            res = youtube.videos().list(
                id=','.join(chunk),
                part='statistics'
            ).execute()
            for item in res.get('items', []):
                views = int(item.get('statistics', {}).get('viewCount', 0))
                videos_with_views.append((item['id'], views))
        except Exception:
            break

    # Passo 3: Ordenar por views e retornar top N
    videos_with_views.sort(key=lambda x: x[1], reverse=True)
    return [vid for vid, _ in videos_with_views[:max_results]]


def get_video_details(youtube, video_ids):
    all_video_stats = []

    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        res = youtube.videos().list(
            id=','.join(chunk),
            part='snippet,statistics'
        ).execute()

        for item in res['items']:
            all_video_stats.append({
                "video_id": item['id'],
                "title": item['snippet']['title'],
                "description": item['snippet']['description'],
                "published_at": item['snippet']['publishedAt'],
                "channel_id": item['snippet']['channelId'],
                "view_count": item.get('statistics', {}).get('viewCount', 0),
                "like_count": item.get('statistics', {}).get('likeCount', 0),
                "comment_count": item.get('statistics', {}).get('commentCount', 0)
            })

    return all_video_stats


def collect_youtube_data(max_videos_per_artist=20):
    print(
        f"Iniciando coleta dos {max_videos_per_artist} vídeos MAIS VISUALIZADOS por artista...")
    youtube = get_youtube_client()
    df_artists = pd.read_csv("data/seed/artistas.csv")

    # Resume: carrega dados existentes para não re-coletar artistas já processados
    all_data = []
    completed_artists = set()
    output_file = "data/raw/youtube_videos_raw.jsonl"

    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        current_artists = set(df_artists['artist_name'].tolist())
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                # Apenas mantém dados de artistas que ainda estão no CSV seed
                if record.get('artist_name') in current_artists:
                    all_data.append(record)
                    completed_artists.add(record.get('artist_name'))
        if completed_artists:
            print(
                f"  [RESUME] {len(completed_artists)} artistas já coletados, continuando...")

    success_count = len(completed_artists)
    error_count = 0

    for index, row in df_artists.iterrows():
        artist_name = row['artist_name']

        if artist_name in completed_artists:
            print(
                f"\n[{index+1}/{len(df_artists)}] {artist_name}: SKIP (já coletado)")
            continue

        print(f"\n[{index+1}/{len(df_artists)}] Processando: {artist_name}")

        try:
            # Usa youtube_channel_id do CSV (já validado pelo artist_source_builder)
            channel_id = None
            if 'youtube_channel_id' in row and pd.notna(row.get('youtube_channel_id')):
                channel_id = row['youtube_channel_id']
                print(f"  [OK] Canal do CSV: {channel_id}")

            if not channel_id:
                channel_id = get_channel_id_by_name(youtube, artist_name)
                print(f"  [OK] Canal resolvido via busca: {channel_id}")

            # Coleta dados do perfil do canal (descrição, links)
            channel_about = get_channel_about(youtube, channel_id)

            # Extração dos vídeos MAIS VISUALIZADOS (order=viewCount)
            video_ids = get_channel_videos(
                youtube, channel_id, max_results=max_videos_per_artist)
            video_details = get_video_details(youtube, video_ids)

            for video in video_details:
                video['artist_name'] = artist_name
                video['channel_description'] = channel_about['channel_description']
                video['channel_keywords'] = channel_about['channel_keywords']

            all_data.extend(video_details)
            success_count += 1
            print(
                f"  [OK] {len(video_details)} vídeos mais visualizados coletados.")

        except Exception as e:
            err_str = str(e)
            if 'quotaExceeded' in err_str or '403' in err_str:
                print(
                    f"\n  [QUOTA ESGOTADA] YouTube API quota excedida após {success_count} artistas.")
                print(f"  Salvando dados coletados até agora...")
                break
            error_count += 1
            print(f"  [ERRO] Falha ao coletar dados para {artist_name}: {e}")

    # Salvar
    os.makedirs("data/raw", exist_ok=True)
    output_file = "data/raw/youtube_videos_raw.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"\n[OK] Dados do YouTube salvos com sucesso em: {output_file}")
    print(
        f"  Total: {len(all_data)} vídeos | {success_count} artistas OK | {error_count} erros")


if __name__ == "__main__":
    collect_youtube_data()

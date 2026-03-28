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


def get_channel_videos(youtube, channel_id, max_results=50):
    # Pega o ID da playlist de uploads
    res = youtube.channels().list(id=channel_id, part='contentDetails').execute()
    if not res.get('items'):
        raise ValueError(
            "O canal foi encontrado, mas não retornou detalhes de conteúdo.")

    uploads_playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    videos = []
    next_page_token = None

    # Busca os vídeos iterando as páginas
    while len(videos) < max_results:
        res = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part='snippet',
            maxResults=min(50, max_results - len(videos)),
            pageToken=next_page_token
        ).execute()

        videos.extend(res['items'])
        next_page_token = res.get('nextPageToken')

        if not next_page_token:
            break

    return [video['snippet']['resourceId']['videoId'] for video in videos]


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


def collect_youtube_data():
    print("Iniciando coleta de dados do YouTube com Resolução Dinâmica de IDs...")
    youtube = get_youtube_client()
    df_artists = pd.read_csv("data/seed/artistas.csv")

    all_data = []

    for index, row in df_artists.iterrows():
        artist_name = row['artist_name']
        print(f"\nProcessando: {artist_name}")

        try:
            # 1. Resolução em tempo de execução
            channel_id = get_channel_id_by_name(youtube, artist_name)
            print(f"[OK] ID resolvido: {channel_id}")

            # 2. Extração dos vídeos
            video_ids = get_channel_videos(youtube, channel_id, max_results=50)
            video_details = get_video_details(youtube, video_ids)

            for video in video_details:
                video['artist_name'] = artist_name

            all_data.extend(video_details)
            print(f"[OK] {len(video_details)} vídeos processados com sucesso.")

        except Exception as e:
            print(f"[ERRO] Falha ao coletar dados para {artist_name}: {e}")

    # Salvar
    output_file = "data/raw/youtube_videos_raw.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"\n✅ Dados do YouTube salvos com sucesso em: {output_file}")


if __name__ == "__main__":
    collect_youtube_data()

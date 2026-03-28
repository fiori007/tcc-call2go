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
    success_count = 0
    error_count = 0

    for index, row in df_artists.iterrows():
        artist_name = row['artist_name']
        print(f"\n[{index+1}/{len(df_artists)}] Processando: {artist_name}")

        try:
            # Usa youtube_channel_id do CSV se disponível, senão busca dinamicamente
            channel_id = None
            if 'youtube_channel_id' in row and pd.notna(row.get('youtube_channel_id')):
                channel_id = row['youtube_channel_id']
                # Verifica se o canal do CSV funciona
                try:
                    res = youtube.channels().list(id=channel_id, part='contentDetails').execute()
                    if not res.get('items') or 'relatedPlaylists' not in res['items'][0].get('contentDetails', {}):
                        print(f"  [AVISO] Canal do CSV inválido, buscando via pesquisa...")
                        channel_id = None
                    else:
                        print(f"  [OK] Canal do CSV: {channel_id}")
                except Exception:
                    channel_id = None

            if not channel_id:
                channel_id = get_channel_id_by_name(youtube, artist_name)
                print(f"  [OK] Canal resolvido via busca: {channel_id}")

            # Extração dos vídeos
            video_ids = get_channel_videos(youtube, channel_id, max_results=50)
            video_details = get_video_details(youtube, video_ids)

            for video in video_details:
                video['artist_name'] = artist_name

            all_data.extend(video_details)
            success_count += 1
            print(f"  [OK] {len(video_details)} vídeos processados com sucesso.")

        except Exception as e:
            error_count += 1
            print(f"  [ERRO] Falha ao coletar dados para {artist_name}: {e}")

    # Salvar
    os.makedirs("data/raw", exist_ok=True)
    output_file = "data/raw/youtube_videos_raw.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"\n✅ Dados do YouTube salvos com sucesso em: {output_file}")
    print(f"  Total: {len(all_data)} vídeos | {success_count} artistas OK | {error_count} erros")


if __name__ == "__main__":
    collect_youtube_data()

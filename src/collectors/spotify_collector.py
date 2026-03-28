import os
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from datetime import datetime, timezone

# Carrega as chaves do arquivo .env
load_dotenv()


def get_spotify_client():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("Chaves do Spotify não encontradas no .env")

    auth_manager = SpotifyClientCredentials(
        client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth_manager)


def collect_spotify_data():
    print("Iniciando coleta de dados do Spotify...")
    sp = get_spotify_client()

    # Lê a lista de artistas
    df_artists = pd.read_csv("data/seed/artistas.csv")

    results = []
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    for index, row in df_artists.iterrows():
        artist_id = row['spotify_id']
        artist_name = row['artist_name']

        try:
            artist_data = sp.artist(artist_id)
            followers = artist_data['followers']['total']
            popularity = artist_data['popularity']

            results.append({
                "date": today_date,
                "artist_name": artist_name,
                "spotify_id": artist_id,
                "followers": followers,
                "popularity": popularity
            })
            print(f"[OK] Coletado: {artist_name} | Pop: {popularity}")

        except Exception as e:
            print(f"[ERRO] Falha ao coletar {artist_name}: {e}")

    # Salva o resultado
    df_results = pd.DataFrame(results)
    os.makedirs("data/raw", exist_ok=True)
    output_file = f"data/raw/spotify_metrics_{today_date}.csv"
    df_results.to_csv(output_file, index=False)
    print(f"\n✅ Dados do Spotify salvos com sucesso em: {output_file}")


if __name__ == "__main__":
    collect_spotify_data()

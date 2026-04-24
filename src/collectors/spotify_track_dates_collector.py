import os
import glob
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

OUTPUT_FILE = "data/raw/spotify_track_dates_Q1_2026.csv"
CHARTS_DIR = "data/raw/spotify_charts"
BATCH_SIZE = 50


def get_spotify_client():
    """Cria e retorna cliente autenticado do Spotify."""
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("Chaves do Spotify nao encontradas no .env")

    auth_manager = SpotifyClientCredentials(
        client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth_manager)


def collect_track_dates():
    """Coleta datas de lancamento de todas as faixas dos charts Spotify Q1 2026."""
    # Cache-first: se arquivo ja existe, pula coleta
    if os.path.exists(OUTPUT_FILE):
        print(f"[OK] Arquivo ja existe, pulando coleta: {OUTPUT_FILE}")
        return

    print("Iniciando coleta de datas de lancamento das faixas Spotify Q1 2026...")

    # Carrega todos os CSVs de charts do Spotify
    csv_files = sorted(glob.glob(os.path.join(
        CHARTS_DIR, "regional-br-weekly-*.csv")))
    if not csv_files:
        print(f"[ERRO] Nenhum CSV encontrado em {CHARTS_DIR}")
        return

    print(f"  {len(csv_files)} arquivos de chart carregados")

    # Extrai URIs únicos de todas as semanas
    all_uris: set = set()
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            if 'uri' in df.columns:
                all_uris.update(df['uri'].dropna().unique())
        except Exception as e:
            print(f"[AVISO] Falha ao ler {f}: {e}")

    # Extrai track IDs e mapeia ID -> URI original
    track_ids = []
    id_to_uri: dict = {}
    for uri in all_uris:
        parts = str(uri).split(':')
        if len(parts) == 3 and parts[1] == 'track':
            track_id = parts[2]
            track_ids.append(track_id)
            id_to_uri[track_id] = uri

    print(f"  {len(track_ids)} faixas unicas identificadas")

    sp = get_spotify_client()
    results = []

    # Divide em batches de 50 (limite da API)
    batches = [track_ids[i:i + BATCH_SIZE]
               for i in range(0, len(track_ids), BATCH_SIZE)]
    total_batches = len(batches)

    for batch_num, batch in enumerate(batches, start=1):
        try:
            response = sp.tracks(batch)
            tracks_data = response.get('tracks', []) if response else []
            for track in tracks_data:
                if track is None:
                    continue
                track_id = track['id']
                uri = id_to_uri.get(track_id, f"spotify:track:{track_id}")
                artist_names = ', '.join(
                    a['name'] for a in track.get('artists', []))
                album = track.get('album', {})
                release_date = album.get('release_date', '')
                release_date_precision = album.get(
                    'release_date_precision', '')
                results.append({
                    'uri': uri,
                    'track_name': track['name'],
                    'artist_names': artist_names,
                    'release_date': release_date,
                    'release_date_precision': release_date_precision,
                })
            print(f"[OK] Batch {batch_num}/{total_batches}: "
                  f"{len(batch)} faixas coletadas")
        except Exception as e:
            print(f"[ERRO] Batch {batch_num}/{total_batches}: {e}")
            continue

    # Salva resultado
    df_results = pd.DataFrame(results)
    os.makedirs(os.path.dirname(OUTPUT_FILE) if os.path.dirname(OUTPUT_FILE) else ".", exist_ok=True)
    df_results.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[OK] Datas de lancamento salvas: {OUTPUT_FILE} "
          f"({len(df_results)} faixas)")


if __name__ == "__main__":
    collect_track_dates()

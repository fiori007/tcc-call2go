"""
Coletor de dados do Last.fm para enriquecimento cross-platform.

Coleta metricas de artistas via Last.fm API (audioscrobbler):
- artist.getInfo: listeners, playcount, tags, bio, artistas similares
- artist.getTopTracks: top 10 tracks com playcount/listeners individuais
- artist.getTopAlbums: top 5 albuns com playcount

O Last.fm funciona como um "IMDB da musica": fornece dados de audiencia
baseados em scrobbles (execucoes reais registradas por usuarios),
complementando as metricas de popularidade do Spotify e views do YouTube.

Fluxo:
    python -m src.collectors.lastfm_collector
    ou via run_pipeline.py (etapa automatica)
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Constantes da API
BASE_URL = "http://ws.audioscrobbler.com/2.0/"
REQUEST_DELAY = 0.25  # 250ms entre requests (respeita rate limit)


def _get_api_key():
    """Retorna a API key do Last.fm configurada no .env."""
    key = os.getenv("LASTFM_API_KEY")
    if not key:
        raise ValueError(
            "LASTFM_API_KEY nao encontrada no .env. "
            "Crie uma em: https://www.last.fm/api/account/create"
        )
    return key


def _api_call(method, params, api_key):
    """Faz uma chamada a API do Last.fm com tratamento de erros."""
    params.update({
        'method': method,
        'api_key': api_key,
        'format': 'json',
        'autocorrect': 1,  # Corrige nomes de artistas automaticamente
    })
    headers = {'User-Agent': 'TCC-Call2Go/1.0 (academic research)'}

    try:
        resp = requests.get(BASE_URL, params=params, headers=headers,
                            timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Verifica erro da API
        if 'error' in data:
            return None, f"Erro {data['error']}: {data.get('message', '')}"

        return data, None
    except requests.exceptions.Timeout:
        return None, "Timeout na requisicao"
    except requests.exceptions.RequestException as e:
        return None, f"Erro HTTP: {e}"
    except ValueError:
        return None, "Resposta nao e JSON valido"


def _get_artist_info(artist_name, api_key):
    """Coleta informacoes gerais do artista: listeners, playcount, tags."""
    data, err = _api_call('artist.getInfo', {'artist': artist_name}, api_key)
    if err or not data:
        return None, err

    artist = data.get('artist', {})
    stats = artist.get('stats', {})

    # Extrai tags (top 5)
    tags_raw = artist.get('tags', {}).get('tag', [])
    if isinstance(tags_raw, dict):
        tags_raw = [tags_raw]
    tags = [t.get('name', '') for t in tags_raw[:5]]

    # Nome corrigido pelo autocorrect
    corrected_name = artist.get('name', artist_name)

    return {
        'lastfm_name': corrected_name,
        'lastfm_url': artist.get('url', ''),
        'listeners': int(stats.get('listeners', 0)),
        'playcount': int(stats.get('playcount', 0)),
        'tags': '|'.join(tags),
        'bio_summary': (artist.get('bio', {}).get('summary', '') or '')[:500],
    }, None


def _get_top_tracks(artist_name, api_key, limit=10):
    """Coleta as top N tracks do artista com playcount e listeners."""
    data, err = _api_call(
        'artist.getTopTracks',
        {'artist': artist_name, 'limit': limit},
        api_key
    )
    if err or not data:
        return [], err

    tracks_raw = data.get('toptracks', {}).get('track', [])
    if isinstance(tracks_raw, dict):
        tracks_raw = [tracks_raw]

    tracks = []
    for t in tracks_raw[:limit]:
        tracks.append({
            'name': t.get('name', ''),
            'playcount': int(t.get('playcount', 0)),
            'listeners': int(t.get('listeners', 0)),
            'rank': int(t.get('@attr', {}).get('rank', 0)),
        })

    return tracks, None


def _get_top_albums(artist_name, api_key, limit=5):
    """Coleta os top N albuns do artista com playcount."""
    data, err = _api_call(
        'artist.getTopAlbums',
        {'artist': artist_name, 'limit': limit},
        api_key
    )
    if err or not data:
        return [], err

    albums_raw = data.get('topalbums', {}).get('album', [])
    if isinstance(albums_raw, dict):
        albums_raw = [albums_raw]

    albums = []
    for a in albums_raw[:limit]:
        albums.append({
            'name': a.get('name', ''),
            'playcount': int(a.get('playcount', 0)),
        })

    return albums, None


def collect_lastfm_data(seed_file="data/seed/artistas.csv",
                        output_dir="data/raw"):
    """
    Coleta dados do Last.fm para todos os artistas do seed.

    Gera 2 CSVs:
      - lastfm_artists_YYYY-MM-DD.csv: metricas por artista
      - lastfm_top_tracks_YYYY-MM-DD.csv: top tracks por artista

    Returns:
        tuple: (df_artists, df_tracks) ou (None, None) em caso de erro
    """
    print("Iniciando coleta de dados do Last.fm...")
    api_key = _get_api_key()

    df_seed = pd.read_csv(seed_file)
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    artist_rows = []
    track_rows = []
    found = 0
    not_found = 0

    for idx, row in df_seed.iterrows():
        artist_name = row['artist_name']

        # 1. Info do artista (listeners, playcount, tags)
        info, err = _get_artist_info(artist_name, api_key)
        time.sleep(REQUEST_DELAY)

        if err or not info:
            print(f"  [AVISO] {artist_name}: {err or 'sem dados'}")
            not_found += 1
            # Registra artista mesmo sem dados (para manter completude)
            artist_rows.append({
                'date': today,
                'artist_name': artist_name,
                'lastfm_name': '',
                'lastfm_url': '',
                'listeners': 0,
                'playcount': 0,
                'tags': '',
                'bio_summary': '',
                'top_track_1': '',
                'top_track_1_playcount': 0,
                'top_track_2': '',
                'top_track_2_playcount': 0,
                'top_track_3': '',
                'top_track_3_playcount': 0,
                'top_album_1': '',
                'top_album_1_playcount': 0,
                'found_on_lastfm': False,
            })
            continue

        # 2. Top tracks
        tracks, _ = _get_top_tracks(artist_name, api_key, limit=10)
        time.sleep(REQUEST_DELAY)

        # 3. Top albums
        albums, _ = _get_top_albums(artist_name, api_key, limit=5)
        time.sleep(REQUEST_DELAY)

        # Monta linha do artista com top 3 tracks e top album inline
        artist_row = {
            'date': today,
            'artist_name': artist_name,
            'lastfm_name': info['lastfm_name'],
            'lastfm_url': info['lastfm_url'],
            'listeners': info['listeners'],
            'playcount': info['playcount'],
            'tags': info['tags'],
            'bio_summary': info['bio_summary'],
            'top_track_1': tracks[0]['name'] if len(tracks) > 0 else '',
            'top_track_1_playcount': tracks[0]['playcount'] if len(tracks) > 0 else 0,
            'top_track_2': tracks[1]['name'] if len(tracks) > 1 else '',
            'top_track_2_playcount': tracks[1]['playcount'] if len(tracks) > 1 else 0,
            'top_track_3': tracks[2]['name'] if len(tracks) > 2 else '',
            'top_track_3_playcount': tracks[2]['playcount'] if len(tracks) > 2 else 0,
            'top_album_1': albums[0]['name'] if len(albums) > 0 else '',
            'top_album_1_playcount': albums[0]['playcount'] if len(albums) > 0 else 0,
            'found_on_lastfm': True,
        }
        artist_rows.append(artist_row)

        # Monta linhas detalhadas de tracks (para analise granular)
        for t in tracks:
            track_rows.append({
                'date': today,
                'artist_name': artist_name,
                'track_name': t['name'],
                'track_playcount': t['playcount'],
                'track_listeners': t['listeners'],
                'track_rank': t['rank'],
            })

        found += 1
        print(f"  [OK] {artist_name}: {info['listeners']:,} listeners, "
              f"{info['playcount']:,} scrobbles, {len(tracks)} tracks")

    # Salva CSVs
    os.makedirs(output_dir, exist_ok=True)

    df_artists = pd.DataFrame(artist_rows)
    artists_file = os.path.join(output_dir, f"lastfm_artists_{today}.csv")
    df_artists.to_csv(artists_file, index=False)

    df_tracks = pd.DataFrame(track_rows)
    tracks_file = os.path.join(output_dir, f"lastfm_top_tracks_{today}.csv")
    df_tracks.to_csv(tracks_file, index=False)

    print(f"\n[OK] Dados do Last.fm salvos:")
    print(f"  Artistas: {artists_file} ({found} encontrados, "
          f"{not_found} nao encontrados)")
    print(f"  Top tracks: {tracks_file} ({len(track_rows)} tracks)")

    return df_artists, df_tracks


if __name__ == "__main__":
    collect_lastfm_data()

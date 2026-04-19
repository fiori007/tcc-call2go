"""
Coletor de charts brasileiros do Last.fm (geo endpoints).

Coleta os rankings de popularidade do Brasil via Last.fm:
- geo.getTopArtists: Top artistas do Brasil (por scrobbles recentes)
- geo.getTopTracks: Top tracks do Brasil (semana mais recente)

Esses dados servem como validacao independente do seed de 67 artistas:
se um artista aparece nos charts do Spotify, YouTube E Last.fm, sua relevancia
e triplamente confirmada por fontes independentes.

NOTA TEMPORAL: A API retorna dados da semana mais recente, nao historicos.
Para o TCC (janela Q1 2026: jan-mar), isso serve como snapshot de validacao,
ja que artistas persistentes nos charts mantem posicoes estaveis ao longo
do trimestre.

Fluxo:
    python -m src.collectors.lastfm_chart_collector
    ou via run_pipeline.py (etapa 4, junto com lastfm_collector)
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://ws.audioscrobbler.com/2.0/"
REQUEST_DELAY = 0.25


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
    })
    headers = {'User-Agent': 'TCC-Call2Go/1.0 (academic research)'}

    try:
        resp = requests.get(BASE_URL, params=params, headers=headers,
                            timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if 'error' in data:
            return None, f"Erro {data['error']}: {data.get('message', '')}"

        return data, None
    except requests.exceptions.Timeout:
        return None, "Timeout na requisicao"
    except requests.exceptions.RequestException as e:
        return None, f"Erro HTTP: {e}"
    except ValueError:
        return None, "Resposta nao e JSON valido"


def collect_chart_artists(country="Brazil", total=200):
    """
    Coleta Top N artistas do Brasil no Last.fm via geo.getTopArtists.

    Returns:
        list[dict]: artistas com name, listeners, url, rank
    """
    api_key = _get_api_key()
    all_artists = []
    per_page = 50
    pages = (total + per_page - 1) // per_page

    print(f"  Coletando Top {total} artistas do Last.fm ({country})...")

    for page in range(1, pages + 1):
        data, err = _api_call('geo.getTopArtists', {
            'country': country,
            'limit': per_page,
            'page': page,
        }, api_key)
        time.sleep(REQUEST_DELAY)

        if err or not data:
            print(f"    [AVISO] Pagina {page}: {err or 'sem dados'}")
            continue

        artists_raw = data.get('topartists', {}).get('artist', [])
        if isinstance(artists_raw, dict):
            artists_raw = [artists_raw]

        for i, a in enumerate(artists_raw):
            rank = (page - 1) * per_page + i + 1
            all_artists.append({
                'rank': rank,
                'artist_name': a.get('name', ''),
                'listeners': int(a.get('listeners', 0)),
                'mbid': a.get('mbid', ''),
                'url': a.get('url', ''),
            })

        print(f"    Pagina {page}/{pages}: {len(artists_raw)} artistas")

    return all_artists[:total]


def collect_chart_tracks(country="Brazil", total=200):
    """
    Coleta Top N tracks do Brasil no Last.fm via geo.getTopTracks.

    Returns:
        list[dict]: tracks com name, artist, listeners, rank
    """
    api_key = _get_api_key()
    all_tracks = []
    per_page = 50
    pages = (total + per_page - 1) // per_page

    print(f"  Coletando Top {total} tracks do Last.fm ({country})...")

    for page in range(1, pages + 1):
        data, err = _api_call('geo.getTopTracks', {
            'country': country,
            'limit': per_page,
            'page': page,
        }, api_key)
        time.sleep(REQUEST_DELAY)

        if err or not data:
            print(f"    [AVISO] Pagina {page}: {err or 'sem dados'}")
            continue

        tracks_raw = data.get('tracks', {}).get('track', [])
        if isinstance(tracks_raw, dict):
            tracks_raw = [tracks_raw]

        for i, t in enumerate(tracks_raw):
            rank = (page - 1) * per_page + i + 1
            all_tracks.append({
                'rank': rank,
                'track_name': t.get('name', ''),
                'artist_name': t.get('artist', {}).get('name', ''),
                'listeners': int(t.get('listeners', 0)),
                'mbid': t.get('mbid', ''),
                'url': t.get('url', ''),
            })

        print(f"    Pagina {page}/{pages}: {len(tracks_raw)} tracks")

    return all_tracks[:total]


def collect_lastfm_charts(country="Brazil", total=200,
                          output_dir="data/raw"):
    """
    Coleta charts brasileiros do Last.fm (artistas + tracks).

    Gera 2 CSVs:
      - lastfm_chart_artists_brazil_YYYY-MM-DD.csv
      - lastfm_chart_tracks_brazil_YYYY-MM-DD.csv

    Returns:
        tuple: (df_chart_artists, df_chart_tracks)
    """
    print("Coletando charts brasileiros do Last.fm...")
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Coleta artistas
    artists = collect_chart_artists(country, total)
    df_artists = pd.DataFrame(artists)
    df_artists['date'] = today
    df_artists['country'] = country

    # Coleta tracks
    tracks = collect_chart_tracks(country, total)
    df_tracks = pd.DataFrame(tracks)
    df_tracks['date'] = today
    df_tracks['country'] = country

    # Salva CSVs
    os.makedirs(output_dir, exist_ok=True)

    artists_file = os.path.join(
        output_dir, f"lastfm_chart_artists_brazil_{today}.csv")
    df_artists.to_csv(artists_file, index=False)

    tracks_file = os.path.join(
        output_dir, f"lastfm_chart_tracks_brazil_{today}.csv")
    df_tracks.to_csv(tracks_file, index=False)

    print(f"\n[OK] Charts do Last.fm ({country}) salvos:")
    print(f"  Artistas: {artists_file} ({len(df_artists)} artistas)")
    print(f"  Tracks: {tracks_file} ({len(df_tracks)} tracks)")

    return df_artists, df_tracks


if __name__ == "__main__":
    collect_lastfm_charts()

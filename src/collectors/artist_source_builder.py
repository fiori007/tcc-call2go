import os
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()


def get_spotify_client():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("Chaves do Spotify não encontradas no .env")
    auth_manager = SpotifyClientCredentials(
        client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth_manager)


def build_from_playlists(sp, playlist_ids):
    """Tenta extrair artistas de playlists oficiais do Spotify."""
    all_artists = {}
    for playlist in playlist_ids:
        pid = playlist['id']
        pname = playlist['name']
        print(f"\n  Tentando playlist: {pname} ({pid})")
        try:
            results = sp.playlist_tracks(
                pid, fields='items(track(artists(id,name)))')
            for item in results.get('items', []):
                track = item.get('track')
                if not track:
                    continue
                for artist in track.get('artists', []):
                    aid = artist['id']
                    if aid not in all_artists:
                        all_artists[aid] = {
                            'artist_name': artist['name'],
                            'spotify_id': aid,
                            'source': pname,
                            'occurrence_count': 0
                        }
                    all_artists[aid]['occurrence_count'] += 1
            print(f"  [OK] {len(results.get('items', []))} faixas")
        except Exception as e:
            print(f"  [FALHA] {e}")
    return all_artists


def build_from_search(sp, genres, market='BR', limit_per_genre=15):
    """Busca artistas por gênero como fallback quando playlists falham."""
    all_artists = {}
    for genre in genres:
        print(f"\n  Buscando gênero: {genre}")
        try:
            results = sp.search(q=genre, type='artist', market=market, limit=limit_per_genre)
            items = results.get('artists', {}).get('items', [])
            for a in items:
                aid = a['id']
                if aid not in all_artists:
                    all_artists[aid] = {
                        'artist_name': a['name'],
                        'spotify_id': aid,
                        'source': f'search:{genre}',
                        'occurrence_count': 0,
                        'popularity': a['popularity'],
                        'followers': a['followers']['total']
                    }
                all_artists[aid]['occurrence_count'] += 1
            print(f"  [OK] {len(items)} artistas encontrados")
        except Exception as e:
            print(f"  [FALHA] {e}")
    return all_artists


def build_artist_base(playlist_ids=None, output_file="data/seed/artistas.csv",
                      max_artists=30):
    """
    Constrói a base de artistas a partir de fontes oficiais do Spotify.

    Estratégia em duas fases:
        1. Tenta playlists oficiais (reprodutível por ID fixo)
        2. Fallback: busca por gênero com filtro de mercado BR

    O resultado final é limitado a max_artists para viabilidade do pipeline.
    """
    print("=" * 60)
    print("CONSTRUÇÃO DA BASE DE ARTISTAS — FONTE OFICIAL SPOTIFY")
    print("=" * 60)

    sp = get_spotify_client()
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    all_artists = {}

    # Fase 1: Playlists oficiais
    if playlist_ids:
        print("\n--- FASE 1: Playlists Oficiais ---")
        all_artists = build_from_playlists(sp, playlist_ids)

    # Fase 2: Fallback por busca de gênero
    if len(all_artists) < 10:
        print("\n--- FASE 2: Busca por Gênero (fallback) ---")
        genres = [
            'sertanejo universitario',
            'funk brasil',
            'pop brasil',
            'pagode',
            'trap brasileiro',
            'mpb',
            'sertanejo',
            'rap brasileiro',
        ]
        search_artists = build_from_search(sp, genres)
        # Merge sem duplicar
        for aid, data in search_artists.items():
            if aid not in all_artists:
                all_artists[aid] = data

    if not all_artists:
        print("[ERRO] Nenhum artista encontrado. Verifique as credenciais.")
        return None

    # Enriquece com dados completos do Spotify
    print(f"\n--- Enriquecendo {len(all_artists)} artistas com dados completos ---")
    enriched = []
    for aid, data in all_artists.items():
        try:
            artist_full = sp.artist(aid)
            enriched.append({
                'artist_name': artist_full['name'],
                'spotify_id': aid,
                'followers': artist_full['followers']['total'],
                'popularity': artist_full['popularity'],
                'genres': '; '.join(artist_full.get('genres', [])[:3]),
                'source': data.get('source', 'unknown'),
                'occurrence_count': data.get('occurrence_count', 1),
                'extraction_date': today,
                'selection_criteria': 'Spotify Search by Genre (Market: BR)',
            })
        except Exception as e:
            print(f"  [SKIP] {data.get('artist_name', aid)}: {e}")

    df = pd.DataFrame(enriched)

    # Filtra: apenas artistas com popularidade razoável (>40) para relevância
    df = df[df['popularity'] >= 40]

    # Ordena por popularidade e limita
    df = df.sort_values('popularity', ascending=False).reset_index(drop=True)
    if len(df) > max_artists:
        df = df.head(max_artists)

    # Salva
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8')

    print(f"\n{'=' * 60}")
    print(f"Base de artistas construída: {len(df)} artistas")
    print(f"Salvo em: {output_file}")
    print(f"Data de extração: {today}")
    print(f"Top 5 por popularidade:")
    for _, row in df.head(5).iterrows():
        print(f"  {row['artist_name']} | pop={row['popularity']} | followers={row['followers']:,}")
    print(f"{'=' * 60}")

    return df


if __name__ == "__main__":
    OFFICIAL_PLAYLISTS = [
        {'id': '37i9dQZEVXbMXbN3EUUhlg', 'name': 'Top 50 Brasil'},
        {'id': '37i9dQZEVXbKzoK95AbRy9', 'name': 'Viral 50 Brasil'},
        {'id': '37i9dQZF1DX0FOF1IUWK1W', 'name': 'Top Hits Brasil'},
    ]
    build_artist_base(OFFICIAL_PLAYLISTS)

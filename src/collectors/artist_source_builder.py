import os
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build as yt_build
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


def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("Chave do YouTube não encontrada no .env")
    return yt_build('youtube', 'v3', developerKey=api_key)


def build_from_playlists(sp, playlist_ids):
    """Extrai artistas de playlists oficiais do Spotify (com paginação completa)."""
    all_artists = {}
    for playlist in playlist_ids:
        pid = playlist['id']
        pname = playlist['name']
        print(f"\n  Tentando playlist: {pname} ({pid})")
        try:
            results = sp.playlist_tracks(pid)
            items = results.get('items', [])
            # Paginação: playlists podem ter mais de 100 faixas
            while results.get('next'):
                results = sp.next(results)
                items.extend(results.get('items', []))

            for item in items:
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
            print(
                f"  [OK] {len(items)} faixas -> {len(all_artists)} artistas acumulados")
        except Exception as e:
            print(f"  [FALHA] {e}")
    return all_artists


def search_playlists_br(sp):
    """Busca playlists 'Top 50 Brasil' dinamicamente quando IDs fixos falham."""
    print("\n  Buscando playlists brasileiras dinamicamente...")
    queries = ['Top 50 Brasil', 'Top Brasil', 'Hits Brasil', 'Brasil Top']
    found = []
    for q in queries:
        try:
            results = sp.search(q=q, type='playlist', market='BR', limit=5)
            for pl in results.get('playlists', {}).get('items', []):
                if pl and pl.get('tracks', {}).get('total', 0) >= 30:
                    found.append({'id': pl['id'], 'name': pl['name']})
                    print(
                        f"    Encontrada: {pl['name']} ({pl['id']}) -- {pl['tracks']['total']} faixas")
        except Exception as e:
            print(f"    [FALHA] busca '{q}': {e}")
    return found


def build_from_search(sp, genres, market='BR', limit_per_genre=20):
    """Busca artistas por gênero como fallback quando playlists falham."""
    all_artists = {}
    for genre in genres:
        print(f"\n  Buscando gênero: {genre}")
        try:
            results = sp.search(q=genre, type='artist',
                                market=market, limit=limit_per_genre)
            items = results.get('artists', {}).get('items', [])
            for a in items:
                aid = a['id']
                if aid not in all_artists:
                    all_artists[aid] = {
                        'artist_name': a['name'],
                        'spotify_id': aid,
                        'source': f'search:{genre}',
                        'occurrence_count': 0,
                    }
                all_artists[aid]['occurrence_count'] += 1
            print(f"  [OK] {len(items)} artistas encontrados")
        except Exception as e:
            print(f"  [FALHA] {e}")
    return all_artists


def _validate_and_deduplicate(sp, enriched, min_followers_threshold=5000):
    """
    Valida e deduplica artistas após enriquecimento do Spotify.

    1. Agrupa por nome normalizado -- se houver duplicatas, mantém o de maior followers.
    2. Para artistas com followers suspeitamente baixo (< threshold), busca o perfil
       correto via Spotify Search e substitui se encontrar um melhor.

    Isso corrige casos como perfis tributo/duplicado que aparecem em playlists
    (ex: Marília Mendonça com 1.235 followers vs perfil real com ~40M).
    """
    print(f"\n--- FASE 2b: Validação e Deduplicação ---")

    # Passo 1: Deduplicar por nome (manter maior followers)
    by_name = {}
    for artist in enriched:
        name_key = artist['artist_name'].strip().lower()
        if name_key not in by_name:
            by_name[name_key] = artist
        else:
            existing = by_name[name_key]
            if artist['followers'] > existing['followers']:
                print(f"  [DEDUP] {artist['artist_name']}: "
                      f"substituindo perfil ({existing['followers']:,} seg) "
                      f"por ({artist['followers']:,} seg)")
                by_name[name_key] = artist

    deduped = list(by_name.values())
    if len(deduped) < len(enriched):
        print(
            f"  Removidos {len(enriched) - len(deduped)} duplicatas por nome")

    # Passo 2: Verificar artistas com followers suspeitamente baixo
    validated = []
    fixes = 0
    for artist in deduped:
        if artist['followers'] < min_followers_threshold:
            name = artist['artist_name']
            print(
                f"  [VALIDAÇÃO] {name}: apenas {artist['followers']:,} seg -- buscando perfil correto...", end=' ')
            try:
                results = sp.search(q=name, type='artist',
                                    market='BR', limit=5)
                candidates = results.get('artists', {}).get('items', [])

                best = None
                for c in candidates:
                    c_name = c['name'].strip().lower()
                    a_name = name.strip().lower()
                    if c_name == a_name or c_name in a_name or a_name in c_name:
                        if best is None or c['followers']['total'] > best['followers']['total']:
                            best = c

                if best and best['followers']['total'] > artist['followers']:
                    old_followers = artist['followers']
                    artist['spotify_id'] = best['id']
                    artist['followers'] = best['followers']['total']
                    artist['popularity'] = best['popularity']
                    artist['genres'] = '; '.join(best.get('genres', [])[:3])
                    fixes += 1
                    print(
                        f"CORRIGIDO -> {artist['followers']:,} seg (era {old_followers:,})")
                else:
                    print(f"mantido (sem perfil melhor encontrado)")
            except Exception as e:
                print(f"erro na busca: {e}")

        validated.append(artist)

    if fixes > 0:
        print(f"  {fixes} perfil(is) corrigido(s) via Spotify Search")

    return validated


def find_youtube_channel(youtube, artist_name):
    """
    Busca o canal oficial do artista no YouTube.
    Retorna (channel_id, total_views) ou (None, 0) se não encontrar.
    """
    try:
        res = youtube.search().list(
            q=f'{artist_name} canal oficial',
            part='snippet',
            type='channel',
            maxResults=5,
            relevanceLanguage='pt'
        ).execute()

        if not res.get('items'):
            return None, 0

        # Pega stats de todos os candidatos para escolher o melhor
        candidate_ids = [item['snippet']['channelId'] for item in res['items']]
        stats_res = youtube.channels().list(
            id=','.join(candidate_ids),
            part='statistics,snippet,status'
        ).execute()

        best_channel = None
        best_views = 0
        artist_lower = artist_name.lower()

        for ch in stats_res.get('items', []):
            ch_title = ch['snippet']['title'].lower()
            total_views = int(ch['statistics'].get('viewCount', 0))

            # Prioriza canais cujo título contém o nome do artista
            name_match = artist_lower in ch_title or ch_title in artist_lower

            if name_match and total_views > best_views:
                best_views = total_views
                best_channel = ch['id']

        # Se nenhum match por nome, pega o primeiro com mais views
        if not best_channel and stats_res.get('items'):
            for ch in sorted(stats_res['items'],
                             key=lambda x: int(
                                 x['statistics'].get('viewCount', 0)),
                             reverse=True):
                best_channel = ch['id']
                best_views = int(ch['statistics'].get('viewCount', 0))
                break

        return best_channel, best_views

    except Exception as e:
        err_str = str(e)
        if 'quotaExceeded' in err_str or '403' in err_str:
            print(f"    [QUOTA ESGOTADA] Parando busca no YouTube.")
            return 'QUOTA_EXHAUSTED', 0
        print(f"    [ERRO YouTube] {artist_name}: {e}")
        return None, 0


def build_artist_base(playlist_ids=None, output_file="data/seed/artistas.csv",
                      max_artists=50, min_popularity=60):
    """
    Constrói a base de artistas Top 50 BR cruzando Spotify e YouTube.

    Estratégia:
        1. Extrai artistas das playlists oficiais do Spotify (Top 50 Brasil, etc.)
        2. Enriquece com dados completos do Spotify (followers, popularity, genres)
        3. Busca canal YouTube de cada artista e total de views
        4. Filtra: popularity >= min_popularity + canal YouTube encontrado
        5. Ordena por total de views no YouTube (descendente)
    """
    print("=" * 60)
    print("CONSTRUÇÃO DA BASE DE ARTISTAS -- TOP 50 BR (SPOTIFY x YOUTUBE)")
    print("=" * 60)

    sp = get_spotify_client()
    youtube = get_youtube_client()
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    all_artists = {}

    # Fase 1: Playlists oficiais do Spotify
    if playlist_ids:
        print("\n--- FASE 1: Playlists Oficiais do Spotify ---")
        all_artists = build_from_playlists(sp, playlist_ids)

    # Fase 1b: Se playlists fixas falharam, busca dinamicamente
    if len(all_artists) < 10:
        print("\n--- FASE 1b: Busca Dinâmica de Playlists ---")
        dynamic_playlists = search_playlists_br(sp)
        if dynamic_playlists:
            dynamic_artists = build_from_playlists(sp, dynamic_playlists)
            for aid, data in dynamic_artists.items():
                if aid not in all_artists:
                    all_artists[aid] = data

    # Fase 1c: Fallback por gênero se ainda não tem artistas suficientes
    if len(all_artists) < 10:
        print("\n--- FASE 1c: Busca por Gênero (fallback) ---")
        genres = [
            'sertanejo universitario', 'funk brasil', 'pop brasil',
            'pagode', 'trap brasileiro', 'sertanejo', 'rap brasileiro',
        ]
        search_artists = build_from_search(sp, genres)
        for aid, data in search_artists.items():
            if aid not in all_artists:
                all_artists[aid] = data

    if not all_artists:
        print("[ERRO] Nenhum artista encontrado. Verifique as credenciais.")
        return None

    print(f"\n  Total de artistas únicos nas playlists: {len(all_artists)}")

    # Fase 2: Enriquecer com dados completos do Spotify
    print(f"\n--- FASE 2: Enriquecendo com Spotify API ---")
    enriched = []
    for aid, data in all_artists.items():
        try:
            artist_full = sp.artist(aid)
            pop = artist_full['popularity']
            followers = artist_full['followers']['total']

            # Filtra por popularity mínima (remove artistas irrelevantes)
            if pop < min_popularity:
                continue

            enriched.append({
                'artist_name': artist_full['name'],
                'spotify_id': aid,
                'followers': followers,
                'popularity': pop,
                'genres': '; '.join(artist_full.get('genres', [])[:3]),
                'source': data.get('source', 'unknown'),
                'occurrence_count': data.get('occurrence_count', 1),
            })
        except Exception as e:
            print(f"  [SKIP] {data.get('artist_name', aid)}: {e}")

    print(f"  Artistas com popularity >= {min_popularity}: {len(enriched)}")

    # Fase 2b: Validação e deduplicação de perfis do Spotify
    enriched = _validate_and_deduplicate(sp, enriched)

    # Fase 3: Buscar canal YouTube + total de views
    print(f"\n--- FASE 3: Buscando canais no YouTube ---")
    final_artists = []
    quota_exhausted = False
    for i, artist in enumerate(enriched):
        if quota_exhausted:
            break
        name = artist['artist_name']
        print(f"  [{i+1}/{len(enriched)}] {name}...", end=' ')

        channel_id, total_views = find_youtube_channel(youtube, name)

        if channel_id == 'QUOTA_EXHAUSTED':
            print(
                f"\n  [QUOTA ESGOTADA] Parando após {len(final_artists)} artistas com canal.")
            quota_exhausted = True
            continue
        elif channel_id and total_views > 0:
            artist['youtube_channel_id'] = channel_id
            artist['total_youtube_views'] = total_views
            artist['extraction_date'] = today
            artist['selection_criteria'] = 'Top 50 Brasil Playlists + YouTube Views'
            final_artists.append(artist)
            print(f"[v] {channel_id} ({total_views:,} views)")
        else:
            print(f"[X] canal não encontrado")

    print(f"\n  Artistas com canal YouTube encontrado: {len(final_artists)}")

    if not final_artists:
        print("[ERRO] Nenhum artista com canal YouTube encontrado.")
        return None

    df = pd.DataFrame(final_artists)

    # Ordena por total de views no YouTube (descendente) -- ranking real
    df = df.sort_values('total_youtube_views',
                        ascending=False).reset_index(drop=True)

    if len(df) > max_artists:
        df = df.head(max_artists)

    # Salva
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8')

    print(f"\n{'=' * 60}")
    print(f"BASE DE ARTISTAS TOP 50 BR -- RESULTADO FINAL")
    print(f"{'=' * 60}")
    print(f"  Total: {len(df)} artistas")
    print(f"  Salvo em: {output_file}")
    print(f"  Data de extração: {today}")
    print(f"\n  Top 10 por views no YouTube:")
    for i, (_, row) in enumerate(df.head(10).iterrows()):
        yt_views = row.get('total_youtube_views', 0)
        print(
            f"    {i+1}. {row['artist_name']} | YT={yt_views:,.0f} views | Spotify pop={row['popularity']} | {row['followers']:,} seg")
    print(f"{'=' * 60}")

    return df


if __name__ == "__main__":
    OFFICIAL_PLAYLISTS = [
        {'id': '37i9dQZEVXbMXbN3EUUhlg', 'name': 'Top 50 Brasil'},
        {'id': '37i9dQZEVXbKzoK95AbRy9', 'name': 'Viral 50 Brasil'},
        {'id': '37i9dQZF1DX0FOF1IUWK1W', 'name': 'Top Hits Brasil'},
    ]
    build_artist_base(OFFICIAL_PLAYLISTS, max_artists=50, min_popularity=60)

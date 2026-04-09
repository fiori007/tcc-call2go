"""
Scraper para capturar links estruturados da aba Sobre (About) de canais do YouTube.

A YouTube Data API v3 NÃO expõe os links estruturados que aparecem na aba Sobre
do canal (aqueles botões de Instagram, Spotify, TikTok, etc.). Esses links só
existem no HTML da página.

Este módulo faz web scraping de DUAS páginas por canal:
1. Página principal do canal -- captura links do ytInitialData
2. Página /about -- captura channelExternalLinkViewModel (links estruturados)

Para canais OAC (auto-gerados pelo YouTube / Topic channels), o scraper
busca automaticamente o canal OFICIAL do artista via YouTube Search,
pois canais OAC não possuem links personalizados.

Saída: data/raw/channel_links_scraped.json
"""
import os
import re
import json
import time
import requests
from urllib.parse import unquote, quote_plus


_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

_SPOTIFY_DOMAINS = ['open.spotify.com', 'spoti.fi',
                    'sptfy.com', 'spotify.com', 'spotify.link']

_INTERNAL_DOMAINS = [
    'youtube.com', 'ytimg.com', 'googlevideo.com',
    'googleadservices.com', 'google.com', 'gstatic.com',
    'googleapis.com', 'ggpht.com', 'youtube-nocookie.com',
    'googleusercontent.com', 'schema.org',
]


def _extract_urls_from_text(text):
    """Extrai todos os URLs de um bloco de texto, decodificando redirects."""
    # Unescape JSON unicode sequences que quebram a extração de URLs
    # YouTube usa \u0026 para & no JSON, o que impede capturar ?q= dos redirects
    text = text.replace('\\u0026', '&')
    text = text.replace('\\u003d', '=')
    text = text.replace('\\u003c', '<')
    text = text.replace('\\u003e', '>')
    text = text.replace('\\u002F', '/')
    text = text.replace('\\u002f', '/')

    urls = []
    seen = set()

    for match in re.finditer(r'https?://[^\s"\\<>{}|^`\[\]]+', text):
        u = match.group(0)

        # Decodifica YouTube redirects
        if 'youtube.com/redirect' in u and 'q=' in u:
            q_match = re.search(r'[?&]q=([^&"]+)', u)
            if q_match:
                u = unquote(q_match.group(1))

        # Decodifica URL-encoded
        if '%3A%2F%2F' in u:
            u = unquote(u)

        u = u.rstrip('.,;:)]}')

        # Filtra internas
        if any(d in u.lower() for d in _INTERNAL_DOMAINS):
            continue
        if u in seen or len(u) < 10:
            continue

        seen.add(u)
        urls.append(u)

    return urls


def _is_spotify_url(url):
    """Verifica se um URL é do Spotify."""
    return any(d in url.lower() for d in _SPOTIFY_DOMAINS)


def find_official_channel(artist_name, session=None):
    """
    Busca o canal OFICIAL de um artista no YouTube via scraping da página de busca.

    Canais OAC (auto-gerados / Topic) não possuem links personalizados.
    Esta função pesquisa no YouTube pelo nome do artista e retorna o
    channel_id do primeiro canal OFICIAL encontrado (não-OAC).

    Estratégia:
        1. Busca no YouTube: "{artist_name} canal oficial"
        2. Extrai channel_ids do ytInitialData da página de resultados
        3. Filtra channels que NÃO são Topic/OAC
        4. Retorna o primeiro match

    Returns:
        channel_id (str) ou None se não encontrar
    """
    if session is None:
        session = requests.Session()

    query = quote_plus(f"{artist_name} canal oficial")
    url = f"https://www.youtube.com/results?search_query={query}&sp=EgIQAg%3D%3D"
    # sp=EgIQAg== filtra por "Canais" nos resultados de busca

    try:
        resp = session.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text

        yt_match = re.search(
            r'(?:var\s+)?ytInitialData\s*=\s*({.*?})\s*;\s*</script>',
            html, re.DOTALL
        )
        if not yt_match:
            return None

        data = yt_match.group(1)

        # Extrai todos os channel_ids dos resultados
        # Formato: "channelId":"UC..."
        channel_ids = re.findall(
            r'"channelId"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"', data)
        if not channel_ids:
            return None

        # Remove duplicatas mantendo ordem
        seen = set()
        unique_ids = []
        for cid in channel_ids:
            if cid not in seen:
                seen.add(cid)
                unique_ids.append(cid)

        # Verifica cada canal encontrado -- retorna o primeiro que NÃO é OAC
        for cid in unique_ids[:5]:  # Testa no máximo os 5 primeiros
            time.sleep(0.5)
            try:
                resp_ch = session.get(
                    f"https://www.youtube.com/channel/{cid}/about",
                    headers=_HEADERS, timeout=15
                )
                resp_ch.raise_for_status()
                ch_html = resp_ch.text

                # Se NÃO é OAC, é o canal oficial
                if 'Gerado automaticamente pelo YouTube' not in ch_html and \
                   'Auto-generated by YouTube' not in ch_html:
                    return cid

            except requests.RequestException:
                continue

        return None

    except requests.RequestException as e:
        print(f"  [ERRO] Busca oficial para '{artist_name}': {e}")
        return None


def scrape_channel_links(channel_id, session=None):
    """
    Acessa a página do canal + /about no YouTube e extrai links.

    Estratégia em 2 fases:
        Fase 1: Página principal -- extrai ytInitialData para links gerais
        Fase 2: Página /about -- extrai channelExternalLinkViewModel para links
                 estruturados da aba Sobre (botões de redes sociais)

    Também detecta se o canal é auto-gerado (OAC).

    Returns:
        dict com 'links', 'spotify_links', 'has_spotify', 'is_auto_generated_channel'
    """
    if session is None:
        session = requests.Session()

    all_links = []
    spotify_links = []
    is_oac = False

    # Fase 1: Página principal do canal
    try:
        resp = session.get(
            f"https://www.youtube.com/channel/{channel_id}",
            headers=_HEADERS, timeout=15
        )
        resp.raise_for_status()
        html_main = resp.text

        yt_match = re.search(
            r'(?:var\s+)?ytInitialData\s*=\s*({.*?})\s*;\s*</script>',
            html_main, re.DOTALL
        )
        if yt_match:
            all_links.extend(_extract_urls_from_text(yt_match.group(1)))

    except requests.RequestException as e:
        print(f"  [ERRO] Página principal {channel_id}: {e}")
        return {
            'links': [], 'spotify_links': [], 'has_spotify': False,
            'is_auto_generated_channel': False, 'error': str(e)
        }

    # Fase 2: Página /about (links estruturados)
    try:
        time.sleep(0.5)  # delay entre requests ao mesmo canal
        resp_about = session.get(
            f"https://www.youtube.com/channel/{channel_id}/about",
            headers=_HEADERS, timeout=15
        )
        resp_about.raise_for_status()
        html_about = resp_about.text

        # Detecta canal auto-gerado (OAC)
        if 'Gerado automaticamente pelo YouTube' in html_about or 'Auto-generated by YouTube' in html_about:
            is_oac = True

        # Extrai channelExternalLinkViewModel -- links estruturados
        yt_about_match = re.search(
            r'(?:var\s+)?ytInitialData\s*=\s*({.*?})\s*;\s*</script>',
            html_about, re.DOTALL
        )
        if yt_about_match:
            about_data = yt_about_match.group(1)

            # Busca todos os URLs do about data inteiro (inclui redirect URLs)
            # Important: fazemos no about_data completo para pegar URLs de redirect
            # com q= que contêm as URLs reais dos links estruturados
            about_urls = _extract_urls_from_text(about_data)
            all_links.extend(about_urls)

        # Fallback: busca direta no HTML por URLs do Spotify
        spotify_html = re.findall(
            r'(https?://(?:open\.spotify\.com|spoti\.fi|sptfy\.com|spotify\.link)[^\s"\\<>]*)',
            html_about, re.IGNORECASE
        )
        for link in spotify_html:
            clean = link.rstrip('.,;:)')
            if clean not in all_links:
                all_links.append(clean)

    except requests.RequestException as e:
        print(f"  [AVISO] Página /about {channel_id}: {e}")

    # Deduplica e classifica
    seen = set()
    unique_links = []
    for u in all_links:
        if u not in seen:
            seen.add(u)
            unique_links.append(u)
            if _is_spotify_url(u):
                spotify_links.append(u)

    return {
        'links': unique_links,
        'spotify_links': spotify_links,
        'has_spotify': len(spotify_links) > 0,
        'is_auto_generated_channel': is_oac,
    }


def scrape_all_channels(artists_channels, output_file="data/raw/channel_links_scraped.json",
                        delay=2.0, force=False):
    """
    Faz scraping de todos os canais dos artistas.

    Para canais OAC (auto-gerados), busca automaticamente o canal oficial
    do artista via YouTube Search e faz scraping dele também.

    Args:
        artists_channels: dict {artist_name: channel_id}
        output_file: caminho para salvar o cache JSON
        delay: segundos entre requests (respeita rate limiting)
        force: se True, ignora cache e re-scrapa todos
    """
    print("=" * 60)
    print("SCRAPING DE LINKS ESTRUTURADOS DOS CANAIS DO YOUTUBE")
    print("(Página principal + /about + descoberta de canal oficial)")
    print("=" * 60)

    cache = {}
    if not force and os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        print(
            f"  Cache existente: {len(cache)} canais (use --force para re-scraper)")

    session = requests.Session()
    total = len(artists_channels)
    scraped = 0
    spotify_found = 0
    oac_count = 0
    official_found = 0

    for i, (artist, channel_id) in enumerate(artists_channels.items()):
        # Usa cache se já existe e não tem erro
        if not force and channel_id in cache and 'error' not in cache[channel_id]:
            result = cache[channel_id]
            oac_tag = " [OAC]" if result.get(
                'is_auto_generated_channel') else ""
            spotify_tag = "Spotify SIM" if result['has_spotify'] else "sem Spotify"
            official_tag = ""
            if result.get('official_channel_id'):
                official_tag = f" -> oficial: {result['official_channel_id'][:15]}..."
            print(
                f"  [{i+1}/{total}] {artist}: CACHE ({spotify_tag}{oac_tag}{official_tag})")
            if result['has_spotify']:
                spotify_found += 1
            if result.get('is_auto_generated_channel'):
                oac_count += 1
            if result.get('official_channel_id'):
                official_found += 1
            continue

        print(f"  [{i+1}/{total}] Scraping: {artist} ({channel_id})...", end=' ')

        result = scrape_channel_links(channel_id, session)
        result['artist_name'] = artist

        oac_tag = ""
        if result.get('is_auto_generated_channel'):
            oac_count += 1
            oac_tag = " [OAC]"

            # Canal é OAC -> busca canal oficial do artista
            print(f"OAC detectado. Buscando canal oficial...", end=' ')
            time.sleep(delay)
            official_id = find_official_channel(artist, session)

            if official_id:
                official_found += 1
                result['official_channel_id'] = official_id
                print(f"encontrado: {official_id}. Scraping...", end=' ')
                time.sleep(delay)

                # Faz scraping do canal oficial
                official_result = scrape_channel_links(official_id, session)
                official_result['artist_name'] = artist

                # Armazena o canal oficial no cache também (com chave própria)
                cache[official_id] = official_result

                # Mescla links do oficial no resultado do OAC
                # para que a lookup por artist->channel_id funcione
                result['official_links'] = official_result['links']
                result['official_spotify_links'] = official_result['spotify_links']

                # O has_spotify do artista = oficial OU OAC
                if official_result['has_spotify']:
                    result['has_spotify'] = True
                    result['spotify_links'] = official_result['spotify_links']
                    # Também garante que os links estejam no resultado principal
                    for link in official_result['spotify_links']:
                        if link not in result.get('spotify_links', []):
                            result.setdefault('spotify_links', []).append(link)

            else:
                print(f"canal oficial NÃO encontrado.", end=' ')
                result['official_channel_id'] = None

        cache[channel_id] = result

        if result['has_spotify']:
            spotify_found += 1
            print(f"[OK] Spotify: {result['spotify_links']}{oac_tag}")
        else:
            print(f"-- sem Spotify ({len(result['links'])} links){oac_tag}")

        scraped += 1
        if i < total - 1:
            time.sleep(delay)

    # Salva cache
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    print(
        f"\n[OK] Scraping concluído: {scraped} novos + {total - scraped} do cache")
    print(f"[OK] Artistas com Spotify no perfil: {spotify_found}/{total}")
    print(f"[!]  Canais auto-gerados (OAC): {oac_count}/{total}")
    print(
        f"📌 Canais oficiais descobertos (para OAC): {official_found}/{oac_count}")
    print(f"[OK] Cache salvo em: {output_file}")

    return cache


def load_cached_channel_links(cache_file="data/raw/channel_links_scraped.json"):
    """Carrega links já scrapeados do cache."""
    if not os.path.exists(cache_file):
        return {}
    with open(cache_file, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == "__main__":
    import sys

    force = '--force' in sys.argv

    # Carrega artistas -> channel_ids preferencialmente do CSV seed
    artists_channels = {}
    seed_file = "data/seed/artistas.csv"
    jsonl_file = "data/raw/youtube_videos_raw.jsonl"

    if os.path.exists(seed_file):
        import pandas as pd
        df = pd.read_csv(seed_file)
        for _, row in df.iterrows():
            name = row.get('artist_name')
            cid = row.get('youtube_channel_id')
            if name and isinstance(cid, str) and cid.startswith('UC'):
                artists_channels[name] = cid
        print(f"  Carregados {len(artists_channels)} artistas de {seed_file}")
    elif os.path.exists(jsonl_file):
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                v = json.loads(line)
                a = v.get('artist_name')
                c = v.get('channel_id')
                if a and c and a not in artists_channels:
                    artists_channels[a] = c
        print(f"  Carregados {len(artists_channels)} artistas de {jsonl_file}")
    else:
        print("[ERRO] Nenhuma fonte de dados encontrada.")
        sys.exit(1)

    scrape_all_channels(artists_channels, force=force)

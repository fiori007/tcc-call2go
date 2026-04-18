"""
Processador de Charts — Artistas Persistentes Cross-Platform
=============================================================

Processa CSVs semanais de charts do Spotify (Top 200) e YouTube (Top 100)
para identificar artistas com presença persistente nos 3 meses (Jan-Mar 2026)
em ambas plataformas.

Metodologia:
  1. Spotify: extrai artistas de cada track (split por vírgula)
  2. YouTube: extrai artistas de cada track (split por ' & ', com proteção de duplas)
  3. Presença binária: artista apareceu ≥1 vez no mês = presente naquele mês
  4. Filtro de persistência: artista presente em TODOS os 3 meses
  5. Interseção cross-platform: artistas persistentes em AMBAS as plataformas

Problema resolvido — Ambiguidade do '&' no YouTube:
  O YouTube usa ' & ' tanto para separar artistas distintos (DJ Japa NK & MC Ryan SP)
  quanto em nomes oficiais de duplas sertanejas (Diego & Victor Hugo).
  Solução: extrair lista de duplas conhecidas do Spotify (que usa vírgula como
  separador, tornando a detecção trivial) e usá-la como lookup ao parsear YouTube.

Limitação documentada:
  Featured artists que aparecem SOMENTE no título da track no YouTube
  (ex: 'feat. DJ DAVI DOGDOG') não são extraídos — parsing de texto livre
  com nomes separados por espaço é frágil demais. Usa-se apenas a coluna
  'Artist Names'. Spotify inclui todos os artistas (incluindo feats) na coluna
  'artist_names', então essa limitação afeta apenas o YouTube.
"""

import os
import re
import glob
import csv
import unicodedata
from collections import defaultdict


# ─────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────

_SPOTIFY_CHARTS_DIR = "data/raw/spotify_charts"
_YOUTUBE_CHARTS_DIR = "data/raw/youtube_charts"
_OUTPUT_DIR = "data/processed"

# Mapeamento de mês pelo número no filename
# Abril (mês 4) é atribuído a Março — semana de chart ~27/Mar-02/Abr
_MONTH_MAP = {1: 'jan', 2: 'fev', 3: 'mar', 4: 'mar'}
_REQUIRED_MONTHS = {'jan', 'fev', 'mar'}

# ─────────────────────────────────────────────────────
# Detecção automática de labels/selos/gravadoras
# ─────────────────────────────────────────────────────

# Keywords que indicam entidades não-artísticas (labels, selos, gravadoras)
# Compilado uma vez na carga do módulo para performance
_LABEL_KEYWORDS = re.compile(
    r'\b('
    r'records?|'
    r'ent(ertainment)?|'
    r'label|'
    r'selo|'
    r'produtora|'
    r'productions?|'
    r'produ[çc][õo]es|'
    r'gravadora|'
    r'distribuidora|'
    r'music\s*group|'
    r'publishing'
    r')\b',
    re.IGNORECASE
)

# Padrões que indicam artistas legítimos — poder de VETO sobre keywords
# Protege DJs, MCs, beatmakers, produtores musicais, grupos, bandas etc.
_ARTIST_PATTERNS = re.compile(
    r'\b('
    r'dj|'
    r'mc|'
    r'beat[sz]?|'
    r'no\s*beat|'
    r'produtor|'
    r'grupo|'
    r'banda|'
    r'trio|'
    r'dupla|'
    r'rapper|'
    r'cantor[a]?'
    r')\b',
    re.IGNORECASE
)

# Override manual para edge cases não capturados por keywords
# Entidades que são labels/selos mas cujo nome não contém keywords detectáveis
_LABEL_OVERRIDES = {
    'get worship',
}


# ─────────────────────────────────────────────────────
# Classificação de entidade (artista vs label)
# ─────────────────────────────────────────────────────


def _collect_source_labels(csv_files):
    """
    Coleta todos os valores únicos do campo 'source' dos CSVs do Spotify Charts.

    O campo 'source' contém o nome da distribuidora/selo de cada track.
    Útil como referência cruzada para detecção de labels.

    Returns:
        set[str]: nomes de source normalizados (lowercase, strip, sem pontuação final)
    """
    sources = set()
    for filepath in csv_files:
        with open(filepath, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw = row.get('source', '').strip()
                if raw:
                    # Normaliza: lowercase, strip pontuação final (.),
                    # colapsa espaços
                    normalized = raw.lower().rstrip('.').strip()
                    normalized = re.sub(r'\s+', ' ', normalized)
                    sources.add(normalized)
    return sources


def _classify_entity(name, source_labels=None):
    """
    Classifica se um nome é artista legítimo ou label/selo/gravadora.

    Lógica em camadas (ordem importa):
      1. Override manual → label (edge cases hardcoded)
      2. Artist pattern match (DJ, MC, Beat) → artista (veto — protege
         beatmakers e DJs de serem confundidos com labels)
      3. Label keyword match (Records, Ent) → label
      4. Default → artista

    IMPORTANTE: O campo 'source' dos charts Spotify NÃO é usado como
    critério de exclusão sozinho. Artistas self-distributed (ex: Vitinho
    Imperador) aparecem como source de si mesmos e seriam falsos positivos.
    O source é apenas referência informativa para auditoria futura.

    Args:
        name: nome da entidade a classificar
        source_labels: set de sources normalizados (informativo, não excludente)

    Returns:
        tuple: ('artist', None) ou ('label', motivo_string)
    """
    key = _normalize_key(name)

    # Camada 1: Override manual — edge cases hardcoded
    if key in _LABEL_OVERRIDES:
        return ('label', f'override: {key}')

    # Camada 2: Padrões de artista — poder de VETO
    # Se o nome contém DJ, MC, Beat etc., é artista independente de keywords
    if _ARTIST_PATTERNS.search(key):
        return ('artist', None)

    # Camada 3: Keywords de label no nome
    match = _LABEL_KEYWORDS.search(key)
    if match:
        return ('label', f'keyword: {match.group()}')

    # Camada 4: Default → artista
    return ('artist', None)


# ─────────────────────────────────────────────────────
# Normalização de nomes de artistas
# ─────────────────────────────────────────────────────

def _normalize_key(name):
    """
    Gera chave normalizada para comparação intra-plataforma.
    Lowercase, strip, colapsa espaços múltiplos, normaliza Unicode NFC.
    """
    key = name.strip().lower()
    key = re.sub(r'\s+', ' ', key)
    key = unicodedata.normalize('NFC', key)
    return key


def _cross_platform_key(name):
    """
    Gera chave de matching cross-platform.

    Além da normalização padrão, trata equivalência '&' ↔ 'e' em nomes
    de duplas sertanejas (ex: 'Diego & Victor Hugo' = 'Diego e Victor Hugo').
    """
    key = _normalize_key(name)
    # Normaliza conector: ' & ' → ' e ' para matching cross-platform
    key = key.replace(' & ', ' e ')
    return key


# ─────────────────────────────────────────────────────
# Extração de mês pelo filename
# ─────────────────────────────────────────────────────

def _extract_month_spotify(filename):
    """
    Extrai mês do filename Spotify.
    Formato: regional-br-weekly-YYYY-MM-DD.csv
    """
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})\.csv$', filename)
    if not match:
        raise ValueError(f"Formato inesperado de filename Spotify: {filename}")
    month_num = int(match.group(2))
    month = _MONTH_MAP.get(month_num)
    if month is None:
        raise ValueError(f"Mês {month_num} fora do intervalo Q1 em {filename}")
    return month


def _extract_month_youtube(filename):
    """
    Extrai mês do filename YouTube.
    Formato: youtube-charts-top-songs-br-weekly-YYYYMMDD.csv
    """
    match = re.search(r'(\d{4})(\d{2})(\d{2})\.csv$', filename)
    if not match:
        raise ValueError(f"Formato inesperado de filename YouTube: {filename}")
    month_num = int(match.group(2))
    month = _MONTH_MAP.get(month_num)
    if month is None:
        raise ValueError(f"Mês {month_num} fora do intervalo Q1 em {filename}")
    return month


# ─────────────────────────────────────────────────────
# Splitting de artistas por plataforma
# ─────────────────────────────────────────────────────

def _split_spotify_artists(artist_names_field):
    """
    Extrai lista de artistas de um campo artist_names do Spotify.

    Spotify usa vírgula para separar artistas distintos.
    O '&' em nomes como 'Diego & Victor Hugo' é parte do nome oficial
    da dupla e NÃO é separador.

    Exemplo:
        'Diego & Victor Hugo, Ana Castela' → ['Diego & Victor Hugo', 'Ana Castela']
    """
    return [name.strip() for name in artist_names_field.split(',')
            if name.strip()]


def _extract_known_duos(all_spotify_names):
    """
    Identifica duplas/grupos a partir dos artistas do Spotify.

    Como Spotify usa vírgula como separador de artistas, qualquer nome
    individual que contenha '&' ou 'e' como conector é necessariamente
    um nome oficial de dupla/grupo (ex: 'Diego & Victor Hugo',
    'Henrique & Juliano', 'Felipe e Rodrigo').

    Para duplas com 'e' no Spotify, gera também a variante com '&'
    para lookup no YouTube — que pode usar '&' onde Spotify usa 'e'
    (ex: YouTube 'Felipe & Rodrigo' = Spotify 'Felipe e Rodrigo').

    Returns:
        dict: {nome_normalizado_lower_com_ampersand: nome_canonical_spotify}
    """
    duos = {}

    # Captura duplas com '&' (ex: 'Diego & Victor Hugo')
    for name in all_spotify_names:
        if ' & ' in name:
            duos[_normalize_key(name)] = name

    # Captura duplas com 'e' e gera variante '&' para YouTube
    # YouTube pode grafar 'Felipe & Rodrigo' onde Spotify grafa 'Felipe e Rodrigo'
    for name in all_spotify_names:
        key_lower = _normalize_key(name)
        if ' e ' in key_lower and ' & ' not in name:
            key_ampersand = key_lower.replace(' e ', ' & ', 1)
            if key_ampersand not in duos:
                duos[key_ampersand] = name

    return duos


def _split_youtube_artists(artist_names_field, known_duos_lower):
    """
    Extrai lista de artistas de um campo Artist Names do YouTube.

    YouTube usa ' & ' tanto para separar artistas distintos QUANTO em nomes
    de duplas. Para desambiguar:
      1. Identifica e protege duplas conhecidas (extraídas do Spotify)
         via substituição por placeholder temporário
      2. Splita o restante por ' & '
      3. Restaura os nomes reais das duplas

    Limitação conhecida: duplas que aparecem SOMENTE no YouTube (sem
    correspondência no Spotify) serão splitadas incorretamente. Porém,
    como a análise final exige presença em AMBAS plataformas, esses
    artistas seriam descartados na interseção cross-platform de qualquer forma.

    Args:
        artist_names_field: string bruta do CSV YouTube
        known_duos_lower: dict {nome_lower: nome_canonical} de duplas

    Returns:
        list[str]: nomes de artistas com duplas preservadas
    """
    text = artist_names_field.strip()
    if not text:
        return []

    text_lower = text.lower()

    # Fase 1: Proteger duplas conhecidas
    # Ordena por tamanho (maior primeiro) para evitar matches parciais
    protected = {}
    for duo_lower in sorted(known_duos_lower.keys(), key=len, reverse=True):
        idx = text_lower.find(duo_lower)
        if idx != -1:
            after_end = idx + len(duo_lower)

            # Verificação de fronteira: a dupla deve estar delimitada por
            # início/fim da string ou pelo separador ' & '
            before_ok = (idx == 0 or text_lower[idx - 3:idx] == ' & ')
            after_ok = (after_end >= len(text_lower) or
                        text_lower[after_end:after_end + 3] == ' & ')

            if before_ok and after_ok:
                placeholder = f"__DUO{len(protected)}__"
                original_text = text[idx:after_end]
                protected[placeholder] = original_text
                text = text[:idx] + placeholder + text[after_end:]
                text_lower = text.lower()

    # Fase 2: Split por ' & '
    parts = [p.strip() for p in text.split(' & ')]

    # Fase 3: Restaurar placeholders → nomes reais das duplas
    artists = []
    for part in parts:
        for placeholder, original in protected.items():
            part = part.replace(placeholder, original)
        part = part.strip()
        if part:
            artists.append(part)

    return artists


# ─────────────────────────────────────────────────────
# Processamento por plataforma
# ─────────────────────────────────────────────────────

def _process_platform(csv_files, month_extractor, artist_splitter, platform_name):
    """
    Lógica genérica de processamento de charts para qualquer plataforma.

    Para cada CSV semanal:
      1. Determina o mês pelo filename
      2. Extrai artistas de cada track
      3. Registra presença mensal (binária) e contagem de semanas

    Args:
        csv_files: lista de paths de CSVs ordenados
        month_extractor: função filename → mês ('jan'/'fev'/'mar')
        artist_splitter: função artist_names_field → [nomes]
        platform_name: 'Spotify' ou 'YouTube' (para logs)

    Returns:
        dict: {normalized_key: {canonical, months, total_weeks}}
    """
    # Colunas de artistas diferem entre plataformas
    artist_col = 'artist_names' if platform_name == 'Spotify' else 'Artist Names'

    artist_data = defaultdict(lambda: {
        'canonical': '', 'months': set(), 'total_weeks': 0
    })

    for filepath in csv_files:
        filename = os.path.basename(filepath)
        month = month_extractor(filename)

        with open(filepath, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            week_artists = set()  # Artistas únicos nesta semana

            for row in reader:
                names = artist_splitter(row[artist_col])
                for name in names:
                    key = _normalize_key(name)
                    week_artists.add(key)
                    # Preserva primeira forma canônica encontrada
                    if not artist_data[key]['canonical']:
                        artist_data[key]['canonical'] = name
                    artist_data[key]['months'].add(month)

            # Incrementa semanas para cada artista presente nesta semana
            for key in week_artists:
                artist_data[key]['total_weeks'] += 1

        print(f"  {filename} → mês={month}, "
              f"artistas únicos na semana={len(week_artists)}")

    return dict(artist_data)


def process_spotify_charts(input_dir=_SPOTIFY_CHARTS_DIR):
    """
    Processa 13 CSVs semanais do Spotify Charts Brasil (Top 200).

    Returns:
        tuple: (persistent, all_names, monthly_stats, source_labels)
            persistent: artistas presentes nos 3 meses
            all_names: todos os nomes canônicos (para extração de duplas)
            monthly_stats: contagem de artistas únicos por mês
            source_labels: set de nomes de distribuidoras/selos dos charts
    """
    csv_files = sorted(glob.glob(os.path.join(input_dir, '*.csv')))
    if not csv_files:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {input_dir}")

    print(f"\n{'=' * 60}")
    print(f"  SPOTIFY — Processando {len(csv_files)} CSVs semanais (Top 200)")
    print(f"{'=' * 60}")

    artist_data = _process_platform(
        csv_files, _extract_month_spotify,
        _split_spotify_artists, 'Spotify'
    )

    # Coleta nomes de distribuidoras/selos do campo 'source'
    source_labels = _collect_source_labels(csv_files)
    print(f"\n  Distribuidoras/selos encontrados no campo 'source': "
          f"{len(source_labels)}")

    # Coleta todos os nomes canônicos (para extração de duplas)
    all_names = {data['canonical'] for data in artist_data.values()}

    # Estatísticas por mês
    monthly_stats = {}
    for m in ['jan', 'fev', 'mar']:
        monthly_stats[m] = sum(
            1 for d in artist_data.values() if m in d['months']
        )

    # Filtro de persistência: presença nos 3 meses
    persistent = {
        key: data for key, data in artist_data.items()
        if _REQUIRED_MONTHS.issubset(data['months'])
    }

    print(f"\n  Artistas únicos por mês:")
    for m in ['jan', 'fev', 'mar']:
        print(f"    {m.upper()}: {monthly_stats[m]}")
    print(f"  Total artistas únicos (todas as semanas): {len(artist_data)}")
    print(f"  ✓ PERSISTENTES (presença nos 3 meses): {len(persistent)}")

    return persistent, all_names, monthly_stats, source_labels


def process_youtube_charts(input_dir=_YOUTUBE_CHARTS_DIR, known_duos=None):
    """
    Processa 13 CSVs semanais do YouTube Charts Brasil (Top 100).

    Usa duo-aware split para preservar nomes de duplas sertanejas
    que usam '&' no nome oficial.

    Args:
        input_dir: diretório com CSVs YouTube
        known_duos: dict {nome_lower: canonical} de duplas (extraídas do Spotify)

    Returns:
        tuple: (persistent, monthly_stats)
    """
    if known_duos is None:
        known_duos = {}

    csv_files = sorted(glob.glob(os.path.join(input_dir, '*.csv')))
    if not csv_files:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {input_dir}")

    print(f"\n{'=' * 60}")
    print(f"  YOUTUBE — Processando {len(csv_files)} CSVs semanais (Top 100)")
    print(f"  Duplas conhecidas para proteção: {len(known_duos)}")
    print(f"{'=' * 60}")

    # Cria splitter com closure sobre known_duos
    def yt_splitter(field):
        return _split_youtube_artists(field, known_duos)

    artist_data = _process_platform(
        csv_files, _extract_month_youtube,
        yt_splitter, 'YouTube'
    )

    # Estatísticas por mês
    monthly_stats = {}
    for m in ['jan', 'fev', 'mar']:
        monthly_stats[m] = sum(
            1 for d in artist_data.values() if m in d['months']
        )

    # Filtro de persistência
    persistent = {
        key: data for key, data in artist_data.items()
        if _REQUIRED_MONTHS.issubset(data['months'])
    }

    print(f"\n  Artistas únicos por mês:")
    for m in ['jan', 'fev', 'mar']:
        print(f"    {m.upper()}: {monthly_stats[m]}")
    print(f"  Total artistas únicos (todas as semanas): {len(artist_data)}")
    print(f"  ✓ PERSISTENTES (presença nos 3 meses): {len(persistent)}")

    return persistent, monthly_stats


# ─────────────────────────────────────────────────────
# Interseção cross-platform
# ─────────────────────────────────────────────────────

def cross_platform_intersection(spotify_persistent, youtube_persistent,
                                source_labels=None):
    """
    Calcula interseção entre artistas persistentes de ambas plataformas,
    com filtragem automática de labels/selos/gravadoras.

    Normalização cross-platform: lowercase + '&' ↔ 'e' para equivalência
    de nomes de duplas sertanejas entre plataformas.

    Args:
        spotify_persistent: dict de artistas persistentes do Spotify
        youtube_persistent: dict de artistas persistentes do YouTube
        source_labels: set de nomes de distribuidoras/selos (referência)

    Returns:
        tuple: (intersection_list, spotify_only_keys, youtube_only_keys)
    """
    if source_labels is None:
        source_labels = set()
    print(f"\n{'=' * 60}")
    print(f"  INTERSEÇÃO CROSS-PLATFORM")
    print(f"{'=' * 60}")

    # Gerar chaves cross-platform para cada plataforma
    spotify_by_xkey = {}
    for key, data in spotify_persistent.items():
        xkey = _cross_platform_key(data['canonical'])
        spotify_by_xkey[xkey] = {
            'name': data['canonical'],
            'weeks': data['total_weeks'],
        }

    youtube_by_xkey = {}
    for key, data in youtube_persistent.items():
        xkey = _cross_platform_key(data['canonical'])
        youtube_by_xkey[xkey] = {
            'name': data['canonical'],
            'weeks': data['total_weeks'],
        }

    # Calcular conjuntos
    common_keys_raw = set(spotify_by_xkey.keys()) & set(youtube_by_xkey.keys())
    spotify_only = set(spotify_by_xkey.keys()) - common_keys_raw
    youtube_only = set(youtube_by_xkey.keys()) - common_keys_raw

    # ── Filtragem de labels/selos/gravadoras ──
    excluded = []
    common_keys = set()
    for xkey in common_keys_raw:
        # Usa nome do Spotify como referência para classificação
        entity_name = spotify_by_xkey[xkey]['name']
        entity_type, reason = _classify_entity(entity_name, source_labels)
        if entity_type == 'label':
            excluded.append((entity_name, reason))
        else:
            common_keys.add(xkey)

    # Montar lista da interseção (apenas artistas)
    intersection = []
    for xkey in sorted(common_keys):
        sp = spotify_by_xkey[xkey]
        yt = youtube_by_xkey[xkey]
        intersection.append({
            'match_key': xkey,
            'artist_name_spotify': sp['name'],
            'artist_name_youtube': yt['name'],
            'spotify_weeks': sp['weeks'],
            'youtube_weeks': yt['weeks'],
        })

    # ── Relatório ──
    print(f"\n  Spotify persistentes: {len(spotify_persistent)}")
    print(f"  YouTube persistentes: {len(youtube_persistent)}")
    print(f"\n  ┌─────────────────────────────────────────┐")
    print(f"  │  DIAGRAMA DE VENN (artistas únicos)      │")
    print(f"  │                                          │")
    print(f"  │  Só Spotify: {len(spotify_only):>4}                       │")
    print(f"  │  Só YouTube: {len(youtube_only):>4}                       │")
    print(
        f"  │  Interseção bruta: {len(common_keys_raw):>4}                  │")
    print(f"  │                                          │")
    print(f"  └─────────────────────────────────────────┘")

    # Labels removidas
    if excluded:
        print(f"\n  ┌─────────────────────────────────────────┐")
        print(
            f"  │  LABELS/SELOS REMOVIDOS: {len(excluded):>4}              │")
        print(f"  └─────────────────────────────────────────┘")
        for name, reason in sorted(excluded):
            print(f"    ✗ {name} ({reason})")

    print(f"\n  ★ ARTISTAS CONSOLIDADOS (após filtragem): "
          f"{len(intersection)}")

    # Lista completa da interseção
    print(f"\n  Lista dos artistas consolidados "
          f"(3 meses × 2 plataformas):")
    for i, entry in enumerate(intersection, 1):
        sp_name = entry['artist_name_spotify']
        yt_name = entry['artist_name_youtube']
        name_diff = f"  [YT: {yt_name}]" if sp_name != yt_name else ""
        print(f"    {i:>3}. {sp_name}{name_diff}")

    # Artistas que ficaram de fora (referência para análise)
    if spotify_only:
        print(
            f"\n  Artistas persistentes SOMENTE no Spotify ({len(spotify_only)}):")
        for xkey in sorted(spotify_only):
            print(f"    - {spotify_by_xkey[xkey]['name']}")

    if youtube_only:
        print(
            f"\n  Artistas persistentes SOMENTE no YouTube ({len(youtube_only)}):")
        for xkey in sorted(youtube_only):
            print(f"    - {youtube_by_xkey[xkey]['name']}")

    return intersection, list(spotify_only), list(youtube_only)


# ─────────────────────────────────────────────────────
# Persistência — salva CSVs de output
# ─────────────────────────────────────────────────────

def _save_persistent_csv(persistent, output_path, platform_name):
    """Salva artistas persistentes em CSV, ordenados por total_weeks desc."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    rows = []
    for key, data in sorted(persistent.items(),
                            key=lambda x: x[1]['total_weeks'], reverse=True):
        rows.append({
            'artist_name': data['canonical'],
            'total_weeks': data['total_weeks'],
            'jan': 'jan' in data['months'],
            'fev': 'fev' in data['months'],
            'mar': 'mar' in data['months'],
        })

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f, fieldnames=['artist_name', 'total_weeks', 'jan', 'fev', 'mar'])
        writer.writeheader()
        writer.writerows(rows)

    print(f"  [OK] {platform_name}: {len(rows)} artistas → {output_path}")


def _save_intersection_csv(intersection, output_path):
    """Salva interseção cross-platform em CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fields = ['artist_name_spotify', 'artist_name_youtube', 'match_key',
              'spotify_weeks', 'youtube_weeks']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(intersection)

    print(f"  [OK] Interseção: {len(intersection)} artistas → {output_path}")


# ─────────────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────────────

def run_chart_processing(spotify_dir=_SPOTIFY_CHARTS_DIR,
                         youtube_dir=_YOUTUBE_CHARTS_DIR,
                         output_dir=_OUTPUT_DIR):
    """
    Pipeline completo de processamento de charts.

    Etapas:
      A. Processa Spotify Charts → artistas persistentes (3 meses)
      B. Extrai duplas conhecidas do Spotify (nomes com '&')
      C. Processa YouTube Charts → artistas persistentes (duo-aware)
      D. Calcula interseção cross-platform

    Salva 3 CSVs em data/processed/:
      - spotify_persistent_artists.csv
      - youtube_persistent_artists.csv
      - cross_platform_persistent_artists.csv
    """
    print("=" * 60)
    print("  CHART PROCESSOR — Artistas Persistentes Cross-Platform")
    print("  Período: Q1 2026 (Janeiro–Março)")
    print("  Critério: presença binária em TODOS os 3 meses")
    print("=" * 60)

    # ── Fase A: Spotify ──
    spotify_persistent, all_spotify_names, sp_stats, source_labels = \
        process_spotify_charts(spotify_dir)

    # ── Fase B: Extrai duplas conhecidas ──
    known_duos = _extract_known_duos(all_spotify_names)
    print(f"\n  Duplas/grupos identificados no Spotify: {len(known_duos)}")
    for duo_lower, canonical in sorted(known_duos.items()):
        print(f"    • {canonical}")

    # ── Fase C: YouTube (com proteção de duplas) ──
    youtube_persistent, yt_stats = \
        process_youtube_charts(youtube_dir, known_duos)

    # ── Fase D: Interseção cross-platform (com filtragem de labels) ──
    intersection, sp_only, yt_only = \
        cross_platform_intersection(spotify_persistent, youtube_persistent,
                                    source_labels)

    # ── Salva resultados ──
    print(f"\n{'=' * 60}")
    print(f"  SALVANDO RESULTADOS")
    print(f"{'=' * 60}")

    _save_persistent_csv(
        spotify_persistent,
        os.path.join(output_dir, 'spotify_persistent_artists.csv'),
        'Spotify')

    _save_persistent_csv(
        youtube_persistent,
        os.path.join(output_dir, 'youtube_persistent_artists.csv'),
        'YouTube')

    _save_intersection_csv(
        intersection,
        os.path.join(output_dir, 'cross_platform_persistent_artists.csv'))

    # ── Resumo final ──
    print(f"\n{'=' * 60}")
    print(f"  RESULTADO FINAL")
    print(f"{'=' * 60}")
    print(f"  Spotify persistentes (3 meses): {len(spotify_persistent)}")
    print(f"  YouTube persistentes (3 meses): {len(youtube_persistent)}")
    print(f"  Só Spotify: {len(sp_only)}")
    print(f"  Só YouTube: {len(yt_only)}")
    print(f"\n  ★ ARTISTAS CONSOLIDADOS (3 meses × 2 plataformas, "
          f"labels excluídas): {len(intersection)}")
    print(f"{'=' * 60}")

    return intersection


if __name__ == "__main__":
    
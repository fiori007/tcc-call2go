"""
ANALISE DE FUSAO DE RANKINGS -- Cross-Platform Q1 2026

Calcula score de fusao para artistas presentes nos charts semanais
do Spotify e YouTube Brasil (Q1 2026: jan-mar, 13 semanas cada).

Score de fusao: soma de 1/rank para cada mes em que o artista aparece.
Meses sem presenca contribuem 0 para o score.

Artistas do dataset (67 seed) sao marcados com in_dataset=True.
Analises restritas ao dataset: Call2Go, Last.fm, lag temporal.

Analises:
    1. Score de fusao cross-platform (Spotify + YouTube)
    2. Heatmap de presenca mensal
    3. Comparacao Call2Go vs. nao-Call2Go (Mann-Whitney)
    4. Correlacoes com Last.fm (Pearson + Spearman)
    5. Analise de lag temporal (release Spotify vs. primeiro video Call2Go)
    6. Relatorio consolidado

Fluxo:
    python -m src.analytics.ranking_fusion
    ou via run_pipeline.py (etapa 16)
"""

import seaborn as sns
import matplotlib.pyplot as plt
import os
import re
import glob
import unicodedata
import calendar
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats
import matplotlib
matplotlib.use('Agg')


# ============================================================
# NORMALIZACAO DE NOMES
# ============================================================

def _normalize_name(name: str) -> str:
    """Normaliza nome para matching: minusculo, sem acentos, sem pontuacao."""
    name = str(name).lower().strip()
    name = unicodedata.normalize('NFKD', name)
    name = ''.join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r'[^a-z0-9 ]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


# ============================================================
# MAPA DE ARTISTAS (PRIMARY vs. FEATURED)
# ============================================================

def _build_featured_map(weekly_charts_sp: dict, weekly_charts_yt: dict) -> dict:
    """
    Constroi sets de artistas primarios e todos (incluindo featured) por plataforma.

    Spotify: separados por virgula — primario = primeiro token.
    YouTube: separados por ' & ' — primario = primeiro token.

    Retorna dict com chaves:
        'primary_sp': set de primarios normalizados do Spotify
        'all_sp':     set de todos os artistas normalizados do Spotify
        'primary_yt': set de primarios normalizados do YouTube
        'all_yt':     set de todos os artistas normalizados do YouTube
    """
    primary_sp, all_sp = set(), set()
    for df in weekly_charts_sp.values():
        for artists_str in df['artist_names']:
            parts = [a.strip() for a in str(artists_str).split(',')]
            primary_sp.add(_normalize_name(parts[0]))
            for p in parts:
                all_sp.add(_normalize_name(p))

    primary_yt, all_yt = set(), set()
    for df in weekly_charts_yt.values():
        for artists_str in df['artist_names']:
            parts = [a.strip() for a in str(artists_str).split(' & ')]
            primary_yt.add(_normalize_name(parts[0]))
            for p in parts:
                all_yt.add(_normalize_name(p))

    print(
        f"  Spotify: {len(primary_sp)} primarios, {len(all_sp)} total (incl. featured)")
    print(
        f"  YouTube: {len(primary_yt)} primarios, {len(all_yt)} total (incl. featured)")
    return {
        'primary_sp': primary_sp,
        'all_sp': all_sp,
        'primary_yt': primary_yt,
        'all_yt': all_yt,
    }


# ============================================================
# CARGA DE CHARTS SEMANAIS
# ============================================================

def load_weekly_charts(charts_dir: str, platform: str) -> dict:
    """
    Carrega CSVs semanais de charts em um dict {semana: DataFrame}.

    Parametros:
        charts_dir: diretorio com os CSVs
        platform: 'spotify' ou 'youtube'

    Retorna dict com chave 'YYYY-MM-DD' e valor DataFrame com colunas
    [rank (int), artist_names (str), track_name (str)].
    """
    weekly = {}

    if platform == 'spotify':
        pattern = os.path.join(charts_dir, "regional-br-weekly-*.csv")
        files = sorted(glob.glob(pattern))
        for f in files:
            # Extrai data do nome: regional-br-weekly-YYYY-MM-DD.csv
            basename = os.path.basename(f)
            date_part = basename.replace(
                "regional-br-weekly-", "").replace(".csv", "")
            try:
                datetime.strptime(date_part, '%Y-%m-%d')
            except ValueError:
                continue
            try:
                df = pd.read_csv(f)
                df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
                df = df[['rank', 'artist_names', 'track_name']].dropna(
                    subset=['rank'])
                df['rank'] = df['rank'].astype(int)
                weekly[date_part] = df
            except Exception as e:
                print(f"[AVISO] Falha ao ler {f}: {e}")

    elif platform == 'youtube':
        pattern = os.path.join(
            charts_dir, "youtube-charts-top-songs-br-weekly-*.csv")
        files = sorted(glob.glob(pattern))
        for f in files:
            # Extrai data do nome: youtube-charts-top-songs-br-weekly-YYYYMMDD.csv
            basename = os.path.basename(f)
            date_compact = basename.replace(
                "youtube-charts-top-songs-br-weekly-", "").replace(".csv", "")
            try:
                dt = datetime.strptime(date_compact, '%Y%m%d')
                date_part = dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
            try:
                df = pd.read_csv(f)
                df = df.rename(columns={
                    'Rank': 'rank',
                    'Artist Names': 'artist_names',
                    'Track Name': 'track_name',
                })
                df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
                df = df[['rank', 'artist_names', 'track_name']].dropna(
                    subset=['rank'])
                df['rank'] = df['rank'].astype(int)
                weekly[date_part] = df
            except Exception as e:
                print(f"[AVISO] Falha ao ler {f}: {e}")

    print(f"  [{platform}] {len(weekly)} semanas carregadas")
    return weekly


# ============================================================
# ROTULAGEM MENSAL
# ============================================================

def assign_month_label(week_date_str: str) -> str:
    """
    Retorna abreviacao de 3 letras do mes para a semana.

    Usa calendar.month_abbr para abreviacoes em ingles independente do locale.
    Nota Q1 2026: semana 2026-04-02 pertence a marco (ultima semana do Q1).
    """
    dt = datetime.strptime(week_date_str, '%Y-%m-%d')
    # Semana 2026-04-02 representa a ultima semana do Q1 (marco)
    if dt.month == 4 and dt.day <= 7:
        return calendar.month_abbr[3]  # 'Mar'
    return calendar.month_abbr[dt.month]


# ============================================================
# EXTRACAO DO ARTISTA PRIMARIO
# ============================================================

def extract_primary_artist(artist_names: str, platform: str) -> str:
    """
    Extrai o artista primario (primeiro da lista) e normaliza o nome.

    Separadores: ',' para Spotify, ' & ' para YouTube.
    Retorna nome normalizado via _normalize_name.
    """
    if platform == 'spotify':
        primary = str(artist_names).split(',')[0].strip()
    else:  # youtube
        primary = str(artist_names).split(' & ')[0].strip()
    return _normalize_name(primary)


# ============================================================
# AGREGACAO ARTISTA x MES
# ============================================================

def aggregate_to_artist_monthly(weekly_charts: dict, platform: str) -> pd.DataFrame:
    """
    Agrega charts semanais para nivel artista-mes.

    Para cada (artista_normalizado, mes): melhor rank = min(rank)
    entre todas as semanas daquele mes. Inclui todos os artistas dos charts.

    Retorna DataFrame com colunas: [artist_normalized, month, best_rank].
    """
    records = []
    for week_date_str, df in weekly_charts.items():
        month_label = assign_month_label(week_date_str)
        for _, row in df.iterrows():
            artist_norm = extract_primary_artist(row['artist_names'], platform)
            if not artist_norm:
                continue
            records.append({
                'artist_normalized': artist_norm,
                'month': month_label,
                'rank': int(row['rank']),
            })

    if not records:
        return pd.DataFrame(columns=['artist_normalized', 'month', 'best_rank'])

    df_all = pd.DataFrame(records)
    # best_rank = menor rank em cada (artista, mes)
    df_agg = (df_all
              .groupby(['artist_normalized', 'month'], as_index=False)['rank']
              .min()
              .rename(columns={'rank': 'best_rank'}))
    return df_agg


# ============================================================
# ESTATISTICAS DE ENTRADA NOS CHARTS
# ============================================================

def compute_chart_entry_stats(weekly_charts: dict, platform: str) -> dict:
    """
    Computa primeira semana nos charts e total de semanas para cada artista primario.

    Usa o mesmo criterio de extract_primary_artist (artista[0]).
    Retorna dict {artist_normalized: {'first_week': 'YYYY-MM-DD', 'total_weeks': int}}.
    """
    records: dict = {}
    for week_date_str, df in weekly_charts.items():
        for artists_str in df['artist_names']:
            artist_norm = extract_primary_artist(artists_str, platform)
            if not artist_norm:
                continue
            if artist_norm not in records:
                records[artist_norm] = set()
            records[artist_norm].add(week_date_str)

    return {
        artist: {
            'first_week': sorted(weeks)[0],
            'total_weeks': len(weeks),
        }
        for artist, weeks in records.items()
    }


# ============================================================
# PADRAO DE PRESENCA TEMPORAL JAN -> MAR
# ============================================================

def classify_presence_pattern(rank_jan, rank_feb, rank_mar) -> str:
    """
    Classifica o padrao de presenca de um artista nos charts Q1 (Jan -> Mar).

    Taxonomia estrutural pura baseada unicamente na presenca/ausencia
    em cada mes do trimestre. Nenhum threshold numerico e usado.
    A magnitude da variacao de rank e representada em separado pela
    variavel continua rank_delta (rank_jan - rank_mar).

    Categorias (6):
        'absent':       nenhum mes presente
        'single':       exatamente 1 mes presente
        'persistent':   presente nos 3 meses (Jan + Fev + Mar)
        'new':          Jan=ausente E Mar=presente (emergiu no Q1)
        'exit':         Jan=presente E Mar=ausente (saiu no Q1)
        'intermittent': Jan=presente E Fev=ausente E Mar=presente

    Parametros:
        rank_jan, rank_feb, rank_mar: int ou None (None = ausente no mes)
    """
    present_count = sum(
        1 for r in [rank_jan, rank_feb, rank_mar] if r is not None)

    if present_count == 0:
        return 'absent'
    if present_count == 1:
        return 'single'
    if present_count == 3:
        return 'persistent'
    # Exatamente 2 meses presentes: identificar padrao estrutural
    if rank_jan is None and rank_mar is not None:
        return 'new'
    if rank_jan is not None and rank_mar is None:
        return 'exit'
    if rank_jan is not None and rank_feb is None and rank_mar is not None:
        return 'intermittent'
    # Fallback (Jan + Fev, sem Mar -- coberto por present_count==2 acima)
    return 'single'


# ============================================================
# CALCULO DO FUSION SCORE
# ============================================================

def compute_fusion_score(monthly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula score de fusao por artista a partir dos ranks mensais.

    Score = soma de 1/best_rank para cada mes em que o artista aparece.
    Meses ausentes contribuem 0 para o score.

    Retorna DataFrame ordenado por score desc com colunas:
    artist_normalized, score, rank_<mes>, presence_count,
    presence_vector_str, global_rank.
    """
    if monthly_df.empty:
        return pd.DataFrame()

    # Pivot: linhas=artistas, colunas=meses, valores=best_rank
    pivot = monthly_df.pivot_table(
        index='artist_normalized',
        columns='month',
        values='best_rank',
        aggfunc='min',
    )

    # Ordena meses em ordem calendaria
    month_order = {abbr: i for i, abbr in enumerate(
        calendar.month_abbr) if abbr}
    months_sorted = sorted(
        pivot.columns.tolist(),
        key=lambda m: month_order.get(m, 99))
    pivot = pivot[months_sorted]

    # Calcula score e vetor de presenca por artista
    rows = []
    for artist, row in pivot.iterrows():
        score = sum(1.0 / r for r in row if pd.notna(r) and r > 0)
        presence = [1 if pd.notna(r) else 0 for r in row]
        presence_count = sum(presence)
        presence_vector_str = '(' + ','.join(str(p) for p in presence) + ')'
        entry = {
            'artist_normalized': artist,
            'score': round(score, 6),
            'presence_count': presence_count,
            'presence_vector_str': presence_vector_str,
        }
        # Colunas de rank por mes (None se ausente)
        for month in months_sorted:
            val = pivot.at[artist, month]
            entry[f'rank_{month}'] = int(val) if pd.notna(val) else None
        rows.append(entry)

    df_scores = pd.DataFrame(rows)
    df_scores = df_scores.sort_values(
        'score', ascending=False).reset_index(drop=True)
    df_scores['global_rank'] = range(1, len(df_scores) + 1)
    return df_scores


# ============================================================
# TABELA DE FUSAO FINAL
# ============================================================

def build_fusion_table(artists_csv: str) -> pd.DataFrame:
    """
    Constroi tabela de fusao cross-platform para todos os artistas primarios
    nos charts Spotify Top 200 e YouTube Top 100 Brasil (Q1 2026).

    Escopo: apenas artistas primarios (primeiro artista de cada faixa).
    Featurings e colaboracoes secundarias sao excluidos da tabela.
    Artistas-semente (64 do dataset) que aparecem apenas como featured
    NAO sao injetados na tabela — apenas o diagnostico de cobertura e salvo.

    Score combinado normalizado (RRF normalizado):
        score_spotify_normalized = score_spotify / n_semanas_spotify
        score_youtube_normalized = score_youtube / n_semanas_youtube
        score_combined = score_sp_norm + score_yt_norm
    Normalizacao garante comparabilidade entre plataformas independente
    do numero de semanas coletadas. Referencia: Cormack et al., 2009 (SIGIR).

    Padrao de presenca (taxonomia estrutural, 6 categorias, zero threshold):
        absent / single / persistent / new / exit / intermittent
    Variavel continua rank_delta_spotify/youtube = rank_Jan - rank_Mar
    (positivo = melhorou; negativo = piorou; None se algum mes ausente).

    Salva em data/processed/ranking_fusion_scores.csv.
    Diagnostico de seed: data/validation/seed_matching_diagnostic.csv.
    """
    print("\n--- CARGA DE CHARTS ---")
    sp_charts = load_weekly_charts("data/raw/spotify_charts", "spotify")
    yt_charts = load_weekly_charts("data/raw/youtube_charts", "youtube")

    # Numero de semanas por plataforma (para normalizacao do score)
    n_weeks_sp = len(sp_charts)
    n_weeks_yt = len(yt_charts)
    print(f"  Semanas carregadas: Spotify={n_weeks_sp}, YouTube={n_weeks_yt}")

    print("\n--- MAPA DE ARTISTAS FEATURED ---")
    featured_map = _build_featured_map(sp_charts, yt_charts)

    print("\n--- AGREGACAO ARTISTA x MES ---")
    sp_monthly = aggregate_to_artist_monthly(sp_charts, "spotify")
    yt_monthly = aggregate_to_artist_monthly(yt_charts, "youtube")

    print(
        f"  Spotify: {sp_monthly['artist_normalized'].nunique()} artistas unicos")
    print(
        f"  YouTube: {yt_monthly['artist_normalized'].nunique()} artistas unicos")

    print("\n--- ESTATISTICAS DE ENTRADA NOS CHARTS ---")
    sp_entry_stats = compute_chart_entry_stats(sp_charts, "spotify")
    yt_entry_stats = compute_chart_entry_stats(yt_charts, "youtube")

    print("\n--- CALCULO DE FUSION SCORES ---")
    df_sp = compute_fusion_score(sp_monthly)
    df_yt = compute_fusion_score(yt_monthly)

    # Renomeia colunas Spotify com sufixo _sp
    sp_rename = {
        'score': 'score_spotify',
        'presence_count': 'presence_count_spotify',
        'presence_vector_str': 'presence_vector_str_spotify',
        'global_rank': 'global_rank_spotify',
    }
    for col in list(df_sp.columns):
        if col.startswith('rank_'):
            sp_rename[col] = col + '_sp'
    df_sp = df_sp.rename(columns=sp_rename)

    # Renomeia colunas YouTube com sufixo _yt
    yt_rename = {
        'score': 'score_youtube',
        'presence_count': 'presence_count_youtube',
        'presence_vector_str': 'presence_vector_str_youtube',
        'global_rank': 'global_rank_youtube',
    }
    for col in list(df_yt.columns):
        if col.startswith('rank_'):
            yt_rename[col] = col + '_yt'
    df_yt = df_yt.rename(columns=yt_rename)

    # Merge outer: todos os artistas primarios de ambas plataformas
    df_merged = pd.merge(df_sp, df_yt, on='artist_normalized', how='outer')
    df_merged = df_merged.reset_index(drop=True)

    # ---- Seed matching: apenas artistas primarios ----
    df_seed = pd.read_csv(artists_csv)
    seed_norm_map = {_normalize_name(n): n for n in df_seed['artist_name']}

    df_merged['in_dataset'] = df_merged['artist_normalized'].map(
        lambda x: x in seed_norm_map)
    df_merged['artist_name_seed'] = df_merged['artist_normalized'].map(
        seed_norm_map)

    # ---- Score normalizado por numero de semanas (Fase 2) ----
    # Normalizacao garante comparabilidade entre plataformas.
    # score_raw / n_semanas = score medio semanal (invariante ao periodo coletado).
    if n_weeks_sp > 0:
        df_merged['score_spotify_normalized'] = df_merged['score_spotify'] / n_weeks_sp
    else:
        df_merged['score_spotify_normalized'] = df_merged['score_spotify']

    if n_weeks_yt > 0:
        df_merged['score_youtube_normalized'] = df_merged['score_youtube'] / n_weeks_yt
    else:
        df_merged['score_youtube_normalized'] = df_merged['score_youtube']

    # score_combined = soma dos scores normalizados (plataformas em mesma escala)
    df_merged['score_combined'] = (
        df_merged['score_spotify_normalized'].fillna(0)
        + df_merged['score_youtube_normalized'].fillna(0)
    )
    # Artistas sem nenhum score real ficam com NaN
    has_real_score = (
        df_merged['score_spotify'].notna()
        | df_merged['score_youtube'].notna()
    )
    df_merged.loc[~has_real_score, 'score_combined'] = float('nan')

    # Global rank combinado (apenas artistas com pelo menos 1 score real)
    df_merged['global_rank_combined'] = pd.NA
    ranked_idx = (
        df_merged[has_real_score]
        .sort_values('score_combined', ascending=False)
        .index.tolist()
    )
    for pos, idx in enumerate(ranked_idx, start=1):
        df_merged.at[idx, 'global_rank_combined'] = pos

    # ---- Padrao de presenca temporal (taxonomia estrutural) ----
    def _safe_rank(v):
        """Converte valor de rank para int ou None (NaN -> None)."""
        try:
            if pd.isna(v):
                return None
        except TypeError:
            pass
        return None if v is None else int(v)

    if 'rank_Jan_sp' in df_merged.columns:
        df_merged['pattern_spotify'] = df_merged.apply(
            lambda r: classify_presence_pattern(
                _safe_rank(r.get('rank_Jan_sp')),
                _safe_rank(r.get('rank_Feb_sp')),
                _safe_rank(r.get('rank_Mar_sp')),
            ), axis=1)

    if 'rank_Jan_yt' in df_merged.columns:
        df_merged['pattern_youtube'] = df_merged.apply(
            lambda r: classify_presence_pattern(
                _safe_rank(r.get('rank_Jan_yt')),
                _safe_rank(r.get('rank_Feb_yt')),
                _safe_rank(r.get('rank_Mar_yt')),
            ), axis=1)

    # ---- rank_delta: variavel continua de variacao Jan->Mar (Fase 4) ----
    # rank_delta positivo = melhorou (numero menor); negativo = piorou.
    # None quando Jan ou Mar ausentes (sem magnitude calculavel).
    def _rank_delta(jan_val, mar_val):
        """Retorna rank_jan - rank_mar (int) ou None se algum estiver ausente."""
        rj = _safe_rank(jan_val)
        rm = _safe_rank(mar_val)
        if rj is None or rm is None:
            return None
        return rj - rm

    if 'rank_Jan_sp' in df_merged.columns and 'rank_Mar_sp' in df_merged.columns:
        df_merged['rank_delta_spotify'] = df_merged.apply(
            lambda r: _rank_delta(r.get('rank_Jan_sp'), r.get('rank_Mar_sp')),
            axis=1,
        )

    if 'rank_Jan_yt' in df_merged.columns and 'rank_Mar_yt' in df_merged.columns:
        df_merged['rank_delta_youtube'] = df_merged.apply(
            lambda r: _rank_delta(r.get('rank_Jan_yt'), r.get('rank_Mar_yt')),
            axis=1,
        )

    # ---- Datas de entrada nos charts ----
    df_merged['first_chart_week_spotify'] = df_merged['artist_normalized'].map(
        lambda x: sp_entry_stats.get(x, {}).get('first_week'))
    df_merged['total_weeks_spotify'] = df_merged['artist_normalized'].map(
        lambda x: sp_entry_stats.get(x, {}).get('total_weeks'))
    df_merged['first_chart_week_youtube'] = df_merged['artist_normalized'].map(
        lambda x: yt_entry_stats.get(x, {}).get('first_week'))
    df_merged['total_weeks_youtube'] = df_merged['artist_normalized'].map(
        lambda x: yt_entry_stats.get(x, {}).get('total_weeks'))

    # ---- Diagnostico de matching do seed ----
    diag_rows = []
    for norm, original in seed_norm_map.items():
        in_prim_sp = norm in featured_map['primary_sp']
        in_prim_yt = norm in featured_map['primary_yt']
        in_feat_sp = (norm in featured_map['all_sp']) and not in_prim_sp
        in_feat_yt = (norm in featured_map['all_yt']) and not in_prim_yt
        in_table = norm in set(df_merged['artist_normalized'])
        diag_rows.append({
            'artist_name_seed': original,
            'artist_normalized': norm,
            'found_as_primary_sp': in_prim_sp,
            'found_as_primary_yt': in_prim_yt,
            'found_as_featured_sp': in_feat_sp,
            'found_as_featured_yt': in_feat_yt,
            'in_fusion_table': in_table,
        })
    df_diag = pd.DataFrame(diag_rows).sort_values('artist_name_seed')
    os.makedirs("data/validation", exist_ok=True)
    df_diag.to_csv("data/validation/seed_matching_diagnostic.csv", index=False)

    n_any_primary = int(
        (df_diag['found_as_primary_sp'] | df_diag['found_as_primary_yt']).sum())
    n_feat_only = int(
        ((~df_diag['found_as_primary_sp']) & (~df_diag['found_as_primary_yt'])
         & (df_diag['found_as_featured_sp'] | df_diag['found_as_featured_yt'])).sum())
    n_not_found = int(
        (~df_diag['found_as_primary_sp'] & ~df_diag['found_as_primary_yt']
         & ~df_diag['found_as_featured_sp'] & ~df_diag['found_as_featured_yt']).sum())
    print(f"  Cobertura seed: {n_any_primary} primarios (in_dataset=True), "
          f"{n_feat_only} featured-only (excluidos da tabela), "
          f"{n_not_found} nao encontrados")
    print(f"  Diagnostico: data/validation/seed_matching_diagnostic.csv")

    # ---- Salva resultado ----
    os.makedirs("data/processed", exist_ok=True)
    output_path = "data/processed/ranking_fusion_scores.csv"
    df_merged.to_csv(output_path, index=False)

    total = len(df_merged)
    in_ds = int(df_merged['in_dataset'].sum())
    sp_scores = df_merged['score_spotify'].dropna()
    yt_scores = df_merged['score_youtube'].dropna()
    comb_scores = df_merged['score_combined'].dropna()

    print(
        f"\n  Total artistas primarios: {total} | In dataset (seed primario): {in_ds}")
    print(
        f"  Normalizacao: n_semanas_sp={n_weeks_sp}, n_semanas_yt={n_weeks_yt}")
    if not sp_scores.empty:
        print(
            f"  Score Spotify (raw): min={sp_scores.min():.4f}, max={sp_scores.max():.4f}")
    if not yt_scores.empty:
        print(
            f"  Score YouTube (raw): min={yt_scores.min():.4f}, max={yt_scores.max():.4f}")
    if not comb_scores.empty:
        print(
            f"  Score Combinado (norm): min={comb_scores.min():.6f}, max={comb_scores.max():.6f}")
    print(f"  Salvo em: {output_path}")

    return df_merged


# ============================================================
# HEATMAP DE PRESENCA
# ============================================================

def plot_presence_heatmap(df_fusion: pd.DataFrame, output_dir: str):
    """
    Gera heatmaps de presenca mensal para os Top 75 artistas por score_combined.

    Escopo: todos os artistas primarios dos charts (nao restrito ao seed).
    Selecionados os 75 com maior score_combined para legibilidade.
    Linhas: artistas ordenados por score_combined desc. Colunas: meses.
    Cor: 1=presente, 0=ausente.
    Salva presence_heatmap_spotify.png e presence_heatmap_youtube.png.
    figsize=(6,9) dpi=200 -> 1200x1800px (dentro do limite de 1800px).
    """
    os.makedirs(output_dir, exist_ok=True)
    # Top 75 artistas primarios por score_combined (universo completo)
    df_ds = (
        df_fusion
        .dropna(subset=['score_combined'])
        .nlargest(75, 'score_combined')
        .copy()
    )
    print(
        f"  Heatmap: {len(df_ds)} artistas selecionados (top 75 score_combined)")

    month_order = {abbr: i for i, abbr in enumerate(
        calendar.month_abbr) if abbr}

    for platform, score_col, suffix, filename in [
        ('Spotify', 'score_spotify', '_sp', 'presence_heatmap_spotify.png'),
        ('YouTube', 'score_youtube', '_yt', 'presence_heatmap_youtube.png'),
    ]:
        rank_cols = [c for c in df_fusion.columns
                     if c.startswith('rank_') and c.endswith(suffix)]
        if not rank_cols or 'score_combined' not in df_ds.columns:
            print(f"[AVISO] Colunas de rank nao encontradas para {platform}, "
                  "pulando heatmap")
            continue

        # Ordena artistas por score_combined decrescente
        df_plot = df_ds.sort_values('score_combined', ascending=False)

        # Ordena colunas de rank em ordem calendaria
        rank_cols_sorted = sorted(
            rank_cols,
            key=lambda c: month_order.get(
                c.replace('rank_', '').replace(suffix, ''), 99))
        month_labels = [c.replace('rank_', '').replace(suffix, '')
                        for c in rank_cols_sorted]

        # Constroi matriz de presenca (1=presente, 0=ausente)
        artist_labels = df_plot['artist_name_seed'].fillna(
            df_plot['artist_normalized']).tolist()
        presence_matrix = df_plot[rank_cols_sorted].notna().astype(int)
        presence_matrix.index = artist_labels
        presence_matrix.columns = month_labels

        # figsize=(6,9) dpi=200 -> 1200x1800px -- dentro do limite com 75 artistas
        fig, ax = plt.subplots(figsize=(6, 9))
        sns.heatmap(
            presence_matrix,
            cmap='Blues',
            linewidths=0.3,
            ax=ax,
            cbar_kws={'label': 'Presenca'},
            vmin=0,
            vmax=1,
        )
        ax.set_title(
            f'Presenca Mensal -- Top 75 por Score Combinado ({platform} Q1 2026)')
        ax.set_xlabel('Mes')
        ax.set_ylabel('Artista')
        plt.tight_layout()

        out_path = os.path.join(output_dir, filename)
        fig.savefig(out_path, dpi=200)
        plt.close(fig)
        print(f"  [OK] Heatmap salvo: {out_path}")


# ============================================================
# EVOLUCAO DE RANK MENSAL
# ============================================================

def plot_rank_evolution(df_fusion: pd.DataFrame, output_dir: str):
    """
    Gera line chart mostrando evolucao de rank no Spotify Q1 2026
    para os top 25 artistas por score_combined com presenca >= 2 meses.

    Eixo Y invertido (posicao 1 no topo). Linhas coloridas por padrao
    de presenca (taxonomia estrutural: 6 categorias, zero threshold).
    Nomes anotados ao final de cada linha.
    figsize=(6,8) dpi=200 -> 1200x1600px -- dentro do limite de 1800px.
    """
    from matplotlib.lines import Line2D

    os.makedirs(output_dir, exist_ok=True)
    # Universo completo (nao restrito ao seed)
    df_all = df_fusion.dropna(subset=['score_combined']).copy()

    sp_rank_cols = [c for c in ['rank_Jan_sp', 'rank_Feb_sp', 'rank_Mar_sp']
                    if c in df_all.columns]
    if len(sp_rank_cols) < 2:
        print("[AVISO] Colunas de rank insuficientes para plot de evolucao")
        return

    # Artistas com presenca >= 2 meses
    df_plot = df_all[
        df_all[sp_rank_cols].notna().sum(axis=1) >= 2
    ].copy()
    if df_plot.empty:
        print("[AVISO] Nenhum artista com >= 2 meses para plot de evolucao")
        return

    # Top 25 por score_combined para legibilidade
    df_plot = df_plot.sort_values(
        'score_combined', ascending=False, na_position='last')
    df_plot = df_plot.head(25)

    # Cores por padrao de presenca (taxonomia estrutural, 6 categorias)
    pattern_colors = {
        'persistent':   '#2ca02c',   # verde -- presente nos 3 meses
        'new':          '#9467bd',   # roxo  -- emergiu no Q1
        'exit':         '#d62728',   # vermelho -- saiu no Q1
        'intermittent': '#ff7f0e',   # laranja -- alternado
        'single':       '#7f7f7f',   # cinza  -- apenas 1 mes
        'absent':       '#c7c7c7',   # cinza claro -- ausente
    }

    month_cols = ['rank_Jan_sp', 'rank_Feb_sp', 'rank_Mar_sp']
    month_labels_x = ['Jan', 'Fev', 'Mar']
    x_positions = [1, 2, 3]

    fig, ax = plt.subplots(figsize=(6, 8))

    for _, row in df_plot.iterrows():
        name = (row['artist_name_seed']
                if pd.notna(row.get('artist_name_seed', float('nan')))
                else row['artist_normalized'])
        name = str(name)
        if len(name) > 20:
            name = name[:18] + '..'

        pattern = row.get('pattern_spotify', 'single')
        color = pattern_colors.get(str(pattern), '#1f77b4')

        # Pares (x, rank) apenas para meses presentes
        pts = [
            (xi, row.get(col))
            for xi, col in zip(x_positions, month_cols)
            if pd.notna(row.get(col))
        ]
        if len(pts) < 2:
            continue

        xs, ys = zip(*pts)
        ax.plot(xs, ys, marker='o', linewidth=1.2, markersize=4,
                color=color, alpha=0.8)
        # Anotacao ao lado do ultimo ponto
        ax.annotate(
            name,
            xy=(xs[-1], ys[-1]),
            xytext=(4, 0),
            textcoords='offset points',
            fontsize=5.5,
            va='center',
            color=color,
        )

    ax.set_xticks(x_positions)
    ax.set_xticklabels(month_labels_x)
    ax.invert_yaxis()
    ax.set_xlabel('Mes')
    ax.set_ylabel('Posicao no Chart (1 = melhor)')
    ax.set_title(
        'Evolucao de Rank Spotify Q1 2026 -- Top 25 por Score Combinado')

    # Legenda manual de padroes de presenca
    legend_elements = [
        Line2D([0], [0], color=c, linewidth=1.5, label=t)
        for t, c in pattern_colors.items()
        if t != 'absent'
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=5.5,
              title='Padrao', title_fontsize=6)

    plt.tight_layout()
    out_path = os.path.join(output_dir, 'rank_evolution_spotify.png')
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"  [OK] Plot evolucao salvo: {out_path}")


# ============================================================
# COMPARACAO GRUPOS CALL2GO
# ============================================================

def compare_call2go_groups(df_fusion: pd.DataFrame,
                           df_flagged: pd.DataFrame,
                           output_dir: str) -> dict:
    """
    Compara scores de fusao entre artistas com e sem Call2Go.

    Restringe aos 67 artistas do dataset. Usa Mann-Whitney U para
    comparar distribuicoes de score entre grupos.
    Salva boxplot em data/plots/fusion_score_by_call2go.png.

    Retorna dict com estatisticas dos grupos.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Restringe ao dataset
    df_ds = df_fusion[df_fusion['in_dataset'] == True].copy()

    # Flag has_call2go por artista (qualquer video com has_call2go=1)
    c2g = (df_flagged.groupby('artist_name')['has_call2go']
           .max()
           .reset_index()
           .rename(columns={'has_call2go': 'has_call2go_flag'}))
    c2g['artist_norm'] = c2g['artist_name'].apply(_normalize_name)

    # Normaliza nomes do seed para merge
    df_ds['artist_norm_seed'] = df_ds['artist_name_seed'].apply(
        lambda x: _normalize_name(x) if pd.notna(x) else '')

    # Merge por nome normalizado
    df_merged = df_ds.merge(
        c2g[['artist_norm', 'has_call2go_flag']],
        left_on='artist_norm_seed',
        right_on='artist_norm',
        how='left',
    )
    df_merged['has_call2go'] = df_merged['has_call2go_flag'].fillna(
        0).astype(int)

    group_yes = df_merged[df_merged['has_call2go'] == 1]
    group_no = df_merged[df_merged['has_call2go'] == 0]

    print(f"\n  Grupo Call2Go=1: {len(group_yes)} artistas")
    print(f"  Grupo Call2Go=0: {len(group_no)} artistas")

    results = {}

    for score_col in ['score_spotify', 'score_youtube']:
        if score_col not in df_merged.columns:
            continue
        y = group_yes[score_col].dropna()
        n = group_no[score_col].dropna()
        med_y = y.median() if not y.empty else float('nan')
        med_n = n.median() if not n.empty else float('nan')
        mean_y = y.mean() if not y.empty else float('nan')
        mean_n = n.mean() if not n.empty else float('nan')

        print(f"\n  {score_col}:")
        print(
            f"    Call2Go=1 -- mediana={med_y:.4f}, media={mean_y:.4f} (n={len(y)})")
        print(
            f"    Call2Go=0 -- mediana={med_n:.4f}, media={mean_n:.4f} (n={len(n)})")

        if len(y) >= 3 and len(n) >= 3:
            stat, pval = stats.mannwhitneyu(y, n, alternative='two-sided')
            sig = ('***' if pval < 0.001 else '**' if pval < 0.01
                   else '*' if pval < 0.05 else 'ns')
            print(f"    Mann-Whitney U={stat:.1f}, p={pval:.4f} [{sig}]")
            results[score_col] = {
                'median_yes': med_y, 'median_no': med_n,
                'mean_yes': mean_y, 'mean_no': mean_n,
                'U': stat, 'p': pval, 'sig': sig,
            }
        else:
            print(f"    [AVISO] Grupos pequenos demais para teste")
            results[score_col] = {
                'median_yes': med_y, 'median_no': med_n,
                'mean_yes': mean_y, 'mean_no': mean_n,
            }

    # Comparacao presence_count_spotify entre grupos
    if 'presence_count_spotify' in df_merged.columns:
        pc_y = group_yes['presence_count_spotify'].dropna()
        pc_n = group_no['presence_count_spotify'].dropna()
        if len(pc_y) >= 3 and len(pc_n) >= 3:
            stat, pval = stats.mannwhitneyu(
                pc_y, pc_n, alternative='two-sided')
            sig = ('***' if pval < 0.001 else '**' if pval < 0.01
                   else '*' if pval < 0.05 else 'ns')
            print(f"\n  presence_count_spotify: "
                  f"U={stat:.1f}, p={pval:.4f} [{sig}]")
            results['presence_count_spotify'] = {
                'U': stat, 'p': pval, 'sig': sig}

    # Boxplot: score_spotify e score_youtube por grupo
    plot_cols = [c for c in ['score_spotify', 'score_youtube']
                 if c in df_merged.columns]
    if plot_cols:
        fig, axes = plt.subplots(1, len(plot_cols), figsize=(6, 4))
        if len(plot_cols) == 1:
            axes = [axes]
        for ax, col in zip(axes, plot_cols):
            data_plot = [
                df_merged[df_merged['has_call2go'] == 0][col].dropna().values,
                df_merged[df_merged['has_call2go'] == 1][col].dropna().values,
            ]
            ax.boxplot(data_plot, labels=['Sem Call2Go', 'Com Call2Go'])
            ax.set_title(col.replace('_', ' ').title())
            ax.set_ylabel('Fusion Score')
        plt.tight_layout()
        out_path = os.path.join(output_dir, 'fusion_score_by_call2go.png')
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        print(f"\n  [OK] Boxplot salvo: {out_path}")

    return results


# ============================================================
# CORRELACOES COM LAST.FM
# ============================================================

def analyze_lastfm_correlations(df_fusion: pd.DataFrame,
                                df_lastfm: pd.DataFrame,
                                output_dir: str) -> pd.DataFrame:
    """
    Calcula correlacoes (Pearson + Spearman) entre scores de fusao
    e metricas do Last.fm (listeners, playcount).

    Restringe aos 67 artistas do dataset com dados Last.fm disponiveis.
    Salva heatmap da matriz Spearman em fusion_lastfm_correlation.png.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Restringe ao dataset
    df_ds = df_fusion[df_fusion['in_dataset'] == True].copy()
    df_ds['artist_norm_seed'] = df_ds['artist_name_seed'].apply(
        lambda x: _normalize_name(x) if pd.notna(x) else '')

    # Normaliza nomes no Last.fm
    df_lf = df_lastfm.copy()
    df_lf['artist_norm'] = df_lf['artist_name'].apply(_normalize_name)
    df_lf = df_lf.drop_duplicates(subset='artist_norm')

    # Merge
    df_merged = df_ds.merge(
        df_lf[['artist_norm', 'listeners', 'playcount']],
        left_on='artist_norm_seed',
        right_on='artist_norm',
        how='inner',
    )
    print(f"\n  Artistas com dados Last.fm: {len(df_merged)}")

    # Pares de correlacao
    pairs = [
        ('score_spotify', 'listeners'),
        ('score_spotify', 'playcount'),
        ('score_youtube', 'listeners'),
        ('score_youtube', 'playcount'),
        ('score_spotify', 'score_youtube'),
    ]

    corr_rows = []
    for col_a, col_b in pairs:
        if col_a not in df_merged.columns or col_b not in df_merged.columns:
            continue
        valid = df_merged[[col_a, col_b]].dropna()
        if len(valid) < 5:
            continue
        r_p, p_p = stats.pearsonr(valid[col_a], valid[col_b])
        r_s, p_s = stats.spearmanr(valid[col_a], valid[col_b])
        sig_p = ('***' if p_p < 0.001 else '**' if p_p < 0.01
                 else '*' if p_p < 0.05 else 'ns')
        sig_s = ('***' if p_s < 0.001 else '**' if p_s < 0.01
                 else '*' if p_s < 0.05 else 'ns')
        print(f"\n  {col_a} x {col_b} (n={len(valid)}):")
        print(f"    Pearson  r={r_p:.3f}, p={p_p:.4f} [{sig_p}]")
        print(f"    Spearman rho={r_s:.3f}, p={p_s:.4f} [{sig_s}]")
        corr_rows.append({
            'var_a': col_a, 'var_b': col_b, 'n': len(valid),
            'pearson_r': r_p, 'pearson_p': p_p, 'pearson_sig': sig_p,
            'spearman_rho': r_s, 'spearman_p': p_s, 'spearman_sig': sig_s,
        })

    df_corr = pd.DataFrame(corr_rows)

    # Heatmap da matriz de correlacao Spearman
    vars_matrix = [c for c in ['score_spotify', 'score_youtube', 'listeners', 'playcount']
                   if c in df_merged.columns]
    if len(vars_matrix) >= 2:
        sp_matrix = df_merged[vars_matrix].dropna().corr(method='spearman')
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.heatmap(
            sp_matrix,
            annot=True,
            fmt='.2f',
            cmap='coolwarm',
            center=0,
            ax=ax,
            linewidths=0.3,
        )
        ax.set_title('Correlacao Spearman -- Fusao x Last.fm Q1 2026')
        plt.tight_layout()
        out_path = os.path.join(output_dir, 'fusion_lastfm_correlation.png')
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        print(f"\n  [OK] Heatmap de correlacao salvo: {out_path}")

    return df_corr


# ============================================================
# ANALISE DE LAG TEMPORAL
# ============================================================

def _parse_release_date(date_str: str) -> pd.Timestamp:
    """
    Converte data de lancamento para Timestamp.
    Formatos aceitos: 'YYYY-MM-DD', 'YYYY-MM', 'YYYY'.
    Normaliza para o primeiro dia do mes/ano quando incompleto.
    Retorna NaT se nao for possivel parsear.
    """
    date_str = str(date_str).strip()
    for fmt in ('%Y-%m-%d', '%Y-%m', '%Y'):
        try:
            return pd.Timestamp(datetime.strptime(date_str, fmt))
        except ValueError:
            continue
    return pd.NaT


def temporal_lag_analysis(df_fusion: pd.DataFrame,
                          df_yt_videos: pd.DataFrame,
                          df_sp_dates: pd.DataFrame,
                          output_dir: str):
    """
    Analisa o lag temporal entre lancamento no Spotify e primeiro video
    Call2Go no YouTube, para artistas com Call2Go no dataset.

    lag_call2go_days = yt_first_call2go_date - sp_first_release_date
    Negativo = YouTube publicou antes do lancamento oficial no Spotify.

    Salva data/validation/temporal_lag_results.csv e
    data/plots/temporal_lag_analysis.png.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Verifica disponibilidade dos dados Spotify
    if df_sp_dates is None or df_sp_dates.empty:
        print("[AVISO] Datas Spotify nao disponiveis, pulando analise temporal.")
        return None

    # Artistas do dataset
    df_ds = df_fusion[df_fusion['in_dataset'] == True].copy()
    dataset_artists = df_ds['artist_name_seed'].dropna().tolist()

    results = []
    for artist_seed in dataset_artists:
        artist_norm = _normalize_name(artist_seed)

        # Videos do YouTube deste artista
        yt_artist = df_yt_videos[
            df_yt_videos['artist_name'].apply(_normalize_name) == artist_norm
        ]
        if yt_artist.empty:
            continue

        # Apenas artistas com pelo menos um video Call2Go
        yt_c2g = yt_artist[yt_artist['has_call2go'] == 1]
        if yt_c2g.empty:
            continue

        # Normaliza para tz-naive (UTC -> sem timezone) para compatibilidade
        # com datas Spotify que sao tz-naive
        yt_dates = pd.to_datetime(
            yt_artist['published_at'], errors='coerce', utc=True
        ).dt.tz_convert(None)
        yt_c2g_dates = pd.to_datetime(
            yt_c2g['published_at'], errors='coerce', utc=True
        ).dt.tz_convert(None)

        yt_first_call2go = yt_c2g_dates.dropna().min()
        yt_first_any = yt_dates.dropna().min()

        if pd.isna(yt_first_call2go):
            continue

        # Release date Spotify: artista primario nas faixas dos charts
        sp_artist = df_sp_dates[
            df_sp_dates['artist_names'].apply(
                lambda x: _normalize_name(
                    str(x).split(',')[0].strip()) == artist_norm
            )
        ]
        if sp_artist.empty:
            sp_first_release = pd.NaT
        else:
            sp_dates_parsed = sp_artist['release_date'].apply(
                _parse_release_date)
            sp_first_release = sp_dates_parsed.dropna().min()

        # lag = yt_first_call2go - sp_first_release (negativo = YT antes do Spotify)
        lag_call2go = (
            (yt_first_call2go - sp_first_release).days
            if pd.notna(sp_first_release) else float('nan')
        )
        lag_any = (
            (yt_first_any - sp_first_release).days
            if pd.notna(yt_first_any) and pd.notna(sp_first_release)
            else float('nan')
        )

        results.append({
            'artist_name': artist_seed,
            'yt_first_call2go_date': yt_first_call2go,
            'yt_first_any_date': yt_first_any,
            'sp_first_release_date': sp_first_release,
            'lag_call2go_days': lag_call2go,
            'lag_any_days': lag_any,
        })

    if not results:
        print("[AVISO] Nenhum artista com dados suficientes para analise temporal.")
        return None

    df_lag = pd.DataFrame(results)
    lags = df_lag['lag_call2go_days'].dropna()
    n_yt_first = int((lags < 0).sum())
    n_sp_first = int((lags > 0).sum())
    n_same = int((lags == 0).sum())

    print(f"\n  Artistas analisados: {len(df_lag)}")
    print(f"  Mediana lag (dias): {lags.median():.1f}")
    print(f"  YouTube antes do Spotify (lag < 0): {n_yt_first} artistas")
    print(f"  Spotify antes do YouTube (lag > 0): {n_sp_first} artistas")
    print(f"  Mesmo dia (lag = 0): {n_same} artistas")

    # Salva CSV de resultados
    val_dir = "data/validation"
    os.makedirs(val_dir, exist_ok=True)
    lag_path = os.path.join(val_dir, "temporal_lag_results.csv")
    df_lag.to_csv(lag_path, index=False)
    print(f"  [OK] Resultados salvos: {lag_path}")

    # Histograma
    if not lags.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(lags.values, bins=15, edgecolor='black', color='steelblue')
        ax.axvline(0, color='red', linestyle='--',
                   linewidth=1, label='Simultaneo')
        ax.set_xlabel('Dias (negativo = YouTube antes do Spotify)')
        ax.set_ylabel('Numero de artistas')
        ax.set_title(
            'Lag Temporal: Release Spotify vs. Primeiro Video Call2Go')
        ax.legend()
        plt.tight_layout()
        out_path = os.path.join(output_dir, 'temporal_lag_analysis.png')
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        print(f"  [OK] Histograma salvo: {out_path}")

    return df_lag


# ============================================================
# RELATORIO CONSOLIDADO
# ============================================================

def generate_ranking_report(df_fusion, call2go_stats, corr_results, output_dir):
    """
    Gera relatorio textual consolidado da analise de fusao de rankings.

    Inclui: total artistas, cobertura seed, normalizacao de score,
    top 10 por score_combined, distribuicao de padroes de presenca,
    estatisticas por grupo Call2Go, resumo de correlacoes Last.fm.

    Metodologia:
    - Score de fusao: Reciprocal Rank Fusion (RRF), normalizado pelo
      numero de semanas por plataforma. Ref: Cormack et al., 2009 (SIGIR).
    - Padrao de presenca: taxonomia estrutural de 6 categorias baseada
      unicamente em presenca/ausencia binaria por mes (zero threshold).
    - rank_delta: variavel continua (rank_jan - rank_mar) para analises
      de magnitude sem threshold arbitrario.
    """
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "ranking_fusion_report.txt")

    lines = []
    lines.append("=" * 60)
    lines.append("RELATORIO -- FUSAO DE RANKINGS CROSS-PLATFORM Q1 2026")
    lines.append("=" * 60)
    lines.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Totais e cobertura
    total = len(df_fusion)
    in_ds = int(df_fusion['in_dataset'].sum())
    lines.append(f"Total de artistas primarios nos charts: {total}")
    lines.append(
        f"Artistas do dataset (seed, encontrados como primarios): {in_ds}")
    lines.append("")

    # Nota metodologica de normalizacao
    lines.append("--- METODOLOGIA DE SCORE ---")
    lines.append(
        "  score = Reciprocal Rank Fusion (Cormack et al., SIGIR 2009)")
    lines.append(
        "  score_Xplatform = sum(1/best_rank_mes) para cada mes presente")
    lines.append("  score_X_normalized = score_X / n_semanas_plataforma")
    lines.append(
        "  score_combined = score_sp_normalized + score_yt_normalized")
    sp_norm_scores = df_fusion['score_spotify_normalized'].dropna(
    ) if 'score_spotify_normalized' in df_fusion.columns else pd.Series(dtype=float)
    yt_norm_scores = df_fusion['score_youtube_normalized'].dropna(
    ) if 'score_youtube_normalized' in df_fusion.columns else pd.Series(dtype=float)
    if not sp_norm_scores.empty:
        lines.append(
            f"  n_semanas_spotify: implicito em score_spotify_normalized")
    if not yt_norm_scores.empty:
        lines.append(
            f"  n_semanas_youtube: implicito em score_youtube_normalized")
    lines.append("")

    # Ranges de score (raw e normalizado)
    lines.append("--- RANGES DE SCORE ---")
    for col in ['score_spotify', 'score_youtube', 'score_combined']:
        if col in df_fusion.columns:
            s = df_fusion[col].dropna()
            if not s.empty:
                lines.append(
                    f"  {col}: min={s.min():.6f}, max={s.max():.6f}, "
                    f"mediana={s.median():.6f}")
    lines.append("")

    # Top 10 por Score Combinado (normalizado)
    lines.append("--- TOP 10 POR SCORE COMBINADO (normalizado) ---")
    if 'score_combined' in df_fusion.columns:
        top10_c = (df_fusion[
            ['artist_normalized', 'artist_name_seed',
                'score_combined', 'in_dataset']
        ]
            .dropna(subset=['score_combined'])
            .sort_values('score_combined', ascending=False)
            .head(10))
        for i, (_, row) in enumerate(top10_c.iterrows(), start=1):
            name = (row['artist_name_seed'] if pd.notna(row['artist_name_seed'])
                    else row['artist_normalized'])
            mark = '[*]' if row['in_dataset'] else '   '
            lines.append(
                f"  {i:2d}. {mark} {name}: {row['score_combined']:.6f}")
    lines.append("")

    # Top 10 por Spotify
    lines.append("--- TOP 10 POR SCORE SPOTIFY ---")
    if 'score_spotify' in df_fusion.columns:
        top10_sp = (df_fusion[['artist_normalized', 'artist_name_seed',
                               'score_spotify', 'in_dataset']]
                    .dropna(subset=['score_spotify'])
                    .sort_values('score_spotify', ascending=False)
                    .head(10))
        for i, (_, row) in enumerate(top10_sp.iterrows(), start=1):
            name = (row['artist_name_seed'] if pd.notna(row['artist_name_seed'])
                    else row['artist_normalized'])
            mark = '[*]' if row['in_dataset'] else '   '
            lines.append(
                f"  {i:2d}. {mark} {name}: {row['score_spotify']:.4f}")
    lines.append("")

    # Top 10 por YouTube
    lines.append("--- TOP 10 POR SCORE YOUTUBE ---")
    if 'score_youtube' in df_fusion.columns:
        top10_yt = (df_fusion[['artist_normalized', 'artist_name_seed',
                               'score_youtube', 'in_dataset']]
                    .dropna(subset=['score_youtube'])
                    .sort_values('score_youtube', ascending=False)
                    .head(10))
        for i, (_, row) in enumerate(top10_yt.iterrows(), start=1):
            name = (row['artist_name_seed'] if pd.notna(row['artist_name_seed'])
                    else row['artist_normalized'])
            mark = '[*]' if row['in_dataset'] else '   '
            lines.append(
                f"  {i:2d}. {mark} {name}: {row['score_youtube']:.4f}")
    lines.append("")

    # Distribuicao de padroes de presenca (todos os artistas primarios)
    lines.append("--- PADROES DE PRESENCA JAN->MAR (TODOS OS ARTISTAS) ---")
    lines.append(
        "  Taxonomia estrutural: absent/single/persistent/new/exit/intermittent")
    for pattern_col, platform in [('pattern_spotify', 'Spotify'),
                                  ('pattern_youtube', 'YouTube')]:
        if pattern_col in df_fusion.columns:
            lines.append(f"  {platform}:")
            counts = df_fusion[pattern_col].value_counts()
            total_patt = counts.sum()
            for t, c in counts.items():
                pct = 100.0 * c / total_patt if total_patt > 0 else 0
                lines.append(f"    {t}: {c} ({pct:.1f}%)")
    lines.append("")

    # Distribuicao de padroes de presenca (dataset seed only)
    lines.append("--- PADROES DE PRESENCA JAN->MAR (DATASET SEED) ---")
    df_ds_only = df_fusion[df_fusion['in_dataset'] == True]
    for pattern_col, platform in [('pattern_spotify', 'Spotify'),
                                  ('pattern_youtube', 'YouTube')]:
        if pattern_col in df_fusion.columns:
            lines.append(f"  {platform}:")
            counts = df_ds_only[pattern_col].value_counts()
            for t, c in counts.items():
                lines.append(f"    {t}: {c}")
    lines.append("")

    # Estatisticas Call2Go
    lines.append("--- COMPARACAO GRUPOS CALL2GO ---")
    if call2go_stats:
        for metric, s in call2go_stats.items():
            lines.append(f"  {metric}:")
            if 'median_yes' in s:
                med_y = s.get('median_yes')
                med_n = s.get('median_no')
                if med_y is not None and not (isinstance(med_y, float) and np.isnan(med_y)):
                    lines.append(f"    Call2Go=1: mediana={med_y:.4f}")
                if med_n is not None and not (isinstance(med_n, float) and np.isnan(med_n)):
                    lines.append(f"    Call2Go=0: mediana={med_n:.4f}")
            if 'p' in s:
                lines.append(
                    f"    Mann-Whitney p={s['p']:.4f} [{s.get('sig', '')}]")
    else:
        lines.append("  Nao disponivel")
    lines.append("")

    # Correlacoes Last.fm
    lines.append("--- CORRELACOES LAST.FM ---")
    if corr_results is not None and isinstance(corr_results, pd.DataFrame) \
            and not corr_results.empty:
        for _, row in corr_results.iterrows():
            lines.append(f"  {row['var_a']} x {row['var_b']} (n={row['n']}):")
            lines.append(
                f"    Pearson  r={row['pearson_r']:.3f} [{row['pearson_sig']}]")
            lines.append(
                f"    Spearman rho={row['spearman_rho']:.3f} [{row['spearman_sig']}]")
    else:
        lines.append("  Nao disponivel")
    lines.append("")
    lines.append("=" * 60)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"  [OK] Relatorio salvo: {report_path}")


# ============================================================
# ORQUESTRADOR PRINCIPAL
# ============================================================

def run_ranking_fusion_analysis():
    """Executa a analise completa de fusao de rankings cross-platform."""
    print("\n" + "#" * 60)
    print("#    FUSAO DE RANKINGS -- ANALISE CROSS-PLATFORM Q1 2026")
    print("#    Plataformas: Spotify + YouTube Brasil")
    print("#" * 60)

    output_dir = "data/plots"
    val_dir = "data/validation"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(val_dir, exist_ok=True)

    # ===== 1. TABELA DE FUSAO =====
    print("\n" + "=" * 60)
    print("1. CONSTRUCAO DA TABELA DE FUSAO")
    print("=" * 60)
    df_fusion = build_fusion_table("data/seed/artistas.csv")

    # ===== 2. HEATMAP DE PRESENCA =====
    print("\n" + "=" * 60)
    print("2. HEATMAP DE PRESENCA MENSAL")
    print("=" * 60)
    plot_presence_heatmap(df_fusion, output_dir)

    # ===== 2.5 EVOLUCAO DE RANK =====
    print("\n" + "=" * 60)
    print("2.5 EVOLUCAO DE RANK (LINE CHART)")
    print("=" * 60)
    try:
        plot_rank_evolution(df_fusion, output_dir)
    except Exception as e:
        print(f"[ERRO] Falha no plot de evolucao: {e}")

    # ===== 3. COMPARACAO GRUPOS CALL2GO =====
    print("\n" + "=" * 60)
    print("3. COMPARACAO GRUPOS CALL2GO")
    print("=" * 60)
    call2go_stats = {}
    try:
        df_flagged = pd.read_csv("data/processed/youtube_call2go_flagged.csv")
        call2go_stats = compare_call2go_groups(
            df_fusion, df_flagged, output_dir)
    except Exception as e:
        print(f"[ERRO] Falha na comparacao Call2Go: {e}")

    # ===== 4. CORRELACOES LAST.FM =====
    print("\n" + "=" * 60)
    print("4. CORRELACOES LAST.FM")
    print("=" * 60)
    corr_results = None
    try:
        lastfm_files = sorted(glob.glob("data/raw/lastfm_artists_*.csv"))
        if lastfm_files:
            df_lastfm = pd.read_csv(lastfm_files[-1])
            for col in ['listeners', 'playcount']:
                df_lastfm[col] = pd.to_numeric(
                    df_lastfm[col], errors='coerce').fillna(0)
            corr_results = analyze_lastfm_correlations(
                df_fusion, df_lastfm, output_dir)
        else:
            print("[AVISO] Dados Last.fm nao encontrados, pulando correlacoes.")
    except Exception as e:
        print(f"[ERRO] Falha nas correlacoes Last.fm: {e}")

    # ===== 5. ANALISE DE LAG TEMPORAL =====
    print("\n" + "=" * 60)
    print("5. ANALISE DE LAG TEMPORAL")
    print("=" * 60)
    sp_dates_path = "data/raw/spotify_track_dates_Q1_2026.csv"
    if not os.path.exists(sp_dates_path):
        print("[AVISO] Datas Spotify nao disponiveis, pulando analise temporal.")
        print("        Execute a etapa 15 primeiro: step_15_collect_spotify_track_dates")
    else:
        try:
            df_yt_videos = pd.read_csv(
                "data/processed/youtube_call2go_flagged.csv")
            df_sp_dates = pd.read_csv(sp_dates_path)
            temporal_lag_analysis(df_fusion, df_yt_videos,
                                  df_sp_dates, output_dir)
        except Exception as e:
            print(f"[ERRO] Falha na analise temporal: {e}")

    # ===== 6. RELATORIO CONSOLIDADO =====
    print("\n" + "=" * 60)
    print("6. RELATORIO CONSOLIDADO")
    print("=" * 60)
    generate_ranking_report(df_fusion, call2go_stats, corr_results, val_dir)

    print("\n" + "#" * 60)
    print("#    FUSAO DE RANKINGS -- ANALISE CONCLUIDA")
    print("#" * 60)


if __name__ == "__main__":
    run_ranking_fusion_analysis()

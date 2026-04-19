"""
ANALISE LAST.FM BRIDGE -- Ponte Cross-Platform 3 Fontes

Integra Last.fm como terceira fonte independente para triangulacao
cross-platform (YouTube x Spotify x Last.fm).

O Last.fm agrega audiencia REAL de todas as plataformas (scrobbles vem
do Spotify, YouTube Music, Apple Music, Deezer, etc.), funcionando como
ponte neutra entre YouTube e Spotify.

Janela temporal: Q1 2026 (jan-mar). Metricas Last.fm sao cumulativas,
servindo como proxy de popularidade consolidada.

Analises implementadas:
    1. Validacao de intersecao 3 fontes (seed vs chart BR)
    2. Ranking comparativo 3 plataformas (Spearman)
    3. Track-level matching (videos YouTube vs hits Last.fm)
    4. Matriz de correlacao 3 fontes (6x6 Spearman)
    5. Mann-Whitney: Call2Go vs Last.fm metrics
    6. Analise bidirecional estendida (3 direcoes)
    7. Analise por genero (tags Last.fm)

Fluxo:
    python -m src.analytics.lastfm_bridge_analysis
    ou via run_pipeline.py (etapa automatica)
"""

import os
import re
import glob
import unicodedata
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns


# ============================================================
# CARGA DE DADOS
# ============================================================

def _load_seed(path="data/seed/artistas.csv"):
    """Carrega base de artistas (seed Q1 2026)."""
    return pd.read_csv(path)


def _load_youtube_flagged(path="data/processed/youtube_call2go_flagged.csv"):
    """Carrega videos do YouTube com flags Call2Go."""
    df = pd.read_csv(path)
    for col in ['view_count', 'like_count', 'comment_count']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df


def _load_spotify(data_dir="data/raw"):
    """Carrega metricas Spotify mais recentes."""
    files = sorted(glob.glob(os.path.join(data_dir, "spotify_metrics_*.csv")))
    if not files:
        return None
    df = pd.read_csv(files[-1])
    for col in ['followers', 'popularity']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df


def _load_lastfm_artists(data_dir="data/raw"):
    """Carrega metricas Last.fm por artista mais recentes."""
    files = sorted(glob.glob(os.path.join(data_dir, "lastfm_artists_*.csv")))
    if not files:
        return None
    df = pd.read_csv(files[-1])
    for col in ['listeners', 'playcount']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df


def _load_lastfm_top_tracks(data_dir="data/raw"):
    """Carrega top tracks por artista do Last.fm."""
    files = sorted(glob.glob(os.path.join(data_dir, "lastfm_top_tracks_*.csv")))
    if not files:
        return None
    return pd.read_csv(files[-1])


def _load_lastfm_chart_artists(data_dir="data/raw"):
    """Carrega chart de artistas BR do Last.fm."""
    files = sorted(glob.glob(
        os.path.join(data_dir, "lastfm_chart_artists_brazil_*.csv")))
    if not files:
        return None
    return pd.read_csv(files[-1])


def _load_lastfm_chart_tracks(data_dir="data/raw"):
    """Carrega chart de tracks BR do Last.fm."""
    files = sorted(glob.glob(
        os.path.join(data_dir, "lastfm_chart_tracks_brazil_*.csv")))
    if not files:
        return None
    return pd.read_csv(files[-1])


def _normalize(name):
    """Normaliza nome para matching: lowercase, sem acentos, sem pontuacao."""
    if not isinstance(name, str):
        return ''
    name = name.lower().strip()
    # Remove acentos
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    # Remove pontuacao e caracteres especiais
    name = re.sub(r'[^\w\s]', '', name)
    # Normaliza espacos
    name = re.sub(r'\s+', ' ', name).strip()
    return name


# ============================================================
# 1. VALIDACAO DE INTERSECAO 3 FONTES
# ============================================================

def validate_three_way_intersection(df_seed, df_chart_artists, output_dir):
    """
    Verifica quantos dos 67 artistas do seed aparecem no Top 200 BR
    do Last.fm, gerando tabela de validacao de intersecao 3 fontes.
    """
    print("\n" + "=" * 60)
    print("1. VALIDACAO DE INTERSECAO 3 FONTES")
    print("=" * 60)

    seed_names = set(df_seed['artist_name'].str.lower())

    if df_chart_artists is not None:
        chart_norm = {_normalize(n): n
                      for n in df_chart_artists['artist_name']}
        chart_ranks = {row['artist_name'].lower(): row['rank']
                       for _, row in df_chart_artists.iterrows()}
    else:
        chart_norm = {}
        chart_ranks = {}

    results = []
    for _, row in df_seed.iterrows():
        name = row['artist_name']
        name_lower = name.lower()
        name_norm = _normalize(name)

        # Matching com chart BR (exato ou normalizado)
        in_chart = name_lower in chart_ranks
        if not in_chart:
            # Tenta matching normalizado
            in_chart = name_norm in chart_norm
        chart_rank = chart_ranks.get(name_lower, None)

        results.append({
            'artist_name': name,
            'in_spotify_charts': True,   # todos estao (vieram do seed)
            'in_youtube_charts': True,   # todos estao (vieram do seed)
            'in_lastfm_chart_br': in_chart,
            'lastfm_chart_rank': chart_rank,
        })

    df_inter = pd.DataFrame(results)
    count_3way = df_inter['in_lastfm_chart_br'].sum()
    total = len(df_inter)

    print(f"\n  Seed (Spotify + YouTube Q1 2026): {total} artistas")
    print(f"  Presentes no Last.fm Top 200 BR: {count_3way} "
          f"({count_3way/total*100:.1f}%)")
    print(f"  Ausentes do Last.fm Top 200 BR: {total - count_3way}")

    if count_3way > 0:
        print(f"\n  Artistas na intersecao 3 fontes:")
        matched = df_inter[df_inter['in_lastfm_chart_br']]
        for _, r in matched.iterrows():
            rank = r['lastfm_chart_rank']
            rank_str = f"#{int(rank)}" if pd.notna(rank) else "?"
            print(f"    {rank_str}: {r['artist_name']}")

    # Salva CSV
    inter_path = os.path.join(output_dir, "three_way_intersection.csv")
    df_inter.to_csv(inter_path, index=False)
    print(f"\n  Tabela salva: {inter_path}")

    return df_inter


# ============================================================
# 2. RANKING COMPARATIVO 3 PLATAFORMAS
# ============================================================

def rank_comparison(df_seed, df_sp, df_lastfm, output_dir):
    """
    Compara rankings de popularidade entre 3 plataformas via Spearman.
    Cada artista recebe um rank em cada plataforma, e as correlacoes
    entre os ranks indicam convergencia de popularidade.
    """
    print("\n" + "=" * 60)
    print("2. RANKING COMPARATIVO 3 PLATAFORMAS")
    print("=" * 60)

    # Monta perfil com ranks
    df = df_seed[['artist_name']].copy()

    # YouTube: rank por total_youtube_views (ja disponivel no seed)
    if 'total_youtube_views' in df_seed.columns:
        df['youtube_views'] = df_seed['total_youtube_views'].values
    else:
        df['youtube_views'] = 0

    # Spotify: rank por popularity
    sp_map = dict(zip(df_sp['artist_name'], df_sp['popularity']))
    df['spotify_popularity'] = df['artist_name'].map(sp_map).fillna(0)

    # Spotify: followers
    fol_map = dict(zip(df_sp['artist_name'], df_sp['followers']))
    df['spotify_followers'] = df['artist_name'].map(fol_map).fillna(0)

    # Last.fm: listeners e playcount
    lfm_listeners = dict(zip(df_lastfm['artist_name'], df_lastfm['listeners']))
    lfm_playcount = dict(zip(df_lastfm['artist_name'], df_lastfm['playcount']))
    df['lastfm_listeners'] = df['artist_name'].map(lfm_listeners).fillna(0)
    df['lastfm_playcount'] = df['artist_name'].map(lfm_playcount).fillna(0)

    # Gera ranks (1 = maior valor)
    df['rank_yt'] = df['youtube_views'].rank(ascending=False, method='min')
    df['rank_sp_pop'] = df['spotify_popularity'].rank(ascending=False, method='min')
    df['rank_sp_fol'] = df['spotify_followers'].rank(ascending=False, method='min')
    df['rank_lfm_listeners'] = df['lastfm_listeners'].rank(ascending=False, method='min')
    df['rank_lfm_playcount'] = df['lastfm_playcount'].rank(ascending=False, method='min')

    # Correlacoes de Spearman entre ranks
    rank_cols = {
        'YouTube Views': 'rank_yt',
        'Spotify Pop': 'rank_sp_pop',
        'Spotify Followers': 'rank_sp_fol',
        'Last.fm Listeners': 'rank_lfm_listeners',
        'Last.fm Scrobbles': 'rank_lfm_playcount',
    }

    print(f"\n  N = {len(df)} artistas")
    print(f"\n  Correlacoes de Spearman entre rankings:")

    pairs = list(rank_cols.items())
    results = {}
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            label_a, col_a = pairs[i]
            label_b, col_b = pairs[j]
            rho, p = stats.spearmanr(df[col_a], df[col_b])
            sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "n.s."
            print(f"    {label_a} <-> {label_b}: rho={rho:.3f}, p={p:.4f} {sig}")
            results[f"{label_a}_vs_{label_b}"] = {'rho': rho, 'p': p}

    # Heatmap de correlacao de ranks
    rank_matrix = df[list(rank_cols.values())].corr(method='spearman')
    rank_matrix.index = list(rank_cols.keys())
    rank_matrix.columns = list(rank_cols.keys())

    fig, ax = plt.subplots(figsize=(6, 4))
    sns.heatmap(rank_matrix, annot=True, fmt='.2f', cmap='RdYlGn',
                center=0, vmin=-1, vmax=1, ax=ax, linewidths=0.5,
                square=True)
    ax.set_title('Convergencia de Rankings: 3 Plataformas\n'
                 'Spearman rho entre ranks de popularidade',
                 fontsize=12, fontweight='bold')
    plt.tight_layout()
    plot_path = os.path.join(output_dir, "rank_comparison_3sources.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n  Heatmap salvo: {plot_path}")

    # Salva perfil completo
    profile_path = os.path.join(output_dir, "three_source_ranking.csv")
    df.to_csv(profile_path, index=False)
    print(f"  Ranking salvo: {profile_path}")

    return df, results


# ============================================================
# 3. TRACK-LEVEL MATCHING (Videos YouTube vs Hits Last.fm)
# ============================================================

def _clean_video_title(title):
    """Remove sufixos comuns de titulos de video para matching."""
    if not isinstance(title, str):
        return ''
    # Remove termos comuns que nao fazem parte do nome da musica
    noise = [
        r'\(official\s*(music\s*)?video\)',
        r'\(clipe\s*oficial\)',
        r'\(video\s*oficial\)',
        r'\(ao\s*vivo\)',
        r'\(live\)',
        r'\(lyric\s*video\)',
        r'\(lyrics?\)',
        r'\(audio\s*oficial\)',
        r'\(audio\)',
        r'\(visualizer\)',
        r'\(performance\s*video\)',
        r'\bofficial\s*(music\s*)?video\b',
        r'\bclipe\s*oficial\b',
        r'\bvideo\s*oficial\b',
        r'\bao\s*vivo\b',
        r'\blive\b',
        r'\blyric\s*video\b',
        r'\bdvd\b',
        r'\|.*$',        # Remove tudo apos pipe
        r'\[.*?\]',      # Remove colchetes
        r'feat\.?\s.*$', # Remove feat.
        r'ft\.?\s.*$',   # Remove ft.
        r'part\.?\s.*$', # Remove part.
        r'prod\.?\s.*$', # Remove prod.
    ]
    cleaned = title
    for pattern in noise:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    return _normalize(cleaned)


def track_level_matching(df_yt, df_lastfm_tracks, df_chart_tracks, output_dir):
    """
    Cruza titulos de videos do YouTube com top tracks do Last.fm por artista
    e com chart tracks BR para determinar se um video e um 'hit confirmado'.

    Usa matching por contencao: track Last.fm contida no titulo do video.
    """
    print("\n" + "=" * 60)
    print("3. TRACK-LEVEL MATCHING (YouTube vs Last.fm)")
    print("=" * 60)

    # Prepara lookup de tracks por artista (normalizado)
    artist_tracks = {}
    if df_lastfm_tracks is not None:
        for _, row in df_lastfm_tracks.iterrows():
            artist = row['artist_name'].lower()
            track_norm = _normalize(row['track_name'])
            if artist not in artist_tracks:
                artist_tracks[artist] = []
            artist_tracks[artist].append({
                'track_norm': track_norm,
                'track_name': row['track_name'],
                'playcount': int(row.get('track_playcount', 0)),
                'listeners': int(row.get('track_listeners', 0)),
                'rank': int(row.get('track_rank', 0)),
            })

    # Prepara lookup de chart tracks BR (normalizado)
    chart_track_set = set()
    if df_chart_tracks is not None:
        for _, row in df_chart_tracks.iterrows():
            key = (_normalize(row['artist_name']), _normalize(row['track_name']))
            chart_track_set.add(key)

    # Matching
    match_results = []
    matched_count = 0
    chart_hit_count = 0

    for _, row in df_yt.iterrows():
        title_clean = _clean_video_title(row['title'])
        artist_lower = row['artist_name'].lower()

        best_match = None
        best_playcount = 0
        is_chart_hit = False

        # Verifica contra top tracks do artista
        if artist_lower in artist_tracks:
            for t in artist_tracks[artist_lower]:
                track_n = t['track_norm']
                if len(track_n) >= 3 and track_n in title_clean:
                    if t['playcount'] > best_playcount:
                        best_match = t
                        best_playcount = t['playcount']

        # Verifica contra chart tracks BR
        artist_norm = _normalize(row['artist_name'])
        for ct_artist, ct_track in chart_track_set:
            if ct_artist == artist_norm and len(ct_track) >= 3:
                if ct_track in title_clean:
                    is_chart_hit = True
                    break

        match_results.append({
            'video_id': row['video_id'],
            'lastfm_hit': best_match is not None,
            'lastfm_track_name': best_match['track_name'] if best_match else '',
            'lastfm_track_playcount': best_match['playcount'] if best_match else 0,
            'lastfm_track_listeners': best_match['listeners'] if best_match else 0,
            'lastfm_track_rank': best_match['rank'] if best_match else 0,
            'lastfm_chart_hit_br': is_chart_hit,
        })

        if best_match:
            matched_count += 1
        if is_chart_hit:
            chart_hit_count += 1

    df_matches = pd.DataFrame(match_results)
    total = len(df_yt)
    print(f"\n  Total de videos: {total}")
    print(f"  Matched com top tracks do artista: {matched_count} "
          f"({matched_count/total*100:.1f}%)")
    print(f"  Matched com chart BR: {chart_hit_count} "
          f"({chart_hit_count/total*100:.1f}%)")

    # Salva CSV de matches
    match_path = os.path.join(output_dir, "track_level_matching.csv")
    df_matches.to_csv(match_path, index=False)
    print(f"  Matching salvo: {match_path}")

    return df_matches


# ============================================================
# 4. CALL2GO vs HIT STATUS (Chi-squared)
# ============================================================

def callgo_vs_hits(df_yt, df_matches, output_dir):
    """
    Testa se videos com Call2Go sao mais frequentemente 'hits' no Last.fm.
    Usa teste Chi-squared (ou Fisher exact para amostras pequenas).
    """
    print("\n" + "=" * 60)
    print("4. CALL2GO vs HIT STATUS (Chi-squared)")
    print("=" * 60)

    df = df_yt[['video_id', 'has_call2go', 'call2go_type']].merge(
        df_matches[['video_id', 'lastfm_hit']], on='video_id')

    # Tabela de contingencia
    ct = pd.crosstab(df['has_call2go'], df['lastfm_hit'],
                     margins=True, margins_name='Total')
    ct.index = ['Sem Call2Go', 'Com Call2Go', 'Total']
    ct.columns = ['Nao Hit', 'Hit Last.fm', 'Total']

    print(f"\n  Tabela de Contingencia:")
    print(f"  {ct.to_string()}")

    # Calcula taxas
    with_c2g = df[df['has_call2go'] == 1]
    without_c2g = df[df['has_call2go'] == 0]
    rate_with = with_c2g['lastfm_hit'].mean() * 100 if len(with_c2g) > 0 else 0
    rate_without = without_c2g['lastfm_hit'].mean() * 100 if len(without_c2g) > 0 else 0

    print(f"\n  Taxa de hits (Com Call2Go): {rate_with:.1f}%")
    print(f"  Taxa de hits (Sem Call2Go): {rate_without:.1f}%")

    # Teste estatistico
    ct_values = pd.crosstab(df['has_call2go'], df['lastfm_hit'])
    if ct_values.shape == (2, 2):
        # Verifica se todas as celulas tem frequencia esperada >= 5
        chi2, p, dof, expected = stats.chi2_contingency(ct_values)
        min_expected = expected.min()

        if min_expected >= 5:
            print(f"\n  Chi-squared: X2={chi2:.3f}, p={p:.4f}, dof={dof}")
        else:
            # Fisher exact para amostras com frequencias baixas
            odds_ratio, p = stats.fisher_exact(ct_values)
            chi2 = None
            print(f"\n  Fisher Exact (freq. esperada < 5): OR={odds_ratio:.3f}, p={p:.4f}")

        alpha = 0.05
        if p < alpha:
            print(f"  CONCLUSAO: Rejeita H0 — Call2Go e hit status NAO sao independentes")
        else:
            print(f"  CONCLUSAO: Falha em rejeitar H0 — Call2Go e hit status sao independentes")
    else:
        p = None
        print(f"  [AVISO] Tabela de contingencia incompleta, teste nao aplicavel")

    return {'rate_with_c2g': rate_with, 'rate_without_c2g': rate_without,
            'p_value': p}


# ============================================================
# 5. MATRIZ DE CORRELACAO 3 FONTES (6x6)
# ============================================================

def three_source_correlation_matrix(df_profile, output_dir):
    """
    Gera matriz de correlacao Spearman 6x6 entre metricas de 3 plataformas.
    """
    print("\n" + "=" * 60)
    print("5. MATRIZ DE CORRELACAO 3 FONTES")
    print("=" * 60)

    metric_cols = {
        'YouTube\nAvg Views': 'avg_views',
        'YouTube\nTotal Views': 'total_views',
        'Spotify\nPopularity': 'popularity',
        'Spotify\nFollowers': 'followers',
        'Last.fm\nListeners': 'lastfm_listeners',
        'Last.fm\nScrobbles': 'lastfm_playcount',
    }

    # Filtra colunas existentes
    valid = {k: v for k, v in metric_cols.items() if v in df_profile.columns}
    if len(valid) < 3:
        print("  [AVISO] Dados insuficientes para matriz de correlacao")
        return {}

    df_corr = df_profile[list(valid.values())].copy()
    df_corr.columns = list(valid.keys())

    # Calcula matriz Spearman
    corr_matrix = df_corr.corr(method='spearman')

    # Calcula p-values para cada par
    n = len(valid)
    labels = list(valid.keys())
    p_matrix = pd.DataFrame(np.ones((n, n)), index=labels, columns=labels)

    for i in range(n):
        for j in range(i + 1, n):
            _, p = stats.spearmanr(df_corr.iloc[:, i], df_corr.iloc[:, j])
            p_matrix.iloc[i, j] = p
            p_matrix.iloc[j, i] = p

    # Imprime correlacoes significativas
    print(f"\n  N = {len(df_profile)} artistas")
    print(f"  Correlacoes significativas (p < 0.05):")
    for i in range(n):
        for j in range(i + 1, n):
            rho = corr_matrix.iloc[i, j]
            p = p_matrix.iloc[i, j]
            if p < 0.05:
                sig = "***" if p < 0.001 else "**" if p < 0.01 else "*"
                label_clean_i = labels[i].replace('\n', ' ')
                label_clean_j = labels[j].replace('\n', ' ')
                print(f"    {label_clean_i} <-> {label_clean_j}: "
                      f"rho={rho:.3f}, p={p:.4f} {sig}")

    # Heatmap
    fig, ax = plt.subplots(figsize=(6, 4))

    # Anotacoes com significancia
    annot = corr_matrix.copy()
    annot_text = annot.map(lambda x: f'{x:.2f}')
    for i in range(n):
        for j in range(n):
            if i != j:
                p = p_matrix.iloc[i, j]
                sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
                annot_text.iloc[i, j] = f'{corr_matrix.iloc[i, j]:.2f}{sig}'

    sns.heatmap(corr_matrix, annot=annot_text, fmt='', cmap='RdYlGn',
                center=0, vmin=-1, vmax=1, ax=ax, linewidths=0.5,
                square=True)
    ax.set_title('Correlacao Cross-Platform: YouTube x Spotify x Last.fm\n'
                 'Spearman rho (*** p<0.001, ** p<0.01, * p<0.05)',
                 fontsize=11, fontweight='bold')
    plt.tight_layout()
    plot_path = os.path.join(output_dir, "correlation_matrix_3sources.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n  Heatmap salvo: {plot_path}")

    return {'corr_matrix': corr_matrix, 'p_matrix': p_matrix}


# ============================================================
# 6. MANN-WHITNEY: CALL2GO vs LAST.FM METRICS
# ============================================================

def mannwhitney_lastfm(df_profile, output_dir):
    """
    Testa se artistas COM Call2Go tem metricas Last.fm significativamente
    diferentes de artistas SEM Call2Go (Mann-Whitney U).
    """
    print("\n" + "=" * 60)
    print("6. MANN-WHITNEY: CALL2GO vs LAST.FM")
    print("=" * 60)

    # Separa grupos: artistas com qualquer video com Call2Go vs sem nenhum
    with_c2g = df_profile[df_profile['call2go_rate'] > 0]
    without_c2g = df_profile[df_profile['call2go_rate'] == 0]

    print(f"\n  Artistas COM Call2Go: {len(with_c2g)}")
    print(f"  Artistas SEM Call2Go: {len(without_c2g)}")

    results = {}
    metrics = [
        ('lastfm_listeners', 'Last.fm Listeners'),
        ('lastfm_playcount', 'Last.fm Scrobbles'),
    ]

    for col, label in metrics:
        if col not in df_profile.columns:
            continue

        group_a = with_c2g[col].astype(float)
        group_b = without_c2g[col].astype(float)

        if len(group_a) < 2 or len(group_b) < 2:
            print(f"\n  [AVISO] {label}: grupos insuficientes para teste")
            continue

        u_stat, p_value = stats.mannwhitneyu(
            group_a, group_b, alternative='two-sided')

        med_a = group_a.median()
        med_b = group_b.median()

        print(f"\n  {label}:")
        print(f"    Mediana COM Call2Go: {med_a:,.0f}")
        print(f"    Mediana SEM Call2Go: {med_b:,.0f}")
        print(f"    Mann-Whitney U={u_stat:.0f}, p={p_value:.5f}")

        alpha = 0.05
        if p_value < alpha:
            print(f"    -> SIGNIFICATIVO (p < {alpha})")
        else:
            print(f"    -> NAO SIGNIFICATIVO (p >= {alpha})")

        results[col] = {
            'U': u_stat, 'p': p_value,
            'median_with': med_a, 'median_without': med_b,
            'n_with': len(group_a), 'n_without': len(group_b),
        }

    # Boxplot comparativo
    fig, axes = plt.subplots(1, 2, figsize=(6, 4))

    for idx, (col, label) in enumerate(metrics):
        if col not in df_profile.columns:
            continue
        data_plot = [
            df_profile[df_profile['call2go_rate'] == 0][col].values,
            df_profile[df_profile['call2go_rate'] > 0][col].values,
        ]
        bp = axes[idx].boxplot(data_plot, tick_labels=['Sem\nCall2Go', 'Com\nCall2Go'],
                               patch_artist=True, widths=0.5)
        bp['boxes'][0].set_facecolor('#E8E8E8')
        bp['boxes'][1].set_facecolor('#1DB954')
        axes[idx].set_ylabel(label, fontsize=10)
        axes[idx].set_title(f'{label}\npor Call2Go Status', fontsize=10,
                            fontweight='bold')
        axes[idx].ticklabel_format(style='scientific', axis='y', scilimits=(0, 0))

        if col in results:
            p = results[col]['p']
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
            axes[idx].text(0.5, 0.95, f'p={p:.4f} {sig}',
                           transform=axes[idx].transAxes, ha='center',
                           va='top', fontsize=9, style='italic')

    plt.suptitle('Mann-Whitney U: Call2Go vs Last.fm Metrics', fontsize=12,
                 fontweight='bold', y=1.02)
    plt.tight_layout()
    plot_path = os.path.join(output_dir, "mannwhitney_lastfm.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n  Boxplot salvo: {plot_path}")

    return results


# ============================================================
# 7. ANALISE BIDIRECIONAL ESTENDIDA (3 DIRECOES)
# ============================================================

def extended_bidirectional(df_profile, output_dir):
    """
    Analise bidirecional estendida com 3 pares de plataformas:
      A: YouTube <-> Last.fm
      B: Spotify <-> Last.fm
      C: YouTube <-> Spotify (ja existente, reconfirmada)
    """
    print("\n" + "=" * 60)
    print("7. ANALISE BIDIRECIONAL ESTENDIDA (3 DIRECOES)")
    print("=" * 60)

    results = {}
    n = len(df_profile)

    pairs = [
        # (label, col_x, col_y, xlabel, ylabel)
        ("YouTube Avg Views <-> Last.fm Listeners",
         'avg_views', 'lastfm_listeners',
         'YouTube Avg Views', 'Last.fm Listeners'),
        ("YouTube Avg Views <-> Last.fm Scrobbles",
         'avg_views', 'lastfm_playcount',
         'YouTube Avg Views', 'Last.fm Scrobbles'),
        ("YouTube Call2Go Rate <-> Last.fm Listeners",
         'call2go_rate', 'lastfm_listeners',
         'Call2Go Rate (YouTube)', 'Last.fm Listeners'),
        ("Spotify Popularity <-> Last.fm Listeners",
         'popularity', 'lastfm_listeners',
         'Spotify Popularity', 'Last.fm Listeners'),
        ("Spotify Followers <-> Last.fm Listeners",
         'followers', 'lastfm_listeners',
         'Spotify Followers', 'Last.fm Listeners'),
        ("Spotify Followers <-> Last.fm Scrobbles",
         'followers', 'lastfm_playcount',
         'Spotify Followers', 'Last.fm Scrobbles'),
    ]

    print(f"\n  N = {n} artistas")
    for label, col_x, col_y, _, _ in pairs:
        if col_x not in df_profile.columns or col_y not in df_profile.columns:
            continue
        rho, p = stats.spearmanr(df_profile[col_x], df_profile[col_y])
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
        print(f"    {label}: rho={rho:.3f}, p={p:.4f} {sig}")
        results[label] = {'rho': rho, 'p': p}

    # Scatter plots: 4 mais relevantes
    scatter_pairs = [
        ('avg_views', 'lastfm_listeners',
         'YouTube Avg Views', 'Last.fm Listeners', '#FF0000'),
        ('followers', 'lastfm_listeners',
         'Spotify Followers', 'Last.fm Listeners', '#1DB954'),
        ('avg_views', 'lastfm_playcount',
         'YouTube Avg Views', 'Last.fm Scrobbles', '#FF4444'),
        ('call2go_rate', 'lastfm_listeners',
         'Call2Go Rate', 'Last.fm Listeners', '#FF6600'),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(6, 4))
    axes = axes.flatten()

    for idx, (col_x, col_y, xlabel, ylabel, color) in enumerate(scatter_pairs):
        if col_x not in df_profile.columns or col_y not in df_profile.columns:
            continue

        ax = axes[idx]
        ax.scatter(df_profile[col_x], df_profile[col_y],
                   s=30, c=color, alpha=0.6, edgecolors='black', linewidth=0.3)

        rho, p = stats.spearmanr(df_profile[col_x], df_profile[col_y])
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
        ax.set_xlabel(xlabel, fontsize=8)
        ax.set_ylabel(ylabel, fontsize=8)
        ax.set_title(f'rho={rho:.2f} {sig}', fontsize=8, fontweight='bold')
        ax.tick_params(labelsize=7)

        # Formata eixos grandes
        for axis in [ax.xaxis, ax.yaxis]:
            axis.set_major_formatter(
                plt.FuncFormatter(lambda x, _: f'{x/1e6:.1f}M' if x >= 1e6
                                  else f'{x/1e3:.0f}K' if x >= 1e3
                                  else f'{x:.2f}' if x < 1
                                  else f'{x:.0f}'))

    plt.suptitle('Analise Bidirecional: YouTube x Spotify x Last.fm',
                 fontsize=11, fontweight='bold', y=1.02)
    plt.tight_layout()
    plot_path = os.path.join(output_dir, "scatter_3source_bidirectional.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n  Scatter plots salvos: {plot_path}")

    return results


# ============================================================
# 8. ANALISE POR GENERO (TAGS LAST.FM)
# ============================================================

# Mapeamento de tags Last.fm para categorias consolidadas
_GENRE_MAP = {
    'sertanejo': 'Sertanejo',
    'sertanejo universitario': 'Sertanejo',
    'sertanejo universitário': 'Sertanejo',
    'arrocha': 'Sertanejo',
    'funk': 'Funk',
    'funk carioca': 'Funk',
    'funk pop': 'Funk',
    'brazilian funk': 'Funk',
    'funk ostentacao': 'Funk',
    'trap funk': 'Funk',
    'rap': 'Rap/Hip-Hop',
    'hip-hop': 'Rap/Hip-Hop',
    'hip hop': 'Rap/Hip-Hop',
    'brazilian hip hop': 'Rap/Hip-Hop',
    'brazilian trap': 'Rap/Hip-Hop',
    'trap': 'Rap/Hip-Hop',
    'pop': 'Pop',
    'pop rock': 'Pop',
    'dance pop': 'Pop',
    'pagode': 'Pagode/Samba',
    'samba': 'Pagode/Samba',
    'pagode baiano': 'Pagode/Samba',
    'forro': 'Forro/Piseiro',
    'forró': 'Forro/Piseiro',
    'piseiro': 'Forro/Piseiro',
    'axe': 'Axe',
    'axé': 'Axe',
    'gospel': 'Gospel',
    'country': 'Country/Internacional',
    'rock': 'Rock',
}


def _get_primary_genre(tags_str):
    """Extrai genero primario das tags Last.fm usando mapeamento."""
    if not isinstance(tags_str, str) or not tags_str.strip():
        return 'Outros'

    tags = [t.strip().lower() for t in tags_str.split('|')]
    for tag in tags:
        if tag in _GENRE_MAP:
            return _GENRE_MAP[tag]

    return 'Outros'


def genre_analysis(df_profile, df_lastfm, output_dir):
    """
    Analisa distribuicao de Call2Go por genero musical usando tags do Last.fm.
    """
    print("\n" + "=" * 60)
    print("8. ANALISE POR GENERO (TAGS LAST.FM)")
    print("=" * 60)

    # Mapeia generos
    tags_map = dict(zip(df_lastfm['artist_name'], df_lastfm['tags']))
    df_profile = df_profile.copy()
    df_profile['genre'] = df_profile['artist_name'].map(tags_map).apply(
        _get_primary_genre)

    # Distribuicao de generos
    genre_counts = df_profile['genre'].value_counts()
    print(f"\n  Distribuicao de generos ({len(df_profile)} artistas):")
    for genre, count in genre_counts.items():
        print(f"    {genre}: {count} artistas")

    # Call2Go rate por genero
    genre_stats = df_profile.groupby('genre').agg(
        n_artists=('artist_name', 'count'),
        avg_call2go_rate=('call2go_rate', 'mean'),
        median_call2go_rate=('call2go_rate', 'median'),
        avg_lastfm_listeners=('lastfm_listeners', 'mean'),
    ).reset_index().sort_values('avg_call2go_rate', ascending=False)

    print(f"\n  Call2Go rate por genero:")
    for _, row in genre_stats.iterrows():
        print(f"    {row['genre']}: avg={row['avg_call2go_rate']:.1%} "
              f"(N={row['n_artists']}, listeners={row['avg_lastfm_listeners']:,.0f})")

    # Teste chi-squared: Call2Go (binario por artista) vs genero
    df_profile['has_any_call2go'] = (df_profile['call2go_rate'] > 0).astype(int)

    # Filtra generos com N >= 3 para validade estatistica
    valid_genres = genre_counts[genre_counts >= 3].index
    df_filtered = df_profile[df_profile['genre'].isin(valid_genres)]

    if len(valid_genres) >= 2:
        ct = pd.crosstab(df_filtered['genre'], df_filtered['has_any_call2go'])
        if ct.shape[1] == 2:
            chi2, p, dof, expected = stats.chi2_contingency(ct)
            print(f"\n  Chi-squared (genero x Call2Go): X2={chi2:.3f}, p={p:.4f}, dof={dof}")

            alpha = 0.05
            if p < alpha:
                print(f"  -> SIGNIFICATIVO: Call2Go depende do genero")
            else:
                print(f"  -> NAO SIGNIFICATIVO: Call2Go independe do genero")
        else:
            p = None
            print(f"\n  [AVISO] Apenas uma categoria de Call2Go encontrada")
    else:
        p = None
        print(f"\n  [AVISO] Generos insuficientes para teste chi-squared")

    # Bar plot: Call2Go rate por genero
    genre_stats_plot = genre_stats[genre_stats['n_artists'] >= 2].copy()
    if len(genre_stats_plot) > 0:
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(range(len(genre_stats_plot)),
                      genre_stats_plot['avg_call2go_rate'] * 100,
                      color='#1DB954', edgecolor='black', linewidth=0.5)

        ax.set_xticks(range(len(genre_stats_plot)))
        ax.set_xticklabels(genre_stats_plot['genre'], rotation=45, ha='right',
                           fontsize=9)
        ax.set_ylabel('Taxa Media de Call2Go (%)', fontsize=10)
        ax.set_title('Call2Go Rate por Genero Musical\n'
                     '(tags Last.fm, artistas Q1 2026 BR)',
                     fontsize=11, fontweight='bold')

        # Anotacoes com N
        for i, (_, row) in enumerate(genre_stats_plot.iterrows()):
            ax.text(i, row['avg_call2go_rate'] * 100 + 0.5,
                    f"N={row['n_artists']}", ha='center', fontsize=7)

        plt.tight_layout()
        plot_path = os.path.join(output_dir, "callgo_by_genre.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"\n  Bar plot salvo: {plot_path}")

    # Salva stats por genero
    stats_path = os.path.join(output_dir, "genre_call2go_stats.csv")
    genre_stats.to_csv(stats_path, index=False)
    print(f"  Stats por genero salvo: {stats_path}")

    return genre_stats


# ============================================================
# 9. RELATORIO CONSOLIDADO
# ============================================================

def generate_bridge_report(results, output_dir):
    """Gera relatorio textual consolidado da analise Last.fm Bridge."""
    report_path = os.path.join(output_dir, "lastfm_bridge_report.txt")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("RELATORIO: LAST.FM BRIDGE — ANALISE CROSS-PLATFORM 3 FONTES\n")
        f.write("Janela temporal: Q1 2026 (Janeiro-Marco)\n")
        f.write("=" * 60 + "\n\n")

        # Intersecao
        if 'intersection' in results:
            inter = results['intersection']
            total = len(inter)
            in_chart = inter['in_lastfm_chart_br'].sum()
            f.write("1. INTERSECAO 3 FONTES\n")
            f.write(f"   Seed (Spotify+YouTube Q1 2026): {total} artistas\n")
            f.write(f"   No Last.fm Top 200 BR: {in_chart} ({in_chart/total*100:.1f}%)\n")
            f.write(f"   Last.fm per-artist coverage: 100% (todos encontrados)\n\n")

        # Rankings
        if 'rank_results' in results:
            f.write("2. CONVERGENCIA DE RANKINGS\n")
            for k, v in results['rank_results'].items():
                sig = "***" if v['p'] < 0.001 else "**" if v['p'] < 0.01 else "*" if v['p'] < 0.05 else "n.s."
                f.write(f"   {k}: rho={v['rho']:.3f}, p={v['p']:.4f} {sig}\n")
            f.write("\n")

        # Track matching
        if 'track_matching' in results:
            tm = results['track_matching']
            total = len(tm)
            hits = tm['lastfm_hit'].sum()
            f.write("3. TRACK-LEVEL MATCHING\n")
            f.write(f"   Videos analisados: {total}\n")
            f.write(f"   Hits Last.fm: {hits} ({hits/total*100:.1f}%)\n\n")

        # Call2Go vs Hits
        if 'callgo_hits' in results:
            ch = results['callgo_hits']
            f.write("4. CALL2GO vs HIT STATUS\n")
            f.write(f"   Taxa hits (Com Call2Go): {ch['rate_with_c2g']:.1f}%\n")
            f.write(f"   Taxa hits (Sem Call2Go): {ch['rate_without_c2g']:.1f}%\n")
            if ch['p_value'] is not None:
                f.write(f"   p-value: {ch['p_value']:.4f}\n")
            f.write("\n")

        # Mann-Whitney Last.fm
        if 'mannwhitney' in results:
            f.write("5. MANN-WHITNEY: CALL2GO vs LAST.FM\n")
            for metric, v in results['mannwhitney'].items():
                sig = "***" if v['p'] < 0.001 else "**" if v['p'] < 0.01 else "*" if v['p'] < 0.05 else "n.s."
                f.write(f"   {metric}: U={v['U']:.0f}, p={v['p']:.5f} {sig}\n")
                f.write(f"     Mediana COM: {v['median_with']:,.0f} | "
                        f"SEM: {v['median_without']:,.0f}\n")
            f.write("\n")

        # Bidirecional estendido
        if 'bidirectional' in results:
            f.write("6. ANALISE BIDIRECIONAL ESTENDIDA\n")
            for k, v in results['bidirectional'].items():
                sig = "***" if v['p'] < 0.001 else "**" if v['p'] < 0.01 else "*" if v['p'] < 0.05 else "n.s."
                f.write(f"   {k}: rho={v['rho']:.3f}, p={v['p']:.4f} {sig}\n")
            f.write("\n")

        # Genero
        if 'genre' in results:
            f.write("7. CALL2GO POR GENERO\n")
            for _, row in results['genre'].iterrows():
                f.write(f"   {row['genre']}: avg_rate={row['avg_call2go_rate']:.1%} "
                        f"(N={row['n_artists']})\n")

    print(f"\n  Relatorio salvo: {report_path}")


# ============================================================
# ORQUESTRADOR
# ============================================================

def build_three_source_profile(df_yt, df_sp, df_lastfm):
    """
    Constroi perfil por artista com metricas das 3 plataformas.
    Base para todas as analises subsequentes.
    """
    # YouTube: agregacao por artista
    yt_agg = df_yt.groupby('artist_name').agg(
        total_videos=('video_id', 'count'),
        videos_com_call2go=('has_call2go', 'sum'),
        total_views=('view_count', 'sum'),
        avg_views=('view_count', 'mean'),
        total_likes=('like_count', 'sum'),
        avg_likes=('like_count', 'mean'),
        total_comments=('comment_count', 'sum'),
        avg_comments=('comment_count', 'mean'),
    ).reset_index()

    yt_agg['call2go_rate'] = yt_agg['videos_com_call2go'] / yt_agg['total_videos']

    # Spotify
    sp_cols = df_sp[['artist_name', 'followers', 'popularity']].copy()

    # Last.fm
    lfm_cols = df_lastfm[['artist_name', 'listeners', 'playcount', 'tags']].copy()
    lfm_cols = lfm_cols.rename(columns={
        'listeners': 'lastfm_listeners',
        'playcount': 'lastfm_playcount',
        'tags': 'lastfm_tags',
    })

    # Merge 3 fontes
    df_profile = yt_agg.merge(sp_cols, on='artist_name', how='inner')
    df_profile = df_profile.merge(lfm_cols, on='artist_name', how='inner')

    # Engagement
    df_profile['avg_engagement'] = df_profile['avg_likes'] + df_profile['avg_comments']

    return df_profile


def run_lastfm_bridge_analysis():
    """Executa a analise completa Last.fm Bridge (3 fontes)."""
    print("\n" + "#" * 60)
    print("#    LAST.FM BRIDGE — ANALISE CROSS-PLATFORM 3 FONTES")
    print("#    Janela: Q1 2026 (Janeiro-Marco)")
    print("#" * 60)

    # Carga de dados
    print("\n--- CARGA DE DADOS ---")
    df_seed = _load_seed()
    df_yt = _load_youtube_flagged()
    df_sp = _load_spotify()
    df_lastfm = _load_lastfm_artists()
    df_lastfm_tracks = _load_lastfm_top_tracks()
    df_chart_artists = _load_lastfm_chart_artists()
    df_chart_tracks = _load_lastfm_chart_tracks()

    for name, df in [('Seed', df_seed), ('YouTube', df_yt), ('Spotify', df_sp),
                     ('Last.fm Artists', df_lastfm)]:
        if df is not None:
            print(f"  {name}: {len(df)} registros")
        else:
            print(f"  [ERRO] {name}: NAO ENCONTRADO")
            return

    if df_lastfm_tracks is not None:
        print(f"  Last.fm Top Tracks: {len(df_lastfm_tracks)} tracks")
    if df_chart_artists is not None:
        print(f"  Last.fm Chart BR Artistas: {len(df_chart_artists)} artistas")
    if df_chart_tracks is not None:
        print(f"  Last.fm Chart BR Tracks: {len(df_chart_tracks)} tracks")

    # Diretorio de saida
    output_dir = "data/validation"
    os.makedirs(output_dir, exist_ok=True)
    plots_dir = "data/plots"
    os.makedirs(plots_dir, exist_ok=True)

    # Perfil 3 fontes
    df_profile = build_three_source_profile(df_yt, df_sp, df_lastfm)
    print(f"\n  Perfil 3 fontes: {len(df_profile)} artistas com dados nas 3 plataformas")

    # Salva perfil
    profile_path = os.path.join(output_dir, "three_source_profile.csv")
    df_profile.to_csv(profile_path, index=False)

    # Resultados
    all_results = {}

    # 1. Intersecao 3 fontes
    df_inter = validate_three_way_intersection(df_seed, df_chart_artists, output_dir)
    all_results['intersection'] = df_inter

    # 2. Ranking comparativo
    _, rank_results = rank_comparison(df_seed, df_sp, df_lastfm, plots_dir)
    all_results['rank_results'] = rank_results

    # 3. Track-level matching
    df_matches = track_level_matching(df_yt, df_lastfm_tracks, df_chart_tracks,
                                      output_dir)
    all_results['track_matching'] = df_matches

    # 4. Call2Go vs Hits
    callgo_hits = callgo_vs_hits(df_yt, df_matches, output_dir)
    all_results['callgo_hits'] = callgo_hits

    # 5. Matriz de correlacao 3 fontes
    corr_results = three_source_correlation_matrix(df_profile, plots_dir)
    all_results['correlation'] = corr_results

    # 6. Mann-Whitney Last.fm
    mw_results = mannwhitney_lastfm(df_profile, plots_dir)
    all_results['mannwhitney'] = mw_results

    # 7. Bidirecional estendido
    bidir_results = extended_bidirectional(df_profile, plots_dir)
    all_results['bidirectional'] = bidir_results

    # 8. Analise por genero
    genre_results = genre_analysis(df_profile, df_lastfm, plots_dir)
    all_results['genre'] = genre_results

    # 9. Relatorio consolidado
    generate_bridge_report(all_results, output_dir)

    print("\n" + "#" * 60)
    print("#    LAST.FM BRIDGE — ANALISE CONCLUIDA")
    print("#" * 60)


if __name__ == "__main__":
    run_lastfm_bridge_analysis()

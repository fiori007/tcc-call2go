"""
Analise Temporal de Charts: YouTube activity vs Spotify chart entry.

Responde a pergunta do orientador: a atividade no YouTube (publicacao de
videos + uso de Call2Go) antecede a entrada dos artistas no chart Spotify,
ou e o contrario?

Diferente de temporal_lag_analysis() (que usa sp_first_release_date de apenas
6 artistas), este modulo usa first_chart_week_spotify (entrada no chart BR Q1
2026) e cobre todos os 39 artistas seed encontrados nos charts.

Analises realizadas:
  A. Defasagem (lag) YouTube activity -> Spotify chart entry
     lag_any_days: primeiro video do artista em relacao ao chart entry
     lag_call2go_days: primeiro video Call2Go em relacao ao chart entry
     Negativo = YouTube foi ativo ANTES da entrada no chart Spotify

  B. Janelas de tempo relativas ao chart entry:
     [-90,-60], [-60,-30], [-30,0], [0,+30] dias
     Contagem de todos os videos e de videos Call2Go por janela

  C. Correlacoes Spearman (n>=5):
     lag_call2go_days <-> score_spotify_normalized
     videos_30d_pre_chart <-> score_combined
     call2go_videos_pre_chart <-> score_spotify_normalized

Inputs:
  data/processed/ranking_fusion_scores.csv -- first_chart_week_spotify
  data/processed/youtube_call2go_flagged.csv -- published_at, video_call2go

Outputs:
  data/validation/chart_temporal_results.csv
  data/plots/chart_temporal_lag_histogram.png
  data/plots/chart_temporal_windows.png
  data/plots/chart_temporal_correlation.png
"""

from datetime import datetime
from scipy import stats
import seaborn as sns
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
import os
import json
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')

warnings.filterwarnings('ignore', category=FutureWarning)


# ------------------------------------------------------------------ #
#  Constantes                                                          #
# ------------------------------------------------------------------ #

FUSION_CSV = "data/processed/ranking_fusion_scores.csv"
FLAGGED_CSV = "data/processed/youtube_call2go_flagged.csv"
RESULTS_CSV = "data/validation/chart_temporal_results.csv"
HIST_PNG = "data/plots/chart_temporal_lag_histogram.png"
WINDOWS_PNG = "data/plots/chart_temporal_windows.png"
CORR_PNG = "data/plots/chart_temporal_correlation.png"

# Janelas em dias relativas ao chart entry (inicio, fim)
WINDOWS = [(-90, -60), (-60, -30), (-30, 0), (0, 30)]
WINDOW_LABELS = ["-90:-60", "-60:-30", "-30:0", "0:+30"]


# ------------------------------------------------------------------ #
#  Normaliza nome do artista (para match entre tabelas)               #
# ------------------------------------------------------------------ #

def _normalize(name):
    import unicodedata
    import re
    if not isinstance(name, str):
        return ''
    nfkd = unicodedata.normalize('NFKD', name.lower())
    ascii_str = nfkd.encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9\s]', '', ascii_str).strip()


# ------------------------------------------------------------------ #
#  Funcao principal                                                    #
# ------------------------------------------------------------------ #

def run_chart_temporal_analysis():
    """Executa a analise temporal YouTube activity vs Spotify chart entry."""
    os.makedirs("data/validation", exist_ok=True)
    os.makedirs("data/plots", exist_ok=True)

    print("=" * 60)
    print("ANALISE TEMPORAL CHARTS -- YouTube vs Spotify")
    print("=" * 60)

    # -------------------------------------------------------------- #
    # 1. Carrega dados                                                #
    # -------------------------------------------------------------- #
    if not os.path.exists(FUSION_CSV):
        print(f"[ERRO] Nao encontrado: {FUSION_CSV}")
        return
    if not os.path.exists(FLAGGED_CSV):
        print(f"[ERRO] Nao encontrado: {FLAGGED_CSV}")
        return

    df_fusion = pd.read_csv(FUSION_CSV)
    df_yt = pd.read_csv(FLAGGED_CSV)

    # Filtra apenas artistas seed primarios com chart entry Spotify
    seed_artists = df_fusion[
        (df_fusion['in_dataset'] == True) &
        (df_fusion['first_chart_week_spotify'].notna())
    ][['artist_name_seed', 'first_chart_week_spotify',
       'score_spotify_normalized', 'score_combined',
       'total_weeks_spotify']].copy()

    seed_artists['first_chart_week_spotify'] = pd.to_datetime(
        seed_artists['first_chart_week_spotify'], errors='coerce')
    seed_artists = seed_artists[seed_artists['first_chart_week_spotify'].notna(
    )]

    # Normaliza nome para matching
    seed_artists['name_norm'] = seed_artists['artist_name_seed'].apply(
        _normalize)

    df_yt['published_at'] = pd.to_datetime(
        df_yt['published_at'], utc=True, errors='coerce')
    df_yt['published_at'] = df_yt['published_at'].dt.tz_localize(None)
    df_yt['name_norm'] = df_yt['artist_name'].apply(_normalize)

    print(
        f"\n  Artistas seed com first_chart_week_spotify: {len(seed_artists)}")
    print(
        f"  Videos com published_at valido: {df_yt['published_at'].notna().sum()}/{len(df_yt)}")

    # Diagnostico: quantos videos Call2Go (OR: video OU canal) existem no corpus
    if 'video_call2go' in df_yt.columns and 'channel_call2go' in df_yt.columns:
        n_or_c2g = (
            (df_yt['video_call2go'] != 'nenhum') | (
                df_yt['channel_call2go'] != 'nenhum')
        ).sum()
    else:
        n_or_c2g = 0
    print(f"  Videos com Call2Go OR (video ou canal) no corpus: {n_or_c2g}")

    # -------------------------------------------------------------- #
    # 2. Computa lag e janelas por artista                            #
    # -------------------------------------------------------------- #
    results = []

    for _, artist_row in seed_artists.iterrows():
        name = artist_row['artist_name_seed']
        name_n = artist_row['name_norm']
        chart_entry = artist_row['first_chart_week_spotify']  # Timestamp

        # Videos do artista
        yt_artist = df_yt[df_yt['name_norm'] ==
                          name_n].dropna(subset=['published_at'])

        if yt_artist.empty:
            continue

        dates = yt_artist['published_at']
        # Lógica OR: Call2Go se video_call2go != 'nenhum' OU channel_call2go != 'nenhum'
        mask_or = (
            (yt_artist['video_call2go'] != 'nenhum') |
            (yt_artist['channel_call2go'] != 'nenhum')
        )
        call2go_dates = yt_artist.loc[mask_or, 'published_at']

        # Lag em dias (negativo = YouTube ativo ANTES do chart entry)
        first_video_date = dates.min()
        lag_any_days = (first_video_date - chart_entry).days

        lag_call2go_days = None
        if not call2go_dates.empty:
            first_call2go_date = call2go_dates.min()
            lag_call2go_days = (first_call2go_date - chart_entry).days

        # Contagem por janela de tempo
        window_counts = {}
        window_call2go_counts = {}
        for (w_start, w_end), label in zip(WINDOWS, WINDOW_LABELS):
            mask_window = (
                (dates >= chart_entry + pd.Timedelta(days=w_start)) &
                (dates < chart_entry + pd.Timedelta(days=w_end))
            )
            window_counts[f'videos_window_{label}'] = mask_window.sum()

            if not call2go_dates.empty:
                c2g_dates_series = yt_artist.loc[mask_or, 'published_at']
                mask_c2g = (
                    (c2g_dates_series >= chart_entry + pd.Timedelta(days=w_start)) &
                    (c2g_dates_series < chart_entry + pd.Timedelta(days=w_end))
                )
                window_call2go_counts[f'call2go_window_{label}'] = mask_c2g.sum(
                )
            else:
                window_call2go_counts[f'call2go_window_{label}'] = 0

        # Videos nos 30 dias antes do chart entry (janela [-30, 0])
        mask_30d_pre = (
            (dates >= chart_entry - pd.Timedelta(days=30)) &
            (dates < chart_entry)
        )
        videos_30d_pre_chart = mask_30d_pre.sum()

        # Videos Call2Go antes do chart entry (qualquer janela negativa)
        if not call2go_dates.empty:
            mask_pre_chart = call2go_dates < chart_entry
            call2go_videos_pre_chart = mask_pre_chart.sum()
        else:
            call2go_videos_pre_chart = 0

        results.append({
            'artist_name': name,
            'first_chart_week_spotify': chart_entry.date(),
            'score_spotify_normalized': artist_row['score_spotify_normalized'],
            'score_combined': artist_row['score_combined'],
            'total_weeks_spotify': artist_row['total_weeks_spotify'],
            'total_videos_yt': len(yt_artist),
            'total_call2go_videos': len(call2go_dates),
            'first_video_date': first_video_date.date(),
            'lag_any_days': lag_any_days,
            'lag_call2go_days': lag_call2go_days,
            'videos_30d_pre_chart': videos_30d_pre_chart,
            'call2go_videos_pre_chart': call2go_videos_pre_chart,
            **window_counts,
            **window_call2go_counts,
        })

    df_results = pd.DataFrame(results)

    if df_results.empty:
        print("\n[AVISO] Nenhum artista com dados suficientes para analise temporal.")
        return

    # Artistas com lag_call2go_days disponivel (tem videos Call2Go)
    df_c2g = df_results[df_results['lag_call2go_days'].notna()].copy()

    print(f"\n  Artistas com lag computado (any):    {len(df_results)}")
    print(f"  Artistas com lag_call2go disponivel: {len(df_c2g)}")

    # -------------------------------------------------------------- #
    # 3. Estatisticas descritivas                                     #
    # -------------------------------------------------------------- #
    print("\n--- DEFASAGEM (LAG) YouTube -> Spotify Chart Entry ---")
    print(f"  lag_any_days:     mediana={df_results['lag_any_days'].median():.0f}d  "
          f"IQR=[{df_results['lag_any_days'].quantile(0.25):.0f}, "
          f"{df_results['lag_any_days'].quantile(0.75):.0f}]")
    if not df_c2g.empty:
        print(f"  lag_call2go_days: mediana={df_c2g['lag_call2go_days'].median():.0f}d  "
              f"IQR=[{df_c2g['lag_call2go_days'].quantile(0.25):.0f}, "
              f"{df_c2g['lag_call2go_days'].quantile(0.75):.0f}]")

    n_youtube_precedes_any = (df_results['lag_any_days'] < 0).sum()
    print(f"\n  YouTube ativo ANTES do chart Spotify: {n_youtube_precedes_any}/{len(df_results)} "
          f"({n_youtube_precedes_any/len(df_results)*100:.0f}%)")

    if not df_c2g.empty:
        n_c2g_precedes = (df_c2g['lag_call2go_days'] < 0).sum()
        print(f"  Call2Go colocado ANTES do chart:      {n_c2g_precedes}/{len(df_c2g)} "
              f"({n_c2g_precedes/len(df_c2g)*100:.0f}%)")

    # -------------------------------------------------------------- #
    # 4. Correlacoes Spearman                                         #
    # -------------------------------------------------------------- #
    corr_results = {}
    MIN_N = 5

    def _spearman(a, b, label):
        """Calcula Spearman entre duas series, reporta resultado."""
        paired = pd.DataFrame({'a': a, 'b': b}).dropna()
        n = len(paired)
        if n < MIN_N:
            print(f"  [{label}] n={n} < {MIN_N} -- INSUFICIENTE para correlacao")
            return None, None, n
        # Array constante = correlacao nao definida
        if paired['a'].nunique() <= 1 or paired['b'].nunique() <= 1:
            print(
                f"  [{label}] array constante -- correlacao nao calculavel (n={n})")
            return None, None, n
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            rho, pval = stats.spearmanr(paired['a'], paired['b'])
        sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else "n.s."
        print(f"  [{label}] rho={rho:.3f}, p={pval:.4f} {sig} (n={n})")
        return rho, pval, n

    print("\n--- CORRELACOES SPEARMAN ---")
    rho1, p1, n1 = _spearman(
        df_c2g['lag_call2go_days'],
        df_c2g['score_spotify_normalized'],
        "lag_call2go vs score_spotify_normalized"
    )
    rho2, p2, n2 = _spearman(
        df_results['videos_30d_pre_chart'],
        df_results['score_combined'],
        "videos_30d_pre_chart vs score_combined"
    )
    rho3, p3, n3 = _spearman(
        df_results['call2go_videos_pre_chart'],
        df_results['score_spotify_normalized'],
        "call2go_videos_pre_chart vs score_spotify_normalized"
    )

    # -------------------------------------------------------------- #
    # 5. Salva CSV de resultados                                      #
    # -------------------------------------------------------------- #
    df_results.to_csv(RESULTS_CSV, index=False, encoding='utf-8-sig')
    print(f"\n  [OK] Resultados: {RESULTS_CSV}")

    # -------------------------------------------------------------- #
    # 6. Graficos                                                     #
    # -------------------------------------------------------------- #

    # --- 6a. Histograma de lag_any_days ------------------------------ #
    fig, ax = plt.subplots(figsize=(6, 4))
    data_hist = df_results['lag_any_days'].dropna()
    if not data_hist.empty:
        bins = min(20, len(data_hist))
        ax.hist(data_hist, bins=bins, color='steelblue',
                edgecolor='white', linewidth=0.5)
        ax.axvline(0, color='red', linestyle='--',
                   linewidth=1.2, label='Chart entry')
        ax.axvline(data_hist.median(), color='orange', linestyle='--',
                   linewidth=1.2, label=f'Mediana={data_hist.median():.0f}d')
        if not df_c2g.empty and df_c2g['lag_call2go_days'].notna().any():
            ax.axvline(df_c2g['lag_call2go_days'].median(),
                       color='green', linestyle=':', linewidth=1.2,
                       label=f'Mediana Call2Go={df_c2g["lag_call2go_days"].median():.0f}d')
    ax.set_xlabel(
        "Defasagem (dias) -- negativo = YouTube antes do chart", fontsize=9)
    ax.set_ylabel("Artistas", fontsize=9)
    ax.set_title(
        "Lag YouTube vs Entrada no Chart Spotify (Q1 2026)", fontsize=10)
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(HIST_PNG, dpi=300)
    plt.close()
    print(f"  [OK] Histograma: {HIST_PNG}")

    # --- 6b. Barras empilhadas por janela de tempo ------------------- #
    fig, ax = plt.subplots(figsize=(6, 4))
    if not df_results.empty:
        window_cols = [f'videos_window_{l}' for l in WINDOW_LABELS]
        c2g_cols = [f'call2go_window_{l}' for l in WINDOW_LABELS]
        total_per_window = df_results[window_cols].sum()
        c2g_per_window = df_results[c2g_cols].sum()

        x = np.arange(len(WINDOW_LABELS))
        width = 0.35
        bars1 = ax.bar(x - width/2, total_per_window.values, width,
                       label='Todos os videos', color='steelblue', alpha=0.85)
        bars2 = ax.bar(x + width/2, c2g_per_window.values, width,
                       label='Videos Call2Go', color='darkorange', alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(WINDOW_LABELS, fontsize=8)
        ax.set_xlabel(
            "Janela de tempo relativa ao chart entry (dias)", fontsize=9)
        ax.set_ylabel("Total de videos (todos artistas)", fontsize=9)
        ax.set_title(
            "Videos por Janela Temporal (Q1 2026 -- 39 artistas seed)", fontsize=10)
        ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(WINDOWS_PNG, dpi=300)
    plt.close()
    print(f"  [OK] Janelas: {WINDOWS_PNG}")

    # --- 6c. Scatter correlacao principal ---------------------------- #
    fig, ax = plt.subplots(figsize=(6, 4))
    if not df_c2g.empty and df_c2g['lag_call2go_days'].notna().any():
        x_corr = df_c2g['lag_call2go_days']
        y_corr = df_c2g['score_spotify_normalized']
        ax.scatter(x_corr, y_corr, color='steelblue', alpha=0.7,
                   s=40, edgecolors='white', linewidths=0.3)

        # Linha de tendencia (regressao linear simples para visualizacao)
        paired_c = pd.DataFrame({'x': x_corr, 'y': y_corr}).dropna()
        if len(paired_c) >= 3:
            m, b = np.polyfit(paired_c['x'], paired_c['y'], 1)
            x_line = np.linspace(paired_c['x'].min(), paired_c['x'].max(), 100)
            ax.plot(x_line, m * x_line + b, color='red',
                    linewidth=1.2, linestyle='--', alpha=0.8)

        ax.axvline(0, color='gray', linestyle=':', linewidth=0.8)
        label_rho = f"rho={rho1:.3f}, p={p1:.3f}" if rho1 is not None else "n < 5"
        ax.set_xlabel(
            "lag_call2go_days (negativo = CTA antes do chart)", fontsize=9)
        ax.set_ylabel("score_spotify_normalized", fontsize=9)
        ax.set_title(
            f"Lag Call2Go vs Score Spotify Normalizado\n({label_rho}, n={n1})", fontsize=9)
    else:
        ax.text(0.5, 0.5, "Dados insuficientes\n(sem artistas com Call2Go e chart entry)",
                ha='center', va='center', transform=ax.transAxes, fontsize=10)
    plt.tight_layout()
    plt.savefig(CORR_PNG, dpi=300)
    plt.close()
    print(f"  [OK] Correlacao: {CORR_PNG}")

    # -------------------------------------------------------------- #
    # 7. Relatorio sumario no console                                 #
    # -------------------------------------------------------------- #
    print("\n" + "=" * 60)
    print("SUMARIO DA ANALISE TEMPORAL")
    print("=" * 60)
    print(
        f"Artistas analisados: {len(df_results)} (seed primarios com first_chart_week_spotify)")
    print(f"  com dados Call2Go: {len(df_c2g)}")
    print(
        f"\nLag (any video): mediana={df_results['lag_any_days'].median():.0f} dias")
    if not df_c2g.empty:
        print(
            f"Lag (Call2Go):    mediana={df_c2g['lag_call2go_days'].median():.0f} dias")
    print(f"\nArquivos gerados:")
    for path in [RESULTS_CSV, HIST_PNG, WINDOWS_PNG, CORR_PNG]:
        status = "[OK]" if os.path.exists(path) else "[AUSENTE]"
        print(f"  {status} {path}")


if __name__ == "__main__":
    run_chart_temporal_analysis()

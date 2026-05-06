"""Analise de confundidor: Call2Go vs popularidade pre-existente.

Pergunta de pesquisa secundaria:
    Os resultados nao-significativos de H2/H3 (Call2Go vs views/popularity)
    podem ser artefato de um confundidor: artistas ja populares no Spotify
    talvez adotem Call2Go com mais frequencia (pratica REATIVA), em vez de
    Call2Go gerar popularidade (pratica PREDITIVA).

Estrategia em 2 niveis:
    1. Regressao logistica: has_any_call2go_or ~ popularity + followers
       Mede se popularidade pre-existente prediz adocao de Call2Go.
    2. Estratificacao: divide os 67 artistas em quartis de popularity e
       roda H2 (Mann-Whitney views vs Call2Go) DENTRO de cada quartil.
       Se H2 continua n.s. em todos os quartis -> resultado robusto.
       Se H2 vira significativa em algum quartil -> nuance interessante.

Os resultados originais de H2 (U=280705, p=0.872) e H3 (p=1.000) NAO sao
alterados -- esta analise e complementar, para guiar a interpretacao.
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm

from src.config import ALPHA_DEFAULT, VALIDATION_DIR
from src.analytics._universe import filter_videos_to_topk


_DB_PATH = "data/processed/call2go.db"
_REPORT_PATH = VALIDATION_DIR / "confounder_analysis.txt"
_CSV_PATH = VALIDATION_DIR / "confounder_analysis_strat.csv"


def _load_artist_level_data():
    """Agrega: para cada artista, has_any Call2Go e popularidade Spotify.

    Fase 18: restringe ao universo Top-K do Rank Fusion antes de agregar.
    """
    conn = sqlite3.connect(_DB_PATH)

    df_videos_all = pd.read_sql_query(
        "SELECT artist_name, has_call2go_or, has_call2go, view_count "
        "FROM fact_yt_videos", conn)

    df_spotify = pd.read_sql_query(
        "SELECT artist_name, MAX(popularity) AS popularity, "
        "MAX(followers) AS followers FROM fact_spotify_metrics "
        "GROUP BY artist_name", conn)

    conn.close()

    # Fase 18: filtra para Top-K
    df_videos = filter_videos_to_topk(df_videos_all, artist_col='artist_name')
    print(f"  Videos apos filtro Top-K: {len(df_videos)}/{len(df_videos_all)}")

    df_artist = df_videos.groupby('artist_name').agg(
        has_any_or=('has_call2go_or', 'max'),
        has_any_and=('has_call2go', 'max'),
        n_videos=('view_count', 'count'),
        median_views=('view_count', 'median'),
    ).reset_index()

    df = df_artist.merge(df_spotify, on='artist_name', how='inner')
    return df, df_videos


def _fit_logit(df, target_col):
    """Ajusta logit Call2Go ~ popularity + followers. Retorna fit + odds + IC."""
    X = df[['popularity', 'followers']].astype(float)
    X = sm.add_constant(X)
    y = df[target_col].astype(int)

    if y.sum() == 0 or y.sum() == len(y):
        return None, None, None  # sem variabilidade -> logit nao converge

    try:
        model = sm.Logit(y, X).fit(disp=0, maxiter=100)
    except Exception:
        return None, None, None

    odds = np.exp(model.params)
    ci = np.exp(model.conf_int())
    ci.columns = ['ci_lower', 'ci_upper']
    return model, odds, ci


def _stratified_mann_whitney(df_artist, df_videos):
    """Roda H2 (views vs Call2Go OR) dentro de cada quartil de popularity."""
    df_artist = df_artist.copy()
    df_artist['pop_quartile'] = pd.qcut(
        df_artist['popularity'], q=4, labels=['Q1', 'Q2', 'Q3', 'Q4'],
        duplicates='drop')

    df_join = df_videos.merge(
        df_artist[['artist_name', 'pop_quartile']], on='artist_name', how='inner')

    results = []
    for q in ['Q1', 'Q2', 'Q3', 'Q4']:
        sub = df_join[df_join['pop_quartile'] == q]
        g1 = sub[sub['has_call2go_or'] == 1]['view_count']
        g0 = sub[sub['has_call2go_or'] == 0]['view_count']

        if len(g1) < 5 or len(g0) < 5:
            results.append({
                'quartile': q,
                'n_with': len(g1),
                'n_without': len(g0),
                'U': None,
                'p': None,
                'note': 'amostra insuficiente (n<5 em algum grupo)',
            })
            continue

        u, p = stats.mannwhitneyu(g1, g0, alternative='greater')
        results.append({
            'quartile': q,
            'n_with': len(g1),
            'n_without': len(g0),
            'U': float(u),
            'p': float(p),
            'note': 'significativo' if p < ALPHA_DEFAULT else 'n.s.',
        })
    return results


def run_confounder_analysis():
    print("Iniciando analise de confundidor (Call2Go vs popularidade SP)...")

    df_artist, df_videos = _load_artist_level_data()
    print(f"  Artistas com metricas completas: {len(df_artist)}")

    # 1. Regressao logistica
    model_or, odds_or, ci_or = _fit_logit(df_artist, 'has_any_or')
    model_and, odds_and, ci_and = _fit_logit(df_artist, 'has_any_and')

    # 2. Estratificacao
    strat = _stratified_mann_whitney(df_artist, df_videos)

    # 3. Persiste CSV de estratificacao
    os.makedirs(VALIDATION_DIR, exist_ok=True)
    pd.DataFrame(strat).to_csv(_CSV_PATH, index=False)

    # 4. Relatorio textual
    with open(_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("ANALISE DE CONFUNDIDOR -- Call2Go vs Popularidade SP\n")
        f.write("=" * 60 + "\n\n")
        f.write("Pergunta: artistas ja populares no Spotify tendem a adotar\n")
        f.write("Call2Go com mais frequencia (pratica REATIVA, nao PREDITIVA)?\n\n")
        f.write(f"Dataset: {len(df_artist)} artistas com metricas Spotify completas.\n")
        f.write(f"  has_any_call2go_or = 1: {int(df_artist['has_any_or'].sum())} artistas\n")
        f.write(f"  has_any_call2go_and = 1: {int(df_artist['has_any_and'].sum())} artistas\n\n")

        f.write("-" * 60 + "\n")
        f.write("REGRESSAO LOGISTICA -- has_any_call2go_or ~ popularity + followers\n")
        f.write("-" * 60 + "\n")
        if model_or is not None:
            f.write(model_or.summary().as_text() + "\n\n")
            f.write("Odds Ratio (IC 95%):\n")
            for var in odds_or.index:
                f.write(f"  {var}: OR={odds_or[var]:.6f} "
                        f"IC95=[{ci_or.loc[var,'ci_lower']:.6f}, "
                        f"{ci_or.loc[var,'ci_upper']:.6f}]\n")
            f.write("\nLeitura: OR>1 e IC nao cruzando 1 indica que aumento na variavel\n")
            f.write("aumenta odds de adotar Call2Go OR. OR=1 = sem efeito.\n\n")
        else:
            f.write("[AVISO] Logit nao convergiu (provavel falta de variabilidade).\n\n")

        f.write("-" * 60 + "\n")
        f.write("REGRESSAO LOGISTICA -- has_any_call2go_and ~ popularity + followers\n")
        f.write("-" * 60 + "\n")
        if model_and is not None:
            f.write(model_and.summary().as_text() + "\n\n")
            f.write("Odds Ratio (IC 95%):\n")
            for var in odds_and.index:
                f.write(f"  {var}: OR={odds_and[var]:.6f} "
                        f"IC95=[{ci_and.loc[var,'ci_lower']:.6f}, "
                        f"{ci_and.loc[var,'ci_upper']:.6f}]\n")
            f.write("\n")
        else:
            f.write("[AVISO] Logit nao convergiu para AND.\n\n")

        f.write("-" * 60 + "\n")
        f.write("ESTRATIFICACAO POR QUARTIL DE POPULARITY (H2 Mann-Whitney)\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'Quartil':<10}{'n_with':<10}{'n_without':<12}"
                f"{'U':<15}{'p':<10}{'Conclusao':<25}\n")
        f.write("-" * 80 + "\n")
        for r in strat:
            u_str = f"{r['U']:.0f}" if r['U'] is not None else "-"
            p_str = f"{r['p']:.4f}" if r['p'] is not None else "-"
            f.write(f"{r['quartile']:<10}{r['n_with']:<10}{r['n_without']:<12}"
                    f"{u_str:<15}{p_str:<10}{r['note']:<25}\n")
        f.write("\n")

        # Interpretacao final
        f.write("-" * 60 + "\n")
        f.write("INTERPRETACAO\n")
        f.write("-" * 60 + "\n")
        valid = [r for r in strat if r['p'] is not None]
        all_ns = valid and all(r['p'] >= ALPHA_DEFAULT for r in valid)
        any_sig = any(r['p'] is not None and r['p'] < ALPHA_DEFAULT for r in strat)

        if all_ns:
            f.write("H2 continua NAO-significativa em TODOS os quartis de popularidade.\n")
            f.write("Resultado ROBUSTO: Call2Go nao gera mais views, independente do nivel\n")
            f.write("de popularidade Spotify pre-existente. Confundidor nao explica o\n")
            f.write("resultado nulo de H2 -- o efeito (ou ausencia dele) e consistente.\n")
        elif any_sig:
            sig = [r['quartile'] for r in strat
                   if r['p'] is not None and r['p'] < ALPHA_DEFAULT]
            f.write(f"H2 SIGNIFICATIVA em quartis: {sig}.\n")
            f.write("Achado nuancado: Call2Go pode ser efetivo em segmentos especificos\n")
            f.write("de popularidade. Investigar se popularidade modera o efeito.\n")
        else:
            f.write("[AVISO] Nenhum quartil teve amostra suficiente para o teste.\n")

    print(f"[OK] Analise de confundidor salva em: {_REPORT_PATH}")
    print(f"[OK] Estratificacao em CSV: {_CSV_PATH}")
    return df_artist


if __name__ == "__main__":
    run_confounder_analysis()

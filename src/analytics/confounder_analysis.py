"""Analise de confundidor: Call2Go vs popularidade Spotify pre-existente.

Pergunta de pesquisa secundaria:
    O efeito observado em H2 (Call2Go associado a maiores views no YouTube)
    pode ser artefato de um confundidor: artistas ja populares no Spotify
    talvez adotem Call2Go com mais frequencia, e naturalmente ja teriam
    mais views, independente da estrategia.

Estrategia em 2 niveis:
    1. Regressao logistica (sklearn): has_any_call2go_or ~ popularity + followers
       Mede se a popularidade pre-existente prediz a adocao de Call2Go.
       Inferencia (p-values via Wald, pseudo-R^2 McFadden, LRT, IC 95%) e
       calculada manualmente sobre o LogisticRegression do sklearn -- veja
       `_logistic_inference.py`.
    2. Estratificacao: divide os artistas com dados em quartis de
       popularidade Spotify e roda H2 (Mann-Whitney views vs Call2Go) DENTRO
       de cada quartil. Heterogeneidade entre quartis indica que o efeito
       depende do nivel de popularidade.
"""

import os
import sqlite3

import pandas as pd
import numpy as np
from scipy import stats

from src.config import ALPHA_DEFAULT, VALIDATION_DIR
from src.analytics._universe import filter_videos_to_topk
from src.analytics._logistic_inference import (
    fit_logistic_with_inference,
    LogitInference,
)


_DB_PATH = "data/processed/call2go.db"
_REPORT_PATH = VALIDATION_DIR / "confounder_analysis.txt"
_CSV_PATH = VALIDATION_DIR / "confounder_analysis_strat.csv"

_FEATURES = ['popularity', 'followers']


def _load_artist_level_data():
    """Para cada artista do Top-K, agrega has_any Call2Go e popularidade Spotify."""
    conn = sqlite3.connect(_DB_PATH)

    df_videos_all = pd.read_sql_query(
        "SELECT artist_name, has_call2go_or, has_call2go, view_count "
        "FROM fact_yt_videos", conn)

    df_spotify = pd.read_sql_query(
        "SELECT artist_name, MAX(popularity) AS popularity, "
        "MAX(followers) AS followers FROM fact_spotify_metrics "
        "GROUP BY artist_name", conn)

    conn.close()

    # Restringe ao Top-K do Rank Fusion
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


def _fit_logit(df: pd.DataFrame, target_col: str) -> LogitInference | None:
    """Ajusta logit Call2Go ~ popularity + followers via sklearn + inferencia.

    Retorna None se a variavel-resposta nao tem variabilidade (todos 0 ou 1).
    """
    X = df[_FEATURES].astype(float).values
    y = df[target_col].astype(int).values

    if y.sum() == 0 or y.sum() == len(y):
        return None

    try:
        return fit_logistic_with_inference(X, y, feature_names=_FEATURES)
    except Exception as e:
        print(f"  [AVISO] Logit falhou para {target_col}: {e}")
        return None


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


def _write_logit_section(f, title: str, fit: LogitInference | None):
    f.write("-" * 60 + "\n")
    f.write(title + "\n")
    f.write("-" * 60 + "\n")
    if fit is None:
        f.write("[AVISO] Logit nao convergiu (falta de variabilidade ou erro).\n\n")
        return
    f.write(fit.summary_text() + "\n\n")
    f.write("Leitura: OR > 1 e IC 95% nao cruzando 1 indica que aumento na\n")
    f.write("variavel aumenta as odds de adotar Call2Go. OR = 1 = sem efeito.\n\n")


def run_confounder_analysis():
    print("Iniciando analise de confundidor (Call2Go vs popularidade SP)...")

    df_artist, df_videos = _load_artist_level_data()
    print(f"  Artistas com metricas completas: {len(df_artist)}")

    fit_or = _fit_logit(df_artist, 'has_any_or')
    fit_and = _fit_logit(df_artist, 'has_any_and')
    strat = _stratified_mann_whitney(df_artist, df_videos)

    os.makedirs(VALIDATION_DIR, exist_ok=True)
    pd.DataFrame(strat).to_csv(_CSV_PATH, index=False)

    with open(_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("ANALISE DE CONFUNDIDOR -- Call2Go vs Popularidade SP\n")
        f.write("=" * 60 + "\n\n")
        f.write("Pergunta: artistas ja populares no Spotify tendem a adotar\n")
        f.write("Call2Go com mais frequencia, gerando uma associacao espuria\n")
        f.write("entre Call2Go e maior numero de views?\n\n")
        f.write(f"Dataset: {len(df_artist)} artistas com metricas Spotify completas.\n")
        f.write(f"  has_any_call2go_or = 1: {int(df_artist['has_any_or'].sum())} artistas\n")
        f.write(f"  has_any_call2go_and = 1: {int(df_artist['has_any_and'].sum())} artistas\n\n")

        _write_logit_section(
            f, "REGRESSAO LOGISTICA -- has_any_call2go_or ~ popularity + followers",
            fit_or)

        _write_logit_section(
            f, "REGRESSAO LOGISTICA -- has_any_call2go_and ~ popularity + followers",
            fit_and)

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

        f.write("-" * 60 + "\n")
        f.write("INTERPRETACAO\n")
        f.write("-" * 60 + "\n")
        valid = [r for r in strat if r['p'] is not None]
        all_ns = valid and all(r['p'] >= ALPHA_DEFAULT for r in valid)
        any_sig = any(r['p'] is not None and r['p'] < ALPHA_DEFAULT for r in strat)

        if fit_or is not None:
            llr_p = fit_or.llr_p_value
            if llr_p > ALPHA_DEFAULT:
                f.write(f"Modelo logistico (LRT): p = {llr_p:.4f} > {ALPHA_DEFAULT}.\n")
                f.write("Popularidade Spotify NAO prediz adocao de Call2Go.\n")
                f.write("Hipotese de pratica reativa nao se sustenta em escala global.\n\n")
            else:
                f.write(f"Modelo logistico (LRT): p = {llr_p:.4f} < {ALPHA_DEFAULT}.\n")
                f.write("Popularidade Spotify prediz adocao de Call2Go.\n")
                f.write("Sugere pratica reativa: artistas populares adotam mais.\n\n")

        if all_ns:
            f.write("H2 nao-significativa em TODOS os quartis: efeito uniforme/ausente.\n")
        elif any_sig:
            sig = [r['quartile'] for r in strat
                   if r['p'] is not None and r['p'] < ALPHA_DEFAULT]
            f.write(f"H2 SIGNIFICATIVA em quartis: {sig}.\n")
            f.write("Heterogeneidade do efeito por nivel de popularidade.\n")
        else:
            f.write("[AVISO] Nenhum quartil teve amostra suficiente para o teste.\n")

    print(f"[OK] Analise de confundidor salva em: {_REPORT_PATH}")
    print(f"[OK] Estratificacao em CSV: {_CSV_PATH}")


if __name__ == "__main__":
    run_confounder_analysis()

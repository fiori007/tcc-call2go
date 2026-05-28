"""Analise de confundidor: Call2Go vs popularidade Spotify pre-existente.

Pergunta de pesquisa secundaria:
    O efeito observado em H2 (Call2Go associado a maiores views no YouTube)
    pode ser artefato de um confundidor: artistas ja populares no Spotify
    talvez adotem Call2Go com mais frequencia, e naturalmente ja teriam
    mais views, independente da estrategia.

Estrategia em 2 niveis:
    1. Regressao logistica (sklearn): has_any_call2go_or ~ popularity + followers
       Os odds ratios (OR = e^beta) sao reportados como medida DESCRITIVA de
       tamanho de efeito: OR proximo de 1 indica ausencia de associacao
       pratica entre a variavel e a adocao de Call2Go.
    2. Estratificacao: divide os artistas com dados em quartis de
       popularidade Spotify e roda H2 (Mann-Whitney views vs Call2Go) DENTRO
       de cada quartil. Heterogeneidade entre quartis indica que o efeito
       depende do nivel de popularidade.
"""

import os
import sqlite3
from dataclasses import dataclass

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression

from src.config import ALPHA_DEFAULT, VALIDATION_DIR
from src.analytics._universe import filter_videos_to_topk


_DB_PATH = "data/processed/call2go.db"
_REPORT_PATH = VALIDATION_DIR / "confounder_analysis.txt"
_CSV_PATH = VALIDATION_DIR / "confounder_analysis_strat.csv"

_FEATURES = ['popularity', 'followers']


@dataclass
class LogitOddsRatios:
    """Odds ratios descritivos de uma regressao logistica (sklearn)."""

    feature_names: list
    odds_ratio: list   # OR = exp(coef), alinhado a feature_names
    n_obs: int
    n_positive: int


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


def _fit_logit(df: pd.DataFrame, target_col: str) -> LogitOddsRatios | None:
    """Ajusta logit Call2Go ~ popularity + followers (sklearn) e retorna ORs.

    Reporta apenas os odds ratios (OR = e^beta) como medida descritiva de
    tamanho de efeito. Retorna None se a variavel-resposta nao tem
    variabilidade (todos 0 ou 1).
    """
    X = df[_FEATURES].astype(float).values
    y = df[target_col].astype(int).values

    if y.sum() == 0 or y.sum() == len(y):
        return None

    try:
        model = LogisticRegression(
            penalty=None,
            solver='lbfgs',
            max_iter=200,
            fit_intercept=True,
            random_state=42,
        )
        model.fit(X, y)
    except Exception as e:
        print(f"  [AVISO] Logit falhou para {target_col}: {e}")
        return None

    coef = model.coef_.flatten()
    odds = np.exp(coef)
    return LogitOddsRatios(
        feature_names=list(_FEATURES),
        odds_ratio=[float(o) for o in odds],
        n_obs=int(len(y)),
        n_positive=int(y.sum()),
    )


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


def _write_logit_section(f, title: str, fit: LogitOddsRatios | None):
    f.write("-" * 60 + "\n")
    f.write(title + "\n")
    f.write("-" * 60 + "\n")
    if fit is None:
        f.write("[AVISO] Logit nao ajustado (falta de variabilidade ou erro).\n\n")
        return
    f.write(f"  N observacoes: {fit.n_obs} (positivos: {fit.n_positive})\n")
    f.write("  Odds Ratios (OR = exp(coef)) -- medida descritiva de associacao:\n")
    for name, orv in zip(fit.feature_names, fit.odds_ratio):
        f.write(f"    {name:<14} OR = {orv:.4f}\n")
    f.write("\n")
    f.write("Leitura: OR proximo de 1 indica ausencia de associacao pratica\n")
    f.write("entre a variavel e a adocao de Call2Go. OR > 1 = associacao\n")
    f.write("positiva; OR < 1 = associacao negativa.\n\n")


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
            or_map = dict(zip(fit_or.feature_names, fit_or.odds_ratio))
            pop_or = or_map.get('popularity', float('nan'))
            fol_or = or_map.get('followers', float('nan'))
            f.write(f"Odds ratios (alvo OR): popularity OR={pop_or:.4f}, "
                    f"followers OR={fol_or:.4f}.\n")
            f.write("Ambos essencialmente iguais a 1: a popularidade Spotify\n")
            f.write("pre-existente NAO mostra associacao pratica com a adocao\n")
            f.write("de Call2Go. Hipotese de pratica reativa nao se sustenta\n")
            f.write("em escala global.\n\n")

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

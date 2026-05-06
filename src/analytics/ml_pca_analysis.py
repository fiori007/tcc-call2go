"""Reducao dimensional PCA dos artistas Top-K (Fase 19, sklearn).

Projeta os 46 artistas em um plano 2D baseado em similaridade multidimensional
(score, popularidade, presenca, last.fm). Pontos coloridos por has_call2go
permitem visualizar se ha agrupamento de Call2Go no espaco reduzido.

Output:
- data/plots/ml_pca_artists.png
- data/validation/ml_pca_report.txt (variancia explicada + loading scores)
"""

import os
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from src.config import RANDOM_SEED, VALIDATION_DIR, PLOT_DPI
from src.analytics._universe import (
    load_topk_dataframe, filter_videos_to_topk, _normalize_name)


logger = logging.getLogger(__name__)


_REPORT_PATH = VALIDATION_DIR / "ml_pca_report.txt"
_PLOT_PATH = "data/plots/ml_pca_artists.png"
_FLAGGED_CSV = "data/processed/youtube_call2go_flagged.csv"

# Features cross-platform (cobrem score + presenca; Spotify/Last.fm vem do merge)
_FEATURES_CORE = [
    'score_combined',
    'score_spotify_normalized',
    'score_youtube_normalized',
    'presence_count_spotify',
    'presence_count_youtube',
]


def _build_dataset() -> pd.DataFrame:
    """Carrega Top-K + has_any_call2go_or."""
    df = load_topk_dataframe(only_topk=True)
    if df.empty:
        return df

    if os.path.exists(_FLAGGED_CSV):
        df_flag = pd.read_csv(_FLAGGED_CSV)
        df_flag = filter_videos_to_topk(df_flag, artist_col='artist_name')
        df_flag['_norm'] = df_flag['artist_name'].apply(_normalize_name)
        agg = df_flag.groupby('_norm', as_index=False)['has_call2go_or'].max()
        agg.columns = ['artist_normalized', 'has_any_call2go_or']
        df = df.merge(agg, on='artist_normalized', how='left')

    return df


def _project(df: pd.DataFrame) -> dict:
    """Padroniza features e projeta em 2D via PCA."""
    X = df[_FEATURES_CORE].copy()
    X = X.fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X.values)

    pca = PCA(n_components=2, random_state=RANDOM_SEED)
    X_2d = pca.fit_transform(X_scaled)

    # Loading scores (peso de cada feature em cada componente)
    loadings = pd.DataFrame(
        pca.components_.T,
        columns=['PC1', 'PC2'],
        index=_FEATURES_CORE,
    )

    return {
        'X_2d': X_2d,
        'explained': pca.explained_variance_ratio_,
        'cumulative': pca.explained_variance_ratio_.cumsum(),
        'loadings': loadings,
    }


def _plot_pca(df: pd.DataFrame, result: dict):
    X_2d = result['X_2d']
    explained = result['explained']

    has_call2go = 'has_any_call2go_or' in df.columns
    fig, ax = plt.subplots(figsize=(7, 5))

    if has_call2go:
        for label, color, marker in [(1, 'crimson', 'o'),
                                      (0, 'steelblue', 's')]:
            mask = df['has_any_call2go_or'] == label
            ax.scatter(X_2d[mask, 0], X_2d[mask, 1],
                       c=color, marker=marker,
                       s=80, alpha=0.75, edgecolors='black', linewidth=0.5,
                       label=f'Call2Go = {label}')
        # NaN tambem
        nan_mask = df['has_any_call2go_or'].isna()
        if nan_mask.any():
            ax.scatter(X_2d[nan_mask, 0], X_2d[nan_mask, 1],
                       c='lightgray', marker='x', s=60,
                       label='Call2Go = N/A')
        ax.legend(loc='best')
    else:
        ax.scatter(X_2d[:, 0], X_2d[:, 1], c='steelblue', s=70, alpha=0.7)

    ax.set_xlabel(f'PC1 ({explained[0]*100:.1f}% variancia)')
    ax.set_ylabel(f'PC2 ({explained[1]*100:.1f}% variancia)')
    ax.set_title(f'PCA 2D dos {len(df)} artistas Top-K -- '
                 f'{result["cumulative"][-1]*100:.1f}% var. acumulada')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    os.makedirs(os.path.dirname(_PLOT_PATH), exist_ok=True)
    fig.savefig(_PLOT_PATH, dpi=PLOT_DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  [OK] Plot salvo: {_PLOT_PATH}")


def _write_report(df: pd.DataFrame, result: dict):
    os.makedirs(VALIDATION_DIR, exist_ok=True)
    with open(_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("PCA 2D -- Artistas Top-K (sklearn)\n")
        f.write("Fase 19 -- reducao dimensional\n")
        f.write("=" * 60 + "\n\n")

        f.write("DATASET\n")
        f.write("-" * 60 + "\n")
        f.write(f"  Top-K artistas: {len(df)}\n")
        f.write(f"  Features: {len(_FEATURES_CORE)}\n")
        for c in _FEATURES_CORE:
            f.write(f"    - {c}\n")
        f.write("\n")

        f.write("VARIANCIA EXPLICADA\n")
        f.write("-" * 60 + "\n")
        f.write(f"  PC1: {result['explained'][0]*100:.2f}%\n")
        f.write(f"  PC2: {result['explained'][1]*100:.2f}%\n")
        f.write(f"  Acumulada (PC1+PC2): {result['cumulative'][-1]*100:.2f}%\n\n")

        f.write("INTERPRETACAO\n")
        f.write("-" * 60 + "\n")
        f.write("  Variancia explicada >= 60% -> visualizacao 2D representativa.\n")
        f.write("  Variancia explicada <  60% -> 3 componentes podem ser necessarios.\n\n")

        f.write("LOADING SCORES (peso de cada feature em cada componente)\n")
        f.write("-" * 60 + "\n")
        f.write(result['loadings'].round(4).to_string() + "\n\n")

        f.write("LEITURA DOS LOADINGS\n")
        f.write("-" * 60 + "\n")
        f.write("  |loading| > 0,5 -> feature dominante naquele componente.\n")
        f.write("  PC1 e o eixo onde a maioria da variabilidade reside;\n")
        f.write("  PC2 captura variabilidade residual ortogonal a PC1.\n")

    print(f"  [OK] Relatorio: {_REPORT_PATH}")


def run_ml_pca_analysis():
    print("=" * 60)
    print("ML PCA -- visualizacao 2D")
    print("=" * 60)

    df = _build_dataset()
    if df.empty:
        print("[ERRO] Top-K vazio.")
        return

    print(f"  Dataset: {len(df)} artistas, {len(_FEATURES_CORE)} features")
    result = _project(df)

    print(f"  Variancia explicada: PC1={result['explained'][0]*100:.1f}%, "
          f"PC2={result['explained'][1]*100:.1f}% "
          f"(acumulada {result['cumulative'][-1]*100:.1f}%)")

    _plot_pca(df, result)
    _write_report(df, result)


if __name__ == "__main__":
    run_ml_pca_analysis()

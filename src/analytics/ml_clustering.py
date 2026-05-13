"""Clustering nao-supervisionado de artistas (KMeans + silhouette, scikit-learn).

Aplica KMeans sobre vetores comportamentais dos artistas Top-K, descobrindo
agrupamentos automaticos que substituem (ou complementam) a taxonomia
hardcoded do ranking_fusion (absent / single / persistent / ...).

Features usadas: ranks mensais nas duas plataformas + score_combined.
Decisao do K: melhor silhouette_score em uma faixa k=2..6.

Output:
- data/processed/artist_clusters.csv (artist + cluster_label)
- data/plots/ml_clustering_pca.png (visualizacao 2D)
- data/validation/ml_clustering_report.txt
"""

import os
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

from src.config import RANDOM_SEED, VALIDATION_DIR, PLOT_DPI
from src.analytics._universe import load_topk_dataframe


logger = logging.getLogger(__name__)


_CLUSTERS_CSV = "data/processed/artist_clusters.csv"
_REPORT_PATH = VALIDATION_DIR / "ml_clustering_report.txt"
_PCA_PLOT = "data/plots/ml_clustering_pca.png"

# Features comportamentais (cobrem padroes de presenca + magnitude)
_FEATURES = [
    'rank_Jan_sp', 'rank_Feb_sp', 'rank_Mar_sp',
    'rank_Jan_yt', 'rank_Feb_yt', 'rank_Mar_yt',
    'score_combined',
]

# Faixa de K a testar (centralizada em src/config.py)
from src.config import ML_K_RANGE as _K_RANGE


def _prepare_features(df: pd.DataFrame) -> tuple:
    """Prepara features (substitui NaN por 101 = ausente em chart Top-100)."""
    X = df[_FEATURES].copy()
    # Rank ausente: artista nao apareceu naquele mes -- usamos 101 (pior que 100)
    rank_cols = [c for c in _FEATURES if c.startswith('rank_')]
    for c in rank_cols:
        X[c] = X[c].fillna(101)
    # score_combined ausente: 0
    X['score_combined'] = X['score_combined'].fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X.values)
    return X_scaled, X


def _find_best_k(X_scaled: np.ndarray) -> dict:
    """Testa K em [2..6] e retorna o melhor pelo silhouette_score."""
    results = []
    for k in _K_RANGE:
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_SEED)
        labels = km.fit_predict(X_scaled)
        if len(set(labels)) < 2:
            continue
        sil = silhouette_score(X_scaled, labels)
        results.append({'k': k, 'silhouette': sil, 'inertia': km.inertia_})
    if not results:
        return {}
    df_res = pd.DataFrame(results).sort_values('silhouette', ascending=False)
    best = df_res.iloc[0].to_dict()
    return {'best_k': int(best['k']), 'best_silhouette': best['silhouette'],
            'all': df_res.to_dict('records')}


def _fit_final(X_scaled: np.ndarray, k: int):
    """Ajusta KMeans com k otimo e retorna labels + centroides."""
    km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_SEED)
    labels = km.fit_predict(X_scaled)
    return km, labels


def _project_pca(X_scaled: np.ndarray) -> tuple:
    """Reduz para 2D para plot."""
    pca = PCA(n_components=2, random_state=RANDOM_SEED)
    X_2d = pca.fit_transform(X_scaled)
    explained = pca.explained_variance_ratio_
    return X_2d, explained


def _plot_clusters(X_2d, labels, df_topk, explained, k):
    fig, ax = plt.subplots(figsize=(7, 5))
    cmap = plt.get_cmap('tab10')
    for cluster_id in sorted(set(labels)):
        mask = labels == cluster_id
        ax.scatter(X_2d[mask, 0], X_2d[mask, 1],
                   c=[cmap(cluster_id)], label=f'Cluster {cluster_id}',
                   s=80, alpha=0.7, edgecolors='black', linewidth=0.5)
    ax.set_xlabel(f'PC1 ({explained[0]*100:.1f}% var.)')
    ax.set_ylabel(f'PC2 ({explained[1]*100:.1f}% var.)')
    ax.set_title(f'KMeans clustering (k={k}) sobre artistas Top-K -- '
                 f'projecao PCA 2D')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    os.makedirs(os.path.dirname(_PCA_PLOT), exist_ok=True)
    fig.savefig(_PCA_PLOT, dpi=PLOT_DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  [OK] Plot salvo: {_PCA_PLOT}")


def _summarize_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """Sumariza cada cluster: mediana de cada feature + n + has_call2go_or rate."""
    cols = _FEATURES + ['has_any_call2go_or'] if 'has_any_call2go_or' in df.columns else _FEATURES
    summary = df.groupby('cluster_label')[cols].agg(['median', 'mean']).round(3)
    counts = df.groupby('cluster_label').size().rename('n')
    return summary, counts


def _write_report(df: pd.DataFrame, k_search: dict, summary, counts):
    os.makedirs(VALIDATION_DIR, exist_ok=True)
    with open(_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("ML CLUSTERING -- KMeans + silhouette (sklearn)\n")
        f.write("Agrupamento comportamental nao-supervisionado\n")
        f.write("=" * 60 + "\n\n")

        f.write("FEATURES USADAS\n")
        f.write("-" * 60 + "\n")
        for c in _FEATURES:
            f.write(f"  - {c}\n")
        f.write("\n")

        f.write("BUSCA DE K (silhouette_score, k in [2,6])\n")
        f.write("-" * 60 + "\n")
        f.write(f"  {'k':>3}  {'silhouette':>12}  {'inertia':>12}\n")
        for entry in k_search['all']:
            f.write(f"  {entry['k']:>3}  {entry['silhouette']:>12.4f}  "
                    f"{entry['inertia']:>12.4f}\n")
        f.write(f"\n  K otimo: {k_search['best_k']} "
                f"(silhouette = {k_search['best_silhouette']:.4f})\n\n")

        f.write("INTERPRETACAO DO SILHOUETTE\n")
        f.write("-" * 60 + "\n")
        f.write("  s ~ +1  -> cluster bem separado e coeso\n")
        f.write("  s ~  0  -> objeto esta na fronteira entre clusters\n")
        f.write("  s ~ -1  -> objeto esta no cluster errado\n")
        f.write("  Heuristica: silhouette >= 0,5 = boa separacao;\n")
        f.write("              silhouette >= 0,25 = aceitavel para dados ruidosos.\n\n")

        f.write("CLUSTERS RESULTANTES\n")
        f.write("-" * 60 + "\n")
        f.write(f"  Total artistas: {len(df)}\n")
        for cl, n in counts.items():
            f.write(f"  Cluster {cl}: {n} artistas\n")
        f.write("\n")

        f.write("MEDIANAS POR CLUSTER\n")
        f.write("-" * 60 + "\n")
        f.write(summary.to_string() + "\n\n")

        if 'has_any_call2go_or' in df.columns:
            f.write("DISTRIBUICAO DE CALL2GO POR CLUSTER\n")
            f.write("-" * 60 + "\n")
            tab = pd.crosstab(df['cluster_label'], df['has_any_call2go_or'])
            f.write(tab.to_string() + "\n")

    print(f"  [OK] Relatorio: {_REPORT_PATH}")


def run_ml_clustering():
    print("=" * 60)
    print("ML CLUSTERING -- KMeans + silhouette")
    print("=" * 60)

    df = load_topk_dataframe(only_topk=True)
    if df.empty:
        print("[ERRO] Top-K vazio.")
        return

    # Adiciona has_any_call2go_or se disponivel (para distribuicao por cluster)
    flagged_path = "data/processed/youtube_call2go_flagged.csv"
    if os.path.exists(flagged_path):
        from src.analytics._universe import _normalize_name, filter_videos_to_topk
        df_flag = pd.read_csv(flagged_path)
        df_flag = filter_videos_to_topk(df_flag, artist_col='artist_name')
        df_flag['_norm'] = df_flag['artist_name'].apply(_normalize_name)
        flag = df_flag.groupby('_norm', as_index=False)['has_call2go_or'].max()
        flag.columns = ['artist_normalized', 'has_any_call2go_or']
        df = df.merge(flag, on='artist_normalized', how='left')

    X_scaled, X_orig = _prepare_features(df)
    print(f"  Dataset: {len(df)} artistas, {len(_FEATURES)} features")

    k_search = _find_best_k(X_scaled)
    if not k_search:
        print("[ERRO] silhouette nao calculavel.")
        return

    print(f"\n  Melhor K: {k_search['best_k']} "
          f"(silhouette = {k_search['best_silhouette']:.4f})")

    km, labels = _fit_final(X_scaled, k_search['best_k'])
    df['cluster_label'] = labels

    X_2d, explained = _project_pca(X_scaled)
    print(f"  PCA: variancia explicada PC1={explained[0]*100:.1f}%, "
          f"PC2={explained[1]*100:.1f}%")

    _plot_clusters(X_2d, labels, df, explained, k_search['best_k'])

    summary, counts = _summarize_clusters(df)
    _write_report(df, k_search, summary, counts)

    # Salva CSV de saida
    os.makedirs(os.path.dirname(_CLUSTERS_CSV), exist_ok=True)
    df_out = df[['artist_normalized', 'cluster_label'] + _FEATURES].copy()
    if 'has_any_call2go_or' in df.columns:
        df_out['has_any_call2go_or'] = df['has_any_call2go_or']
    df_out.to_csv(_CLUSTERS_CSV, index=False)
    print(f"  [OK] Clusters salvos: {_CLUSTERS_CSV}")


if __name__ == "__main__":
    run_ml_clustering()

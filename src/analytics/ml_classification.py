"""Classificador supervisionado para predizer adocao de Call2Go (Fase 19).

Usa Random Forest sobre features cross-platform (score, popularity, followers,
listeners, scrobbles, presence_count) para responder:

    "Dadas as caracteristicas de um artista, da para PREDIZER se ele usa
     Call2Go? E quais variaveis sao mais informativas para essa predicao?"

Complementa a regressao logistica do confounder_analysis (statsmodels):
- Statsmodels: testa significancia individual e interpretabilidade (LLR, OR)
- Sklearn RF: captura interacoes nao-lineares + feature importance
"""

import os
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    roc_curve, auc, confusion_matrix, classification_report,
)
from sklearn.preprocessing import StandardScaler

from src.config import RANDOM_SEED, VALIDATION_DIR, PLOT_DPI
from src.analytics._universe import load_topk_dataframe, filter_videos_to_topk


logger = logging.getLogger(__name__)


_FLAGGED_CSV = "data/processed/youtube_call2go_flagged.csv"
_REPORT_PATH = VALIDATION_DIR / "ml_classification_report.txt"
_ROC_PLOT = "data/plots/ml_call2go_roc.png"
_FEATURE_IMP_PLOT = "data/plots/ml_call2go_feature_importance.png"

_FEATURES = [
    'score_combined',
    'score_spotify_normalized',
    'score_youtube_normalized',
    'presence_count_spotify',
    'presence_count_youtube',
]


def _build_dataset() -> pd.DataFrame:
    """Junta Top-K + has_any_call2go_or por artista."""
    df_topk = load_topk_dataframe(only_topk=True)
    if df_topk.empty:
        return pd.DataFrame()

    if not os.path.exists(_FLAGGED_CSV):
        logger.error("flagged.csv nao existe: %s", _FLAGGED_CSV)
        return pd.DataFrame()

    df_flagged = pd.read_csv(_FLAGGED_CSV)
    # Filtra para Top-K (apenas videos de artistas no universo analitico)
    df_flagged = filter_videos_to_topk(df_flagged, artist_col='artist_name')

    # Agrega por artista: usa_or = max(has_call2go_or) -- ao menos 1 video sim
    from src.analytics._universe import _normalize_name
    df_flagged['_norm'] = df_flagged['artist_name'].apply(_normalize_name)
    flag = df_flagged.groupby('_norm', as_index=False)['has_call2go_or'].max()
    flag.columns = ['artist_normalized', 'has_any_call2go_or']

    df = df_topk.merge(flag, on='artist_normalized', how='left')
    df = df.dropna(subset=['has_any_call2go_or'])
    df['has_any_call2go_or'] = df['has_any_call2go_or'].astype(int)

    # Drop linhas com features faltantes
    df = df.dropna(subset=_FEATURES)
    return df


def _train_evaluate(df: pd.DataFrame) -> dict:
    """Treina RF com 5-fold CV e retorna metricas + modelo treinado em todo o df."""
    X = df[_FEATURES].astype(float).values
    y = df['has_any_call2go_or'].values

    # Padronizacao (RF nao requer mas ajuda interpretacao com features mistas)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Modelo
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=RANDOM_SEED,
    )

    # 5-fold stratified CV (com piso de min(5, classe minoritaria))
    n_splits = min(5, int(min(np.bincount(y))))
    if n_splits < 2:
        return {
            'error': 'classe minoritaria com menos de 2 amostras -- CV inviavel',
            'n': len(y),
            'n_class_1': int(np.sum(y == 1)),
            'n_class_0': int(np.sum(y == 0)),
        }

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True,
                          random_state=RANDOM_SEED)

    auc_scores = cross_val_score(rf, X_scaled, y, cv=skf,
                                 scoring='roc_auc')
    acc_scores = cross_val_score(rf, X_scaled, y, cv=skf,
                                 scoring='accuracy')

    # Predicoes out-of-fold para ROC final agregado
    from sklearn.model_selection import cross_val_predict
    y_proba = cross_val_predict(rf, X_scaled, y, cv=skf,
                                method='predict_proba')[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)

    fpr, tpr, _ = roc_curve(y, y_proba)
    roc_auc = auc(fpr, tpr)

    cm = confusion_matrix(y, y_pred)
    cls_report = classification_report(y, y_pred, target_names=['no', 'yes'],
                                       zero_division=0)

    # Treina no full data para feature importance
    rf.fit(X_scaled, y)
    importances = pd.DataFrame({
        'feature': _FEATURES,
        'importance': rf.feature_importances_,
    }).sort_values('importance', ascending=False)

    return {
        'n': len(y),
        'n_class_1': int(np.sum(y == 1)),
        'n_class_0': int(np.sum(y == 0)),
        'cv_n_splits': n_splits,
        'auc_mean': float(auc_scores.mean()),
        'auc_std': float(auc_scores.std()),
        'acc_mean': float(acc_scores.mean()),
        'acc_std': float(acc_scores.std()),
        'roc_auc_aggregated': float(roc_auc),
        'fpr': fpr.tolist(),
        'tpr': tpr.tolist(),
        'confusion_matrix': cm.tolist(),
        'classification_report': cls_report,
        'feature_importances': importances,
    }


def _plot_roc(result: dict):
    fpr = result['fpr']
    tpr = result['tpr']
    auc_val = result['roc_auc_aggregated']

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(fpr, tpr, label=f'ROC (AUC = {auc_val:.3f})', linewidth=2)
    ax.plot([0, 1], [0, 1], '--', color='gray',
            label='Aleatorio (AUC = 0,5)', linewidth=1)
    ax.set_xlabel('Taxa de falso positivo (FPR)')
    ax.set_ylabel('Taxa de verdadeiro positivo (TPR)')
    ax.set_title('Curva ROC -- Predicao Call2Go via Random Forest')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    os.makedirs(os.path.dirname(_ROC_PLOT), exist_ok=True)
    fig.savefig(_ROC_PLOT, dpi=PLOT_DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  [OK] ROC salva: {_ROC_PLOT}")


def _plot_feature_importance(result: dict):
    df = result['feature_importances']
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(df['feature'][::-1], df['importance'][::-1], color='steelblue')
    ax.set_xlabel('Importancia (impurity decrease normalizada)')
    ax.set_title('Feature Importance -- Random Forest predizendo Call2Go')
    ax.grid(True, axis='x', alpha=0.3)
    fig.tight_layout()
    fig.savefig(_FEATURE_IMP_PLOT, dpi=PLOT_DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  [OK] Feature importance salva: {_FEATURE_IMP_PLOT}")


def _write_report(result: dict):
    os.makedirs(VALIDATION_DIR, exist_ok=True)
    with open(_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("ML CLASSIFICATION -- Random Forest predizendo Call2Go\n")
        f.write("Fase 19 (sklearn integration)\n")
        f.write("=" * 60 + "\n\n")

        f.write("DATASET\n")
        f.write("-" * 60 + "\n")
        f.write(f"  Universo: Top-K do Rank Fusion ({result['n']} artistas)\n")
        f.write(f"  Classe 1 (com Call2Go OR): {result['n_class_1']}\n")
        f.write(f"  Classe 0 (sem Call2Go):    {result['n_class_0']}\n\n")

        f.write("HIPERPARAMETROS\n")
        f.write("-" * 60 + "\n")
        f.write(f"  RandomForestClassifier(n_estimators=200, "
                f"min_samples_leaf=2, class_weight='balanced',\n"
                f"                          random_state={RANDOM_SEED})\n")
        f.write(f"  StratifiedKFold(n_splits={result['cv_n_splits']}, "
                f"shuffle=True, random_state={RANDOM_SEED})\n\n")

        f.write("METRICAS DE VALIDACAO CRUZADA (5-fold estratificada)\n")
        f.write("-" * 60 + "\n")
        f.write(f"  AUC ROC      : {result['auc_mean']:.3f} +/- {result['auc_std']:.3f}\n")
        f.write(f"  Accuracy     : {result['acc_mean']:.3f} +/- {result['acc_std']:.3f}\n")
        f.write(f"  ROC AUC (out-of-fold agregado): {result['roc_auc_aggregated']:.3f}\n\n")

        f.write("LEITURA DA AUC ROC\n")
        f.write("-" * 60 + "\n")
        f.write("  AUC = 0,5 -> classificador no nivel do acaso\n")
        f.write("  AUC = 0,7 -> bom poder discriminativo\n")
        f.write("  AUC = 0,8 -> excelente\n")
        f.write("  AUC = 1,0 -> perfeito\n\n")

        f.write("CLASSIFICATION REPORT (out-of-fold)\n")
        f.write("-" * 60 + "\n")
        f.write(result['classification_report'] + "\n")

        f.write("CONFUSION MATRIX (out-of-fold)\n")
        f.write("-" * 60 + "\n")
        cm = result['confusion_matrix']
        f.write(f"                  pred=0   pred=1\n")
        f.write(f"  real=0 (sem)    {cm[0][0]:>6}   {cm[0][1]:>6}\n")
        f.write(f"  real=1 (com)    {cm[1][0]:>6}   {cm[1][1]:>6}\n\n")

        f.write("FEATURE IMPORTANCE (modelo treinado em todo o dataset)\n")
        f.write("-" * 60 + "\n")
        for _, row in result['feature_importances'].iterrows():
            f.write(f"  {row['feature']:<35s} {row['importance']:.4f}\n")

    print(f"  [OK] Relatorio salvo: {_REPORT_PATH}")


def run_ml_classification():
    print("=" * 60)
    print("ML CLASSIFICATION -- Random Forest")
    print("=" * 60)

    df = _build_dataset()
    if df.empty:
        print("[ERRO] Dataset vazio -- verifique pipeline.")
        return

    result = _train_evaluate(df)
    if 'error' in result:
        print(f"[ERRO] {result['error']}")
        return

    print(f"\n  Dataset: {result['n']} artistas "
          f"(classe 1={result['n_class_1']}, classe 0={result['n_class_0']})")
    print(f"  AUC ROC (CV {result['cv_n_splits']}-fold): "
          f"{result['auc_mean']:.3f} +/- {result['auc_std']:.3f}")
    print(f"  Accuracy   : {result['acc_mean']:.3f} +/- {result['acc_std']:.3f}\n")

    print("  Top features:")
    for _, row in result['feature_importances'].head(3).iterrows():
        print(f"    {row['feature']:<35s} {row['importance']:.4f}")

    _plot_roc(result)
    _plot_feature_importance(result)
    _write_report(result)


if __name__ == "__main__":
    run_ml_classification()

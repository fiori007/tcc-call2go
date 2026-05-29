"""Sincroniza as figuras geradas pelo pipeline para a pasta de figuras dos
documentos LaTeX (artigo e colinha).

Motivacao
---------
O pipeline grava figuras em `data/plots/` (etapas analiticas) e em
`data/validation/` (validacao cross-platform). Os documentos LaTeX, porem,
incluem figuras de `artigo_latex/figs/` (a colinha referencia o mesmo
diretorio via `../../artigo_latex/figs/`). Sem uma sincronizacao explicita,
essas copias defasam silenciosamente em relacao a saida canonica do pipeline.

Este script materializa esse passo de forma MAPEADA, reproduzivel e
versionavel: cada figura usada pelos documentos tem origem declarada abaixo.
Fluxo recomendado:

    python run_pipeline.py --skip-collect --strict   # regenera data/plots e data/validation
    python scripts/sync_figures.py                    # sincroniza -> artigo_latex/figs
    # recompilar LaTeX (artigo e colinha)

Figuras NAO sincronizadas (sem origem no pipeline de 20 etapas):
    confusion_matrix_combined.png, confusion_matrix_video_only.png,
    validation_metrics_per_class.png  -> geradas pela validacao adversarial
    (src/validation/agreement_report.py), executada separadamente; metricas
    (kappa canal 0,80 / video 0,45) estaveis. Mantidas como estao em figs/.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLOTS_DIR = PROJECT_ROOT / "data" / "plots"
VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"
FIGS_DIR = PROJECT_ROOT / "artigo_latex" / "figs"

# Mapa explicito: nome_destino -> caminho_de_origem (saida canonica do pipeline).
# Toda figura consumida pelos documentos LaTeX deve estar mapeada aqui.
FIGURE_MAP: dict[str, Path] = {
    # --- Estatistica / EDA / ML (data/plots) ---
    "boxplot_call2go_views.png": PLOTS_DIR / "boxplot_call2go_views.png",
    "chart_temporal_lag_histogram.png": PLOTS_DIR / "chart_temporal_lag_histogram.png",
    "scatter_cross_platform.png": PLOTS_DIR / "scatter_cross_platform.png",
    "ml_pca_artists.png": PLOTS_DIR / "ml_pca_artists.png",
    "ml_call2go_feature_importance.png": PLOTS_DIR / "ml_call2go_feature_importance.png",
    "ml_call2go_roc.png": PLOTS_DIR / "ml_call2go_roc.png",
    "ml_clustering_pca.png": PLOTS_DIR / "ml_clustering_pca.png",
    # --- Validacao cross-platform bidirecional (data/validation) ---
    "bidirectional_correlation_matrix.png": VALIDATION_DIR / "bidirectional_correlation_matrix.png",
    "direction_a_youtube_to_spotify.png": VALIDATION_DIR / "direction_a_youtube_to_spotify.png",
    "direction_b_spotify_to_youtube.png": VALIDATION_DIR / "direction_b_spotify_to_youtube.png",
}


def sync() -> int:
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    copied, missing = [], []
    for dest_name, src in FIGURE_MAP.items():
        if src.exists():
            shutil.copy2(src, FIGS_DIR / dest_name)
            copied.append(dest_name)
        else:
            missing.append((dest_name, src))

    print(f"Sincronizadas {len(copied)} figuras -> {FIGS_DIR}")
    for name in copied:
        print(f"  [OK] {name}")
    if missing:
        print(f"\n[AVISO] {len(missing)} origem(ns) ausente(s) "
              f"(rode o pipeline antes de sincronizar):")
        for name, src in missing:
            print(f"  [--] {name}  <-  {src.relative_to(PROJECT_ROOT)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(sync())

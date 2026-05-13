"""Constantes centrais do projeto TCC Call2Go.

Centraliza paths, parametros estatisticos e magic numbers de ML/coleta
para evitar dispersao pelo codigo.
"""

from pathlib import Path

# ------------------------------------------------------------------ #
#  Paths                                                              #
# ------------------------------------------------------------------ #
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SEED_DIR = DATA_DIR / "seed"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
PLOTS_DIR = DATA_DIR / "plots"
VALIDATION_DIR = DATA_DIR / "validation"

# ------------------------------------------------------------------ #
#  Estatistica                                                        #
# ------------------------------------------------------------------ #
ALPHA_DEFAULT = 0.05
ALPHA_RELAXED = 0.10  # cross_platform_validator: IC mais largo p/ amostras pequenas
RANDOM_SEED = 42
BOOTSTRAP_RESAMPLES = 2000

# ------------------------------------------------------------------ #
#  Plots                                                              #
# ------------------------------------------------------------------ #
PLOT_DPI = 300
PLOT_ALPHA = 0.7  # transparencia de plot (NAO confundir com nivel de significancia)

# ------------------------------------------------------------------ #
#  ML / Universo analitico                                            #
# ------------------------------------------------------------------ #
TOP_K_PERCENTILE = 0.20            # ranking_fusion: Top-20% por score
TOP_K_FLOOR = 20                   # piso para poder estatistico Mann-Whitney
ML_K_RANGE = list(range(2, 7))     # busca de K em K-means (2..6)
RANDOM_FOREST_TREES = 200
CV_FOLDS = 5

# ------------------------------------------------------------------ #
#  Coleta YouTube                                                     #
# ------------------------------------------------------------------ #
MAX_VIDEOS_PER_ARTIST = 30
MAX_SCAN_VIDEOS = 200

# ------------------------------------------------------------------ #
#  Janela temporal (1o quadrimestre 2026)                             #
# ------------------------------------------------------------------ #
N_MESES = 4
WEEKS_PER_PLATFORM = 17
MONTH_LABELS = ["Jan", "Fev", "Mar", "Abr"]

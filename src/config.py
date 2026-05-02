"""Constantes centrais do projeto TCC Call2Go.

Centraliza paths, parametros estatisticos e configuracoes de plot
para evitar dispersao de magic numbers pelo codigo.

Disponibilizado na Onda 1 do hardening; migracao efetiva dos modulos
para usar estas constantes esta planejada para a Onda 2 (ver
memory-bank/progress.md).
"""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SEED_DIR = DATA_DIR / "seed"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
PLOTS_DIR = DATA_DIR / "plots"
VALIDATION_DIR = DATA_DIR / "validation"

# Estatistica
ALPHA_DEFAULT = 0.05
ALPHA_RELAXED = 0.10  # cross_platform_validator: IC mais largo p/ amostras pequenas
RANDOM_SEED = 42
BOOTSTRAP_RESAMPLES = 2000

# Plots
PLOT_DPI = 300
PLOT_ALPHA = 0.7  # transparencia de plot (NAO confundir com nivel de significancia)

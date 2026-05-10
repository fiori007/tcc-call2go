"""Testes para o módulo de inferência logística (sklearn-based).

Valida que os cálculos manuais de p-value, pseudo-R^2 e LRT produzem
resultados coerentes com expectativas matemáticas.
"""

import numpy as np
import pytest
from src.analytics._logistic_inference import (
    fit_logistic_with_inference,
    _log_likelihood,
)


def test_log_likelihood_basic():
    """Log-verossimilhança binomial em caso trivial."""
    y = np.array([1, 0, 1, 0])
    p = np.array([0.7, 0.3, 0.8, 0.2])
    expected = (
        np.log(0.7) + np.log(1 - 0.3) + np.log(0.8) + np.log(1 - 0.2)
    )
    assert abs(_log_likelihood(p, y) - expected) < 1e-9


def test_log_likelihood_perfect_prediction():
    """Predição perfeita -> ll próximo de 0 (com clip)."""
    y = np.array([1, 0, 1, 0])
    p = np.array([0.999, 0.001, 0.999, 0.001])
    ll = _log_likelihood(p, y)
    assert ll < 0
    assert ll > -1.0  # log(0.999) * 4 ≈ -0.004 each


def test_fit_basic_separable_data():
    """Dados linearmente separáveis: modelo deve atingir alta verossimilhança."""
    rng = np.random.RandomState(42)
    n = 100
    X = rng.randn(n, 2)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)

    result = fit_logistic_with_inference(
        X, y, feature_names=['x1', 'x2'])

    assert result.n_obs == n
    assert len(result.coef) == 2
    assert result.pseudo_r2_mcfadden > 0.3  # modelo bom para dado separável
    assert result.llr_p_value < 0.05  # modelo significativo
    assert len(result.p_values) == 3  # intercept + 2 features
    assert len(result.odds_ratio) == 3


def test_fit_random_data_null_model():
    """Dados aleatórios: modelo deve não ser significativo."""
    rng = np.random.RandomState(42)
    n = 100
    X = rng.randn(n, 2)
    y = rng.randint(0, 2, size=n)  # totalmente aleatório

    result = fit_logistic_with_inference(
        X, y, feature_names=['noise1', 'noise2'])

    # Modelo aleatório não deveria explicar muito
    assert result.pseudo_r2_mcfadden < 0.3
    # LLR p-value pode ou não ser >0.05; verificar apenas que está em [0,1]
    assert 0.0 <= result.llr_p_value <= 1.0


def test_fit_returns_summary_text():
    """summary_text() retorna string não vazia com campos esperados."""
    rng = np.random.RandomState(42)
    X = rng.randn(50, 1)
    y = (X[:, 0] > 0).astype(int)

    result = fit_logistic_with_inference(X, y, feature_names=['var'])
    text = result.summary_text()

    assert isinstance(text, str)
    assert len(text) > 100
    assert 'Pseudo-R²' in text or 'Pseudo-R²' in text
    assert 'LLR' in text
    assert 'OR' in text
    assert 'IC95' in text


def test_odds_ratio_consistent_with_coefs():
    """OR = exp(coef) para todos os parâmetros."""
    rng = np.random.RandomState(42)
    X = rng.randn(80, 2)
    y = (X[:, 0] > 0).astype(int)

    result = fit_logistic_with_inference(
        X, y, feature_names=['a', 'b'])

    # Intercept + 2 coefs
    expected_ors = np.exp(np.concatenate(
        [[result.intercept], result.coef]))
    np.testing.assert_allclose(
        result.odds_ratio, expected_ors, rtol=1e-9)


def test_ci_bounds_make_sense():
    """IC inferior ≤ central ≤ superior para todos os coeficientes."""
    rng = np.random.RandomState(42)
    X = rng.randn(100, 2)
    y = (X[:, 0] - X[:, 1] > 0).astype(int)

    result = fit_logistic_with_inference(
        X, y, feature_names=['v1', 'v2'])

    central = np.concatenate([[result.intercept], result.coef])
    assert np.all(result.ci_lower <= central + 1e-9)
    assert np.all(central <= result.ci_upper + 1e-9)
    assert np.all(result.or_ci_lower <= result.odds_ratio + 1e-9)
    assert np.all(result.odds_ratio <= result.or_ci_upper + 1e-9)


def test_validation_features_must_match():
    """Erro se feature_names não corresponde a colunas de X."""
    X = np.zeros((10, 3))
    y = np.zeros(10, dtype=int)

    with pytest.raises(ValueError, match="feature_names"):
        fit_logistic_with_inference(X, y, feature_names=['only_one'])

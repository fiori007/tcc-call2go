"""Inferência estatística clássica sobre sklearn LogisticRegression.

Implementa, sobre o modelo já ajustado pelo sklearn, os reports
inferenciais que normalmente vêm prontos em statsmodels:

- Erro padrão dos coeficientes (via matriz de informação de Fisher)
- p-values bilaterais via Wald test
- IC 95% dos coeficientes (Wald) e dos odds ratios
- Pseudo-R² de McFadden
- Likelihood Ratio Test (LRT) do modelo todo

Justificativa metodológica: o sklearn é otimizado para predição (ML),
enquanto reports inferenciais clássicos (p-value, IC, pseudo-R^2) são o
padrão acadêmico em ciências sociais e econometria. Este módulo combina
os dois: ajuste via sklearn + inferência clássica calculada explicitamente
a partir do modelo ajustado.

Referências:
- McFadden, D. (1973). Conditional logit analysis of qualitative choice
  behavior.
- Wald, A. (1943). Tests of statistical hypotheses concerning several
  parameters when the number of observations is large.
- Hosmer, D. W., Lemeshow, S., & Sturdivant, R. X. (2013). Applied
  Logistic Regression (3rd ed.), Wiley.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression


@dataclass
class LogitInference:
    """Resultado completo de regressão logística com reports inferenciais."""

    feature_names: list[str]
    coef: np.ndarray            # shape (n_features,) — sem intercept
    intercept: float
    se: np.ndarray              # erro padrão (com intercept ao final)
    z: np.ndarray               # estatística z (Wald)
    p_values: np.ndarray        # p-values bilaterais
    ci_lower: np.ndarray        # IC 95% inferior dos coeficientes
    ci_upper: np.ndarray        # IC 95% superior dos coeficientes
    odds_ratio: np.ndarray
    or_ci_lower: np.ndarray
    or_ci_upper: np.ndarray
    log_likelihood_full: float
    log_likelihood_null: float
    pseudo_r2_mcfadden: float
    llr_statistic: float
    llr_df: int
    llr_p_value: float
    n_obs: int
    converged: bool = True
    notes: list[str] = field(default_factory=list)

    def summary_text(self) -> str:
        """Resumo textual do ajuste, semelhante ao print de outras bibliotecas."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"Logistic Regression Inference Report (sklearn-based)")
        lines.append("=" * 70)
        lines.append(f"  N observations              : {self.n_obs}")
        lines.append(f"  Convergiu                   : {self.converged}")
        lines.append(f"  Log-likelihood (modelo)     : {self.log_likelihood_full:.4f}")
        lines.append(f"  Log-likelihood (null)       : {self.log_likelihood_null:.4f}")
        lines.append(f"  Pseudo-R² (McFadden)        : {self.pseudo_r2_mcfadden:.4f}")
        lines.append(f"  LLR statistic               : {self.llr_statistic:.4f}")
        lines.append(f"  LLR df                      : {self.llr_df}")
        lines.append(f"  LLR p-value                 : {self.llr_p_value:.4f}")
        lines.append("")
        lines.append("  Coeficientes (Wald):")
        lines.append("  " + "-" * 66)
        header = f"  {'variável':<22}{'coef':>10}{'se':>10}{'z':>8}{'p':>10}"
        lines.append(header)
        lines.append("  " + "-" * 66)

        # Itera com intercept primeiro
        names = ['(intercept)'] + list(self.feature_names)
        coefs = np.concatenate([[self.intercept], self.coef])
        for i, (n, b) in enumerate(zip(names, coefs)):
            lines.append(f"  {n:<22}{b:>10.4f}{self.se[i]:>10.4f}"
                         f"{self.z[i]:>8.3f}{self.p_values[i]:>10.4f}")
        lines.append("")
        lines.append("  Odds Ratios (IC 95%):")
        for i, n in enumerate(names):
            lines.append(f"  {n:<22}OR={self.odds_ratio[i]:.4f} "
                         f"IC95=[{self.or_ci_lower[i]:.4f}, "
                         f"{self.or_ci_upper[i]:.4f}]")

        if self.notes:
            lines.append("")
            lines.append("  Notas:")
            for note in self.notes:
                lines.append(f"    - {note}")

        lines.append("=" * 70)
        return "\n".join(lines)


def _log_likelihood(p: np.ndarray, y: np.ndarray) -> float:
    """Log-verossimilhança binomial. p e y devem ser 1D arrays."""
    eps = 1e-15  # estabilidade numérica
    p = np.clip(p, eps, 1 - eps)
    return float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def fit_logistic_with_inference(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: Sequence[str],
    *,
    add_intercept_in_fit: bool = True,
    max_iter: int = 200,
    random_state: int = 42,
) -> LogitInference:
    """Ajusta regressão logística (sklearn) e calcula inferência clássica.

    Args:
        X: matriz de features (n_obs, n_features), sem intercept.
        y: rótulos binários (n_obs,) com valores 0/1.
        feature_names: nomes das features (sem intercept).
        add_intercept_in_fit: usa fit_intercept=True (padrão).
        max_iter: máximo de iterações da otimização.
        random_state: semente para reprodutibilidade.

    Returns:
        LogitInference com coeficientes, p-values, IC 95%, pseudo-R² e LRT.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)
    n, k = X.shape

    if len(feature_names) != k:
        raise ValueError(
            f"feature_names tem {len(feature_names)} elementos; X tem {k} colunas")

    # ---- Modelo principal (sklearn) ----
    # Sem regularização (penalty=None) para que coeficientes sejam ML estimates,
    # comparáveis com a matriz de informação de Fisher usada na inferência.
    model = LogisticRegression(
        penalty=None,
        solver='lbfgs',
        max_iter=max_iter,
        fit_intercept=add_intercept_in_fit,
        random_state=random_state,
    )
    notes = []
    try:
        model.fit(X, y)
        converged = True
    except Exception as e:
        notes.append(f"Falha no ajuste: {e}; usando solver alternativo")
        model = LogisticRegression(
            penalty=None, solver='newton-cg', max_iter=max_iter,
            fit_intercept=add_intercept_in_fit, random_state=random_state)
        model.fit(X, y)
        converged = False

    coef = model.coef_.flatten()  # (k,)
    intercept = float(model.intercept_[0]) if add_intercept_in_fit else 0.0

    # Probabilidades preditas pelo modelo
    p_pred = model.predict_proba(X)[:, 1]
    ll_full = _log_likelihood(p_pred, y)

    # ---- Modelo null (intercept-only) para LRT e pseudo-R² ----
    p_null = np.full_like(p_pred, fill_value=float(y.mean()))
    ll_null = _log_likelihood(p_null, y)

    # ---- Pseudo-R² de McFadden ----
    if abs(ll_null) < 1e-12:
        pseudo_r2 = 0.0
    else:
        pseudo_r2 = 1.0 - (ll_full / ll_null)

    # ---- Likelihood Ratio Test ----
    llr = -2.0 * (ll_null - ll_full)
    llr_df = k  # nº de features no modelo (sem intercept)
    llr_p = 1.0 - stats.chi2.cdf(llr, df=llr_df) if llr > 0 else 1.0

    # ---- Matriz de covariância dos coeficientes ----
    # Var(beta_hat) = (X' W X)^{-1}, W = diag(p_i (1-p_i))
    # Inclui coluna de 1s para o intercept.
    if add_intercept_in_fit:
        X_full = np.concatenate([np.ones((n, 1)), X], axis=1)
        beta_full = np.concatenate([[intercept], coef])
    else:
        X_full = X
        beta_full = coef

    W = p_pred * (1.0 - p_pred)  # vetor (n,)
    fisher_info = X_full.T @ (X_full * W[:, None])  # (k+1, k+1)

    try:
        cov_beta = np.linalg.inv(fisher_info)
    except np.linalg.LinAlgError:
        notes.append("Matriz de Fisher singular; usando pseudoinversa")
        cov_beta = np.linalg.pinv(fisher_info)

    se = np.sqrt(np.maximum(np.diag(cov_beta), 0.0))

    # ---- Wald test ----
    with np.errstate(divide='ignore', invalid='ignore'):
        z = np.where(se > 0, beta_full / se, 0.0)
    p_values = 2.0 * (1.0 - stats.norm.cdf(np.abs(z)))

    # ---- IC 95% Wald ----
    z_crit = stats.norm.ppf(0.975)
    ci_lower = beta_full - z_crit * se
    ci_upper = beta_full + z_crit * se

    odds_ratio = np.exp(beta_full)
    or_ci_lower = np.exp(ci_lower)
    or_ci_upper = np.exp(ci_upper)

    return LogitInference(
        feature_names=list(feature_names),
        coef=coef,
        intercept=intercept,
        se=se,
        z=z,
        p_values=p_values,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        odds_ratio=odds_ratio,
        or_ci_lower=or_ci_lower,
        or_ci_upper=or_ci_upper,
        log_likelihood_full=ll_full,
        log_likelihood_null=ll_null,
        pseudo_r2_mcfadden=pseudo_r2,
        llr_statistic=llr,
        llr_df=llr_df,
        llr_p_value=llr_p,
        n_obs=n,
        converged=converged,
        notes=notes,
    )

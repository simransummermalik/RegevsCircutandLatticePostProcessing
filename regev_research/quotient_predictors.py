"""Frozen predictor comparison for the quotient-recovery study.

This module is analysis-only.  It joins the outcome of the standard Regev
row to predictors recorded on the quotient-gap scoring-only row with the
precommitted key ``(N, model, replicate, sample_count)``.  In particular, it
does not rerun recovery, change any recovery budget, or search for a decision
threshold.

The inferential unit is ``N``:

* Spearman correlation is computed after averaging usable trial rows within
  each ``N`` and its confidence interval resamples whole ``N`` clusters.
* Predictive scores use leave-one-``N``-out logistic regression.  Scaling and
  fitting for a fold use only rows belonging to the training ``N`` values.

The quotient decision rule is fixed at its natural, precommitted threshold:
``log2(L0/useful) > 0``.  Censored minima are reported but are never treated as
observed values in correlations, predictive fits, or threshold evaluation.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import rankdata


STANDARD_REGEV_METHOD = "standard_regev_LLL_basis_endpoint"
QUOTIENT_GAP_METHOD = "quotient_gap_scoring_only"
JOIN_KEYS = ("N", "model", "replicate", "sample_count")

EXACT_A_MODEL = "A_exact_uniform_hard_box"
EXACT_B_MODEL = "B_exact_finite_discrete_gaussian"
EXACT_FOURIER_MODELS = (EXACT_A_MODEL, EXACT_B_MODEL)

ANALYSIS_VERSION = "quotient-predictor-comparison-v1"
DEFAULT_BOOTSTRAP_RESAMPLES = 5_000
DEFAULT_BOOTSTRAP_SEED = 2_026_071_104
FIXED_LOGISTIC_NUMERICAL_RIDGE = 1e-8
NATURAL_QUOTIENT_LOG2_THRESHOLD = 0.0


@dataclass(frozen=True, slots=True)
class PredictorSpec:
    """A frozen scalar predictor and any censor flags attached to it."""

    name: str
    source_column: str
    censor_columns: tuple[str, ...] = ()
    exact_models_only: bool = False


FROZEN_PREDICTORS = (
    PredictorSpec(
        "quotient_gap_log2_ratio",
        "quotient_gap_log2_L0_to_useful_ratio",
        ("quotient_gap_L0_censored", "quotient_gap_useful_censored"),
    ),
    PredictorSpec(
        "bounded_base_diversity",
        "predictor_bounded_product_diversity",
    ),
    PredictorSpec(
        "empirical_fourier_entropy",
        "predictor_empirical_fourier_joint_entropy_bits",
    ),
    PredictorSpec(
        "covariance_effective_rank",
        "predictor_empirical_fourier_covariance_effective_rank",
    ),
    PredictorSpec(
        "relation_lattice_determinant",
        "predictor_relation_lattice_determinant",
    ),
    PredictorSpec("sample_count", "sample_count"),
    PredictorSpec(
        "ordinary_shortest_relation_squared_norm",
        "predictor_ordinary_shortest_relation_squared_norm",
        ("predictor_ordinary_shortest_relation_censored",),
    ),
    PredictorSpec(
        "exact_fourier_entropy",
        "predictor_exact_fourier_joint_entropy_bits",
        exact_models_only=True,
    ),
)


@dataclass(frozen=True, slots=True)
class JoinedTrialRows:
    """Matched standard outcomes, scoring-only predictors, and join audit."""

    rows: tuple[dict, ...]
    diagnostics: dict


def read_trial_rows(path: str | Path) -> list[dict]:
    """Read a study ``trial_rows.csv`` without lossy eager type inference."""

    source = Path(path)
    with source.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "none", "null", "nan", "na"}
    try:
        return bool(np.isnan(value))
    except (TypeError, ValueError):
        return False


def _integer(value: object, label: str) -> int:
    if _missing(value):
        raise ValueError(f"{label} is missing")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be an integer, got {value!r}") from error
    if not isfinite(number) or not number.is_integer():
        raise ValueError(f"{label} must be an integer, got {value!r}")
    return int(number)


def _optional_float(value: object) -> float | None:
    if _missing(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _optional_bool(value: object, label: str) -> bool | None:
    if _missing(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        if float(value) in (0.0, 1.0):
            return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "t", "yes", "y", "1"}:
            return True
        if normalized in {"false", "f", "no", "n", "0"}:
            return False
    raise ValueError(f"{label} must be a Boolean, got {value!r}")


def _optional_binary(value: object, label: str) -> int | None:
    parsed = _optional_bool(value, label)
    return None if parsed is None else int(parsed)


def _trial_key(row: Mapping[str, object]) -> tuple[int, str, int, int]:
    model = row.get("model")
    if _missing(model):
        raise ValueError("model is missing from a trial row")
    return (
        _integer(row.get("N"), "N"),
        str(model),
        _integer(row.get("replicate"), "replicate"),
        _integer(row.get("sample_count"), "sample_count"),
    )


def _serializable_key(key: tuple[int, str, int, int]) -> dict:
    return dict(zip(JOIN_KEYS, key))


def join_standard_and_gap_rows(
    trial_rows: Sequence[Mapping[str, object]],
    *,
    standard_method: str = STANDARD_REGEV_METHOD,
    gap_method: str = QUOTIENT_GAP_METHOD,
) -> JoinedTrialRows:
    """Join the frozen outcome and scoring rows without borrowing outcomes.

    Duplicate keys within either method are rejected because silently choosing
    one would make the analysis dependent on CSV order.  Nonmatching rows are
    retained in diagnostics and excluded from all comparisons.
    """

    standard: dict[tuple[int, str, int, int], Mapping[str, object]] = {}
    gaps: dict[tuple[int, str, int, int], Mapping[str, object]] = {}
    input_count = 0
    ignored_count = 0
    for raw in trial_rows:
        input_count += 1
        method = str(raw.get("method", ""))
        if method not in {standard_method, gap_method}:
            ignored_count += 1
            continue
        key = _trial_key(raw)
        target = standard if method == standard_method else gaps
        if key in target:
            raise ValueError(f"duplicate {method!r} trial key: {_serializable_key(key)}")
        target[key] = raw

    common_keys = sorted(set(standard) & set(gaps))
    only_standard = sorted(set(standard) - set(gaps))
    only_gap = sorted(set(gaps) - set(standard))
    joined: list[dict] = []
    for key in common_keys:
        standard_row = standard[key]
        gap_row = gaps[key]
        row = dict(gap_row)
        row.update(_serializable_key(key))
        row["outcome_standard_regev_factor_success"] = _optional_binary(
            standard_row.get("factor_success"), "standard factor_success"
        )
        row["outcome_standard_regev_status"] = standard_row.get("status")
        row["outcome_source_method"] = standard_method
        row["predictor_source_method"] = gap_method
        joined.append(row)

    diagnostics = {
        "join_keys": list(JOIN_KEYS),
        "input_row_count": input_count,
        "ignored_other_method_row_count": ignored_count,
        "standard_method": standard_method,
        "quotient_gap_method": gap_method,
        "standard_row_count": len(standard),
        "quotient_gap_row_count": len(gaps),
        "matched_row_count": len(joined),
        "unmatched_standard_row_count": len(only_standard),
        "unmatched_quotient_gap_row_count": len(only_gap),
        "unmatched_standard_keys": [_serializable_key(key) for key in only_standard],
        "unmatched_quotient_gap_keys": [_serializable_key(key) for key in only_gap],
    }
    return JoinedTrialRows(tuple(joined), diagnostics)


def _spec_applies(row: Mapping[str, object], spec: PredictorSpec) -> bool:
    return not spec.exact_models_only or str(row["model"]) in EXACT_FOURIER_MODELS


def _predictor_value(row: Mapping[str, object], spec: PredictorSpec) -> float | None:
    return _optional_float(row.get(spec.source_column))


def _predictor_censored(row: Mapping[str, object], spec: PredictorSpec) -> bool:
    return any(
        _optional_bool(row.get(column), column) is True for column in spec.censor_columns
    )


def _usable_rows(
    rows: Sequence[Mapping[str, object]], spec: PredictorSpec
) -> list[tuple[Mapping[str, object], float, int]]:
    output = []
    for row in rows:
        if not _spec_applies(row, spec) or _predictor_censored(row, spec):
            continue
        value = _predictor_value(row, spec)
        outcome = _optional_binary(
            row.get("outcome_standard_regev_factor_success"),
            "outcome_standard_regev_factor_success",
        )
        if value is not None and outcome is not None:
            output.append((row, value, outcome))
    return output


def _coverage(
    rows: Sequence[Mapping[str, object]], spec: PredictorSpec
) -> dict:
    eligible = [row for row in rows if _spec_applies(row, spec)]
    observed = sum(_predictor_value(row, spec) is not None for row in eligible)
    missing = len(eligible) - observed
    censored = sum(_predictor_censored(row, spec) for row in eligible)
    outcome_missing = sum(
        _optional_binary(
            row.get("outcome_standard_regev_factor_success"),
            "outcome_standard_regev_factor_success",
        )
        is None
        for row in eligible
    )
    usable = _usable_rows(rows, spec)
    scope_ns = {int(row["N"]) for row in rows}
    eligible_ns = {int(row["N"]) for row in eligible}
    usable_ns = {int(row["N"]) for row, _, _ in usable}
    return {
        "scope_joined_rows": len(rows),
        "eligible_rows": len(eligible),
        "structurally_ineligible_rows": len(rows) - len(eligible),
        "predictor_observed_rows": observed,
        "predictor_missing_rows": missing,
        "predictor_censored_rows": censored,
        "outcome_missing_rows": outcome_missing,
        "usable_uncensored_complete_rows": len(usable),
        "coverage_fraction_of_eligible": (
            len(usable) / len(eligible) if eligible else None
        ),
        "coverage_fraction_of_scope": len(usable) / len(rows) if rows else None,
        "N_clusters_in_scope": len(scope_ns),
        "N_clusters_eligible": len(eligible_ns),
        "N_clusters_usable": len(usable_ns),
    }


def _cluster_means(
    rows: Sequence[Mapping[str, object]], spec: PredictorSpec
) -> list[dict]:
    grouped: dict[int, list[tuple[float, int]]] = {}
    for row, value, outcome in _usable_rows(rows, spec):
        grouped.setdefault(int(row["N"]), []).append((value, outcome))
    output = []
    for N, values in sorted(grouped.items()):
        output.append(
            {
                "N": N,
                "predictor_mean": float(np.mean([value for value, _ in values])),
                "success_rate": float(np.mean([outcome for _, outcome in values])),
                "usable_trial_rows": len(values),
            }
        )
    return output


def _spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    if len(x) < 2:
        return None
    x_rank = np.asarray(rankdata(x, method="average"), dtype=float)
    y_rank = np.asarray(rankdata(y, method="average"), dtype=float)
    x_rank -= x_rank.mean()
    y_rank -= y_rank.mean()
    denominator = float(np.linalg.norm(x_rank) * np.linalg.norm(y_rank))
    if denominator == 0.0:
        return None
    return float(np.dot(x_rank, y_rank) / denominator)


def n_cluster_spearman(
    rows: Sequence[Mapping[str, object]],
    spec: PredictorSpec,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict:
    """Spearman rho on ``N`` means with a whole-``N`` bootstrap interval."""

    resamples = int(bootstrap_resamples)
    if resamples <= 0:
        raise ValueError("bootstrap_resamples must be positive")
    clusters = _cluster_means(rows, spec)
    x = np.asarray([row["predictor_mean"] for row in clusters], dtype=float)
    y = np.asarray([row["success_rate"] for row in clusters], dtype=float)
    rho = _spearman(x, y)
    rng = np.random.default_rng(int(seed))
    draws: list[float] = []
    if len(clusters) >= 2:
        for _ in range(resamples):
            indices = rng.integers(0, len(clusters), size=len(clusters))
            value = _spearman(x[indices], y[indices])
            if value is not None:
                draws.append(value)
    return {
        "estimand": (
            "Spearman rho across N-level arithmetic means of usable trial rows"
        ),
        "rho": rho,
        "N_clusters": len(clusters),
        "bootstrap_ci_low": (
            float(np.quantile(draws, 0.025)) if draws else None
        ),
        "bootstrap_ci_high": (
            float(np.quantile(draws, 0.975)) if draws else None
        ),
        "bootstrap_resamples_requested": resamples,
        "bootstrap_resamples_valid": len(draws),
        "bootstrap_seed": int(seed),
        "N_level_points": clusters,
    }


def _logistic_fit(
    x: np.ndarray,
    y: np.ndarray,
    *,
    ridge: float = FIXED_LOGISTIC_NUMERICAL_RIDGE,
):
    design = np.column_stack((np.ones(len(x), dtype=float), x))

    def objective(beta: np.ndarray):
        eta = design @ beta
        loss = float(np.sum(np.logaddexp(0.0, eta) - y * eta))
        loss += 0.5 * ridge * float(np.dot(beta, beta))
        gradient = design.T @ (expit(eta) - y) + ridge * beta
        return loss, gradient

    return minimize(
        objective,
        np.zeros(2, dtype=float),
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": 1_000, "ftol": 1e-12, "gtol": 1e-9},
    )


def _auc(y: np.ndarray, probabilities: np.ndarray) -> float | None:
    positives = int(np.count_nonzero(y == 1))
    negatives = int(np.count_nonzero(y == 0))
    if positives == 0 or negatives == 0:
        return None
    ranks = rankdata(probabilities, method="average")
    positive_rank_sum = float(np.sum(ranks[y == 1]))
    return float(
        (positive_rank_sum - positives * (positives + 1) / 2)
        / (positives * negatives)
    )


def leave_one_n_out_logistic(
    rows: Sequence[Mapping[str, object]], spec: PredictorSpec
) -> dict:
    """Evaluate one-predictor logistic regression on held-out ``N`` clusters."""

    usable = _usable_rows(rows, spec)
    clusters = sorted({int(row["N"]) for row, _, _ in usable})
    predicted_y: list[int] = []
    predicted_probability: list[float] = []
    folds = []
    for heldout_N in clusters:
        training = [item for item in usable if int(item[0]["N"]) != heldout_N]
        testing = [item for item in usable if int(item[0]["N"]) == heldout_N]
        training_ns = sorted({int(row["N"]) for row, _, _ in training})
        fold = {
            "heldout_N": heldout_N,
            "training_N": training_ns,
            "train_rows": len(training),
            "test_rows": len(testing),
            "fit_uses_heldout_N": heldout_N in training_ns,
        }
        if not training or not testing:
            fold.update({"status": "not_evaluable", "optimizer_success": False})
            folds.append(fold)
            continue
        train_x = np.asarray([value for _, value, _ in training], dtype=float)
        train_y = np.asarray([outcome for _, _, outcome in training], dtype=float)
        test_x = np.asarray([value for _, value, _ in testing], dtype=float)
        test_y = np.asarray([outcome for _, _, outcome in testing], dtype=int)
        mean = float(train_x.mean())
        scale = float(train_x.std(ddof=0))
        constant_predictor = scale == 0.0
        if constant_predictor:
            scale = 1.0
        fit = _logistic_fit((train_x - mean) / scale, train_y)
        beta = np.asarray(fit.x, dtype=float)
        probabilities = expit(
            beta[0] + beta[1] * ((test_x - mean) / scale)
        )
        finite_fit = bool(
            np.all(np.isfinite(beta)) and np.all(np.isfinite(probabilities))
        )
        fold.update(
            {
                "status": "evaluated" if finite_fit else "nonfinite_fit",
                "optimizer_success": bool(fit.success),
                "optimizer_message": str(fit.message),
                "training_predictor_mean": mean,
                "training_predictor_scale": scale,
                "training_predictor_constant": constant_predictor,
                "standardized_intercept": float(beta[0]) if finite_fit else None,
                "standardized_slope": float(beta[1]) if finite_fit else None,
            }
        )
        folds.append(fold)
        if finite_fit:
            predicted_y.extend(int(value) for value in test_y)
            predicted_probability.extend(float(value) for value in probabilities)

    y = np.asarray(predicted_y, dtype=int)
    probabilities = np.asarray(predicted_probability, dtype=float)
    if len(y):
        clipped = np.clip(probabilities, 1e-15, 1.0 - 1e-15)
        brier = float(np.mean((probabilities - y) ** 2))
        log_loss = float(
            -np.mean(y * np.log(clipped) + (1 - y) * np.log1p(-clipped))
        )
        auc = _auc(y, probabilities)
    else:
        brier = log_loss = auc = None
    return {
        "estimand": "leave-one-N-out one-predictor logistic trial probabilities",
        "fit_scope": "each fold fits and scales on training N values only",
        "fixed_numerical_ridge": FIXED_LOGISTIC_NUMERICAL_RIDGE,
        "ridge_was_tuned": False,
        "N_folds": len(clusters),
        "N_folds_evaluated": sum(fold["status"] == "evaluated" for fold in folds),
        "prediction_rows": len(y),
        "positive_outcomes": int(np.count_nonzero(y == 1)),
        "negative_outcomes": int(np.count_nonzero(y == 0)),
        "brier_score": brier,
        "log_loss": log_loss,
        "auc": auc,
        "folds": folds,
    }


def natural_quotient_threshold_metrics(
    rows: Sequence[Mapping[str, object]],
) -> dict:
    """Evaluate the fixed strict rule ``quotient gap > 0`` where uncensored."""

    spec = FROZEN_PREDICTORS[0]
    usable = _usable_rows(rows, spec)
    truth = np.asarray([outcome for _, _, outcome in usable], dtype=int)
    predicted = np.asarray(
        [int(value > NATURAL_QUOTIENT_LOG2_THRESHOLD) for _, value, _ in usable],
        dtype=int,
    )
    true_positive = int(np.count_nonzero((truth == 1) & (predicted == 1)))
    false_negative = int(np.count_nonzero((truth == 1) & (predicted == 0)))
    true_negative = int(np.count_nonzero((truth == 0) & (predicted == 0)))
    false_positive = int(np.count_nonzero((truth == 0) & (predicted == 1)))
    sensitivity = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else None
    )
    specificity = (
        true_negative / (true_negative + false_positive)
        if true_negative + false_positive
        else None
    )
    balanced = (
        (sensitivity + specificity) / 2
        if sensitivity is not None and specificity is not None
        else None
    )
    return {
        "predictor": spec.name,
        "threshold": NATURAL_QUOTIENT_LOG2_THRESHOLD,
        "operator": ">",
        "threshold_was_tuned": False,
        "evaluation_population": "uncensored complete matched trial rows",
        "evaluated_rows": len(usable),
        "N_clusters": len({int(row["N"]) for row, _, _ in usable}),
        "true_positive": true_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "balanced_accuracy": balanced,
    }


def _scope_predictors(
    rows: Sequence[Mapping[str, object]],
    *,
    scope: str,
    model: str | None,
    bootstrap_resamples: int,
    seed: int,
) -> dict:
    results = []
    predictor_index = 0
    for spec in FROZEN_PREDICTORS:
        if spec.exact_models_only and model is not None and model not in EXACT_FOURIER_MODELS:
            continue
        result = {
            "predictor": spec.name,
            "source_column": spec.source_column,
            "censor_columns": list(spec.censor_columns),
            "exact_models_only": spec.exact_models_only,
            "coverage": _coverage(rows, spec),
            "N_level_spearman": n_cluster_spearman(
                rows,
                spec,
                bootstrap_resamples=bootstrap_resamples,
                seed=seed + predictor_index,
            ),
            "leave_one_N_out_logistic": leave_one_n_out_logistic(rows, spec),
        }
        results.append(result)
        predictor_index += 1
    return {
        "scope": scope,
        "model": model,
        "joined_rows": len(rows),
        "N_clusters": len({int(row["N"]) for row in rows}),
        "predictors": results,
        "natural_quotient_threshold": natural_quotient_threshold_metrics(rows),
    }


def analyze_predictor_comparison(
    trial_rows_or_path: Sequence[Mapping[str, object]] | str | Path,
    *,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> dict:
    """Run the frozen analysis on rows or an existing ``trial_rows.csv``."""

    if isinstance(trial_rows_or_path, (str, Path)):
        trial_rows = read_trial_rows(trial_rows_or_path)
        input_source = str(Path(trial_rows_or_path))
    else:
        trial_rows = [dict(row) for row in trial_rows_or_path]
        input_source = "in-memory rows"
    bootstrap_resamples = int(bootstrap_resamples)
    if bootstrap_resamples <= 0:
        raise ValueError("bootstrap_resamples must be positive")
    joined = join_standard_and_gap_rows(trial_rows)
    models = sorted({str(row["model"]) for row in joined.rows})
    scopes = [
        _scope_predictors(
            joined.rows,
            scope="pooled",
            model=None,
            bootstrap_resamples=bootstrap_resamples,
            seed=int(seed),
        )
    ]
    for model_index, model in enumerate(models, start=1):
        model_rows = tuple(row for row in joined.rows if str(row["model"]) == model)
        scopes.append(
            _scope_predictors(
                model_rows,
                scope="model",
                model=model,
                bootstrap_resamples=bootstrap_resamples,
                seed=int(seed) + 10_000 * model_index,
            )
        )
    return {
        "analysis_version": ANALYSIS_VERSION,
        "input_source": input_source,
        "frozen_contract": {
            "outcome": "factor_success from standard Regev LLL basis endpoint",
            "predictor_source": "quotient-gap scoring-only row",
            "join_keys": list(JOIN_KEYS),
            "N_is_cluster": True,
            "spearman_aggregation": "arithmetic means within N",
            "logistic_validation": "leave one whole N out",
            "bootstrap_resamples": bootstrap_resamples,
            "bootstrap_seed": int(seed),
            "natural_quotient_threshold": NATURAL_QUOTIENT_LOG2_THRESHOLD,
            "natural_quotient_operator": ">",
            "threshold_tuned": False,
            "recovery_tuned_or_rerun": False,
            "censored_predictors_excluded_from_estimands": True,
        },
        "join_diagnostics": joined.diagnostics,
        "scopes": scopes,
    }


# Descriptive alias for callers that think in terms of the study rather than
# the particular output table.
analyze_quotient_study_predictors = analyze_predictor_comparison


def tidy_predictor_rows(analysis: Mapping[str, object]) -> list[dict]:
    """Flatten predictor endpoints to one tidy row per scope and predictor."""

    output = []
    for scope in analysis["scopes"]:
        threshold = scope["natural_quotient_threshold"]
        for predictor in scope["predictors"]:
            coverage = predictor["coverage"]
            spearman = predictor["N_level_spearman"]
            logistic = predictor["leave_one_N_out_logistic"]
            row = {
                "analysis_version": analysis["analysis_version"],
                "scope": scope["scope"],
                "model": scope["model"],
                "predictor": predictor["predictor"],
                "source_column": predictor["source_column"],
                "exact_models_only": predictor["exact_models_only"],
                **coverage,
                "spearman_rho": spearman["rho"],
                "spearman_N_clusters": spearman["N_clusters"],
                "spearman_bootstrap_ci_low": spearman["bootstrap_ci_low"],
                "spearman_bootstrap_ci_high": spearman["bootstrap_ci_high"],
                "spearman_bootstrap_resamples_requested": spearman[
                    "bootstrap_resamples_requested"
                ],
                "spearman_bootstrap_resamples_valid": spearman[
                    "bootstrap_resamples_valid"
                ],
                "lono_N_folds": logistic["N_folds"],
                "lono_N_folds_evaluated": logistic["N_folds_evaluated"],
                "lono_prediction_rows": logistic["prediction_rows"],
                "lono_brier_score": logistic["brier_score"],
                "lono_log_loss": logistic["log_loss"],
                "lono_auc": logistic["auc"],
                "natural_threshold": None,
                "natural_threshold_operator": None,
                "threshold_evaluated_rows": None,
                "threshold_sensitivity": None,
                "threshold_specificity": None,
                "threshold_balanced_accuracy": None,
            }
            if predictor["predictor"] == "quotient_gap_log2_ratio":
                row.update(
                    {
                        "natural_threshold": threshold["threshold"],
                        "natural_threshold_operator": threshold["operator"],
                        "threshold_evaluated_rows": threshold["evaluated_rows"],
                        "threshold_sensitivity": threshold["sensitivity"],
                        "threshold_specificity": threshold["specificity"],
                        "threshold_balanced_accuracy": threshold[
                            "balanced_accuracy"
                        ],
                    }
                )
            output.append(row)
    return output


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _write_tidy_csv_atomic(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError("refusing to write an empty predictor comparison CSV")
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = sorted({column for row in rows for column in row})
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def write_predictor_comparison(
    output_directory: str | Path,
    analysis: Mapping[str, object],
) -> tuple[Path, Path]:
    """Write ``predictor_comparison.json`` and its tidy companion CSV."""

    output = Path(output_directory)
    json_path = output / "predictor_comparison.json"
    csv_path = output / "predictor_comparison.csv"
    _write_json_atomic(json_path, analysis)
    _write_tidy_csv_atomic(csv_path, tidy_predictor_rows(analysis))
    return json_path, csv_path


__all__ = [
    "ANALYSIS_VERSION",
    "DEFAULT_BOOTSTRAP_RESAMPLES",
    "DEFAULT_BOOTSTRAP_SEED",
    "EXACT_FOURIER_MODELS",
    "FROZEN_PREDICTORS",
    "JOIN_KEYS",
    "JoinedTrialRows",
    "NATURAL_QUOTIENT_LOG2_THRESHOLD",
    "PredictorSpec",
    "QUOTIENT_GAP_METHOD",
    "STANDARD_REGEV_METHOD",
    "analyze_predictor_comparison",
    "analyze_quotient_study_predictors",
    "join_standard_and_gap_rows",
    "leave_one_n_out_logistic",
    "n_cluster_spearman",
    "natural_quotient_threshold_metrics",
    "read_trial_rows",
    "tidy_predictor_rows",
    "write_predictor_comparison",
]

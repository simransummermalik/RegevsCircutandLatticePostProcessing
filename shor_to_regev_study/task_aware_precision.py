"""Shared schemas, paired inference, and empirical precision predictors."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from math import comb
from typing import Mapping, Sequence

import numpy as np


@dataclass(frozen=True, slots=True)
class TaskAwarePrecisionRecord:
    algorithm: str
    instance_id: str
    endpoint: str
    approximation_level: int
    worst_case_certified: bool
    state_specific_certified: bool | None
    measured_tv: float | None
    task_success_probability: float
    exact_task_success_probability: float
    task_difference: float
    resource_saving: dict[str, int]

    def __post_init__(self) -> None:
        if self.algorithm not in {"Shor", "Regev"}:
            raise ValueError("algorithm must be Shor or Regev")
        if self.endpoint not in {"order", "factor", "L_minus_L0"}:
            raise ValueError("unknown task endpoint")
        if self.approximation_level < 0:
            raise ValueError("approximation level must be nonnegative")
        for value in (self.task_success_probability, self.exact_task_success_probability):
            if not 0 <= value <= 1:
                raise ValueError("task probabilities must lie in [0,1]")

    def as_record(self) -> dict:
        record = asdict(self)
        resources = record.pop("resource_saving")
        record.update({f"resource_{key}": value for key, value in resources.items()})
        return record


def paired_cluster_bootstrap(
    differences: Mapping[str, Sequence[float]],
    *,
    replicates: int,
    seed: int,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Bootstrap every endpoint with identical cluster indices per draw."""

    arrays = {name: np.asarray(values, dtype=float) for name, values in differences.items()}
    if not arrays or int(replicates) <= 0:
        raise ValueError("differences and positive replicates are required")
    lengths = {len(values) for values in arrays.values()}
    if len(lengths) != 1 or next(iter(lengths)) == 0:
        raise ValueError("endpoint arrays must have one shared nonzero length")
    cluster_count = next(iter(lengths))
    rng = np.random.default_rng(int(seed))
    indices = rng.integers(0, cluster_count, size=(int(replicates), cluster_count))
    draws = {
        name: values[indices].mean(axis=1)
        for name, values in arrays.items()
    }
    return indices, draws


def exact_sign_test(values: Sequence[float]) -> dict[str, float | int]:
    nonzero = np.asarray(values, dtype=float)
    nonzero = nonzero[np.abs(nonzero) > 1e-15]
    n = len(nonzero)
    if n == 0:
        return {"nonzero_pairs": 0, "positive_pairs": 0, "two_sided_p": 1.0}
    positive = int(np.sum(nonzero > 0))
    tail = sum(comb(n, k) for k in range(min(positive, n - positive) + 1)) / (2**n)
    return {
        "nonzero_pairs": n,
        "positive_pairs": positive,
        "two_sided_p": min(1.0, 2.0 * tail),
    }


def exact_sign_flip_p(
    values: Sequence[float], *, shift: float = 0.0, alternative: str = "two-sided"
) -> float:
    shifted = np.asarray(values, dtype=float) + float(shift)
    if shifted.ndim != 1 or len(shifted) == 0:
        raise ValueError("values must be a nonempty vector")
    observed = float(np.mean(shifted))
    draws = np.asarray([
        np.mean(shifted * np.asarray(signs))
        for signs in product((-1.0, 1.0), repeat=len(shifted))
    ])
    if alternative == "two-sided":
        return float(np.mean(np.abs(draws) >= abs(observed) - 1e-15))
    if alternative == "greater":
        return float(np.mean(draws >= observed - 1e-15))
    raise ValueError("unknown alternative")


@dataclass(frozen=True, slots=True)
class LogisticPredictor:
    feature_names: tuple[str, ...]
    mean: tuple[float, ...]
    scale: tuple[float, ...]
    coefficients: tuple[float, ...]
    intercept: float

    def predict_proba(self, rows: Sequence[Mapping[str, float]]) -> np.ndarray:
        matrix = np.asarray(
            [[float(row[name]) for name in self.feature_names] for row in rows],
            dtype=float,
        )
        normalized = (matrix - np.asarray(self.mean)) / np.asarray(self.scale)
        scores = np.clip(normalized @ np.asarray(self.coefficients) + self.intercept, -30, 30)
        return 1.0 / (1.0 + np.exp(-scores))


def fit_logistic_predictor(
    rows: Sequence[Mapping[str, float]],
    labels: Sequence[bool | int],
    feature_names: Sequence[str],
    *,
    iterations: int = 4000,
    learning_rate: float = 0.03,
    l2: float = 0.05,
) -> LogisticPredictor:
    """Fit a deterministic regularized logistic surrogate with gradient descent."""

    names = tuple(feature_names)
    matrix = np.asarray([[float(row[name]) for name in names] for row in rows], dtype=float)
    target = np.asarray(labels, dtype=float)
    if matrix.ndim != 2 or len(matrix) != len(target) or len(matrix) == 0:
        raise ValueError("nonempty aligned rows and labels are required")
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale[scale < 1e-12] = 1.0
    normalized = (matrix - mean) / scale
    coefficients = np.zeros(len(names), dtype=float)
    intercept = 0.0
    for _ in range(int(iterations)):
        scores = np.clip(normalized @ coefficients + intercept, -30, 30)
        predicted = 1.0 / (1.0 + np.exp(-scores))
        residual = predicted - target
        coefficients -= learning_rate * (
            normalized.T @ residual / len(target) + l2 * coefficients
        )
        intercept -= learning_rate * float(np.mean(residual))
    return LogisticPredictor(
        names,
        tuple(float(value) for value in mean),
        tuple(float(value) for value in scale),
        tuple(float(value) for value in coefficients),
        float(intercept),
    )


def binary_metrics(labels: Sequence[bool | int], probabilities: Sequence[float]) -> dict[str, float | int]:
    truth = np.asarray(labels, dtype=bool)
    scores = np.asarray(probabilities, dtype=float)
    predicted = scores >= 0.5
    true_positive = int(np.sum(predicted & truth))
    false_positive = int(np.sum(predicted & ~truth))
    true_negative = int(np.sum(~predicted & ~truth))
    false_negative = int(np.sum(~predicted & truth))
    return {
        "rows": len(truth),
        "accuracy": float(np.mean(predicted == truth)),
        "brier": float(np.mean((scores - truth.astype(float)) ** 2)),
        "false_approvals": false_positive,
        "false_rejections": false_negative,
        "precision": 0.0 if true_positive + false_positive == 0 else true_positive / (true_positive + false_positive),
        "recall": 0.0 if true_positive + false_negative == 0 else true_positive / (true_positive + false_negative),
        "true_negatives": true_negative,
    }


def calibration_rows(
    labels: Sequence[bool | int], probabilities: Sequence[float], bins: int = 5
) -> list[dict]:
    truth = np.asarray(labels, dtype=float)
    scores = np.asarray(probabilities, dtype=float)
    edges = np.linspace(0, 1, int(bins) + 1)
    rows: list[dict] = []
    for index in range(int(bins)):
        selected = (scores >= edges[index]) & (
            scores <= edges[index + 1] if index == bins - 1 else scores < edges[index + 1]
        )
        if np.any(selected):
            rows.append({
                "bin": index,
                "lower": float(edges[index]),
                "upper": float(edges[index + 1]),
                "count": int(np.sum(selected)),
                "mean_prediction": float(np.mean(scores[selected])),
                "observed_frequency": float(np.mean(truth[selected])),
            })
    return rows


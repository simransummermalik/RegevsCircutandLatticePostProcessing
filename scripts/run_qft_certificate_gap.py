"""Frozen exact-fiber holdout for the QFT certification gap.

This runner must be interpreted with ``QFT_CERTIFICATE_GAP_PROTOCOL.md``.
It compares factor-blind analytic certificates with the actual stored-root
augmented-lattice endpoint; it never treats certificate rejection as empirical
or information-theoretic failure.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from itertools import product
from math import comb, pi, sqrt
from pathlib import Path
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from regev_research.core import RootedBaseFamily, sample_distribution
from regev_research.lattice import regev_lattice_postprocess
from regev_research.qft_certificate import (
    distribution_tv_certificate,
    feasible_matrix_distances,
    fiber_state_audit,
    fiber_state_certificate,
    hellinger_affinity,
    original_certificate,
    product_hellinger_certificate,
    slack_factor,
    total_variation_distance,
)
from regev_research.qft_noise import (
    fiber_fourier_distribution,
    omitted_rotation_angle_sum,
    qft_gate_counts,
    qft_matrix,
    register_bits,
    weighted_fiber_fourier_distribution,
)
from regev_research.redteam import regev_gaussian_amplitudes


OUT = ROOT / "results" / "qft_certificate_gap"
ROOTS = (2, 3)
HELDOUT = (55, 65, 85, 95, 115, 119, 133, 161)
FACTOR_MANIFEST = {
    55: (5, 11),
    65: (5, 13),
    85: (5, 17),
    95: (5, 19),
    115: (5, 23),
    119: (7, 17),
    133: (7, 19),
    161: (7, 23),
}
MODULI = (8, 16, 32)
MODELS = ("A_uniform_hard_box", "B_exact_finite_discrete_gaussian")
SAMPLE_COUNT = 7
REPLICATES = 64
LOSS_BUDGET = 0.05
NONINFERIORITY_MARGIN = 0.10
MASTER_SEED = 2026071301
BOOTSTRAPS = 5000
SENSITIVITY_MARGINS = (0.02, 0.05, 0.10, 0.15)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def wilson(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    radius = z * sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


def largest_uniformly_certified_layers(
    configurations: list[dict], M: int, model: str
) -> int:
    """Derive the largest layer omission certified for every held-out ``N``."""

    relevant = [
        row
        for row in configurations
        if int(row["M"]) == int(M) and row["model"] == model
    ]
    if not relevant:
        raise ValueError("no configuration rows match M and model")
    decisions: dict[int, list[bool]] = {}
    for row in relevant:
        decisions.setdefault(int(row["omitted_layers"]), []).append(
            bool(row["original_certified"])
        )
    certified = [layers for layers, values in decisions.items() if all(values)]
    if not certified:
        raise ValueError("no uniformly certified cutoff, including exact QFT")
    return max(certified)


def exact_sign_test(values: np.ndarray) -> dict[str, float | int]:
    """Two-sided exact paired sign test, discarding exact zero differences."""

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
    values: np.ndarray, *, shift: float = 0.0, alternative: str = "two-sided"
) -> float:
    """Exact paired sign-flip randomization p-value under symmetry.

    ``shift=margin`` tests the boundary ``mean(values)=-margin`` after moving
    it to zero.  The one-sided ``greater`` alternative is a non-inferiority
    sensitivity analysis, not the primary preregistered cluster bootstrap.
    """

    shifted = np.asarray(values, dtype=float) + float(shift)
    if shifted.ndim != 1 or len(shifted) == 0:
        raise ValueError("values must be a nonempty one-dimensional array")
    observed = float(np.mean(shifted))
    permuted = np.asarray(
        [np.mean(shifted * np.asarray(signs)) for signs in product((-1.0, 1.0), repeat=len(shifted))]
    )
    tolerance = 1e-15
    if alternative == "two-sided":
        return float(np.mean(np.abs(permuted) >= abs(observed) - tolerance))
    if alternative == "greater":
        return float(np.mean(permuted >= observed - tolerance))
    raise ValueError("alternative must be 'two-sided' or 'greater'")


def qft_only_resources(d: int, M: int, cutoff: int) -> dict[str, int]:
    from qiskit import QuantumCircuit, transpile

    q = register_bits(M)
    circuit = QuantumCircuit(d * q)
    for coordinate in range(d):
        offset = coordinate * q
        sub = QuantumCircuit(q)
        for j in reversed(range(q)):
            sub.h(j)
            for k in reversed(range(j)):
                separation = j - k
                if separation <= cutoff:
                    sub.cp(pi / (2**separation), j, k)
        for j in range(q // 2):
            sub.swap(j, q - 1 - j)
        circuit.compose(sub.inverse(), qubits=range(offset, offset + q), inplace=True)
    compiled = transpile(
        circuit,
        basis_gates=("rz", "sx", "x", "cx"),
        optimization_level=1,
        seed_transpiler=MASTER_SEED,
    )
    return {
        "logical_depth": circuit.depth(),
        "compiled_depth": compiled.depth(),
        "compiled_cx": int(compiled.count_ops().get("cx", 0)),
        "compiled_two_qubit": sum(
            int(count)
            for name, count in compiled.count_ops().items()
            if name in {"cx", "cz", "ecr", "swap", "cp"}
        ),
    }


def probabilities_for(
    family: RootedBaseFamily, M: int, model: str, cutoff: int
) -> np.ndarray:
    if model == "A_uniform_hard_box":
        return fiber_fourier_distribution(family.N, family.bases, M, cutoff=cutoff)
    amplitudes = regev_gaussian_amplitudes(M, 4.0)
    return weighted_fiber_fourier_distribution(
        family.N, family.bases, M, amplitudes, cutoff=cutoff
    )


def audit_configurations() -> tuple[list[dict], dict[tuple[int, int, str, int], np.ndarray]]:
    rows: list[dict] = []
    cache: dict[tuple[int, int, str, int], np.ndarray] = {}
    resource_cache: dict[tuple[int, int], dict[str, int]] = {}
    for M in MODULI:
        q = register_bits(M)
        exact_resource = qft_only_resources(2, M, q - 1)
        for cutoff in range(q):
            resource_cache[(M, cutoff)] = qft_only_resources(2, M, cutoff)
        matrix = {
            cutoff: feasible_matrix_distances(2, M, cutoff, max_dimension=256)
            for cutoff in range(q)
        }
        counts_exact = qft_gate_counts(2, q, q - 1)
        for N in HELDOUT:
            family = RootedBaseFamily.from_roots(N, ROOTS)
            for model in MODELS:
                exact = probabilities_for(family, M, model, q - 1)
                cache[(N, M, model, q - 1)] = exact
                amplitudes = (
                    np.ones(M)
                    if model == "A_uniform_hard_box"
                    else regev_gaussian_amplitudes(M, 4.0)
                )
                for cutoff in range(q):
                    approximate = probabilities_for(family, M, model, cutoff)
                    cache[(N, M, model, cutoff)] = approximate
                    original = original_certificate(2, M, SAMPLE_COUNT, cutoff, LOSS_BUDGET)
                    distribution = distribution_tv_certificate(
                        exact, approximate, SAMPLE_COUNT, LOSS_BUDGET
                    )
                    hellinger = product_hellinger_certificate(
                        exact, approximate, SAMPLE_COUNT, LOSS_BUDGET
                    )
                    state_audit = None
                    state_certificate = None
                    if M <= 16:
                        state_audit = fiber_state_audit(
                            N, family.bases, M, amplitudes, cutoff
                        )
                        state_certificate = fiber_state_certificate(
                            state_audit, SAMPLE_COUNT, LOSS_BUDGET
                        )
                    counts = qft_gate_counts(2, q, cutoff)
                    resources = resource_cache[(M, cutoff)]
                    exact_flat = exact.ravel()
                    approximate_flat = approximate.ravel()
                    exact_peak = np.unravel_index(int(np.argmax(exact_flat)), exact.shape)
                    approximate_peak = np.unravel_index(int(np.argmax(approximate_flat)), approximate.shape)
                    coordinate_differences = [
                        min(abs(int(a) - int(b)), M - abs(int(a) - int(b))) / M
                        for a, b in zip(exact_peak, approximate_peak, strict=True)
                    ]
                    exact_positive = exact_flat[exact_flat > 0]
                    approximate_positive = approximate_flat[approximate_flat > 0]
                    exact_sorted = np.sort(exact_flat)[::-1]
                    approximate_sorted = np.sort(approximate_flat)[::-1]
                    low_probability_mask = exact_flat < (1.0 / exact_flat.size)
                    absolute_change = np.abs(exact_flat - approximate_flat)
                    rows.append({
                        "N": N,
                        "M": M,
                        "q": q,
                        "d": 2,
                        "m": SAMPLE_COUNT,
                        "model": model,
                        "cutoff": cutoff,
                        "omitted_layers": q - 1 - cutoff,
                        "original_certified": original.certified,
                        "original_per_shot_bound": original.per_shot_bound,
                        "original_m_shot_bound": original.m_shot_bound,
                        "distribution_tv": total_variation_distance(exact, approximate),
                        "exact_peak": json.dumps([int(value) for value in exact_peak]),
                        "approximate_peak": json.dumps([int(value) for value in approximate_peak]),
                        "peak_torus_displacement": float(np.linalg.norm(coordinate_differences)),
                        "exact_entropy_bits": float(-np.sum(exact_positive * np.log2(exact_positive))),
                        "approximate_entropy_bits": float(-np.sum(approximate_positive * np.log2(approximate_positive))),
                        "entropy_broadening_bits": float(
                            -np.sum(approximate_positive * np.log2(approximate_positive))
                            + np.sum(exact_positive * np.log2(exact_positive))
                        ),
                        "exact_top2_gap": float(exact_sorted[0] - exact_sorted[1]),
                        "approximate_top2_gap": float(approximate_sorted[0] - approximate_sorted[1]),
                        "top2_gap_change": float(
                            (approximate_sorted[0] - approximate_sorted[1])
                            - (exact_sorted[0] - exact_sorted[1])
                        ),
                        "fraction_change_on_low_probability_outcomes": float(
                            absolute_change[low_probability_mask].sum() / absolute_change.sum()
                        ) if absolute_change.sum() > 0 else 0.0,
                        "distribution_tv_certified": distribution.certified,
                        "distribution_m_shot_bound": distribution.m_shot_bound,
                        "hellinger_affinity": hellinger_affinity(exact, approximate),
                        "hellinger_certified": hellinger.certified,
                        "hellinger_product_bound": hellinger.m_shot_bound,
                        "state_trace_bound": None if state_audit is None else state_audit.trace_distance_bound,
                        "state_norm_error": None if state_audit is None else state_audit.state_vector_norm_error,
                        "state_certified": None if state_certificate is None else state_certificate.certified,
                        "state_m_shot_bound": None if state_certificate is None else state_certificate.m_shot_bound,
                        "one_register_operator_error": matrix[cutoff]["one_register_operator_error"],
                        "product_operator_error": matrix[cutoff]["product_operator_error"],
                        "phase_triangle_bound": omitted_rotation_angle_sum(q, cutoff),
                        "product_triangle_bound": matrix[cutoff]["product_triangle_bound"],
                        "exact_cp": counts_exact["controlled_phase"],
                        "cutoff_cp": counts["controlled_phase"],
                        "cp_saving": counts_exact["controlled_phase"] - counts["controlled_phase"],
                        "compiled_cx": resources["compiled_cx"],
                        "compiled_cx_saving": exact_resource["compiled_cx"] - resources["compiled_cx"],
                        "compiled_depth": resources["compiled_depth"],
                        "compiled_depth_saving": exact_resource["compiled_depth"] - resources["compiled_depth"],
                    })
    return rows, cache


def run_trials(cache: dict[tuple[int, int, str, int], np.ndarray]) -> list[dict]:
    rows: list[dict] = []
    for N in HELDOUT:
        family = RootedBaseFamily.from_roots(N, ROOTS)
        for M in MODULI:
            q = register_bits(M)
            for model in MODELS:
                for cutoff in range(q):
                    probabilities = cache[(N, M, model, cutoff)]
                    for replicate in range(REPLICATES):
                        seed = (
                            MASTER_SEED
                            + 1_000_000 * HELDOUT.index(N)
                            + 10_000 * MODULI.index(M)
                            + 1_000 * MODELS.index(model)
                            + replicate
                        )
                        samples = sample_distribution(probabilities, SAMPLE_COUNT, seed)
                        started = perf_counter()
                        result = regev_lattice_postprocess(
                            family,
                            samples,
                            M,
                            claim_norm_bound=4,
                            scale=4,
                        )
                        runtime = perf_counter() - started
                        factor_success = result.factor_pair is not None
                        if factor_success and tuple(result.factor_pair) != tuple(FACTOR_MANIFEST[N]):
                            raise AssertionError("returned factor pair failed post-hoc manifest validation")
                        lminus_success = any(
                            candidate.relation_class == "L_minus_L0"
                            for candidate in result.candidates
                        )
                        rows.append({
                            "N": N,
                            "M": M,
                            "q": q,
                            "model": model,
                            "cutoff": cutoff,
                            "omitted_layers": q - 1 - cutoff,
                            "replicate": replicate,
                            "seed": seed,
                            "factor_success": factor_success,
                            "lminus_success": lminus_success,
                            "candidate_count": len(result.candidates),
                            "lll_runtime_seconds": runtime,
                        })
    return rows


def aggregate_trials(
    trials: list[dict], configurations: list[dict]
) -> tuple[
    list[dict], list[dict], list[dict], list[dict],
    list[dict], list[dict], list[dict], list[dict],
]:
    import pandas as pd

    frame = pd.DataFrame(trials)
    per_n_rows: list[dict] = []
    for (N, M, model, cutoff), group in frame.groupby(["N", "M", "model", "cutoff"]):
        factor_successes = int(group.factor_success.sum())
        lminus_successes = int(group.lminus_success.sum())
        factor_low, factor_high = wilson(factor_successes, len(group))
        lminus_low, lminus_high = wilson(lminus_successes, len(group))
        per_n_rows.append({
            "N": int(N),
            "M": int(M),
            "model": model,
            "cutoff": int(cutoff),
            "omitted_layers": register_bits(int(M)) - 1 - int(cutoff),
            "replicates": len(group),
            "factor_probability": factor_successes / len(group),
            "factor_ci95_low": factor_low,
            "factor_ci95_high": factor_high,
            "lminus_probability": lminus_successes / len(group),
            "lminus_ci95_low": lminus_low,
            "lminus_ci95_high": lminus_high,
            "mean_lll_runtime_seconds": float(group.lll_runtime_seconds.mean()),
        })
    per_n = pd.DataFrame(per_n_rows)
    paired_rows: list[dict] = []
    bootstrap_rows: list[dict] = []
    sensitivity_rows: list[dict] = []
    leave_one_out_rows: list[dict] = []
    rng = np.random.default_rng(MASTER_SEED + 90_000)
    leave_one_out_rng = np.random.default_rng(MASTER_SEED + 190_000)
    for (M, model, cutoff), group in per_n.groupby(["M", "model", "cutoff"]):
        q = register_bits(int(M))
        exact = per_n[(per_n.M == M) & (per_n.model == model) & (per_n.cutoff == q - 1)].set_index("N")
        current = group.set_index("N")
        common = sorted(set(exact.index) & set(current.index))
        factor_diff = np.asarray(
            [current.loc[N, "factor_probability"] - exact.loc[N, "factor_probability"] for N in common]
        )
        lminus_diff = np.asarray(
            [current.loc[N, "lminus_probability"] - exact.loc[N, "lminus_probability"] for N in common]
        )
        factor_boot = np.asarray([
            np.mean(factor_diff[rng.integers(0, len(common), size=len(common))])
            for _ in range(BOOTSTRAPS)
        ])
        lminus_boot = np.asarray([
            np.mean(lminus_diff[rng.integers(0, len(common), size=len(common))])
            for _ in range(BOOTSTRAPS)
        ])
        for draw, (factor_value, lminus_value) in enumerate(
            zip(factor_boot, lminus_boot, strict=True)
        ):
            bootstrap_rows.append({
                "M": int(M),
                "model": model,
                "cutoff": int(cutoff),
                "omitted_layers": q - 1 - int(cutoff),
                "draw": draw,
                "factor_mean_difference": float(factor_value),
                "lminus_mean_difference": float(lminus_value),
            })
        factor_lower = float(np.quantile(factor_boot, 0.025))
        lminus_lower = float(np.quantile(lminus_boot, 0.025))
        paired_rows.append({
            "M": int(M),
            "model": model,
            "cutoff": int(cutoff),
            "omitted_layers": q - 1 - int(cutoff),
            "N_cluster_count": len(common),
            "factor_mean_difference": float(np.mean(factor_diff)),
            "factor_cluster_ci95_low": factor_lower,
            "factor_cluster_ci95_high": float(np.quantile(factor_boot, 0.975)),
            "lminus_mean_difference": float(np.mean(lminus_diff)),
            "lminus_cluster_ci95_low": lminus_lower,
            "lminus_cluster_ci95_high": float(np.quantile(lminus_boot, 0.975)),
            "empirically_noninferior": bool(
                factor_lower >= -NONINFERIORITY_MARGIN
                and lminus_lower >= -NONINFERIORITY_MARGIN
            ),
            "margin": NONINFERIORITY_MARGIN,
            "bootstrap_replicates": BOOTSTRAPS,
        })

        if int(cutoff) != q - 1:
            for endpoint, differences in (
                ("factor", factor_diff),
                ("L_minus_L0", lminus_diff),
            ):
                sign = exact_sign_test(differences)
                sensitivity_rows.append({
                    "M": int(M),
                    "model": model,
                    "cutoff": int(cutoff),
                    "omitted_layers": q - 1 - int(cutoff),
                    "endpoint": endpoint,
                    "N_cluster_count": len(common),
                    "mean_difference": float(np.mean(differences)),
                    "sign_nonzero_pairs": sign["nonzero_pairs"],
                    "sign_positive_pairs": sign["positive_pairs"],
                    "sign_two_sided_p": sign["two_sided_p"],
                    "sign_flip_two_sided_p": exact_sign_flip_p(differences),
                    "sign_flip_noninferiority_p_at_0_10": exact_sign_flip_p(
                        differences, shift=NONINFERIORITY_MARGIN, alternative="greater"
                    ),
                })

            for omitted_N in common:
                keep = np.asarray([N != omitted_N for N in common])
                factor_remaining = factor_diff[keep]
                lminus_remaining = lminus_diff[keep]
                factor_leave_boot = np.asarray([
                    np.mean(
                        factor_remaining[
                            leave_one_out_rng.integers(
                                0, len(factor_remaining), size=len(factor_remaining)
                            )
                        ]
                    )
                    for _ in range(BOOTSTRAPS)
                ])
                lminus_leave_boot = np.asarray([
                    np.mean(
                        lminus_remaining[
                            leave_one_out_rng.integers(
                                0, len(lminus_remaining), size=len(lminus_remaining)
                            )
                        ]
                    )
                    for _ in range(BOOTSTRAPS)
                ])
                factor_leave_lower = float(np.quantile(factor_leave_boot, 0.025))
                lminus_leave_lower = float(np.quantile(lminus_leave_boot, 0.025))
                leave_one_out_rows.append({
                    "M": int(M),
                    "model": model,
                    "cutoff": int(cutoff),
                    "omitted_layers": q - 1 - int(cutoff),
                    "omitted_N": int(omitted_N),
                    "remaining_N_clusters": len(factor_remaining),
                    "factor_mean_difference": float(np.mean(factor_remaining)),
                    "factor_cluster_ci95_low": factor_leave_lower,
                    "lminus_mean_difference": float(np.mean(lminus_remaining)),
                    "lminus_cluster_ci95_low": lminus_leave_lower,
                    "noninferior_at_0_10": bool(
                        factor_leave_lower >= -NONINFERIORITY_MARGIN
                        and lminus_leave_lower >= -NONINFERIORITY_MARGIN
                    ),
                    "bootstrap_replicates": BOOTSTRAPS,
                })

    paired = pd.DataFrame(paired_rows)
    gap_rows: list[dict] = []
    for (M, model), group in paired.groupby(["M", "model"]):
        q = register_bits(int(M))
        empirical_layers = int(
            group[group.empirically_noninferior].omitted_layers.max()
        )
        original_layers = largest_uniformly_certified_layers(
            configurations, int(M), model
        )
        # State/distribution certificates are N-specific; require all held-out
        # N values to certify a layer before reporting it as a general layer.
        gap_rows.append({
            "M": int(M),
            "model": model,
            "exact_cutoff": q - 1,
            "original_certified_layers": original_layers,
            "empirically_noninferior_layers": empirical_layers,
            "G_layers": empirical_layers - original_layers,
        })

    margin_rows: list[dict] = []
    margin_summary_rows: list[dict] = []
    for margin in SENSITIVITY_MARGINS:
        for row in paired_rows:
            margin_rows.append({
                "M": row["M"],
                "model": row["model"],
                "cutoff": row["cutoff"],
                "omitted_layers": row["omitted_layers"],
                "margin": margin,
                "factor_cluster_ci95_low": row["factor_cluster_ci95_low"],
                "lminus_cluster_ci95_low": row["lminus_cluster_ci95_low"],
                "noninferior": bool(
                    row["factor_cluster_ci95_low"] >= -margin
                    and row["lminus_cluster_ci95_low"] >= -margin
                ),
            })
        margin_frame = pd.DataFrame(margin_rows)
        margin_frame = margin_frame[margin_frame.margin == margin]
        for (M, model), group in margin_frame.groupby(["M", "model"]):
            passing = group[group.noninferior]
            margin_summary_rows.append({
                "M": int(M),
                "model": model,
                "margin": margin,
                "largest_noninferior_omitted_layers": (
                    None if passing.empty else int(passing.omitted_layers.max())
                ),
            })
    return (
        per_n_rows,
        paired_rows,
        gap_rows,
        bootstrap_rows,
        sensitivity_rows,
        leave_one_out_rows,
        margin_rows,
        margin_summary_rows,
    )


def proof_slack_rows(configurations: list[dict], per_n_rows: list[dict]) -> list[dict]:
    per_n = {
        (row["N"], row["M"], row["model"], row["cutoff"]): row
        for row in per_n_rows
    }
    rows: list[dict] = []
    for row in configurations:
        key = (row["N"], row["M"], row["model"], row["cutoff"])
        empirical = per_n[key]
        exact_key = (row["N"], row["M"], row["model"], row["q"] - 1)
        exact = per_n[exact_key]
        empirical_loss = abs(empirical["factor_probability"] - exact["factor_probability"])
        steps = [
            ("omitted_gate_triangle", row["phase_triangle_bound"], row["one_register_operator_error"]),
            ("product_tensor_triangle", row["product_triangle_bound"], row["product_operator_error"]),
            ("prepared_state_restriction", row["product_operator_error"], row["state_trace_bound"]),
            ("measurement_data_processing", row["state_trace_bound"], row["distribution_tv"]),
            ("sample_union_vs_hellinger", row["distribution_m_shot_bound"], row["hellinger_product_bound"]),
            ("distribution_bound_vs_factor_event", row["hellinger_product_bound"], empirical_loss),
        ]
        for step, theoretical, observed in steps:
            if theoretical is None or observed is None:
                continue
            rows.append({
                "N": row["N"],
                "M": row["M"],
                "model": row["model"],
                "cutoff": row["cutoff"],
                "proof_step": step,
                "theoretical_bound": theoretical,
                "observed_value": observed,
                "slack_factor": slack_factor(float(theoretical), float(observed)),
            })
    return rows


def controlled_examples(configurations: list[dict]) -> dict:
    # Extreme loose example: the exact and H-only QFT distributions coincide,
    # while the all-state operator certificate rejects the cutoff.
    exact = fiber_fourier_distribution(15, (4, 1), 4, cutoff=1)
    approximate = fiber_fourier_distribution(15, (4, 1), 4, cutoff=0)
    loose = {
        "N": 15,
        "bases": [4, 1],
        "M": 4,
        "cutoff": 0,
        "distribution_tv": total_variation_distance(exact, approximate),
        "original_certified": original_certificate(2, 4, 4, 0, 0.05).certified,
        "distribution_certified": distribution_tv_certificate(exact, approximate, 4, 0.05).certified,
        "mechanism": "fiber/measurement cancellation: identical measured laws despite nonzero all-state unitary error",
    }

    # Near-tight gate-level example: the last omitted phase layer nearly
    # saturates the phase-sum operator bound.
    best = None
    for q in range(2, 8):
        M = 1 << q
        for cutoff in range(q - 1):
            exact_matrix = qft_matrix(M, cutoff=q - 1)
            approximate_matrix = qft_matrix(M, cutoff=cutoff)
            observed = float(np.linalg.norm(exact_matrix - approximate_matrix, 2))
            bound = omitted_rotation_angle_sum(q, cutoff)
            ratio = observed / bound if bound else 0.0
            candidate = {
                "q": q,
                "M": M,
                "cutoff": cutoff,
                "operator_error": observed,
                "phase_sum_bound": bound,
                "tightness_ratio": ratio,
                "mechanism": "largest singular-vector input aligns with the omitted-layer unitary error",
            }
            if best is None or ratio > best["tightness_ratio"]:
                best = candidate
    nonexact = [row for row in configurations if row["omitted_layers"] > 0]
    peak_shift = max(nonexact, key=lambda row: row["peak_torus_displacement"])
    broadening = max(nonexact, key=lambda row: row["entropy_broadening_bits"])
    merging = min(nonexact, key=lambda row: row["top2_gap_change"])
    low_probability = max(
        nonexact, key=lambda row: row["fraction_change_on_low_probability_outcomes"]
    )
    keep = (
        "N", "M", "model", "cutoff", "omitted_layers", "distribution_tv",
        "exact_peak", "approximate_peak", "peak_torus_displacement",
        "entropy_broadening_bits", "top2_gap_change",
        "fraction_change_on_low_probability_outcomes",
    )
    compact = lambda row: {key: row[key] for key in keep}
    return {
        "extreme_loose": loose,
        "near_tight_gate_step": best,
        "largest_observed_peak_shift": compact(peak_shift),
        "largest_observed_broadening": compact(broadening),
        "strongest_observed_top_peak_merge": compact(merging),
        "change_most_concentrated_on_low_probability_outcomes": compact(low_probability),
    }


def make_figures(configurations: list[dict], paired_rows: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    configuration = pd.DataFrame(configurations)
    paired = pd.DataFrame(paired_rows)
    figure, axes = plt.subplots(1, 2, figsize=(11, 4))
    for model, marker in ((MODELS[0], "o"), (MODELS[1], "s")):
        subset = configuration[(configuration.model == model) & (configuration.N == HELDOUT[0])]
        for M in MODULI:
            points = subset[subset.M == M].sort_values("omitted_layers")
            axes[0].plot(points.omitted_layers, points.distribution_tv, marker=marker, label=f"{model[0]}, M={M}")
    axes[0].set_xlabel("omitted phase layers")
    axes[0].set_ylabel("exact one-shot TV")
    axes[0].set_title("State/distribution error versus truncation")
    axes[0].legend(fontsize=7, ncol=2)

    for model, marker in ((MODELS[0], "o"), (MODELS[1], "s")):
        subset = paired[paired.model == model]
        for M in MODULI:
            points = subset[subset.M == M].sort_values("omitted_layers")
            axes[1].plot(points.omitted_layers, points.factor_mean_difference, marker=marker, label=f"{model[0]}, M={M}")
    axes[1].axhline(
        -NONINFERIORITY_MARGIN,
        color="black",
        linestyle="--",
        label="non-inferiority margin",
    )
    axes[1].set_xlabel("omitted phase layers")
    axes[1].set_ylabel("approximate - exact factor probability")
    axes[1].set_title("Held-out recovery certification gap")
    axes[1].legend(fontsize=7, ncol=2)
    figure.tight_layout()
    figure.savefig(OUT / "certification_vs_recovery.png", dpi=180)
    plt.close(figure)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    configurations, cache = audit_configurations()
    trials = run_trials(cache)
    (
        per_n,
        paired,
        gaps,
        bootstrap_draws,
        sensitivity,
        leave_one_out,
        margin_sensitivity,
        margin_summary,
    ) = aggregate_trials(trials, configurations)
    slack = proof_slack_rows(configurations, per_n)
    examples = controlled_examples(configurations)
    write_csv(OUT / "configuration_rows.csv", configurations)
    write_csv(OUT / "trial_rows.csv", trials)
    write_csv(OUT / "per_N_rows.csv", per_n)
    write_csv(OUT / "paired_cluster_rows.csv", paired)
    write_csv(OUT / "certificate_gap_rows.csv", gaps)
    write_csv(OUT / "proof_slack_rows.csv", slack)
    write_csv(OUT / "bootstrap_draw_rows.csv", bootstrap_draws)
    write_csv(OUT / "paired_exact_test_rows.csv", sensitivity)
    write_csv(OUT / "leave_one_N_out_rows.csv", leave_one_out)
    write_csv(OUT / "margin_sensitivity_rows.csv", margin_sensitivity)
    write_csv(OUT / "margin_summary_rows.csv", margin_summary)
    (OUT / "controlled_examples.json").write_text(json.dumps(examples, indent=2, sort_keys=True))
    make_figures(configurations, paired)
    config = {
        "freeze_version": "qft-certificate-gap-v1",
        "heldout_N": HELDOUT,
        "roots": ROOTS,
        "M_values": MODULI,
        "models": MODELS,
        "sample_count": SAMPLE_COUNT,
        "replicates": REPLICATES,
        "loss_budget": LOSS_BUDGET,
        "noninferiority_margin": NONINFERIORITY_MARGIN,
        "master_seed": MASTER_SEED,
        "bootstrap_replicates": BOOTSTRAPS,
        "sensitivity_margins": SENSITIVITY_MARGINS,
        "sensitivity_analyses_posthoc": True,
        "configuration_rows": len(configurations),
        "trial_rows": len(trials),
        "per_N_rows": len(per_n),
        "paired_cluster_rows": len(paired),
        "gap_rows": len(gaps),
        "slack_rows": len(slack),
        "bootstrap_draw_rows": len(bootstrap_draws),
        "paired_exact_test_rows": len(sensitivity),
        "leave_one_N_out_rows": len(leave_one_out),
        "margin_sensitivity_rows": len(margin_sensitivity),
        "margin_summary_rows": len(margin_summary),
        "known_factors_used_only_posthoc": True,
    }
    (OUT / "configuration.json").write_text(json.dumps(config, indent=2, sort_keys=True))
    manifest_names = (
        "configuration.json",
        "configuration_rows.csv",
        "trial_rows.csv",
        "per_N_rows.csv",
        "paired_cluster_rows.csv",
        "certificate_gap_rows.csv",
        "proof_slack_rows.csv",
        "bootstrap_draw_rows.csv",
        "paired_exact_test_rows.csv",
        "leave_one_N_out_rows.csv",
        "margin_sensitivity_rows.csv",
        "margin_summary_rows.csv",
        "controlled_examples.json",
        "certification_vs_recovery.png",
    )
    completion = {
        "freeze_version": config["freeze_version"],
        "status": "complete",
        "heldout_moduli_executed": list(HELDOUT),
        "primary_unit_of_generalization": "N",
        "known_factors_used_only_posthoc": True,
        "row_counts": {
            "configuration_rows": len(configurations),
            "trial_rows": len(trials),
            "per_N_rows": len(per_n),
            "paired_cluster_rows": len(paired),
            "gap_rows": len(gaps),
            "slack_rows": len(slack),
            "bootstrap_draw_rows": len(bootstrap_draws),
            "paired_exact_test_rows": len(sensitivity),
            "leave_one_N_out_rows": len(leave_one_out),
            "margin_sensitivity_rows": len(margin_sensitivity),
            "margin_summary_rows": len(margin_summary),
        },
        "sha256": {
            name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
            for name in manifest_names
        },
    }
    (OUT / "completion.json").write_text(
        json.dumps(completion, indent=2, sort_keys=True)
    )
    print(json.dumps(config, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

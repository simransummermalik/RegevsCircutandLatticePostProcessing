"""Frozen scaling, matrix-audit, and RV-structured-noise comparison.

The large parameter grid is evaluated analytically from the exact finite tail
formula.  Exact fiber laws and the full lattice endpoint are run only where
the tensor matrix is feasible (d=2, M<=32), and a Qiskit matrix overlap is
checked for M<=16.  This keeps the distinction between a theorem-level scaling
statement and a circuit-derived experiment explicit.
"""

from __future__ import annotations

import csv
import json
import sys
from math import sqrt
from pathlib import Path
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from regev_research.core import RootedBaseFamily, sample_distribution
from regev_research.lattice import regev_lattice_postprocess
from regev_research.qft_noise import (
    dimensionless_precision_ratio,
    exact_qft_matrix,
    fiber_fourier_distribution,
    qft_gate_counts,
    qft_matrix,
    qft_tv_bound,
    register_bits,
    select_qft_cutoff,
    weighted_fiber_fourier_distribution,
)
from regev_research.quotient_recovery import RecoveryBudget, short_combination_recovery
from regev_research.redteam import regev_gaussian_amplitudes
from regev_research.rv_filter import rv_filter_then_short_combination_recovery

OUT = ROOT / "results" / "qft_precision_scaling"
MASTER_SEED = 2026071211
DS = (2, 3, 4, 5)
MS = (8, 16, 32, 64, 128)
SAMPLE_COUNTS = (4, 8, 12, 24)
BUDGETS = (0.05, 0.10, 0.20)
ENDPOINT_INPUTS = (35, 77, 143)
ENDPOINT_M = (8, 16, 32)
ENDPOINT_REPLICATES = 16


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _wilson(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    p = successes / trials
    denom = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    radius = z * sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return max(0.0, center - radius), min(1.0, center + radius)


def analytic_scaling() -> list[dict]:
    rows: list[dict] = []
    for d in DS:
        for M in MS:
            q = register_bits(M)
            exact_counts = qft_gate_counts(d, q, q - 1)
            for m in SAMPLE_COUNTS:
                for budget in BUDGETS:
                    choice = select_qft_cutoff(d, M, m, budget)
                    for cutoff in range(q):
                        counts = qft_gate_counts(d, q, cutoff)
                        rows.append({
                            "d": d,
                            "M": M,
                            "q": q,
                            "m": m,
                            "loss_budget": budget,
                            "cutoff": cutoff,
                            "operator_tv_bound": qft_tv_bound(d, q, cutoff),
                            "dimensionless_ratio": dimensionless_precision_ratio(d, M, m, cutoff, budget),
                            "certified": dimensionless_precision_ratio(d, M, m, cutoff, budget) <= 1,
                            "selected_cutoff": choice.cutoff,
                            "selected_exact": choice.cutoff == q - 1,
                            "exact_cp": exact_counts["controlled_phase"],
                            "cutoff_cp": counts["controlled_phase"],
                            "cp_saving": exact_counts["controlled_phase"] - counts["controlled_phase"],
                            "two_qubit_saving": exact_counts["two_qubit_qft_gates"] - counts["two_qubit_qft_gates"],
                        })
    return rows


def matrix_audit() -> list[dict]:
    rows: list[dict] = []
    for M in (2, 4, 8, 16):
        q = register_bits(M)
        exact = exact_qft_matrix(M, inverse=True)
        for cutoff in range(q):
            approx = qft_matrix(M, cutoff=cutoff, inverse=True)
            rows.append({
                "M": M,
                "q": q,
                "cutoff": cutoff,
                "matrix_error_to_direct": float(np.linalg.norm(approx - exact, 2)),
                "unitarity_error": float(np.linalg.norm(approx.conj().T @ approx - np.eye(M), 2)),
                "full_cutoff_exact": bool(np.allclose(approx, exact, atol=1e-12)),
            })
    return rows


def exact_endpoint() -> list[dict]:
    rows: list[dict] = []
    for N in ENDPOINT_INPUTS:
        for roots in ((2, 3),):
            family = RootedBaseFamily.from_roots(N, roots)
            for M in ENDPOINT_M:
                q = register_bits(M)
                for model in ("A_uniform_hard_box", "B_exact_finite_discrete_gaussian"):
                    amplitudes = regev_gaussian_amplitudes(M, 4.0)
                    for cutoff in range(q):
                        successes = 0
                        lminus = 0
                        runtimes: list[float] = []
                        for replicate in range(ENDPOINT_REPLICATES):
                            if model.startswith("A"):
                                probabilities = fiber_fourier_distribution(N, family.bases, M, cutoff=cutoff)
                            else:
                                probabilities = weighted_fiber_fourier_distribution(
                                    N, family.bases, M, amplitudes, cutoff=cutoff
                                )
                            samples = sample_distribution(
                                probabilities,
                                7,
                                MASTER_SEED + N + M + cutoff * 100 + replicate,
                            )
                            started = perf_counter()
                            result = regev_lattice_postprocess(
                                family, samples, M, claim_norm_bound=4, scale=4
                            )
                            runtimes.append(perf_counter() - started)
                            successes += int(result.factor_pair is not None)
                            lminus += sum(c.relation_class == "L_minus_L0" for c in result.candidates)
                        low, high = _wilson(successes, ENDPOINT_REPLICATES)
                        rows.append({
                            "N": N,
                            "d": len(roots),
                            "M": M,
                            "m": 7,
                            "model": model,
                            "cutoff": cutoff,
                            "replicates": ENDPOINT_REPLICATES,
                            "factor_successes": successes,
                            "factor_probability": successes / ENDPOINT_REPLICATES,
                            "ci95_low": low,
                            "ci95_high": high,
                            "lminus_candidates": lminus,
                            "mean_lll_seconds": float(np.mean(runtimes)),
                        })
    return rows


def rv_comparison() -> list[dict]:
    """Compare approximate-QFT diffuse/coherent errors with the RV comparator.

    This is a finite structural comparator only; its theorem status is stored
    and must not be read as the asymptotic RV guarantee.
    """

    N, M = 35, 8
    family = RootedBaseFamily.from_roots(N, (2, 3))
    budget = RecoveryBudget(enumeration_rows=4, coefficient_bound=1, max_nodes=100)
    rows: list[dict] = []
    for noise in ("approx_qft", "sparse_corruption", "diffuse_displacement", "coherent_phase"):
        for replicate in range(8):
            seed = MASTER_SEED + 40_000 + replicate
            rng = np.random.default_rng(seed)
            if noise == "coherent_phase":
                phase = 0.20 * np.sin(np.arange(M * M, dtype=float)).reshape(M, M)
                probabilities = weighted_fiber_fourier_distribution(
                    N, family.bases, M, np.ones(M), cutoff=None, phase_errors=phase.ravel()
                )
            else:
                cutoff = 1 if noise == "approx_qft" else None
                probabilities = fiber_fourier_distribution(N, family.bases, M, cutoff=cutoff)
            pool = sample_distribution(probabilities, 11, seed)
            if noise == "sparse_corruption":
                pool[:3] = rng.integers(0, M, size=(3, 2))
            elif noise == "diffuse_displacement":
                pool = (pool + rng.choice((-1, 0, 1), size=pool.shape)) % M
            baseline_factor = None
            baseline_error = None
            try:
                baseline = short_combination_recovery(
                    family, pool[:7], M, scale=4, budget=budget
                )
                baseline_factor = baseline.factor_pair
            except Exception as exc:  # finite comparator rows retain failures
                baseline_error = type(exc).__name__
            try:
                rv = rv_filter_then_short_combination_recovery(
                    family,
                    pool,
                    M,
                    scale=4,
                    target_count=7,
                    budget=budget,
                    max_iterations=7,
                )
                recovery = rv.recovery_result
                rv_factor = getattr(recovery, "factor_pair", None)
                filter_success = rv.filter_result.success
                selected_count = len(rv.filter_result.selected_indices)
                theorem_applicable = rv.filter_result.theorem_status.asymptotic_guarantee_applicable
                rv_error = None
            except Exception as exc:
                rv_factor = None
                filter_success = False
                selected_count = 0
                theorem_applicable = False
                rv_error = type(exc).__name__
            rows.append({
                "N": N,
                "d": 2,
                "M": M,
                "pool_size": 11,
                "target_count": 7,
                "noise_model": noise,
                "replicate": replicate,
                "baseline_factor": baseline_factor is not None,
                "baseline_error": baseline_error,
                "rv_filter_success": filter_success,
                "rv_selected_count": selected_count,
                "rv_factor": rv_factor is not None,
                "rv_error": rv_error,
                "rv_theorem_applicable": theorem_applicable,
            })
    return rows


def make_figures(analytic: list[dict], endpoint: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    frame = pd.DataFrame(analytic)
    primary = frame[frame.loss_budget == 0.05]
    figure, axis = plt.subplots(figsize=(7, 4))
    for d in DS:
        subset = primary[(primary.d == d) & (primary.m == 12)]
        selected = subset.drop_duplicates(["M"]).sort_values("M")
        axis.plot(selected.M, selected.selected_cutoff, marker="o", label=f"d={d}")
    axis.set_xscale("log", base=2)
    axis.set_xlabel("Fourier modulus M")
    axis.set_ylabel("selected cutoff t")
    axis.set_title("Finite-shot selector scaling (Delta=0.05, m=12)")
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUT / "cutoff_scaling.png", dpi=180)
    plt.close(figure)

    endpoint_frame = pd.DataFrame(endpoint)
    figure, axis = plt.subplots(figsize=(7, 4))
    for N in ENDPOINT_INPUTS:
        subset = endpoint_frame[(endpoint_frame.N == N) & (endpoint_frame.model == "A_uniform_hard_box")]
        grouped = subset.groupby("M").factor_probability.mean().sort_index()
        axis.plot(grouped.index, grouped.values, marker="o", label=f"N={N}")
    axis.set_xscale("log", base=2)
    axis.set_ylim(0, 1.05)
    axis.set_xlabel("M")
    axis.set_ylabel("factor recovery probability")
    axis.set_title("Exact-fiber endpoint across M (A, d=2, m=7)")
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUT / "recovery_transition.png", dpi=180)
    plt.close(figure)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    analytic = analytic_scaling()
    matrix = matrix_audit()
    endpoint = exact_endpoint()
    rv = rv_comparison()
    write_csv(OUT / "precision_rows.csv", analytic)
    write_csv(OUT / "matrix_rows.csv", matrix)
    write_csv(OUT / "endpoint_rows.csv", endpoint)
    write_csv(OUT / "rv_rows.csv", rv)
    import pandas as pd
    endpoint_frame = pd.DataFrame(endpoint)
    paired = (
        endpoint_frame.groupby(["N", "M", "model", "cutoff"], as_index=False)
        .agg(
            factor_probability=("factor_probability", "mean"),
            ci95_low=("ci95_low", "mean"),
            ci95_high=("ci95_high", "mean"),
            mean_lll_seconds=("mean_lll_seconds", "mean"),
        )
    )
    paired.to_csv(OUT / "paired_N_comparisons.csv", index=False)
    cluster_rows: list[dict] = []
    cluster_rng = np.random.default_rng(MASTER_SEED + 9000)
    for (M_value, model_value, cutoff_value), group in endpoint_frame.groupby(["M", "model", "cutoff"]):
        per_N = group.groupby("N")["factor_probability"].mean().to_numpy(float)
        if len(per_N) == 0:
            continue
        bootstrap = np.asarray(
            [np.mean(per_N[cluster_rng.integers(0, len(per_N), size=len(per_N))]) for _ in range(5000)]
        )
        cluster_rows.append({
            "M": M_value,
            "model": model_value,
            "cutoff": cutoff_value,
            "N_cluster_count": len(per_N),
            "cluster_mean_probability": float(np.mean(per_N)),
            "cluster_bootstrap95_low": float(np.quantile(bootstrap, 0.025)),
            "cluster_bootstrap95_high": float(np.quantile(bootstrap, 0.975)),
            "bootstrap_replicates": 5000,
            "bootstrap_seed": MASTER_SEED + 9000,
        })
    write_csv(OUT / "cluster_bootstrap_rows.csv", cluster_rows)
    analytic_frame = pd.DataFrame(analytic)
    resources = analytic_frame[
        (analytic_frame.loss_budget == 0.05)
        & (analytic_frame.m == 12)
        & (analytic_frame.cutoff == analytic_frame.selected_cutoff)
    ].copy()
    resources = resources[["d", "M", "m", "loss_budget", "selected_cutoff", "exact_cp", "cutoff_cp", "cp_saving", "two_qubit_saving", "dimensionless_ratio", "selected_exact"]]
    resources.to_csv(OUT / "resource_rows.csv", index=False)
    make_figures(analytic, endpoint)
    config = {
        "freeze_version": "qft-precision-scaling-v1",
        "master_seed": MASTER_SEED,
        "d_values": DS,
        "M_values": MS,
        "sample_counts": SAMPLE_COUNTS,
        "loss_budgets": BUDGETS,
        "endpoint_inputs": ENDPOINT_INPUTS,
        "endpoint_M": ENDPOINT_M,
        "endpoint_replicates": ENDPOINT_REPLICATES,
        "analytic_rows": len(analytic),
        "matrix_rows": len(matrix),
        "endpoint_rows": len(endpoint),
        "rv_rows": len(rv),
        "paired_N_rows": len(paired),
        "resource_rows": len(resources),
        "cluster_bootstrap_rows": len(cluster_rows),
        "primary_variable": "B=m*min(1,2*d*eta)/Delta",
        "selection_is_factor_blind": True,
        "RV_status": "finite structural comparator; theorem applicability false in these cells",
        "full_Qiskit_scope": "matrix overlap M<=16; resource/decomposition validation remains in results/qft_noise",
    }
    (OUT / "configuration.json").write_text(json.dumps(config, indent=2, sort_keys=True))
    print(json.dumps(config, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

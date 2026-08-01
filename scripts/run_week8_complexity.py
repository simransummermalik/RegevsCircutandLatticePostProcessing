#!/usr/bin/env python3
"""Reproduce the Week 8 circuit-constant and simulator-comparison audit."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from regev_research.resource_analysis import (  # noqa: E402
    asymptotic_leading_constants,
    canonical_cx_count,
    first_coprime_prime_square_bases,
    full_circuit_source_counts,
    normalized_scaling_record,
    notebook_parameters,
    qft_closed_form,
)


OUT = ROOT / "all_graphics_and_results" / "results" / "week_8_complexity"
QFT_RESULTS = ROOT / "all_graphics_and_results" / "results" / "qft_certificate_gap"
QUOTIENT_RESULTS = ROOT / "all_graphics_and_results" / "results" / "quotient_study"
SEED = 2_026_080_101
BOOTSTRAPS = 5_000
SYNTHETIC_BITS = (4, 6, 8, 12, 16, 24, 32, 48, 64)
PARAMETER_BITS = tuple(range(4, 257))
QFT_HELDOUT = (55, 65, 85, 95, 115, 119, 133, 161)
QFT_MODELS = (
    "A_uniform_hard_box",
    "B_exact_finite_discrete_gaussian",
)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table {path}")
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parameter_rows() -> list[dict]:
    rows: list[dict] = []
    for mode in ("cover_2n", "notebook"):
        for n in PARAMETER_BITS:
            values = notebook_parameters(n, mode)
            d, q = int(values["d"]), int(values["q"])
            qft = qft_closed_form(d, q)
            rows.append({
                **values,
                "qft_cp": qft["controlled_phase"],
                "qft_canonical_cx": qft["canonical_cx"],
                "qubit_ratio_Q_over_n": int(values["total_qubits"]) / n,
                "qft_cp_ratio_over_n_3_2": qft["controlled_phase"] / (n**1.5),
                "qft_cx_ratio_over_n_3_2": qft["canonical_cx"] / (n**1.5),
            })
    return rows


def arithmetic_scaling_rows() -> list[dict]:
    rows: list[dict] = []
    for n in SYNTHETIC_BITS:
        # This is an n-bit, factor-blind resource probe only.  It is not used
        # as a factoring instance and its factorization is never computed.
        N = (1 << (n - 1)) + 1
        row = normalized_scaling_record(N, "cover_2n")
        row["synthetic_rule"] = "N=2^(n-1)+1; no factoring outcome evaluated"
        rows.append(row)
    return rows


def finite_full_resource_rows() -> list[dict]:
    rows: list[dict] = []
    for N in QFT_HELDOUT:
        for M in (8, 16, 32):
            q = int(math.log2(M))
            for cutoff in range(q):
                counts = full_circuit_source_counts(N, (4, 9), q, qft_cutoff=cutoff)
                qft = qft_closed_form(2, q, cutoff)
                total_cx = canonical_cx_count(counts)
                rows.append({
                    "N": N,
                    "n": N.bit_length(),
                    "M": M,
                    "d": 2,
                    "q": q,
                    "cutoff": cutoff,
                    "omitted_layers": q - 1 - cutoff,
                    "source_ccx": counts["ccx"],
                    "source_cx": counts["cx"],
                    "source_cswap": counts["cswap"],
                    "qft_canonical_cx": qft["canonical_cx"],
                    "full_canonical_cx": total_cx,
                    "arithmetic_and_preparation_canonical_cx": (
                        total_cx - qft["canonical_cx"]
                    ),
                    "qft_fraction_of_full_canonical_cx": (
                        qft["canonical_cx"] / total_cx
                    ),
                    "resource_scope": (
                        "exact source flattening; all-to-all CX basis; no routing/fault tolerance"
                    ),
                })
    return rows


def _cluster_bootstrap_cost_saving(
    exact: pd.DataFrame,
    approximate: pd.DataFrame,
    full_resource: pd.DataFrame,
    *,
    resource_column: str,
    rng: np.random.Generator,
) -> tuple[float, float]:
    Ns = sorted(set(exact.N) & set(approximate.N))
    resource = full_resource.set_index(["N", "omitted_layers"])[resource_column]

    exact_cells = {}
    approximate_cells = {}
    for N in Ns:
        e = exact[exact.N == N]
        a = approximate[approximate.N == N]
        exact_cells[N] = (
            float(e.factor_success.sum()),
            len(e) * 7 * float(resource.loc[(N, 0)]),
        )
        approximate_cells[N] = (
            float(a.factor_success.sum()),
            len(a) * 7 * float(resource.loc[(N, 1)]),
        )

    values = []
    for _ in range(BOOTSTRAPS):
        draw = rng.choice(Ns, size=len(Ns), replace=True)
        exact_success = sum(exact_cells[int(N)][0] for N in draw)
        approximate_success = sum(approximate_cells[int(N)][0] for N in draw)
        if exact_success == 0 or approximate_success == 0:
            continue
        exact_cost = sum(exact_cells[int(N)][1] for N in draw) / exact_success
        approximate_cost = (
            sum(approximate_cells[int(N)][1] for N in draw) / approximate_success
        )
        values.append(100.0 * (1.0 - approximate_cost / exact_cost))
    if not values:
        return float("nan"), float("nan")
    return float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))


def qft_endpoint_cost_rows(full_rows: list[dict]) -> list[dict]:
    trials = pd.read_csv(QFT_RESULTS / "trial_rows.csv")
    resources = pd.DataFrame(full_rows)
    rows: list[dict] = []
    rng = np.random.default_rng(SEED)

    for M in (8, 16, 32):
        q = int(math.log2(M))
        for model in QFT_MODELS:
            relevant = trials[(trials.M == M) & (trials.model == model)]
            exact = relevant[relevant.omitted_layers == 0]
            approximate = relevant[relevant.omitted_layers == 1]
            resource = resources[resources.M == M].set_index(
                ["N", "omitted_layers"]
            )
            model_rows = {}
            for label, frame, omitted in (
                ("exact", exact, 0),
                ("omit_one_layer", approximate, 1),
            ):
                successes = int(frame.factor_success.sum())
                qft_total = 0.0
                full_total = 0.0
                for trial in frame.itertuples():
                    resource_row = resource.loc[(int(trial.N), omitted)]
                    qft_total += 7 * float(resource_row.qft_canonical_cx)
                    full_total += 7 * float(resource_row.full_canonical_cx)
                record = {
                    "M": M,
                    "q": q,
                    "model": model,
                    "comparison": label,
                    "omitted_layers": omitted,
                    "N_clusters": int(frame.N.nunique()),
                    "trials": len(frame),
                    "factor_successes": successes,
                    "pooled_factor_probability": successes / len(frame),
                    "qft_cx_per_recovered_factor": qft_total / successes,
                    "full_cx_per_recovered_factor": full_total / successes,
                    "qft_fraction_of_full_cost": qft_total / full_total,
                }
                rows.append(record)
                model_rows[label] = record

            for resource_column, prefix in (
                ("qft_canonical_cx", "qft"),
                ("full_canonical_cx", "full"),
            ):
                exact_cost = model_rows["exact"][f"{prefix}_cx_per_recovered_factor"]
                approximate_cost = model_rows["omit_one_layer"][
                    f"{prefix}_cx_per_recovered_factor"
                ]
                saving = 100.0 * (1.0 - approximate_cost / exact_cost)
                low, high = _cluster_bootstrap_cost_saving(
                    exact,
                    approximate,
                    resources[resources.M == M],
                    resource_column=resource_column,
                    rng=rng,
                )
                for record in rows[-2:]:
                    record[f"{prefix}_cost_saving_percent_vs_exact"] = (
                        0.0 if record["comparison"] == "exact" else saving
                    )
                    record[f"{prefix}_saving_cluster_bootstrap_ci95_low"] = (
                        0.0 if record["comparison"] == "exact" else low
                    )
                    record[f"{prefix}_saving_cluster_bootstrap_ci95_high"] = (
                        0.0 if record["comparison"] == "exact" else high
                    )
    return rows


def simulation_comparison_rows() -> list[dict]:
    frame = pd.read_csv(QUOTIENT_RESULTS / "per_N_rows.csv")
    frame = frame[
        (frame.method == "standard_regev_LLL_basis_endpoint")
        & (frame.sample_count == 7)
    ]
    labels = {
        "A_exact_uniform_hard_box": "exact finite uniform hard box",
        "B_exact_finite_discrete_gaussian": "exact finite discrete-Gaussian amplitude state",
        "C_theorem_consistent_noisy_dual": "synthetic noisy dual-lattice model",
        "D_circuit_derived_readout_corruption_surrogate": "hard-box plus readout/corrupt-shot surrogate",
    }
    rng = np.random.default_rng(SEED + 1)
    rows: list[dict] = []
    for model, group in frame.groupby("model"):
        per_N = group.groupby("N", as_index=False).factor_success_rate.mean()
        values = per_N.factor_success_rate.to_numpy(dtype=float)
        draws = np.asarray([
            np.mean(values[rng.integers(0, len(values), size=len(values))])
            for _ in range(BOOTSTRAPS)
        ])
        probability = float(values.mean())
        rows.append({
            "model": model,
            "plain_description": labels[model],
            "N_clusters": len(values),
            "replicates_per_N": int(group.replicates.iloc[0]),
            "dimension": 3,
            "sample_count": 7,
            "standard_LLL_macro_factor_probability": probability,
            "N_cluster_bootstrap_ci95_low": float(np.quantile(draws, 0.025)),
            "N_cluster_bootstrap_ci95_high": float(np.quantile(draws, 0.975)),
            "geometric_expected_circuit_executions": 7 / probability,
            "interpretation_scope": (
                "sampler comparison only; model C is not a circuit simulation"
            ),
        })
    return rows


def simulator_complexity_rows() -> list[dict]:
    return [
        {
            "implementation": "qft_noise.weighted_fiber_fourier_distribution",
            "models": "A/B small-state QFT certificate",
            "time_complexity": "O(F*M^(2d)) dense fiber matvecs",
            "memory_complexity": "O(M^(2d) + F*M^d)",
            "meaning": "exact finite law; bypasses explicit arithmetic-oracle matrix",
        },
        {
            "implementation": "redteam.exact_weighted_fourier_distribution",
            "models": "A/B quotient holdout",
            "time_complexity": "O(d*(2M-1)^d + M^d*log(M^d))",
            "memory_complexity": "O((2M-1)^d + M^d)",
            "meaning": "exact autocorrelation/FFT evaluator; not a statevector circuit run",
        },
        {
            "implementation": "dual.synthetic_noisy_dual_samples",
            "models": "C quotient holdout",
            "time_complexity": "O(d*H) Cayley enumeration plus exact HNF and O(m*d^3) sampling",
            "memory_complexity": "O(H*d)",
            "meaning": "factor-blind generator uses relation-lattice oracle then withholds it",
        },
        {
            "implementation": "Aer statevector on complete circuit",
            "models": "not used for held-out endpoint tables",
            "time_complexity": "exponential in Q=d*q+2n+1 in the generic case",
            "memory_complexity": "Theta(2^Q) complex amplitudes",
            "meaning": "closest listed simulator to executing every decomposed circuit gate",
        },
    ]


def make_figures(
    parameters: list[dict],
    arithmetic: list[dict],
    endpoint: list[dict],
    simulations: list[dict],
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")

    parameter_frame = pd.DataFrame(parameters)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for mode, group in parameter_frame.groupby("mode"):
        axes[0].plot(group.n, group.qubit_ratio_Q_over_n, label=mode)
        axes[1].plot(group.n, group.qft_cx_ratio_over_n_3_2, label=mode)
    axes[0].axhline(4, color="black", linestyle="--", label="limit = 4")
    axes[1].axhline(4, color="black", linestyle="--", label="limit = 4")
    axes[0].set(xlabel="input bit length n", ylabel="Q / n", title="Qubit prefactor")
    axes[1].set(
        xlabel="input bit length n",
        ylabel="QFT CX / n$^{3/2}$",
        title="Exact-QFT CX prefactor",
    )
    for axis in axes:
        axis.legend(fontsize=8)
    fig.suptitle("Ceiling effects converge to the same leading constant")
    fig.tight_layout()
    fig.savefig(OUT / "parameter_constant_convergence.png", dpi=220)
    plt.close(fig)

    arithmetic_frame = pd.DataFrame(arithmetic)
    constants = asymptotic_leading_constants()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(
        arithmetic_frame.n,
        arithmetic_frame.normalized_ccx_n3log2n,
        "o-",
        label=r"source CCX / ($n^3\log_2 n$)",
    )
    ax.plot(
        arithmetic_frame.n,
        arithmetic_frame.normalized_canonical_cx_n3log2n,
        "s-",
        label=r"canonical CX / ($n^3\log_2 n$)",
    )
    ax.axhline(80, color="C0", linestyle="--", label="proved CCX limit = 80")
    ax.axhspan(
        constants["full_canonical_cx_lower_over_n_cubed_log2_n"],
        constants["full_canonical_cx_upper_over_n_cubed_log2_n"],
        color="C1",
        alpha=0.16,
        label="proved canonical-CX limit interval 552–568",
    )
    ax.set(
        xlabel="synthetic input bit length n",
        ylabel="normalized gate count",
        title="Finite circuits have large lower-order corrections",
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "arithmetic_constant_convergence.png", dpi=220)
    plt.close(fig)

    endpoint_frame = pd.DataFrame(endpoint)
    approximate = endpoint_frame[endpoint_frame.comparison == "omit_one_layer"].copy()
    approximate["label"] = approximate.apply(
        lambda row: f"{row['model'][0]} · M={row['M']}", axis=1
    )
    x = np.arange(len(approximate))
    width = 0.36
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(
        x - width / 2,
        approximate.qft_cost_saving_percent_vs_exact,
        width,
        label="QFT-only cost saving",
    )
    ax.bar(
        x + width / 2,
        approximate.full_cost_saving_percent_vs_exact,
        width,
        label="full implemented-circuit cost saving",
    )
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x, approximate.label)
    ax.set(
        ylabel="CX per recovered factor: saving vs exact QFT (%)",
        title="A local QFT saving does not imply an end-to-end circuit saving",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "qft_only_vs_full_endpoint_cost.png", dpi=220)
    plt.close(fig)

    simulation_frame = pd.DataFrame(simulations).sort_values("model")
    values = simulation_frame.standard_LLL_macro_factor_probability.to_numpy()
    low = values - simulation_frame.N_cluster_bootstrap_ci95_low.to_numpy()
    high = simulation_frame.N_cluster_bootstrap_ci95_high.to_numpy() - values
    labels = [value.split("_")[0] for value in simulation_frame.model]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(labels, values, yerr=np.vstack([low, high]), capsize=4)
    ax.set_ylim(0, 1.05)
    ax.set(
        xlabel="sampling model",
        ylabel="factor-recovery probability",
        title="Same LLL endpoint, different finite sampling models (m=7)",
    )
    fig.tight_layout()
    fig.savefig(OUT / "simulation_model_comparison.png", dpi=220)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    parameters = parameter_rows()
    arithmetic = arithmetic_scaling_rows()
    finite = finite_full_resource_rows()
    endpoint = qft_endpoint_cost_rows(finite)
    simulations = simulation_comparison_rows()
    simulator_complexity = simulator_complexity_rows()

    tables = {
        "parameter_scaling.csv": parameters,
        "synthetic_arithmetic_scaling.csv": arithmetic,
        "finite_full_circuit_resources.csv": finite,
        "qft_endpoint_cost.csv": endpoint,
        "simulation_model_comparison.csv": simulations,
        "simulator_complexity.csv": simulator_complexity,
    }
    for filename, rows in tables.items():
        write_csv(OUT / filename, rows)
    make_figures(parameters, arithmetic, endpoint, simulations)

    endpoint_frame = pd.DataFrame(endpoint)
    approximate = endpoint_frame[endpoint_frame.comparison == "omit_one_layer"]
    finite_frame = pd.DataFrame(finite)
    simulation_frame = pd.DataFrame(simulations).set_index("model")
    summary = {
        "freeze_version": "week-8-complexity-v1",
        "scope": (
            "exact source audit plus secondary analysis of already-frozen held-out trials"
        ),
        "random_seed": SEED,
        "cluster_bootstraps": BOOTSTRAPS,
        "asymptotic_constants": asymptotic_leading_constants(),
        "finite_resource_finding": {
            "maximum_exact_qft_fraction_of_full_canonical_cx": float(
                finite_frame[finite_frame.omitted_layers == 0]
                .qft_fraction_of_full_canonical_cx.max()
            ),
            "minimum_one_layer_qft_only_cost_saving_percent": float(
                approximate.qft_cost_saving_percent_vs_exact.min()
            ),
            "maximum_one_layer_qft_only_cost_saving_percent": float(
                approximate.qft_cost_saving_percent_vs_exact.max()
            ),
            "full_cost_saving_percent_by_cell": [
                {
                    "M": int(row.M),
                    "model": row.model,
                    "saving_percent": float(row.full_cost_saving_percent_vs_exact),
                    "cluster_ci95": [
                        float(row.full_saving_cluster_bootstrap_ci95_low),
                        float(row.full_saving_cluster_bootstrap_ci95_high),
                    ],
                }
                for row in approximate.itertuples()
            ],
        },
        "standard_LLL_model_probabilities": {
            model: float(row.standard_LLL_macro_factor_probability)
            for model, row in simulation_frame.iterrows()
        },
        "limitations": [
            "canonical CX assumes all-to-all connectivity and exact Qiskit primitive decompositions",
            "no routing, rotation synthesis, error correction, or physical error model is included",
            "A/B/C are different data generators; C is not a circuit simulation",
            "endpoint cost uses eight frozen small semiprimes and 64 trials per cell",
            "cost intervals resample N clusters but do not remove finite Monte Carlo uncertainty within N",
        ],
        "input_hashes": {
            "qft_trial_rows.csv": sha256(QFT_RESULTS / "trial_rows.csv"),
            "quotient_per_N_rows.csv": sha256(QUOTIENT_RESULTS / "per_N_rows.csv"),
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    generated = sorted(path for path in OUT.iterdir() if path.name != "completion.json")
    completion = {
        "status": "complete",
        "freeze_version": "week-8-complexity-v1",
        "files": {path.name: sha256(path) for path in generated},
    }
    (OUT / "completion.json").write_text(
        json.dumps(completion, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

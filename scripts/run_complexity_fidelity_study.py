#!/usr/bin/env python3
"""Reproduce the matched Shor/Regev complexity-fidelity audit.

This is a static circuit analysis plus deterministic synthetic scaling sweep.
It never factors the synthetic integers and never fits the asymptotic class
from wall-clock timings.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from regev_research.resource_analysis import (  # noqa: E402
    canonical_cx_count,
    complexity_fidelity_certificate,
    first_coprime_prime_square_bases,
    full_circuit_source_counts,
    notebook_parameters,
    qft_closed_form,
    shor_full_circuit_source_counts,
)


OUT = ROOT / "all_graphics_and_results" / "results" / "complexity_fidelity"
EXACT_BITS = (4, 6, 8, 12, 16, 24, 32, 48, 64)
FORMULA_BITS = tuple(range(4, 1025))
SIMULATION_TABLE = (
    ROOT
    / "all_graphics_and_results"
    / "results"
    / "week_8_complexity"
    / "simulation_model_comparison.csv"
)
SOURCE_FILES = (
    ROOT / "external/regev-quantum-algorithm/implementations/shor.py",
    ROOT / "external/regev-quantum-algorithm/gates/haner/modular_exponentiation.py",
    ROOT / "external/regev-quantum-algorithm/gates/r_haner/modular_exponentiation.py",
    ROOT / "external/regev-quantum-algorithm/gates/haner/constant_modulo_multiplier.py",
    ROOT / "external/regev-quantum-algorithm/gates/r_haner/constant_modulo_multiplier.py",
    ROOT / "external/regev-quantum-algorithm/gates/haner/constant_modulo_adder.py",
    ROOT / "external/regev-quantum-algorithm/gates/haner/constant_adder.py",
)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table {path}")
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_resource_rows() -> list[dict]:
    rows: list[dict] = []
    for n in EXACT_BITS:
        # Only the bit length and modular constants are used.  No factors or
        # factoring outcomes are computed for these deterministic probes.
        N = (1 << (n - 1)) + 1
        parameters = notebook_parameters(n, "cover_2n")
        d, q = int(parameters["d"]), int(parameters["q"])
        regev_bases = first_coprime_prime_square_bases(N, d)
        shor_base = regev_bases[0]
        regev = full_circuit_source_counts(N, regev_bases, q)
        shor = shor_full_circuit_source_counts(N, shor_base)
        regev_qft = qft_closed_form(d, q)["canonical_cx"]
        shor_qft = qft_closed_form(1, 2 * n)["canonical_cx"]
        regev_cx = canonical_cx_count(regev)
        shor_cx = canonical_cx_count(shor)
        runs = d + 4
        rows.append({
            "n": n,
            "N_resource_probe": N,
            "synthetic_rule": "N=2^(n-1)+1; factorization never computed",
            "d": d,
            "q": q,
            "regev_bases": " ".join(str(value) for value in regev_bases),
            "shor_base": shor_base,
            "regev_qubits": int(parameters["total_qubits"]),
            "shor_qubits": 4 * n + 1,
            "regev_multiplier_invocations": d * q,
            "shor_multiplier_invocations": 2 * n,
            "regev_source_ccx": regev["ccx"],
            "shor_source_ccx": shor["ccx"],
            "regev_canonical_cx": regev_cx,
            "shor_canonical_cx": shor_cx,
            "regev_qft_canonical_cx": regev_qft,
            "shor_qft_canonical_cx": shor_qft,
            "regev_qft_fraction": regev_qft / regev_cx,
            "shor_qft_fraction": shor_qft / shor_cx,
            "per_run_source_ccx_ratio_regev_over_shor": (
                regev["ccx"] / shor["ccx"]
            ),
            "per_run_cx_ratio_regev_over_shor": regev_cx / shor_cx,
            "regev_runs_reference": runs,
            "run_adjusted_cx_ratio_vs_one_shor_run": runs * regev_cx / shor_cx,
            "normalization_warning": (
                "run-adjusted ratio uses one Shor circuit as a reference; it is not "
                "an expected-time factoring claim"
            ),
        })
    return rows


def formula_rows() -> list[dict]:
    return [complexity_fidelity_certificate(n) for n in FORMULA_BITS]


def architecture_ablation_rows() -> list[dict]:
    rows: list[dict] = []
    for n in (16, 64, 256, 1024):
        certificate = complexity_fidelity_certificate(n)
        d, q = int(certificate["d"]), int(certificate["q"])
        exact_qft = int(certificate["regev_qft_canonical_cx"])
        omit_one = qft_closed_form(d, q, q - 2)["canonical_cx"]
        for name, invocations, qft_cx, executable, interpretation in (
            (
                "notebook_exact_QFT",
                d * q,
                exact_qft,
                True,
                "implemented baseline",
            ),
            (
                "notebook_omit_one_QFT_layer",
                d * q,
                omit_one,
                True,
                "QFT-only intervention; arithmetic is unchanged",
            ),
            (
                "notebook_no_QFT_counterfactual",
                d * q,
                0,
                False,
                "removes every QFT gate; arithmetic barrier remains",
            ),
            (
                "sqrt_n_invocation_counterfactual",
                6 * d,
                exact_qft,
                False,
                "abstract call-count ablation; not an implemented replacement",
            ),
            (
                "supplied_ShOR",
                2 * n,
                int(certificate["shor_qft_canonical_cx"]),
                True,
                "matched binary arithmetic comparator",
            ),
        ):
            rows.append({
                "n": n,
                "scenario": name,
                "controlled_multiplier_invocations": invocations,
                "invocations_over_n": invocations / n,
                "qft_canonical_cx": qft_cx,
                "executable_in_repository": executable,
                "interpretation": interpretation,
            })
    return rows


def published_claim_audit_rows() -> list[dict]:
    rows: list[dict] = []
    for n in FORMULA_BITS:
        parameters = notebook_parameters(n)
        d, q = int(parameters["d"]), int(parameters["q"])
        paper_abstract_additions = 2 * d * q * q
        code_additions = 2 * d * q * n
        rows.append({
            "n": n,
            "d": d,
            "q": q,
            "paper_derivation_modular_addition_factor": paper_abstract_additions,
            "executed_code_modular_addition_factor": code_additions,
            "missing_factor_code_over_paper": code_additions / paper_abstract_additions,
            "paper_reported_implementation_class": "O(n^(5/2) log n)",
            "source_verified_implementation_class": "Theta(n^3 log n)",
            "cause": (
                "each constant modular multiplier loops over n result bits, "
                "not q exponent-register bits"
            ),
        })
    return rows


def make_figures(
    exact: list[dict], formulas: list[dict], audit: list[dict]
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    exact_frame = pd.DataFrame(exact)
    formula_frame = pd.DataFrame(formulas)
    audit_frame = pd.DataFrame(audit)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    axes[0].plot(
        exact_frame.n,
        exact_frame.per_run_cx_ratio_regev_over_shor,
        "o-",
        color="#1769aa",
        label="canonical CX",
    )
    axes[0].plot(
        exact_frame.n,
        exact_frame.per_run_source_ccx_ratio_regev_over_shor,
        "s--",
        color="#6a3d9a",
        label="source CCX",
    )
    axes[0].axhline(1.0, color="black", linestyle="--", linewidth=1)
    axes[0].set(
        xlabel="input bit length n",
        ylabel="Regev / Shor canonical CX",
        title="Per run: exact finite costs remain close",
    )
    axes[0].legend()
    axes[1].plot(
        exact_frame.n,
        exact_frame.run_adjusted_cx_ratio_vs_one_shor_run,
        "o-",
        color="#d95f02",
    )
    axes[1].set(
        xlabel="input bit length n",
        ylabel="(d+4) Regev runs / one Shor run",
        title="Required Regev samples multiply the cost",
    )
    fig.suptitle("Matched arithmetic removes the claimed asymptotic separation")
    fig.tight_layout()
    fig.savefig(OUT / "matched_shor_regev_cost.png", dpi=240)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.3, 4.9))
    ax.loglog(
        formula_frame.n,
        formula_frame.qft_ratio_regev_over_shor,
        color="#6a3d9a",
        label="product-QFT CX ratio",
    )
    ax.loglog(
        formula_frame.n,
        formula_frame.per_run_invocation_ratio_regev_over_shor,
        color="#1b9e77",
        label="arithmetic-invocation ratio",
    )
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1)
    ax.set(
        xlabel="input bit length n",
        ylabel="Regev / Shor ratio",
        title="A smaller QFT does not imply a smaller full circuit",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "qft_vs_arithmetic_ratio.png", dpi=240)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.3, 4.9))
    ax.plot(
        audit_frame.n,
        audit_frame.missing_factor_code_over_paper,
        color="#c62828",
    )
    ax.plot(
        audit_frame.n,
        np.sqrt(audit_frame.n) / 2,
        linestyle="--",
        color="black",
        label=r"asymptotic $\sqrt{n}/2$",
    )
    ax.set(
        xlabel="input bit length n",
        ylabel="executed / paper-counted modular additions",
        title="The omitted loop factor grows with problem size",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "published_complexity_gap.png", dpi=240)
    plt.close(fig)

    simulations = pd.read_csv(SIMULATION_TABLE)
    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    labels = ["A\nhard box", "B\nfinite Gaussian", "C\nnoisy dual", "D\nreadout surrogate"]
    probabilities = 100 * simulations.standard_LLL_macro_factor_probability.to_numpy()
    low = 100 * simulations.N_cluster_bootstrap_ci95_low.to_numpy()
    high = 100 * simulations.N_cluster_bootstrap_ci95_high.to_numpy()
    order = [int(str(model)[0] == "B") + 2 * int(str(model)[0] == "C") + 3 * int(str(model)[0] == "D") for model in simulations.model]
    sorted_indices = np.argsort(order)
    probabilities, low, high = (
        probabilities[sorted_indices], low[sorted_indices], high[sorted_indices]
    )
    positions = np.arange(4)
    ax.bar(positions, probabilities, color=("#4c78a8", "#72b7b2", "#f58518", "#e45756"))
    ax.errorbar(
        positions,
        probabilities,
        yerr=np.vstack((probabilities - low, high - probabilities)),
        fmt="none",
        color="black",
        capsize=4,
    )
    ax.set(
        xticks=positions,
        xticklabels=labels,
        ylabel="factor recovery across held-out N (%)",
        title="Simulation models are not interchangeable",
        ylim=(0, 108),
    )
    ax.text(
        0.01,
        0.98,
        "C is a theorem-input generator, not a circuit simulation",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(OUT / "simulation_model_scope.png", dpi=240)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    exact = exact_resource_rows()
    formulas = formula_rows()
    ablations = architecture_ablation_rows()
    audit = published_claim_audit_rows()
    write_csv(OUT / "matched_exact_resources.csv", exact)
    write_csv(OUT / "asymptotic_certificate_rows.csv", formulas)
    write_csv(OUT / "architecture_ablations.csv", ablations)
    write_csv(OUT / "published_claim_audit.csv", audit)
    make_figures(exact, formulas, audit)

    source_hashes = {
        str(path.relative_to(ROOT)): sha256(path) for path in SOURCE_FILES
    }
    simulation_hash = sha256(SIMULATION_TABLE)
    last_exact = exact[-1]
    summary = {
        "freeze_identifier": "complexity-fidelity-v1",
        "analysis_type": "static source audit plus deterministic synthetic scaling",
        "synthetic_bit_lengths": list(EXACT_BITS),
        "formula_range": [FORMULA_BITS[0], FORMULA_BITS[-1]],
        "factorization_of_synthetic_inputs_computed": False,
        "source_hashes": source_hashes,
        "simulation_table_sha256": simulation_hash,
        "verified_correction": {
            "paper_reported_class": "O(n^(5/2) log n)",
            "source_verified_class": "Theta(n^3 log2(n))",
            "source_ccx_leading_constant": 80,
            "canonical_cx_leading_interval": [552, 568],
            "cause": (
                "the published derivation substitutes q for the n result bits "
                "iterated by every constant modular multiplier"
            ),
        },
        "matched_comparison": {
            "shor_controlled_multiplier_invocations": "2n",
            "regev_controlled_multiplier_invocations": "dq=2n+O(sqrt(n))",
            "shor_qft_canonical_cx": "4n^2+n",
            "regev_qft_canonical_cx": "4n^(3/2)+O(n)",
            "proved_per_run_limit": "source-CCX ratio Regev/Shor -> 1",
            "canonical_cx_boundary": (
                "data-dependent source-CX terms give each circuit the same "
                "leading interval [552,568]; an exact canonical-CX ratio limit "
                "is not claimed"
            ),
            "largest_exact_probe_n": int(last_exact["n"]),
            "largest_exact_probe_per_run_cx_ratio": float(
                last_exact["per_run_cx_ratio_regev_over_shor"]
            ),
        },
        "simulation_comparison": {
            "models": ["A hard box", "B finite Gaussian", "C noisy dual", "D readout surrogate"],
            "warning": "model C is not a circuit simulation",
        },
        "claim_boundary": (
            "This corrects and characterizes the supplied implementation. It is "
            "not a lower bound on Regev factoring and not a hardware estimate."
        ),
    }
    (OUT / "complexity_fidelity_certificate.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    produced = sorted(
        path.name for path in OUT.iterdir() if path.name != "completion.json"
    )
    completion = {
        "freeze_identifier": "complexity-fidelity-v1",
        "status": "complete",
        "outputs": produced,
        "output_sha256": {name: sha256(OUT / name) for name in produced},
    }
    (OUT / "completion.json").write_text(
        json.dumps(completion, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

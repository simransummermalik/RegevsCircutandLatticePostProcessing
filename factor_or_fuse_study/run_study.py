"""Execute the frozen Factor-or-Fuse study and generate every reported result."""

from __future__ import annotations

import csv
import hashlib
import importlib
import inspect
import json
import math
import platform
import sys
import tracemalloc
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import qiskit


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from factor_or_fuse_study.freeze import (  # noqa: E402
    ADVERSARIAL_RANDOM_VECTORS,
    ARMS,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    EQUIVALENCE_SEED,
    EXACT_PARTITION_LIMIT,
    HELDOUT_MODULI,
    MAX_POWER,
    PROTOCOL_ID,
    PUBLISHED_BENCHMARKS,
    method_input_from_modulus,
    validate_freeze,
)
from regev_research.core import RootedBaseFamily, modular_product  # noqa: E402
from regev_research.orbit_fusion import (  # noqa: E402
    FactorOrFuseResult,
    OrbitFusionPlan,
    detect_pair_power_relations,
    factor_or_fuse,
    plan_power_orbit_fusion,
)


STUDY_DIR = Path(__file__).resolve().parent
RESULTS_DIR = STUDY_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
EXPECTED_HASHES = {
    "factor_or_fuse_study/freeze.py": "e562492116e4abd491c51dd3380780e9571df917ae8f7a210d00b202957e5eab",
    "factor_or_fuse_study/PROTOCOL.md": "3fcb2feef0c451a1b0909d759d88f67bf6452b28fee98cd2802c14a37558739b",
    "factor_or_fuse_study/factor_manifest.py": "282800c710400036071b759d4c2d09e7d6b364576b3b0717a2c9fbf4cad97fe2",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_protocol_hashes() -> dict[str, str]:
    observed = {name: _sha256(ROOT / name) for name in EXPECTED_HASHES}
    if observed != EXPECTED_HASHES:
        raise RuntimeError("frozen protocol hash mismatch; held-out execution aborted")
    return observed


def _serial_plan(family: RootedBaseFamily, exponent_width: int) -> OrbitFusionPlan:
    return plan_power_orbit_fusion(
        family.N,
        family.bases,
        exponent_width,
        max_power=MAX_POWER,
        exact_partition_limit=EXACT_PARTITION_LIMIT,
        allowed_relations={},
    )


def _factor_from_relations(relations):
    return next(
        (
            row.classification.factor_pair
            for row in relations
            if row.classification.category == "factor_yielding"
        ),
        None,
    )


def _plan_full_width_calls(plan: OrbitFusionPlan) -> int:
    return sum(
        group.accumulator_width if group.fused else plan.exponent_width
        for group in plan.groups
    )


def _evaluate_selected_oracle(plan: OrbitFusionPlan, exponents: Iterable[int]) -> int:
    values = tuple(int(value) for value in exponents)
    result = 1
    for group in plan.groups:
        if group.fused:
            combined = sum(
                weight * values[index]
                for index, weight in zip(
                    group.member_indices, group.weights, strict=True
                )
            )
            factor = pow(plan.bases[group.anchor_index], combined, plan.N)
        else:
            index = group.member_indices[0]
            factor = pow(plan.bases[index], values[index], plan.N)
        result = result * factor % plan.N
    return result


def _equivalence_certificate(plan: OrbitFusionPlan, seed: int) -> tuple[bool, int]:
    q = plan.exponent_width
    maximum = (1 << q) - 1
    vectors: list[tuple[int, ...]] = [
        (0,) * plan.dimension,
        (maximum,) * plan.dimension,
    ]
    for index in range(plan.dimension):
        for bit in range(q):
            vector = [0] * plan.dimension
            vector[index] = 1 << bit
            vectors.append(tuple(vector))
    rng = np.random.default_rng(seed)
    vectors.extend(
        tuple(int(value) for value in row)
        for row in rng.integers(
            0,
            1 << q,
            size=(ADVERSARIAL_RANDOM_VECTORS, plan.dimension),
        )
    )
    for vector in vectors:
        direct = modular_product(plan.N, plan.bases, vector)
        if direct != _evaluate_selected_oracle(plan, vector):
            return False, len(vectors)
    return True, len(vectors)


def _execute_arm(method_input, arm: str) -> dict[str, object]:
    if method_input.setup_factor is not None:
        return {
            "outcome": "setup_factor",
            "factor_pair": method_input.setup_factor,
            "relations": (),
            "plan": None,
        }
    family = method_input.family
    if family is None:
        raise AssertionError("missing rooted family without a setup factor")
    serial = _serial_plan(family, method_input.exponent_width)

    if arm == "serial_baseline":
        return {"outcome": "baseline", "factor_pair": None, "relations": (), "plan": serial}
    if arm == "factor_only_K64":
        relations = detect_pair_power_relations(family, max_power=MAX_POWER)
        factor_pair = _factor_from_relations(relations)
        return {
            "outcome": "classical_factor" if factor_pair else "baseline",
            "factor_pair": factor_pair,
            "relations": relations,
            "plan": None if factor_pair else serial,
        }
    if arm == "duplicate_fusion_only":
        plan = plan_power_orbit_fusion(
            family.N,
            family.bases,
            method_input.exponent_width,
            max_power=1,
            exact_partition_limit=EXACT_PARTITION_LIMIT,
        )
        return {
            "outcome": "fused" if plan.canonical_cx_saved > 0 else "baseline",
            "factor_pair": None,
            "relations": (),
            "plan": plan,
        }
    if arm == "orbit_fusion_only_K64":
        plan = plan_power_orbit_fusion(
            family.N,
            family.bases,
            method_input.exponent_width,
            max_power=MAX_POWER,
            exact_partition_limit=EXACT_PARTITION_LIMIT,
        )
        return {
            "outcome": "fused" if plan.canonical_cx_saved > 0 else "baseline",
            "factor_pair": None,
            "relations": (),
            "plan": plan,
        }
    if arm in (
        "greedy_factor_or_fuse_K64",
        "complete_cost_optimal_factor_or_fuse_K64",
    ):
        limit = 1 if arm.startswith("greedy") else EXACT_PARTITION_LIMIT
        result: FactorOrFuseResult = factor_or_fuse(
            family,
            method_input.exponent_width,
            max_power=MAX_POWER,
            exact_partition_limit=limit,
        )
        outcome = {
            "classical_factor": "classical_factor",
            "l0_orbit_fusion": "fused",
            "baseline_fallback": "baseline",
        }[result.outcome]
        return {
            "outcome": outcome,
            "factor_pair": result.factor_pair,
            "relations": result.relations,
            "plan": result.plan,
            "factor_or_fuse_verified": result.verify(),
        }
    raise ValueError(f"unknown arm: {arm}")


def run_method_on_modulus(N: int, arm: str) -> dict[str, object]:
    """Method-side worker: its complete instance input is exactly ``N, arm``."""

    method_input = method_input_from_modulus(N)
    tracemalloc.start()
    started = perf_counter()
    execution = _execute_arm(method_input, arm)
    runtime = perf_counter() - started
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    family = method_input.family
    if family is None:
        baseline_cx = selected_cx = 0
        baseline_calls = selected_calls = 0
        source = Counter()
        extra_qubits = maximum_accumulator = 0
        plan_verified = True
        equivalence_passed, equivalence_checks = True, 0
        roots = bases = ()
    else:
        serial = _serial_plan(family, method_input.exponent_width)
        baseline_cx = serial.baseline_canonical_cx
        baseline_calls = family.pairs.__len__() * method_input.exponent_width
        plan = execution["plan"]
        if plan is None:
            selected_cx = 0
            selected_calls = 0
            source = Counter()
            extra_qubits = maximum_accumulator = 0
            plan_verified = True
            equivalence_passed, equivalence_checks = True, 0
        else:
            selected_cx = plan.selected_canonical_cx
            selected_calls = _plan_full_width_calls(plan)
            source = plan.selected_arithmetic_counts
            extra_qubits = plan.extra_qubits
            maximum_accumulator = plan.max_accumulator_width
            plan_verified = plan.verify()
            equivalence_passed, equivalence_checks = _equivalence_certificate(
                plan, EQUIVALENCE_SEED + N
            )
        roots, bases = family.roots, family.bases

    factor_pair = execution["factor_pair"]
    factor_valid_without_manifest = bool(
        factor_pair
        and factor_pair[0] > 1
        and factor_pair[1] > 1
        and factor_pair[0] * factor_pair[1] == N
    )
    relations = execution["relations"]
    relation_rows = [
        {
            "anchor": row.anchor_index,
            "target": row.target_index,
            "power": row.power,
            "vector": list(row.classification.vector),
            "root_product": row.classification.root_product,
            "category": row.classification.category,
            "factor_pair": list(row.classification.factor_pair)
            if row.classification.factor_pair
            else None,
        }
        for row in relations
    ]
    outcome = str(execution["outcome"])
    certificate_passed = bool(
        plan_verified
        and equivalence_passed
        and (outcome not in ("classical_factor", "setup_factor") or factor_valid_without_manifest)
        and execution.get("factor_or_fuse_verified", True)
    )
    saving_fraction = (
        (baseline_cx - selected_cx) / baseline_cx if baseline_cx else 0.0
    )
    return {
        "protocol_id": PROTOCOL_ID,
        "N": N,
        "n": method_input.n,
        "dimension": method_input.dimension,
        "exponent_width": method_input.exponent_width,
        "arm": arm,
        "roots": json.dumps(list(roots)),
        "bases": json.dumps(list(bases)),
        "max_power": MAX_POWER,
        "outcome": outcome,
        "actionable": outcome in ("classical_factor", "setup_factor", "fused"),
        "quantum_oracle_required": outcome not in ("classical_factor", "setup_factor"),
        "factor_pair": json.dumps(list(factor_pair)) if factor_pair else "",
        "factor_valid_without_manifest": factor_valid_without_manifest,
        "relation_count": len(relation_rows),
        "l0_relation_count": sum(row["category"] == "L0" for row in relation_rows),
        "factor_relation_count": sum(
            row["category"] == "factor_yielding" for row in relation_rows
        ),
        "relations": json.dumps(relation_rows, sort_keys=True),
        "public_power_steps": (
            method_input.dimension * MAX_POWER
            if arm in (
                "factor_only_K64",
                "orbit_fusion_only_K64",
                "greedy_factor_or_fuse_K64",
                "complete_cost_optimal_factor_or_fuse_K64",
            )
            else method_input.dimension * (1 if arm == "duplicate_fusion_only" else 0)
        ),
        "pair_lookup_count": (
            method_input.dimension * (method_input.dimension - 1)
            if arm != "serial_baseline"
            else 0
        ),
        "gcd_classification_calls": 2 * len(relation_rows),
        "baseline_canonical_cx": baseline_cx,
        "selected_canonical_cx": selected_cx,
        "canonical_cx_saved": baseline_cx - selected_cx,
        "canonical_cx_saving_fraction": saving_fraction,
        "baseline_full_width_multiplier_calls": baseline_calls,
        "selected_full_width_multiplier_calls": selected_calls,
        "full_width_multiplier_calls_saved": baseline_calls - selected_calls,
        "selected_source_x": source["x"],
        "selected_source_cx": source["cx"],
        "selected_source_ccx": source["ccx"],
        "selected_source_cswap": source["cswap"],
        "extra_qubits": extra_qubits,
        "max_accumulator_width": maximum_accumulator,
        "plan_verified": plan_verified,
        "equivalence_passed": equivalence_passed,
        "equivalence_checks": equivalence_checks,
        "certificate_passed": certificate_passed,
        "runtime_seconds": runtime,
        "peak_memory_bytes": peak_memory,
        "factor_information_used": False,
        "group_order_used": False,
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    probability = successes / total
    denominator = 1 + z * z / total
    center = (probability + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(
        probability * (1 - probability) / total + z * z / (4 * total * total)
    ) / denominator
    return center - radius, center + radius


def _bootstrap_mean_interval(values: list[float], seed: int) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(BOOTSTRAP_RESAMPLES, len(array)))
    means = array[indices].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def _arm_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries = []
    for arm in ARMS:
        selected = [row for row in rows if row["arm"] == arm]
        actionable = sum(bool(row["actionable"]) for row in selected)
        savings = [float(row["canonical_cx_saving_fraction"]) for row in selected]
        low, high = _wilson(actionable, len(selected))
        boot_low, boot_high = _bootstrap_mean_interval(
            savings, BOOTSTRAP_SEED + ARMS.index(arm)
        )
        summaries.append(
            {
                "arm": arm,
                "N_count": len(selected),
                "factor_count": sum(
                    row["outcome"] in ("classical_factor", "setup_factor")
                    for row in selected
                ),
                "fused_count": sum(row["outcome"] == "fused" for row in selected),
                "fallback_count": sum(row["outcome"] == "baseline" for row in selected),
                "actionable_count": actionable,
                "actionable_fraction": actionable / len(selected),
                "actionable_wilson_low": low,
                "actionable_wilson_high": high,
                "mean_quantum_cx_saving_fraction": float(np.mean(savings)),
                "median_quantum_cx_saving_fraction": float(np.median(savings)),
                "mean_saving_bootstrap_low": boot_low,
                "mean_saving_bootstrap_high": boot_high,
                "mean_runtime_seconds": float(
                    np.mean([float(row["runtime_seconds"]) for row in selected])
                ),
                "all_certificates_passed": all(
                    bool(row["certificate_passed"]) for row in selected
                ),
            }
        )
    return summaries


def _published_benchmark_rows() -> list[dict[str, object]]:
    rows = []
    for label, N, roots, exponent_width in PUBLISHED_BENCHMARKS:
        family = RootedBaseFamily.from_roots(N, roots)
        result = factor_or_fuse(
            family,
            exponent_width,
            max_power=MAX_POWER,
            exact_partition_limit=EXACT_PARTITION_LIMIT,
        )
        minimum_factor_norm_squared = min(
            (
                sum(value * value for value in row.classification.vector)
                for row in result.relations
                if row.classification.category == "factor_yielding"
            ),
            default=None,
        )
        rows.append(
            {
                "label": label,
                "N": N,
                "roots": json.dumps(list(roots)),
                "bases_as_integers": json.dumps([root * root for root in roots]),
                "bases_mod_N": json.dumps(list(family.bases)),
                "nominal_dimension": len(roots),
                "distinct_base_residues": len(set(family.bases)),
                "outcome": result.outcome,
                "factor_pair": json.dumps(list(result.factor_pair))
                if result.factor_pair
                else "",
                "minimum_factor_relation_norm_squared": minimum_factor_norm_squared,
                "relation_count": len(result.relations),
                "verified": result.verify(),
                "factor_information_used": False,
            }
        )
    return rows


def _plot_results(
    rows: list[dict[str, object]],
    arm_summaries: list[dict[str, object]],
    published: list[dict[str, object]],
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    labels = [
        "Serial",
        "Factor only",
        "Duplicates",
        "Orbit fusion",
        "Greedy F-or-F",
        "Complete F-or-F",
    ]
    factors = [int(row["factor_count"]) for row in arm_summaries]
    fused = [int(row["fused_count"]) for row in arm_summaries]
    fallback = [int(row["fallback_count"]) for row in arm_summaries]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.bar(x, factors, label="factor before circuit", color="#0072B2")
    ax.bar(x, fused, bottom=factors, label="strict circuit fusion", color="#009E73")
    ax.bar(
        x,
        fallback,
        bottom=np.asarray(factors) + np.asarray(fused),
        label="exact baseline fallback",
        color="#B8BCC2",
    )
    ax.set_xticks(x, labels, rotation=20, ha="right")
    ax.set_ylabel("Held-out moduli (N is the unit)")
    ax.set_title("What each pre-circuit method did on 24 frozen semiprimes")
    ax.legend(frameon=False, ncol=3, loc="upper center")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "01_heldout_outcomes.png", dpi=220)
    plt.close(fig)

    means = [100 * float(row["mean_quantum_cx_saving_fraction"]) for row in arm_summaries]
    lows = [100 * float(row["mean_saving_bootstrap_low"]) for row in arm_summaries]
    highs = [100 * float(row["mean_saving_bootstrap_high"]) for row in arm_summaries]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    errors = np.asarray([np.asarray(means) - np.asarray(lows), np.asarray(highs) - np.asarray(means)])
    ax.bar(x, means, color="#56B4E9")
    ax.errorbar(x, means, yerr=errors, fmt="none", color="black", capsize=4)
    ax.set_xticks(x, labels, rotation=20, ha="right")
    ax.set_ylabel("Mean quantum arithmetic CX saved (%)")
    ax.set_title("Matched resource result with 95% modulus-level bootstrap intervals")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "02_mean_quantum_cx_savings.png", dpi=220)
    plt.close(fig)

    complete = [
        row
        for row in rows
        if row["arm"] == "complete_cost_optimal_factor_or_fuse_K64"
    ]
    colors = {
        "classical_factor": "#0072B2",
        "setup_factor": "#0072B2",
        "fused": "#009E73",
        "baseline": "#999999",
    }
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(
        [str(row["N"]) for row in complete],
        [100 * float(row["canonical_cx_saving_fraction"]) for row in complete],
        color=[colors[str(row["outcome"])] for row in complete],
    )
    ax.set_ylabel("Quantum arithmetic CX saved (%)")
    ax.set_xlabel("Frozen held-out semiprime N")
    ax.set_title("Complete Factor-or-Fuse: every held-out modulus")
    ax.tick_params(axis="x", rotation=70)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "03_complete_per_modulus.png", dpi=220)
    plt.close(fig)

    relation_complete = [row for row in complete if int(row["relation_count"]) > 0]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    if relation_complete:
        minimum_powers = []
        for row in relation_complete:
            relations = json.loads(str(row["relations"]))
            minimum_powers.append(min(int(item["power"]) for item in relations))
        ax.scatter(
            [int(row["N"]) for row in relation_complete],
            minimum_powers,
            c=[colors[str(row["outcome"])] for row in relation_complete],
            s=65,
        )
        ax.set_ylabel("Smallest detected exponent k")
    else:
        ax.text(
            0.5,
            0.5,
            "No bounded power relation was detected",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=16,
        )
        ax.set_yticks([])
    ax.set_xlabel("Frozen held-out semiprime N")
    ax.set_title(f"Bounded dependency scan (K = {MAX_POWER})")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "04_detected_relation_exponents.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    benchmark_labels = [str(row["label"]).replace("_", " ") for row in published]
    nominal = [int(row["nominal_dimension"]) for row in published]
    effective = [int(row["distinct_base_residues"]) for row in published]
    xp = np.arange(len(published))
    width = 0.35
    ax.bar(xp - width / 2, nominal, width, label="nominal base count", color="#CC79A7")
    ax.bar(xp + width / 2, effective, width, label="distinct base residues", color="#E69F00")
    for index, row in enumerate(published):
        if row["factor_pair"]:
            ax.text(
                index,
                max(nominal[index], effective[index]) + 0.12,
                f"pre-circuit factor {row['factor_pair']}",
                ha="center",
                fontsize=8,
            )
    ax.set_xticks(xp, benchmark_labels, rotation=18, ha="right")
    ax.set_ylabel("Dimensions / distinct residues")
    ax.set_title("Published toy inputs: nominal dimension can hide arithmetic collapse")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "05_published_benchmark_rank_audit.png", dpi=220)
    plt.close(fig)


def main() -> None:
    if not validate_freeze():
        raise RuntimeError("invalid frozen modulus rule")
    hashes = verify_protocol_hashes()
    # The signature check makes the factor firewall machine-auditable.
    if tuple(inspect.signature(run_method_on_modulus).parameters) != ("N", "arm"):
        raise RuntimeError("method worker accepts undeclared inputs")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    raw_rows = [
        run_method_on_modulus(N, arm)
        for N in HELDOUT_MODULI
        for arm in ARMS
    ]
    raw_payload = json.dumps(raw_rows, indent=2, sort_keys=True)
    raw_path = RESULTS_DIR / "raw_method_rows.json"
    raw_path.write_text(raw_payload + "\n", encoding="utf-8")
    raw_hash = _sha256(raw_path)

    # Only after method outputs are serialized and hashed may this module load.
    manifest_module = importlib.import_module("factor_or_fuse_study.factor_manifest")
    manifest = manifest_module.POSTHOC_FACTOR_MANIFEST
    if set(manifest) != set(HELDOUT_MODULI):
        raise RuntimeError("post-hoc manifest does not match the frozen moduli")
    audited_rows = []
    for row in raw_rows:
        expected = tuple(manifest[int(row["N"])])
        reported = tuple(json.loads(str(row["factor_pair"]))) if row["factor_pair"] else None
        enriched = dict(row)
        enriched["posthoc_expected_factor_pair"] = json.dumps(list(expected))
        enriched["posthoc_factor_match"] = reported is None or tuple(sorted(reported)) == expected
        audited_rows.append(enriched)
    _write_csv(RESULTS_DIR / "heldout_per_arm.csv", audited_rows)

    summaries = _arm_summary(audited_rows)
    _write_csv(RESULTS_DIR / "heldout_arm_summary.csv", summaries)
    complete = next(
        row
        for row in summaries
        if row["arm"] == "complete_cost_optimal_factor_or_fuse_K64"
    )
    thresholds = {
        "minimum_actionable_count": 6,
        "positive_bootstrap_lower_bound_required": True,
    }
    hypothesis_passed = bool(
        int(complete["actionable_count"]) >= thresholds["minimum_actionable_count"]
        and float(complete["mean_saving_bootstrap_low"]) > 0
        and bool(complete["all_certificates_passed"])
    )

    published = _published_benchmark_rows()
    _write_csv(RESULTS_DIR / "published_benchmark_audit.csv", published)
    _plot_results(audited_rows, summaries, published)

    metadata = {
        "protocol_id": PROTOCOL_ID,
        "protocol_hashes": hashes,
        "raw_method_rows_sha256_before_factor_manifest_load": raw_hash,
        "heldout_N": list(HELDOUT_MODULI),
        "heldout_count": len(HELDOUT_MODULI),
        "N_is_primary_generalization_unit": True,
        "arms": list(ARMS),
        "max_power": MAX_POWER,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "equivalence_seed": EQUIVALENCE_SEED,
        "adversarial_random_vectors_per_plan": ADVERSARIAL_RANDOM_VECTORS,
        "thresholds": thresholds,
        "preregistered_hypothesis_passed": hypothesis_passed,
        "complete_method_summary": complete,
        "all_posthoc_factor_checks_passed": all(
            bool(row["posthoc_factor_match"]) for row in audited_rows
        ),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "qiskit": qiskit.__version__,
        "known_factors_used_by_method": False,
        "group_orders_used_by_method": False,
        "exclusions": [],
    }
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

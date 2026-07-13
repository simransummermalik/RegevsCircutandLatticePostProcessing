"""Execute the frozen exact Shor QFT robustness holdout."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from math import pi, sqrt
from pathlib import Path
from time import perf_counter

import numpy as np

from regev_research.qft_certificate import original_certificate
from shor_to_regev_study.shor import (
    apply_readout_bitflips,
    decode_measurement,
    decoder_boundary_metrics,
    hellinger_affinity,
    phase_register_bits,
    qft_resources,
    shor_transformed_fibers,
    joint_state_metrics_from_fibers,
    total_variation,
    verified_factor_pair,
)
from shor_to_regev_study.task_aware_precision import (
    exact_sign_flip_p,
    exact_sign_test,
    paired_cluster_bootstrap,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "shor_qft_robustness"
HELDOUT = ((35, 2), (35, 11), (39, 2), (51, 2), (55, 2), (65, 3), (77, 8), (91, 9))
POSTHOC_FACTORS = {
    "35:2": (5, 7), "35:11": (5, 7), "39:2": (3, 13), "51:2": (3, 17),
    "55:2": (5, 11), "65:3": (5, 13), "77:8": (7, 11), "91:9": (7, 13),
}
SHOT_COUNTS = (4, 8, 16)
READOUT_PROBABILITIES = (0.0, 0.01)
OMITTED_LAYERS = (0, 1, 2, 3)
REPLICATES = 64
LOSS_BUDGET = 0.05
NONINFERIORITY_MARGIN = 0.10
SENSITIVITY_MARGINS = (0.02, 0.05, 0.10, 0.15)
BOOTSTRAPS = 5000
MASTER_SEED = 2026071201


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty output {path}")
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def wilson(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    probability = successes / trials
    denominator = 1 + z * z / trials
    center = (probability + z * z / (2 * trials)) / denominator
    radius = z * sqrt(
        probability * (1 - probability) / trials + z * z / (4 * trials * trials)
    ) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


def qft_compiled_resources(q: int, cutoff: int) -> dict[str, int]:
    from qiskit import QuantumCircuit, transpile

    circuit = QuantumCircuit(q)
    for first in range(q // 2):
        circuit.swap(first, q - 1 - first)
    for target in range(q):
        for control in range(target):
            separation = target - control
            if separation <= cutoff:
                circuit.cp(-pi / (2**separation), target, control)
        circuit.h(target)
    compiled = transpile(
        circuit,
        basis_gates=("rz", "sx", "x", "cx"),
        optimization_level=1,
        seed_transpiler=MASTER_SEED,
    )
    logical = qft_resources(q, cutoff)
    return {
        **logical,
        "compiled_cx": int(compiled.count_ops().get("cx", 0)),
        "compiled_depth": int(compiled.depth()),
    }


def configuration_and_distribution_rows() -> tuple[list[dict], dict[tuple, np.ndarray]]:
    rows: list[dict] = []
    distributions: dict[tuple, np.ndarray] = {}
    resource_cache: dict[tuple[int, int], dict[str, int]] = {}
    for N, base in HELDOUT:
        q = phase_register_bits(N)
        Q = 1 << q
        exact_cutoff = q - 1
        for omitted in OMITTED_LAYERS:
            cutoff = max(0, exact_cutoff - omitted)
            resource_cache.setdefault((q, cutoff), qft_compiled_resources(q, cutoff))
        exact_resource = resource_cache[(q, exact_cutoff)]
        transformed = {
            omitted: shor_transformed_fibers(
                N, base, max(0, exact_cutoff - omitted)
            )
            for omitted in OMITTED_LAYERS
        }
        clean_laws = {
            omitted: (
                np.sum(np.abs(values) ** 2, axis=0).real
                / np.sum(np.abs(values) ** 2)
            )
            for omitted, values in transformed.items()
        }
        exact_clean = clean_laws[0]
        order_mask = np.asarray([
            decode_measurement(N, base, y, Q).verified_order is not None for y in range(Q)
        ])
        factor_mask = np.asarray([
            decode_measurement(N, base, y, Q).factor_pair is not None for y in range(Q)
        ])
        for omitted in OMITTED_LAYERS:
            cutoff = max(0, exact_cutoff - omitted)
            clean = clean_laws[omitted]
            state = joint_state_metrics_from_fibers(
                transformed[0], transformed[omitted]
            )
            resources = resource_cache[(q, cutoff)]
            for readout in READOUT_PROBABILITIES:
                exact = apply_readout_bitflips(exact_clean, readout)
                approximate = apply_readout_bitflips(clean, readout)
                distributions[(N, base, omitted, readout)] = approximate
                boundaries = decoder_boundary_metrics(N, base, exact, approximate)
                one_shot_tv = total_variation(exact, approximate)
                affinity = hellinger_affinity(exact, approximate)
                for shots in SHOT_COUNTS:
                    worst = original_certificate(1, Q, shots, cutoff, LOSS_BUDGET)
                    tv_bound = min(1.0, shots * one_shot_tv)
                    hellinger_bound = sqrt(max(0.0, 1.0 - affinity ** (2 * shots)))
                    state_bound = min(1.0, shots * state["joint_state_trace_distance"])
                    rows.append({
                        "instance_id": f"{N}:{base}",
                        "N": N,
                        "base": base,
                        "phase_qubits": q,
                        "phase_modulus": Q,
                        "shots": shots,
                        "readout_bitflip_probability": readout,
                        "cutoff": cutoff,
                        "omitted_layers": omitted,
                        "loss_budget": LOSS_BUDGET,
                        "worst_case_certified": worst.certified,
                        "worst_case_m_shot_bound": worst.m_shot_bound,
                        "distribution_tv": one_shot_tv,
                        "distribution_m_shot_bound": tv_bound,
                        "distribution_certified": tv_bound <= LOSS_BUDGET,
                        "hellinger_affinity": affinity,
                        "hellinger_product_bound": hellinger_bound,
                        "hellinger_certified": hellinger_bound <= LOSS_BUDGET,
                        "state_trace_distance": state["joint_state_trace_distance"],
                        "state_norm_error": state["joint_state_vector_norm_error"],
                        "state_m_shot_bound": state_bound,
                        "state_certified": state_bound <= LOSS_BUDGET,
                        "exact_order_acceptance_mass": float(np.dot(exact, order_mask)),
                        "approximate_order_acceptance_mass": float(np.dot(approximate, order_mask)),
                        "exact_factor_acceptance_mass": float(np.dot(exact, factor_mask)),
                        "approximate_factor_acceptance_mass": float(np.dot(approximate, factor_mask)),
                        "clean_distribution_tv": total_variation(exact_clean, clean),
                        **boundaries,
                        "exact_controlled_phase": exact_resource["controlled_phase"],
                        "controlled_phase": resources["controlled_phase"],
                        "controlled_phase_saving": (
                            exact_resource["controlled_phase"] - resources["controlled_phase"]
                        ),
                        "compiled_cx": resources["compiled_cx"],
                        "compiled_cx_saving": exact_resource["compiled_cx"] - resources["compiled_cx"],
                        "compiled_depth": resources["compiled_depth"],
                        "compiled_depth_saving": exact_resource["compiled_depth"] - resources["compiled_depth"],
                        "known_factors_used": False,
                        "known_order_used_by_decoder": False,
                    })
    return rows, distributions


def trial_rows(distributions: dict[tuple, np.ndarray]) -> list[dict]:
    rows: list[dict] = []
    for instance_index, (N, base) in enumerate(HELDOUT):
        q = phase_register_bits(N)
        Q = 1 << q
        for shots_index, shots in enumerate(SHOT_COUNTS):
            for readout_index, readout in enumerate(READOUT_PROBABILITIES):
                for omitted in OMITTED_LAYERS:
                    cutoff = max(0, q - 1 - omitted)
                    probabilities = distributions[(N, base, omitted, readout)]
                    for replicate in range(REPLICATES):
                        seed = (
                            MASTER_SEED + 1_000_000 * instance_index
                            + 100_000 * shots_index + 10_000 * readout_index + replicate
                        )
                        started = perf_counter()
                        rng = np.random.default_rng(seed)
                        measurements = rng.choice(Q, size=shots, p=probabilities)
                        decoded = [decode_measurement(N, base, int(y), Q) for y in measurements]
                        runtime = perf_counter() - started
                        order_success = any(item.verified_order is not None for item in decoded)
                        factor_item = next((item for item in decoded if item.factor_pair is not None), None)
                        factor_success = factor_item is not None
                        if factor_item is not None:
                            pair = verified_factor_pair(N, factor_item.factor_pair)
                            if pair != POSTHOC_FACTORS[f"{N}:{base}"]:
                                raise AssertionError("post-hoc factor manifest mismatch")
                        failures = Counter(
                            item.failure_reason for item in decoded if item.failure_reason is not None
                        )
                        rows.append({
                            "instance_id": f"{N}:{base}",
                            "N": N,
                            "base": base,
                            "shots": shots,
                            "readout_bitflip_probability": readout,
                            "cutoff": cutoff,
                            "omitted_layers": omitted,
                            "replicate": replicate,
                            "seed": seed,
                            "order_success": order_success,
                            "factor_success": factor_success,
                            "factor_pair": None if factor_item is None else json.dumps(factor_item.factor_pair),
                            "failure_counts": json.dumps(failures, sort_keys=True),
                            "runtime_seconds": runtime,
                            "factors_used_only_posthoc": True,
                        })
    return rows


def aggregate(trials: list[dict]) -> dict[str, list[dict]]:
    import pandas as pd

    frame = pd.DataFrame(trials)
    per_instance: list[dict] = []
    grouping = ["instance_id", "N", "base", "shots", "readout_bitflip_probability", "omitted_layers", "cutoff"]
    for key, group in frame.groupby(grouping):
        instance_id, N, base, shots, readout, omitted, cutoff = key
        order_count = int(group.order_success.sum())
        factor_count = int(group.factor_success.sum())
        order_low, order_high = wilson(order_count, len(group))
        factor_low, factor_high = wilson(factor_count, len(group))
        per_instance.append({
            "instance_id": instance_id,
            "N": int(N), "base": int(base), "shots": int(shots),
            "readout_bitflip_probability": float(readout),
            "omitted_layers": int(omitted), "cutoff": int(cutoff),
            "replicates": len(group),
            "order_probability": order_count / len(group),
            "order_ci95_low": order_low, "order_ci95_high": order_high,
            "factor_probability": factor_count / len(group),
            "factor_ci95_low": factor_low, "factor_ci95_high": factor_high,
            "mean_runtime_seconds": float(group.runtime_seconds.mean()),
        })
    per_frame = pd.DataFrame(per_instance)
    paired: list[dict] = []
    bootstrap: list[dict] = []
    exact_tests: list[dict] = []
    leave_one_out: list[dict] = []
    bootstrap_seed = MASTER_SEED + 90_000
    for (shots, readout, omitted), group in per_frame.groupby(
        ["shots", "readout_bitflip_probability", "omitted_layers"]
    ):
        exact = per_frame[
            (per_frame.shots == shots)
            & (per_frame.readout_bitflip_probability == readout)
            & (per_frame.omitted_layers == 0)
        ].set_index("instance_id")
        current = group.set_index("instance_id")
        instances = sorted(set(exact.index) & set(current.index))
        order_diff = np.asarray([
            current.loc[item, "order_probability"] - exact.loc[item, "order_probability"]
            for item in instances
        ])
        factor_diff = np.asarray([
            current.loc[item, "factor_probability"] - exact.loc[item, "factor_probability"]
            for item in instances
        ])
        cell_seed = bootstrap_seed + 1000 * SHOT_COUNTS.index(int(shots)) + 100 * READOUT_PROBABILITIES.index(float(readout)) + int(omitted)
        indices, draws = paired_cluster_bootstrap(
            {"order": order_diff, "factor": factor_diff},
            replicates=BOOTSTRAPS,
            seed=cell_seed,
        )
        order_low, order_high = np.quantile(draws["order"], (0.025, 0.975))
        factor_low, factor_high = np.quantile(draws["factor"], (0.025, 0.975))
        paired.append({
            "shots": int(shots),
            "readout_bitflip_probability": float(readout),
            "omitted_layers": int(omitted),
            "instance_clusters": len(instances),
            "order_mean_difference": float(np.mean(order_diff)),
            "order_ci95_low": float(order_low), "order_ci95_high": float(order_high),
            "factor_mean_difference": float(np.mean(factor_diff)),
            "factor_ci95_low": float(factor_low), "factor_ci95_high": float(factor_high),
            "noninferior_at_0_10": bool(
                order_low >= -NONINFERIORITY_MARGIN and factor_low >= -NONINFERIORITY_MARGIN
            ),
            "bootstrap_replicates": BOOTSTRAPS,
        })
        for draw in range(BOOTSTRAPS):
            bootstrap.append({
                "shots": int(shots), "readout_bitflip_probability": float(readout),
                "omitted_layers": int(omitted), "draw": draw,
                "cluster_indices": json.dumps([int(value) for value in indices[draw]]),
                "order_mean_difference": float(draws["order"][draw]),
                "factor_mean_difference": float(draws["factor"][draw]),
            })
        if int(omitted) > 0:
            for endpoint, values in (("order", order_diff), ("factor", factor_diff)):
                sign = exact_sign_test(values)
                exact_tests.append({
                    "shots": int(shots), "readout_bitflip_probability": float(readout),
                    "omitted_layers": int(omitted), "endpoint": endpoint,
                    "mean_difference": float(np.mean(values)), **sign,
                    "sign_flip_two_sided_p": exact_sign_flip_p(values),
                    "sign_flip_noninferiority_p_at_0_10": exact_sign_flip_p(
                        values, shift=NONINFERIORITY_MARGIN, alternative="greater"
                    ),
                })
            for omitted_instance in instances:
                keep = np.asarray([item != omitted_instance for item in instances])
                loo_indices, loo_draws = paired_cluster_bootstrap(
                    {"order": order_diff[keep], "factor": factor_diff[keep]},
                    replicates=BOOTSTRAPS,
                    seed=cell_seed + 10_000 + instances.index(omitted_instance),
                )
                del loo_indices
                loo_order_low = float(np.quantile(loo_draws["order"], 0.025))
                loo_factor_low = float(np.quantile(loo_draws["factor"], 0.025))
                leave_one_out.append({
                    "shots": int(shots), "readout_bitflip_probability": float(readout),
                    "omitted_layers": int(omitted), "omitted_instance": omitted_instance,
                    "remaining_clusters": int(np.sum(keep)),
                    "order_mean_difference": float(np.mean(order_diff[keep])),
                    "order_ci95_low": loo_order_low,
                    "factor_mean_difference": float(np.mean(factor_diff[keep])),
                    "factor_ci95_low": loo_factor_low,
                    "noninferior_at_0_10": bool(
                        loo_order_low >= -NONINFERIORITY_MARGIN
                        and loo_factor_low >= -NONINFERIORITY_MARGIN
                    ),
                })

    margin_rows: list[dict] = []
    margin_summary: list[dict] = []
    for margin in SENSITIVITY_MARGINS:
        for row in paired:
            margin_rows.append({
                **row,
                "tested_margin": margin,
                "noninferior": bool(
                    row["order_ci95_low"] >= -margin and row["factor_ci95_low"] >= -margin
                ),
            })
        for shots in SHOT_COUNTS:
            for readout in READOUT_PROBABILITIES:
                cells = [
                    row for row in margin_rows
                    if row["tested_margin"] == margin and row["shots"] == shots
                    and row["readout_bitflip_probability"] == readout and row["noninferior"]
                ]
                margin_summary.append({
                    "shots": shots, "readout_bitflip_probability": readout,
                    "margin": margin,
                    "largest_noninferior_omitted_layers": max(
                        (row["omitted_layers"] for row in cells), default=None
                    ),
                })
    return {
        "per_instance": per_instance,
        "paired": paired,
        "bootstrap": bootstrap,
        "exact_tests": exact_tests,
        "leave_one_out": leave_one_out,
        "margin": margin_rows,
        "margin_summary": margin_summary,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    configurations, distributions = configuration_and_distribution_rows()
    trials = trial_rows(distributions)
    aggregates = aggregate(trials)
    files = {
        "configuration_rows.csv": configurations,
        "trial_rows.csv": trials,
        "per_instance_rows.csv": aggregates["per_instance"],
        "paired_rows.csv": aggregates["paired"],
        "bootstrap_draw_rows.csv": aggregates["bootstrap"],
        "paired_exact_test_rows.csv": aggregates["exact_tests"],
        "leave_one_instance_out_rows.csv": aggregates["leave_one_out"],
        "margin_sensitivity_rows.csv": aggregates["margin"],
        "margin_summary_rows.csv": aggregates["margin_summary"],
    }
    for name, rows in files.items():
        write_csv(OUT / name, rows)
    configuration = {
        "freeze_identifier": "shor-qft-robustness-v1",
        "heldout_instances": [list(item) for item in HELDOUT],
        "shot_counts": SHOT_COUNTS,
        "readout_bitflip_probabilities": READOUT_PROBABILITIES,
        "omitted_layers": OMITTED_LAYERS,
        "replicates": REPLICATES,
        "loss_budget": LOSS_BUDGET,
        "noninferiority_margin": NONINFERIORITY_MARGIN,
        "sensitivity_margins": SENSITIVITY_MARGINS,
        "master_seed": MASTER_SEED,
        "bootstrap_replicates": BOOTSTRAPS,
        "known_factors_used_only_posthoc": True,
        "known_order_used_by_decoder": False,
        "row_counts": {name.removesuffix(".csv"): len(rows) for name, rows in files.items()},
    }
    (OUT / "configuration.json").write_text(json.dumps(configuration, indent=2, sort_keys=True))
    manifest_files = ["configuration.json", *files]
    completion = {
        "status": "complete",
        "freeze_identifier": configuration["freeze_identifier"],
        "heldout_instances_executed": [f"{N}:{base}" for N, base in HELDOUT],
        "primary_generalization_unit": "(N,base)",
        "row_counts": configuration["row_counts"],
        "sha256": {
            name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
            for name in manifest_files
        },
    }
    (OUT / "completion.json").write_text(json.dumps(completion, indent=2, sort_keys=True))
    print(json.dumps(configuration, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

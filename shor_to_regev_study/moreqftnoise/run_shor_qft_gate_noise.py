"""Execute the Shor QFT gate-level noise robustness study.

This companion to ``run_shor_qft_robustness.py`` isolates *gate-level* inverse
QFT noise from the distance truncation studied there.  The inverse QFT distance
is held at its exact cutoff so that any change in verified order/factor recovery
is attributable to imperfect gates, not dropped layers.  Three coherent/stochastic
axes are swept, all realized in the exact pure-state fiber formalism:

* controlled-phase miscalibration  -- systematic gain and per-gate scatter on the
    two-qubit controlled-phase angles (``cphase_gain`` / ``cphase_sigma``);
* single-qubit RZ over/under-rotation -- systematic bias and per-Hadamard scatter
    on the basis-gate ``rz`` rotations (``rz_bias`` / ``rz_sigma``);
* CX depolarizing -- a global-depolarizing surrogate keyed to the transpiled
    two-qubit gate count (``cx_depolarizing_probability``).

Deterministic settings (gain, bias, depolarizing) yield one exact phase law per
instance; stochastic-scatter settings redraw a fresh quasi-static miscalibration
per realization (fixed across a shot batch, varying across batches), which is the
physically faithful model for coherent calibration drift.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from math import pi, sqrt
from pathlib import Path
from time import perf_counter

import numpy as np

from regev_research.qft_certificate import original_certificate
from shor_to_regev_study.shor import (
    apply_global_depolarizing,
    cx_depolarizing_mixing,
    decode_measurement,
    hellinger_affinity,
    multiplicative_order_for_simulation,
    noisy_inverse_qft_batch,
    phase_register_bits,
    qft_resources,
    total_variation,
    verified_factor_pair,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "shor_qft_gate_noise"
HELDOUT = ((35, 2), (35, 11), (39, 2), (51, 2), (55, 2), (65, 3), (77, 8), (91, 9))
POSTHOC_FACTORS = {
    "35:2": (5, 7), "35:11": (5, 7), "39:2": (3, 13), "51:2": (3, 17),
    "55:2": (5, 11), "65:3": (5, 13), "77:8": (7, 11), "91:9": (7, 13),
}
SHOT_COUNTS = (1, 2, 8, 16)
REALIZATIONS = 48
LOSS_BUDGET = 0.05
NONINFERIORITY_MARGIN = 0.10
MASTER_SEED = 2026071501


@dataclass(frozen=True, slots=True)
class NoiseSetting:
    """A named point in the gate-noise grid.

    ``stochastic`` marks settings whose miscalibration is redrawn per realization;
    deterministic settings share one exact law across every realization.
    """

    name: str
    axis: str
    cphase_gain: float = 0.0
    cphase_sigma: float = 0.0
    rz_bias: float = 0.0
    rz_sigma: float = 0.0
    cx_depolarizing_probability: float = 0.0

    @property
    def stochastic(self) -> bool:
        return bool(self.cphase_sigma or self.rz_sigma)


NOISE_SETTINGS: tuple[NoiseSetting, ...] = (
    NoiseSetting("baseline", "baseline"),
    # Controlled-phase miscalibration -- systematic multiplicative gain.
    NoiseSetting("cphase_gain_0p02", "controlled_phase", cphase_gain=0.02),
    NoiseSetting("cphase_gain_0p05", "controlled_phase", cphase_gain=0.05),
    NoiseSetting("cphase_gain_0p10", "controlled_phase", cphase_gain=0.10),
    # Controlled-phase miscalibration -- per-gate Gaussian scatter (radians).
    NoiseSetting("cphase_sigma_0p02", "controlled_phase", cphase_sigma=0.02),
    NoiseSetting("cphase_sigma_0p05", "controlled_phase", cphase_sigma=0.05),
    NoiseSetting("cphase_sigma_0p10", "controlled_phase", cphase_sigma=0.10),
    # Single-qubit RZ over/under-rotation -- systematic bias (radians).
    NoiseSetting("rz_bias_0p02", "rz_rotation", rz_bias=0.02),
    NoiseSetting("rz_bias_0p05", "rz_rotation", rz_bias=0.05),
    NoiseSetting("rz_bias_0p10", "rz_rotation", rz_bias=0.10),
    # Single-qubit RZ over/under-rotation -- per-Hadamard Gaussian scatter.
    NoiseSetting("rz_sigma_0p02", "rz_rotation", rz_sigma=0.02),
    NoiseSetting("rz_sigma_0p05", "rz_rotation", rz_sigma=0.05),
    NoiseSetting("rz_sigma_0p10", "rz_rotation", rz_sigma=0.10),
    # CX depolarizing -- per-two-qubit-gate error rate.
    NoiseSetting("cx_depol_0p001", "cx_depolarizing", cx_depolarizing_probability=0.001),
    NoiseSetting("cx_depol_0p005", "cx_depolarizing", cx_depolarizing_probability=0.005),
    NoiseSetting("cx_depol_0p010", "cx_depolarizing", cx_depolarizing_probability=0.010),
)


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


def compiled_cx_count(q: int, cutoff: int) -> int:
    """Transpiled two-qubit gate count for the inverse QFT at ``cutoff``."""

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
    return int(compiled.count_ops().get("cx", 0))


def clean_law_from_fibers(fibers: np.ndarray) -> np.ndarray:
    mass = np.sum(np.abs(fibers) ** 2, axis=0).real
    return mass / mass.sum()


def noisy_law(
    base_fibers: np.ndarray,
    cutoff: int,
    setting: NoiseSetting,
    cx_count: int,
    rng: np.random.Generator | None,
) -> np.ndarray:
    """One phase law under ``setting``; ``rng`` drives the stochastic scatter."""

    transformed = noisy_inverse_qft_batch(
        base_fibers,
        cutoff,
        cphase_gain=setting.cphase_gain,
        cphase_sigma=setting.cphase_sigma,
        rz_bias=setting.rz_bias,
        rz_sigma=setting.rz_sigma,
        rng=rng,
    )
    law = clean_law_from_fibers(transformed)
    if setting.cx_depolarizing_probability:
        mixing = cx_depolarizing_mixing(cx_count, setting.cx_depolarizing_probability)
        law = apply_global_depolarizing(law, mixing)
    return law


def configuration_and_trial_rows() -> tuple[list[dict], list[dict]]:
    configurations: list[dict] = []
    trials: list[dict] = []
    for instance_index, (N, base) in enumerate(HELDOUT):
        q = phase_register_bits(N)
        Q = 1 << q
        cutoff = q - 1
        cx_count = compiled_cx_count(q, cutoff)
        controlled_phase = qft_resources(q, cutoff)["controlled_phase"]
        order = multiplicative_order_for_simulation(N, base)
        raw_fibers = np.zeros((order, Q), dtype=complex)
        x = np.arange(Q)
        raw_fibers[x % order, x] = 1.0 / sqrt(Q)
        exact = clean_law_from_fibers(noisy_inverse_qft_batch(raw_fibers, cutoff))
        order_mask = np.asarray([
            decode_measurement(N, base, y, Q).verified_order is not None for y in range(Q)
        ])
        factor_mask = np.asarray([
            decode_measurement(N, base, y, Q).factor_pair is not None for y in range(Q)
        ])

        for setting_index, setting in enumerate(NOISE_SETTINGS):
            mixing = (
                cx_depolarizing_mixing(cx_count, setting.cx_depolarizing_probability)
                if setting.cx_depolarizing_probability
                else 1.0
            )
            # For distribution-level metrics use the mean law: deterministic
            # settings give it directly; stochastic settings are averaged over
            # realizations so the reported TV/affinity is the ensemble law.
            if setting.stochastic:
                accum = np.zeros(Q)
                for realization in range(REALIZATIONS):
                    seed = _seed(instance_index, setting_index, 0, realization, tag=1)
                    accum += noisy_law(
                        raw_fibers, cutoff, setting, cx_count,
                        np.random.default_rng(seed),
                    )
                mean_law = accum / REALIZATIONS
            else:
                mean_law = noisy_law(raw_fibers, cutoff, setting, cx_count, None)

            one_shot_tv = total_variation(exact, mean_law)
            affinity = hellinger_affinity(exact, mean_law)
            for shots in SHOT_COUNTS:
                worst = original_certificate(1, Q, shots, cutoff, LOSS_BUDGET)
                tv_bound = min(1.0, shots * one_shot_tv)
                hellinger_bound = sqrt(max(0.0, 1.0 - affinity ** (2 * shots)))
                configurations.append({
                    "instance_id": f"{N}:{base}",
                    "N": N, "base": base, "phase_qubits": q, "phase_modulus": Q,
                    "cutoff": cutoff, "shots": shots,
                    "noise_setting": setting.name, "noise_axis": setting.axis,
                    "cphase_gain": setting.cphase_gain,
                    "cphase_sigma": setting.cphase_sigma,
                    "rz_bias": setting.rz_bias, "rz_sigma": setting.rz_sigma,
                    "cx_depolarizing_probability": setting.cx_depolarizing_probability,
                    "stochastic_setting": setting.stochastic,
                    "compiled_cx": cx_count,
                    "controlled_phase": controlled_phase,
                    "depolarizing_mixing": mixing,
                    "loss_budget": LOSS_BUDGET,
                    "worst_case_certified": worst.certified,
                    "worst_case_m_shot_bound": worst.m_shot_bound,
                    "distribution_tv": one_shot_tv,
                    "distribution_m_shot_bound": tv_bound,
                    "distribution_certified": tv_bound <= LOSS_BUDGET,
                    "hellinger_affinity": affinity,
                    "hellinger_product_bound": hellinger_bound,
                    "hellinger_certified": hellinger_bound <= LOSS_BUDGET,
                    "exact_order_acceptance_mass": float(np.dot(exact, order_mask)),
                    "noisy_order_acceptance_mass": float(np.dot(mean_law, order_mask)),
                    "exact_factor_acceptance_mass": float(np.dot(exact, factor_mask)),
                    "noisy_factor_acceptance_mass": float(np.dot(mean_law, factor_mask)),
                    "known_factors_used": False,
                    "known_order_used_by_decoder": False,
                })

            # Recovery trials: one quasi-static law per realization (drawn once
            # for a stochastic setting, or the fixed exact law otherwise), reused
            # across every shot budget so the device calibration is shared.
            for realization in range(REALIZATIONS):
                if setting.stochastic:
                    law_seed = _seed(instance_index, setting_index, 0, realization, tag=2)
                    law = noisy_law(
                        raw_fibers, cutoff, setting, cx_count,
                        np.random.default_rng(law_seed),
                    )
                else:
                    law = mean_law
                for shots in SHOT_COUNTS:
                    started = perf_counter()
                    shot_seed = _seed(instance_index, setting_index, shots, realization, tag=3)
                    rng = np.random.default_rng(shot_seed)
                    measurements = rng.choice(Q, size=shots, p=law)
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
                    trials.append({
                        "instance_id": f"{N}:{base}", "N": N, "base": base,
                        "shots": shots, "cutoff": cutoff,
                        "noise_setting": setting.name, "noise_axis": setting.axis,
                        "stochastic_setting": setting.stochastic,
                        "realization": realization,
                        "shot_seed": shot_seed,
                        "order_success": order_success,
                        "factor_success": factor_success,
                        "factor_pair": None if factor_item is None else json.dumps(factor_item.factor_pair),
                        "failure_counts": json.dumps(failures, sort_keys=True),
                        "runtime_seconds": runtime,
                        "factors_used_only_posthoc": True,
                    })
    return configurations, trials


def _seed(instance: int, setting: int, shots: int, realization: int, *, tag: int) -> int:
    return (
        MASTER_SEED
        + 100_000_000 * tag
        + 1_000_000 * instance
        + 10_000 * setting
        + 1_000 * shots
        + realization
    )


def aggregate(trials: list[dict]) -> tuple[list[dict], list[dict]]:
    import pandas as pd

    frame = pd.DataFrame(trials)
    per_instance: list[dict] = []
    grouping = ["instance_id", "N", "base", "shots", "noise_setting", "noise_axis"]
    for key, group in frame.groupby(grouping):
        instance_id, N, base, shots, setting, axis = key
        order_count = int(group.order_success.sum())
        factor_count = int(group.factor_success.sum())
        order_low, order_high = wilson(order_count, len(group))
        factor_low, factor_high = wilson(factor_count, len(group))
        per_instance.append({
            "instance_id": instance_id, "N": int(N), "base": int(base),
            "shots": int(shots), "noise_setting": setting, "noise_axis": axis,
            "realizations": len(group),
            "order_probability": order_count / len(group),
            "order_ci95_low": order_low, "order_ci95_high": order_high,
            "factor_probability": factor_count / len(group),
            "factor_ci95_low": factor_low, "factor_ci95_high": factor_high,
            "mean_runtime_seconds": float(group.runtime_seconds.mean()),
        })
    per_frame = pd.DataFrame(per_instance)
    paired: list[dict] = []
    for (shots, setting), group in per_frame.groupby(["shots", "noise_setting"]):
        if setting == "baseline":
            continue
        axis = group.noise_axis.iloc[0]
        baseline = per_frame[
            (per_frame.shots == shots) & (per_frame.noise_setting == "baseline")
        ].set_index("instance_id")
        current = group.set_index("instance_id")
        instances = sorted(set(baseline.index) & set(current.index))
        order_diff = np.asarray([
            current.loc[i, "order_probability"] - baseline.loc[i, "order_probability"]
            for i in instances
        ])
        factor_diff = np.asarray([
            current.loc[i, "factor_probability"] - baseline.loc[i, "factor_probability"]
            for i in instances
        ])
        paired.append({
            "shots": int(shots), "noise_setting": setting, "noise_axis": axis,
            "instances": len(instances),
            "order_mean_difference": float(np.mean(order_diff)),
            "order_min_difference": float(np.min(order_diff)),
            "factor_mean_difference": float(np.mean(factor_diff)),
            "factor_min_difference": float(np.min(factor_diff)),
            "noninferior_at_0_10": bool(
                np.min(order_diff) >= -NONINFERIORITY_MARGIN
                and np.min(factor_diff) >= -NONINFERIORITY_MARGIN
            ),
        })
    return per_instance, paired


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    configurations, trials = configuration_and_trial_rows()
    per_instance, paired = aggregate(trials)
    files = {
        "configuration_rows.csv": configurations,
        "trial_rows.csv": trials,
        "per_instance_rows.csv": per_instance,
        "paired_rows.csv": paired,
    }
    for name, rows in files.items():
        write_csv(OUT / name, rows)
    configuration = {
        "freeze_identifier": "shor-qft-gate-noise-v1",
        "heldout_instances": [list(item) for item in HELDOUT],
        "shot_counts": SHOT_COUNTS,
        "realizations": REALIZATIONS,
        "noise_settings": [setting.name for setting in NOISE_SETTINGS],
        "cutoff_policy": "exact (q-1); gate noise isolated from truncation",
        "loss_budget": LOSS_BUDGET,
        "noninferiority_margin": NONINFERIORITY_MARGIN,
        "master_seed": MASTER_SEED,
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

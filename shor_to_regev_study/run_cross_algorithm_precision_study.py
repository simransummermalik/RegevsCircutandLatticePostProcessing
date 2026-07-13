"""Compare task-aware QFT precision across Shor and the frozen Regev endpoint."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from regev_research.core import RootedBaseFamily
from regev_research.qft_noise import (
    fiber_fourier_distribution,
    qft_gate_counts,
    weighted_fiber_fourier_distribution,
)
from regev_research.redteam import regev_gaussian_amplitudes
from shor_to_regev_study.shor import (
    decode_measurement,
    decoder_boundary_metrics,
    phase_register_bits,
    shor_phase_distribution,
    total_variation,
)
from shor_to_regev_study.task_aware_precision import (
    TaskAwarePrecisionRecord,
    binary_metrics,
    calibration_rows,
    fit_logistic_predictor,
)


ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parent
SHOR_RESULTS = ROOT / "results" / "shor_qft_robustness"
REGEV_RESULTS = REPOSITORY / "results" / "qft_certificate_gap"
OUT = ROOT / "results" / "cross_algorithm_precision"
MARGIN = 0.10
FEATURES = (
    "algorithm_is_shor",
    "register_bits",
    "omitted_layers",
    "shots",
    "measured_tv",
    "decoder_boundary_proxy",
    "controlled_phase_saving",
)
SHOR_DEVELOPMENT = ((15, 2), (15, 14), (21, 2), (21, 4), (21, 5), (33, 10))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"empty output: {path}")
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_shor_records() -> tuple[list[TaskAwarePrecisionRecord], list[dict]]:
    configurations = pd.read_csv(SHOR_RESULTS / "configuration_rows.csv")
    per_instance = pd.read_csv(SHOR_RESULTS / "per_instance_rows.csv")
    joined = per_instance.merge(
        configurations,
        on=[
            "instance_id", "N", "base", "shots", "readout_bitflip_probability",
            "cutoff", "omitted_layers",
        ],
        validate="one_to_one",
    )
    records: list[TaskAwarePrecisionRecord] = []
    predictor_rows: list[dict] = []
    for _, row in joined.iterrows():
        exact = joined[
            (joined.instance_id == row.instance_id)
            & (joined.shots == row.shots)
            & (joined.readout_bitflip_probability == row.readout_bitflip_probability)
            & (joined.omitted_layers == 0)
        ].iloc[0]
        resources = {
            "controlled_phase": int(row.controlled_phase_saving),
            "cx": int(row.compiled_cx_saving),
            "depth": int(row.compiled_depth_saving),
        }
        for endpoint, column in (("order", "order_probability"), ("factor", "factor_probability")):
            probability = float(row[column])
            exact_probability = float(exact[column])
            records.append(TaskAwarePrecisionRecord(
                algorithm="Shor",
                instance_id=str(row.instance_id),
                endpoint=endpoint,
                approximation_level=int(row.omitted_layers),
                worst_case_certified=bool(row.worst_case_certified),
                state_specific_certified=bool(row.distribution_certified),
                measured_tv=float(row.distribution_tv),
                task_success_probability=probability,
                exact_task_success_probability=exact_probability,
                task_difference=probability - exact_probability,
                resource_saving=resources,
            ))
        if int(row.omitted_layers) > 0:
            predictor_rows.append({
                "split": "heldout",
                "algorithm": "Shor",
                "instance_id": str(row.instance_id),
                "algorithm_is_shor": 1.0,
                "register_bits": float(row.phase_qubits),
                "omitted_layers": float(row.omitted_layers),
                "shots": float(row.shots),
                "measured_tv": float(row.distribution_tv),
                "decoder_boundary_proxy": float(row.absolute_change_near_cf_boundary),
                "controlled_phase_saving": float(row.controlled_phase_saving),
                "worst_case_certified": bool(row.worst_case_certified),
                "task_difference": float(row.factor_probability - exact.factor_probability),
                "noninferior": bool(row.factor_probability - exact.factor_probability >= -MARGIN),
            })
    return records, predictor_rows


def load_regev_records() -> tuple[list[TaskAwarePrecisionRecord], list[dict]]:
    configurations = pd.read_csv(REGEV_RESULTS / "configuration_rows.csv")
    per_n = pd.read_csv(REGEV_RESULTS / "per_N_rows.csv")
    joined = per_n.merge(
        configurations,
        on=["N", "M", "model", "cutoff", "omitted_layers"],
        validate="one_to_one",
    )
    records: list[TaskAwarePrecisionRecord] = []
    predictor_rows: list[dict] = []
    for _, row in joined.iterrows():
        exact = joined[
            (joined.N == row.N) & (joined.M == row.M) & (joined.model == row.model)
            & (joined.omitted_layers == 0)
        ].iloc[0]
        resources = {
            "controlled_phase": int(row.cp_saving),
            "cx": int(row.compiled_cx_saving),
            "depth": int(row.compiled_depth_saving),
        }
        for endpoint, column in (("L_minus_L0", "lminus_probability"), ("factor", "factor_probability")):
            probability = float(row[column])
            exact_probability = float(exact[column])
            records.append(TaskAwarePrecisionRecord(
                algorithm="Regev",
                instance_id=f"{int(row.N)}:{row.model}:M{int(row.M)}",
                endpoint=endpoint,
                approximation_level=int(row.omitted_layers),
                worst_case_certified=bool(row.original_certified),
                state_specific_certified=bool(row.distribution_tv_certified),
                measured_tv=float(row.distribution_tv),
                task_success_probability=probability,
                exact_task_success_probability=exact_probability,
                task_difference=probability - exact_probability,
                resource_saving=resources,
            ))
        if int(row.omitted_layers) > 0:
            predictor_rows.append({
                "split": "heldout",
                "algorithm": "Regev",
                "instance_id": f"{int(row.N)}:{row.model}:M{int(row.M)}",
                "algorithm_is_shor": 0.0,
                "register_bits": float(row.q),
                "omitted_layers": float(row.omitted_layers),
                "shots": float(row.m),
                "measured_tv": float(row.distribution_tv),
                "decoder_boundary_proxy": float(row.fraction_change_on_low_probability_outcomes),
                "controlled_phase_saving": float(row.cp_saving),
                "worst_case_certified": bool(row.original_certified),
                "task_difference": float(row.factor_probability - exact.factor_probability),
                "noninferior": bool(row.factor_probability - exact.factor_probability >= -MARGIN),
            })
    return records, predictor_rows


def shor_development_rows() -> list[dict]:
    rows: list[dict] = []
    for N, base in SHOR_DEVELOPMENT:
        q = phase_register_bits(N)
        Q = 1 << q
        exact = shor_phase_distribution(N, base, qft_cutoff=q - 1)
        exact_factor_mass = sum(
            exact[y] for y in range(Q)
            if decode_measurement(N, base, y, Q).factor_pair is not None
        )
        for omitted in range(1, q):
            approximate = shor_phase_distribution(N, base, qft_cutoff=q - 1 - omitted)
            boundaries = decoder_boundary_metrics(N, base, exact, approximate)
            approximate_factor_mass = sum(
                approximate[y] for y in range(Q)
                if decode_measurement(N, base, y, Q).factor_pair is not None
            )
            for shots in (1, 4, 8):
                exact_probability = 1 - (1 - exact_factor_mass) ** shots
                approximate_probability = 1 - (1 - approximate_factor_mass) ** shots
                rows.append({
                    "split": "development", "algorithm": "Shor",
                    "instance_id": f"{N}:{base}", "algorithm_is_shor": 1.0,
                    "register_bits": float(q), "omitted_layers": float(omitted),
                    "shots": float(shots),
                    "measured_tv": total_variation(exact, approximate),
                    "decoder_boundary_proxy": boundaries["absolute_change_near_cf_boundary"],
                    "controlled_phase_saving": float(
                        qft_gate_counts(1, q, q - 1)["controlled_phase"]
                        - qft_gate_counts(1, q, q - 1 - omitted)["controlled_phase"]
                    ),
                    "worst_case_certified": False,
                    "task_difference": approximate_probability - exact_probability,
                    "noninferior": bool(approximate_probability - exact_probability >= -MARGIN),
                })
    return rows


def regev_development_rows() -> list[dict]:
    endpoints = pd.read_csv(REPOSITORY / "results" / "qft_precision_scaling" / "endpoint_rows.csv")
    rows: list[dict] = []
    for _, row in endpoints.iterrows():
        N, M, cutoff = int(row.N), int(row.M), int(row.cutoff)
        q = int(np.log2(M))
        if cutoff == q - 1:
            continue
        family = RootedBaseFamily.from_roots(N, (2, 3))
        if row.model == "A_uniform_hard_box":
            exact = fiber_fourier_distribution(N, family.bases, M, cutoff=q - 1)
            approximate = fiber_fourier_distribution(N, family.bases, M, cutoff=cutoff)
        else:
            amplitudes = regev_gaussian_amplitudes(M, 4.0)
            exact = weighted_fiber_fourier_distribution(
                N, family.bases, M, amplitudes, cutoff=q - 1
            )
            approximate = weighted_fiber_fourier_distribution(
                N, family.bases, M, amplitudes, cutoff=cutoff
            )
        exact_row = endpoints[
            (endpoints.N == N) & (endpoints.M == M) & (endpoints.model == row.model)
            & (endpoints.cutoff == q - 1)
        ].iloc[0]
        change = np.abs(exact.ravel() - approximate.ravel())
        low = exact.ravel() < 1 / exact.size
        rows.append({
            "split": "development", "algorithm": "Regev",
            "instance_id": f"{N}:{row.model}:M{M}", "algorithm_is_shor": 0.0,
            "register_bits": float(q), "omitted_layers": float(q - 1 - cutoff),
            "shots": float(row.m), "measured_tv": total_variation(exact, approximate),
            "decoder_boundary_proxy": 0.0 if change.sum() == 0 else float(change[low].sum() / change.sum()),
            "controlled_phase_saving": float(
                qft_gate_counts(2, q, q - 1)["controlled_phase"]
                - qft_gate_counts(2, q, cutoff)["controlled_phase"]
            ),
            "worst_case_certified": False,
            "task_difference": float(row.factor_probability - exact_row.factor_probability),
            "noninferior": bool(row.factor_probability - exact_row.factor_probability >= -MARGIN),
        })
    return rows


def best_threshold(rows: list[dict], feature: str) -> float:
    values = np.asarray([float(row[feature]) for row in rows])
    labels = np.asarray([bool(row["noninferior"]) for row in rows])
    candidates = np.unique(np.r_[values, (values[:-1] + values[1:]) / 2])
    scores = [np.mean((values <= threshold) == labels) for threshold in candidates]
    return float(candidates[int(np.argmax(scores))])


def predictor_analysis(development: list[dict], heldout: list[dict]) -> dict[str, list[dict] | dict]:
    labels = [bool(row["noninferior"]) for row in development]
    predictor = fit_logistic_predictor(development, labels, FEATURES)
    heldout_labels = [bool(row["noninferior"]) for row in heldout]
    learned = predictor.predict_proba(heldout)
    tv_threshold = best_threshold(development, "measured_tv")
    layer_threshold = best_threshold(development, "omitted_layers")
    boundary_threshold = best_threshold(development, "decoder_boundary_proxy")
    method_probabilities = {
        "factor_blind_logistic": learned,
        "worst_case_certificate": np.asarray([float(row["worst_case_certified"]) for row in heldout]),
        "measured_tv_alone": np.asarray([float(row["measured_tv"] <= tv_threshold) for row in heldout]),
        "omitted_layers_alone": np.asarray([float(row["omitted_layers"] <= layer_threshold) for row in heldout]),
        "decoder_boundary_proxy_alone": np.asarray([
            float(row["decoder_boundary_proxy"] <= boundary_threshold) for row in heldout
        ]),
    }
    evaluations: list[dict] = []
    predictions: list[dict] = []
    failures: list[dict] = []
    calibration: list[dict] = []
    for method, probabilities in method_probabilities.items():
        evaluations.append({"method": method, **binary_metrics(heldout_labels, probabilities)})
        for row, truth, probability in zip(heldout, heldout_labels, probabilities, strict=True):
            prediction = bool(probability >= 0.5)
            record = {
                "method": method, "algorithm": row["algorithm"],
                "instance_id": row["instance_id"],
                "omitted_layers": row["omitted_layers"], "shots": row["shots"],
                "truth_noninferior": truth, "predicted_noninferior": prediction,
                "probability": float(probability), "task_difference": row["task_difference"],
            }
            predictions.append(record)
            if prediction != truth:
                failures.append(record)
        for item in calibration_rows(heldout_labels, probabilities):
            calibration.append({"method": method, **item})
    model = {
        "feature_names": predictor.feature_names,
        "mean": predictor.mean,
        "scale": predictor.scale,
        "coefficients": predictor.coefficients,
        "intercept": predictor.intercept,
        "tv_threshold_from_development": tv_threshold,
        "layer_threshold_from_development": layer_threshold,
        "boundary_threshold_from_development": boundary_threshold,
        "uses_factors": False,
        "uses_true_orders": False,
        "uses_success_as_feature": False,
    }
    return {
        "evaluation": evaluations, "predictions": predictions,
        "failures": failures, "calibration": calibration, "model": model,
    }


def assign_outcome() -> dict:
    shor_paired = pd.read_csv(SHOR_RESULTS / "paired_rows.csv")
    shor_config = pd.read_csv(SHOR_RESULTS / "configuration_rows.csv")
    shor_gap = False
    for _, row in shor_paired.iterrows():
        relevant = shor_config[
            (shor_config.shots == row.shots)
            & (shor_config.readout_bitflip_probability == row.readout_bitflip_probability)
            & (shor_config.omitted_layers == row.omitted_layers)
        ]
        if row.noninferior_at_0_10 and int(row.omitted_layers) > 0 and not relevant.worst_case_certified.any():
            shor_gap = True
    regev_paired = pd.read_csv(REGEV_RESULTS / "paired_cluster_rows.csv")
    regev_config = pd.read_csv(REGEV_RESULTS / "configuration_rows.csv")
    regev_gap = False
    for _, row in regev_paired.iterrows():
        relevant = regev_config[
            (regev_config.M == row.M) & (regev_config.model == row.model)
            & (regev_config.omitted_layers == row.omitted_layers)
        ]
        if row.empirically_noninferior and int(row.omitted_layers) > 0 and not relevant.original_certified.any():
            regev_gap = True
    outcome = "A" if shor_gap and regev_gap else "B" if regev_gap else "C" if shor_gap else "D"
    return {
        "outcome": outcome,
        "shor_uncertified_noninferior_truncation": shor_gap,
        "regev_uncertified_noninferior_truncation": regev_gap,
        "meaning": {
            "A": "Both Shor and Regev show held-out task robustness beyond the worst-case certificate.",
            "B": "Only Regev shows the gap.", "C": "Only Shor shows the gap.",
            "D": "Neither shows the gap.",
        }[outcome],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shor_records, shor_heldout = load_shor_records()
    regev_records, regev_heldout = load_regev_records()
    records = shor_records + regev_records
    record_rows = [record.as_record() for record in records]
    development = shor_development_rows() + regev_development_rows()
    heldout = shor_heldout + regev_heldout
    predictor = predictor_analysis(development, heldout)
    outcome = assign_outcome()
    summary_frame = pd.DataFrame(record_rows)
    summary_rows = summary_frame.groupby(
        ["algorithm", "endpoint", "approximation_level"], as_index=False
    ).agg(
        instances=("instance_id", "count"),
        mean_task_difference=("task_difference", "mean"),
        mean_measured_tv=("measured_tv", "mean"),
        worst_case_certified_fraction=("worst_case_certified", "mean"),
        state_specific_certified_fraction=("state_specific_certified", "mean"),
        mean_controlled_phase_saving=("resource_controlled_phase", "mean"),
    ).to_dict("records")
    files = {
        "task_aware_records.csv": record_rows,
        "algorithm_summary_rows.csv": summary_rows,
        "predictor_development_rows.csv": development,
        "predictor_heldout_rows.csv": heldout,
        "predictor_evaluation_rows.csv": predictor["evaluation"],
        "predictor_prediction_rows.csv": predictor["predictions"],
        "predictor_failure_rows.csv": predictor["failures"],
        "predictor_calibration_rows.csv": predictor["calibration"],
    }
    for name, rows in files.items():
        write_csv(OUT / name, rows)
    (OUT / "predictor_model.json").write_text(json.dumps(predictor["model"], indent=2, sort_keys=True))
    (OUT / "outcome.json").write_text(json.dumps(outcome, indent=2, sort_keys=True))
    configuration = {
        "uses_frozen_regev_results_read_only": True,
        "regev_results_path": str(REGEV_RESULTS.relative_to(REPOSITORY)),
        "shor_results_path": str(SHOR_RESULTS.relative_to(ROOT)),
        "margin": MARGIN,
        "predictor_features": FEATURES,
        "shor_development_instances": SHOR_DEVELOPMENT,
        "known_factors_as_predictor_features": False,
        "known_orders_as_predictor_features": False,
        "row_counts": {name.removesuffix(".csv"): len(rows) for name, rows in files.items()},
    }
    (OUT / "configuration.json").write_text(json.dumps(configuration, indent=2, sort_keys=True))
    manifest_files = ["configuration.json", "predictor_model.json", "outcome.json", *files]
    completion = {
        "status": "complete", "outcome": outcome["outcome"],
        "row_counts": configuration["row_counts"],
        "sha256": {
            name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
            for name in manifest_files
        },
    }
    (OUT / "completion.json").write_text(json.dumps(completion, indent=2, sort_keys=True))
    print(json.dumps({"outcome": outcome, "row_counts": configuration["row_counts"]}, indent=2))


if __name__ == "__main__":
    main()


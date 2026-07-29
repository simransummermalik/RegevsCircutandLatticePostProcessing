#!/usr/bin/env python3
"""Verify the compact paper package against the frozen result manifest."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def close(actual: float, expected: float, tolerance: float = 5e-5) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{actual} != {expected} within {tolerance}")


def main() -> None:
    completion = json.loads((DATA / "completion.json").read_text(encoding="utf-8"))
    expected_hashes = completion["sha256"]
    packaged = {
        "certificate_gap_rows.csv": DATA / "certificate_gap_rows.csv",
        "configuration.json": DATA / "configuration.json",
        "configuration_rows.csv": DATA / "configuration_rows.csv",
        "controlled_examples.json": DATA / "controlled_examples.json",
        "margin_summary_rows.csv": DATA / "margin_summary_rows.csv",
        "paired_cluster_rows.csv": DATA / "paired_cluster_rows.csv",
        "per_N_rows.csv": DATA / "per_N_rows.csv",
        "proof_slack_rows.csv": DATA / "proof_slack_rows.csv",
        "certification_vs_recovery.png": ROOT / "figures" / "certification_vs_recovery.png",
    }
    for name, path in packaged.items():
        actual = sha256(path)
        expected = expected_hashes[name]
        if actual != expected:
            raise AssertionError(f"SHA-256 mismatch for {name}: {actual} != {expected}")

    config = json.loads((DATA / "configuration.json").read_text(encoding="utf-8"))
    assert config["freeze_version"] == "qft-certificate-gap-v1"
    assert config["heldout_N"] == [55, 65, 85, 95, 115, 119, 133, 161]
    assert config["M_values"] == [8, 16, 32]
    assert config["models"] == [
        "A_uniform_hard_box",
        "B_exact_finite_discrete_gaussian",
    ]
    assert config["roots"] == [2, 3]
    assert config["sample_count"] == 7
    assert config["replicates"] == 64
    assert config["master_seed"] == 2026071301
    assert config["loss_budget"] == 0.05
    assert config["noninferiority_margin"] == 0.1
    assert config["trial_rows"] == 12288

    gap_rows = read_csv("certificate_gap_rows.csv")
    assert len(gap_rows) == 6
    selected_layers: dict[tuple[int, str], int] = {}
    for row in gap_rows:
        assert int(row["original_certified_layers"]) == 0
        selected_layers[(int(row["M"]), row["model"])] = int(
            row["empirically_noninferior_layers"]
        )
    assert selected_layers == {
        (8, "A_uniform_hard_box"): 1,
        (8, "B_exact_finite_discrete_gaussian"): 1,
        (16, "A_uniform_hard_box"): 1,
        (16, "B_exact_finite_discrete_gaussian"): 2,
        (32, "A_uniform_hard_box"): 1,
        (32, "B_exact_finite_discrete_gaussian"): 2,
    }

    paired = read_csv("paired_cluster_rows.csv")
    per_n = read_csv("per_N_rows.csv")
    configurations = read_csv("configuration_rows.csv")
    expected_table = {
        (8, "A_uniform_hard_box"): (0.1191, 0.1074, -0.0117, -0.0273, 0.0, 2, 4),
        (8, "B_exact_finite_discrete_gaussian"): (0.0898, 0.0879, -0.0020, -0.0117, 0.0059, 2, 4),
        (16, "A_uniform_hard_box"): (0.1699, 0.1641, -0.0059, -0.0137, 0.0, 2, 4),
        (16, "B_exact_finite_discrete_gaussian"): (0.0840, 0.0469, -0.0371, -0.0742, 0.0, 6, 12),
        (32, "A_uniform_hard_box"): (0.1992, 0.1934, -0.0059, -0.0176, 0.0, 2, 4),
        (32, "B_exact_finite_discrete_gaussian"): (0.0703, 0.0527, -0.0176, -0.0352, -0.0039, 6, 12),
    }
    for key, omitted in selected_layers.items():
        M, model = key
        chosen = next(
            row
            for row in paired
            if int(row["M"]) == M
            and row["model"] == model
            and int(row["omitted_layers"]) == omitted
        )
        assert chosen["empirically_noninferior"] == "True"
        exact_values = [
            float(row["factor_probability"])
            for row in per_n
            if int(row["M"]) == M
            and row["model"] == model
            and int(row["omitted_layers"]) == 0
        ]
        approximate_values = [
            float(row["factor_probability"])
            for row in per_n
            if int(row["M"]) == M
            and row["model"] == model
            and int(row["omitted_layers"]) == omitted
        ]
        assert len(exact_values) == len(approximate_values) == 8
        exact_mean = sum(exact_values) / 8
        approximate_mean = sum(approximate_values) / 8
        expected = expected_table[key]
        close(exact_mean, expected[0])
        close(approximate_mean, expected[1])
        close(float(chosen["factor_mean_difference"]), expected[2])
        close(float(chosen["factor_cluster_ci95_low"]), expected[3])
        close(float(chosen["factor_cluster_ci95_high"]), expected[4])

        resource = next(
            row
            for row in configurations
            if int(row["M"]) == M
            and row["model"] == model
            and int(row["omitted_layers"]) == omitted
        )
        assert int(resource["cp_saving"]) == expected[5]
        assert int(resource["compiled_cx_saving"]) == expected[6]

    controlled = json.loads((DATA / "controlled_examples.json").read_text(encoding="utf-8"))
    loose = controlled["extreme_loose"]
    assert loose["N"] == 15 and loose["M"] == 4 and loose["cutoff"] == 0
    assert loose["original_certified"] is False
    assert loose["distribution_tv"] < 1e-30

    slack_rows = read_csv("proof_slack_rows.csv")
    assert len(slack_rows) == 912
    print("All packaged hashes, protocol fields, claims, table values, and resources pass.")


if __name__ == "__main__":
    main()

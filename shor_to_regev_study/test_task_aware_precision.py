import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import nbformat
import pytest

from shor_to_regev_study.task_aware_precision import (
    TaskAwarePrecisionRecord,
    binary_metrics,
    fit_logistic_predictor,
    paired_cluster_bootstrap,
)


ROOT = Path(__file__).resolve().parent


def test_cross_algorithm_schema_validation_and_flattening():
    record = TaskAwarePrecisionRecord(
        algorithm="Shor",
        instance_id="35:2",
        endpoint="factor",
        approximation_level=1,
        worst_case_certified=False,
        state_specific_certified=True,
        measured_tv=0.01,
        task_success_probability=0.8,
        exact_task_success_probability=0.82,
        task_difference=-0.02,
        resource_saving={"controlled_phase": 1, "cx": 2},
    )
    flattened = record.as_record()
    assert flattened["resource_controlled_phase"] == 1
    with pytest.raises(ValueError):
        TaskAwarePrecisionRecord(
            "Other", "x", "factor", 0, False, None, None, 0, 0, 0, {}
        )


def test_paired_bootstrap_uses_identical_indices_for_every_endpoint():
    values = np.asarray([0.1, -0.2, 0.3, 0.0])
    indices, draws = paired_cluster_bootstrap(
        {"order": values, "factor": 2 * values}, replicates=25, seed=11
    )
    assert indices.shape == (25, 4)
    assert np.allclose(draws["factor"], 2 * draws["order"])
    repeated_indices, repeated_draws = paired_cluster_bootstrap(
        {"order": values, "factor": 2 * values}, replicates=25, seed=11
    )
    assert np.array_equal(indices, repeated_indices)
    assert np.array_equal(draws["order"], repeated_draws["order"])


def test_empirical_predictor_is_deterministic_and_reports_failures():
    rows = [
        {"tv": 0.01, "layers": 0.0},
        {"tv": 0.03, "layers": 1.0},
        {"tv": 0.3, "layers": 2.0},
        {"tv": 0.5, "layers": 3.0},
    ]
    labels = [1, 1, 0, 0]
    first = fit_logistic_predictor(rows, labels, ("tv", "layers"))
    second = fit_logistic_predictor(rows, labels, ("tv", "layers"))
    assert first == second
    probabilities = first.predict_proba(rows)
    assert np.allclose(probabilities, second.predict_proba(rows))
    metrics = binary_metrics(labels, probabilities)
    assert metrics["rows"] == 4
    assert "false_approvals" in metrics


def test_frozen_shor_configuration_has_complete_heldout_coverage():
    result_root = ROOT / "results" / "shor_qft_robustness"
    configuration = json.loads((result_root / "configuration.json").read_text())
    expected = {
        "35:2", "35:11", "39:2", "51:2",
        "55:2", "65:3", "77:8", "91:9",
    }
    assert {f"{N}:{base}" for N, base in configuration["heldout_instances"]} == expected
    rows = list(csv.DictReader((result_root / "configuration_rows.csv").open()))
    observed = {
        (
            row["instance_id"], int(row["shots"]),
            float(row["readout_bitflip_probability"]), int(row["omitted_layers"]),
        )
        for row in rows
    }
    required = {
        (instance, shots, readout, omitted)
        for instance in expected
        for shots in (4, 8, 16)
        for readout in (0.0, 0.01)
        for omitted in (0, 1, 2, 3)
    }
    assert observed == required
    assert len(rows) == 192


@pytest.mark.parametrize(
    "directory",
    ("shor_experiments", "shor_qft_robustness", "cross_algorithm_precision"),
)
def test_result_manifest_hashes(directory):
    root = ROOT / "results" / directory
    completion = json.loads((root / "completion.json").read_text())
    assert completion["status"] == "complete"
    for name, expected in completion["sha256"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected


def test_cross_study_uses_no_forbidden_predictor_features_and_records_outcome():
    root = ROOT / "results" / "cross_algorithm_precision"
    model = json.loads((root / "predictor_model.json").read_text())
    assert not model["uses_factors"]
    assert not model["uses_true_orders"]
    assert not model["uses_success_as_feature"]
    forbidden = {"factor", "true_order", "success", "task_difference"}
    assert not forbidden.intersection(model["feature_names"])
    outcome = json.loads((root / "outcome.json").read_text())
    assert outcome["outcome"] in {"A", "B", "C", "D", "E"}


def test_exact_result_row_counts_and_executed_notebook():
    shor_completion = json.loads(
        (ROOT / "results" / "shor_qft_robustness" / "completion.json").read_text()
    )
    assert shor_completion["row_counts"] == {
        "bootstrap_draw_rows": 120000,
        "configuration_rows": 192,
        "leave_one_instance_out_rows": 144,
        "margin_sensitivity_rows": 96,
        "margin_summary_rows": 24,
        "paired_exact_test_rows": 36,
        "paired_rows": 24,
        "per_instance_rows": 192,
        "trial_rows": 12288,
    }
    cross_completion = json.loads(
        (ROOT / "results" / "cross_algorithm_precision" / "completion.json").read_text()
    )
    assert cross_completion["row_counts"]["task_aware_records"] == 768
    assert cross_completion["row_counts"]["predictor_failure_rows"] == 319

    notebook = nbformat.read(ROOT / "Shor_to_Regev_Demonstration.ipynb", as_version=4)
    nbformat.validate(notebook)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code_cells
    assert all(cell.execution_count is not None for cell in code_cells)
    assert not any(
        output.get("output_type") == "error"
        for cell in code_cells
        for output in cell.outputs
    )

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from regev_research.quotient_predictors import (
    EXACT_A_MODEL,
    EXACT_B_MODEL,
    QUOTIENT_GAP_METHOD,
    STANDARD_REGEV_METHOD,
    analyze_predictor_comparison,
    join_standard_and_gap_rows,
    tidy_predictor_rows,
)


MODEL_C = "C_theorem_consistent_noisy_dual"


def _paired_rows(
    N,
    model,
    replicate,
    sample_count,
    *,
    gap,
    success,
    gap_censored=False,
    relation_censored=False,
    entropy=None,
):
    key = {
        "N": N,
        "model": model,
        "replicate": replicate,
        "sample_count": sample_count,
    }
    standard = {
        **key,
        "method": STANDARD_REGEV_METHOD,
        "status": "completed",
        "factor_success": success,
        # Deliberately contradictory: the comparison must use the standard
        # row's endpoint, never the scoring-only row's copied recovery result.
        "quotient_gap_log2_L0_to_useful_ratio": -gap,
    }
    scoring = {
        **key,
        "method": QUOTIENT_GAP_METHOD,
        "status": "completed",
        "factor_success": 1 - success,
        "quotient_gap_log2_L0_to_useful_ratio": gap,
        "quotient_gap_L0_censored": gap_censored,
        "quotient_gap_useful_censored": False,
        "predictor_bounded_product_diversity": float(N % 13),
        "predictor_empirical_fourier_joint_entropy_bits": entropy,
        "predictor_empirical_fourier_covariance_effective_rank": 1.0 + N / 100,
        "predictor_relation_lattice_determinant": N + 5,
        "predictor_ordinary_shortest_relation_squared_norm": 2 + N % 7,
        "predictor_ordinary_shortest_relation_censored": relation_censored,
        "predictor_exact_fourier_joint_entropy_bits": (
            4.0 + N / 100 if model in {EXACT_A_MODEL, EXACT_B_MODEL} else None
        ),
    }
    return standard, scoring


def _synthetic_rows():
    rows = []
    Ns = (15, 21, 35, 77)
    gaps = (-2.0, -0.5, 0.5, 2.0)
    for model in (EXACT_A_MODEL, EXACT_B_MODEL, MODEL_C):
        for N_index, (N, base_gap) in enumerate(zip(Ns, gaps)):
            for replicate in (0, 1):
                for sample_count in (7, 8):
                    gap = base_gap + 0.03 * replicate + 0.01 * (sample_count - 7)
                    standard, scoring = _paired_rows(
                        N,
                        model,
                        replicate,
                        sample_count,
                        gap=gap,
                        success=int(gap > 0),
                        gap_censored=(
                            model == EXACT_A_MODEL
                            and N_index == 0
                            and replicate == 0
                            and sample_count == 7
                        ),
                        relation_censored=(
                            model == EXACT_B_MODEL
                            and N_index == 3
                            and replicate == 1
                            and sample_count == 8
                        ),
                        entropy=(
                            None
                            if model == MODEL_C
                            and N_index == 0
                            and replicate == 0
                            and sample_count == 7
                            else 1.5 + N_index + 0.1 * replicate + 0.01 * sample_count
                        ),
                    )
                    # Reverse method order in alternating cells to establish
                    # that the join is key based rather than positional.
                    rows.extend(
                        (scoring, standard)
                        if (N_index + replicate + sample_count) % 2
                        else (standard, scoring)
                    )
    return rows


def _scope(analysis, model):
    return next(scope for scope in analysis["scopes"] if scope["model"] == model)


def _predictor(scope, name):
    return next(row for row in scope["predictors"] if row["predictor"] == name)


def test_join_is_keyed_and_uses_only_standard_regev_outcome():
    standard, scoring = _paired_rows(
        15, EXACT_A_MODEL, 0, 7, gap=1.25, success=0, entropy=2.0
    )
    extra_standard, _ = _paired_rows(
        21, EXACT_A_MODEL, 0, 7, gap=-1, success=1, entropy=2.0
    )
    joined = join_standard_and_gap_rows(
        [scoring, {"method": "another_arm"}, standard, extra_standard]
    )
    assert len(joined.rows) == 1
    assert joined.rows[0]["outcome_standard_regev_factor_success"] == 0
    assert joined.rows[0]["quotient_gap_log2_L0_to_useful_ratio"] == 1.25
    assert joined.diagnostics["unmatched_standard_row_count"] == 1
    assert joined.diagnostics["ignored_other_method_row_count"] == 1

    with pytest.raises(ValueError, match="duplicate"):
        join_standard_and_gap_rows([standard, dict(standard), scoring])

    standard_with_seed = {**standard, "batch_seed": 10}
    scoring_with_seed = {**scoring, "batch_seed": 11}
    with pytest.raises(ValueError, match="batch_seed"):
        join_standard_and_gap_rows([standard_with_seed, scoring_with_seed])


def test_clustered_analysis_is_deterministic_and_reports_missingness_censoring():
    rows = _synthetic_rows()
    first = analyze_predictor_comparison(rows, bootstrap_resamples=80, seed=19)
    second = analyze_predictor_comparison(rows, bootstrap_resamples=80, seed=19)
    assert first == second
    assert first["join_diagnostics"]["matched_row_count"] == 48

    pooled = _scope(first, None)
    gap = _predictor(pooled, "quotient_gap_log2_ratio")
    assert gap["coverage"]["predictor_censored_rows"] == 1
    assert gap["coverage"]["usable_uncensored_complete_rows"] == 47
    assert gap["N_level_spearman"]["N_clusters"] == 4
    assert gap["N_level_spearman"]["rho"] is not None
    assert gap["leave_one_N_out_logistic"]["N_folds"] == 4
    assert gap["leave_one_N_out_logistic"]["prediction_rows"] == 47
    # Whole-N extrapolation is deliberately harder than a shuffled row split;
    # the score need not be perfect even though the fixed threshold is here.
    assert gap["leave_one_N_out_logistic"]["auc"] > 0.5
    assert all(
        not fold["fit_uses_heldout_N"]
        and fold["heldout_N"] not in fold["training_N"]
        for fold in gap["leave_one_N_out_logistic"]["folds"]
    )

    empirical = _predictor(pooled, "empirical_fourier_entropy")
    assert empirical["coverage"]["predictor_missing_rows"] == 1
    ordinary = _predictor(pooled, "ordinary_shortest_relation_squared_norm")
    assert ordinary["coverage"]["predictor_censored_rows"] == 1

    threshold = pooled["natural_quotient_threshold"]
    assert threshold["threshold"] == 0
    assert threshold["operator"] == ">"
    assert threshold["threshold_was_tuned"] is False
    assert threshold["evaluated_rows"] == 47
    assert threshold["sensitivity"] == pytest.approx(1.0)
    assert threshold["specificity"] == pytest.approx(1.0)
    assert threshold["balanced_accuracy"] == pytest.approx(1.0)


def test_exact_entropy_is_extra_predictor_only_for_exact_models():
    analysis = analyze_predictor_comparison(
        _synthetic_rows(), bootstrap_resamples=20, seed=7
    )
    pooled = _scope(analysis, None)
    exact = _predictor(pooled, "exact_fourier_entropy")
    assert exact["coverage"]["eligible_rows"] == 32
    assert exact["coverage"]["structurally_ineligible_rows"] == 16
    assert _predictor(_scope(analysis, EXACT_A_MODEL), "exact_fourier_entropy")
    assert _predictor(_scope(analysis, EXACT_B_MODEL), "exact_fourier_entropy")
    assert "exact_fourier_entropy" not in {
        row["predictor"] for row in _scope(analysis, MODEL_C)["predictors"]
    }

    tidy = tidy_predictor_rows(analysis)
    gap_row = next(
        row
        for row in tidy
        if row["scope"] == "pooled"
        and row["predictor"] == "quotient_gap_log2_ratio"
    )
    assert gap_row["natural_threshold"] == 0
    assert gap_row["threshold_balanced_accuracy"] == pytest.approx(1.0)
    assert all(
        row["natural_threshold"] is None
        for row in tidy
        if row["predictor"] != "quotient_gap_log2_ratio"
    )


def test_cli_reads_csv_and_writes_json_and_tidy_csv_without_running_holdout(tmp_path):
    rows = _synthetic_rows()
    columns = sorted({column for row in rows for column in row})
    trial_path = tmp_path / "trial_rows.csv"
    with trial_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    output = tmp_path / "analysis"
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_quotient_study.py",
            "--trial-rows",
            str(trial_path),
            "--output",
            str(output),
            "--bootstrap-resamples",
            "20",
            "--seed",
            "5",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    json_path = output / "predictor_comparison.json"
    csv_path = output / "predictor_comparison.csv"
    assert str(json_path) in completed.stdout
    assert json_path.exists() and csv_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["frozen_contract"]["recovery_tuned_or_rerun"] is False
    with csv_path.open(newline="", encoding="utf-8") as handle:
        tidy = list(csv.DictReader(handle))
    assert tidy
    assert {row["scope"] for row in tidy} == {"pooled", "model"}

import inspect
from dataclasses import replace
from fractions import Fraction

from regev_research.quotient_experiments import (
    FROZEN_QUOTIENT_EXPERIMENT,
    UNIFORM_HARD_BOX_MODEL,
    FrozenSampleBatch,
)
from regev_research.quotient_recovery import RecoveryBudget
from regev_research.quotient_study import (
    ADAPTIVE_SAMPLING_NO_DEFLATION,
    COMMON_EXACT_NORM_ENUMERATION,
    COMPLETE_SEQUENTIAL_LDAR,
    QUOTIENT_GAP_SCORING_ONLY,
    RANDOM_GENUINE_EXTRA_SAMPLES,
    ROOT_BLIND_POSTHOC,
    RV_STRUCTURED_COMPARATOR,
    aggregate_per_n_rows,
    build_study_outputs,
    evaluate_factor_blind_batch,
    n_cluster_bootstrap_mean,
    nested_prefixes,
    paired_n_level_comparisons,
    study_configuration,
    write_csv_atomic,
    write_json_atomic,
)


def _toy_freeze():
    return replace(
        FROZEN_QUOTIENT_EXPERIMENT,
        recovery_budget=RecoveryBudget(
            enumeration_rows=3,
            coefficient_bound=1,
            max_support=2,
            max_nodes=10,
            max_materialized_nodes=100,
        ),
        ldar_stage_budget=RecoveryBudget(
            enumeration_rows=3,
            coefficient_bound=1,
            max_support=2,
            max_nodes=5,
            max_materialized_nodes=100,
        ),
        quotient_relation_box_bound=1,
        bootstrap_resamples_at_N_level=50,
    )


def _toy_batch_factory(counter):
    def factory(family, model_label, seed, freeze):
        counter.append((family.N, model_label, seed))
        rows = tuple(
            (index % 8, (2 * index) % 8, (3 * index) % 8)
            for index in range(11)
        )
        return FrozenSampleBatch(
            model_label=model_label,
            samples=rows,
            modulus=8,
            reconstruction_scale=Fraction(1, 1),
            seed=seed,
            sample_count=11,
            latent_samples=None,
            metadata=(("generator", "unit-test fixed full batch"),),
        )

    return factory


def test_factor_blind_cell_generates_one_batch_and_reuses_nested_prefixes():
    signature = inspect.signature(evaluate_factor_blind_batch)
    assert not ({"p", "q", "factors", "orders"} & set(signature.parameters))
    counter = []
    freeze = _toy_freeze()
    methods = (
        COMMON_EXACT_NORM_ENUMERATION,
        ADAPTIVE_SAMPLING_NO_DEFLATION,
        ROOT_BLIND_POSTHOC,
        QUOTIENT_GAP_SCORING_ONLY,
        RANDOM_GENUINE_EXTRA_SAMPLES,
    )
    rows = evaluate_factor_blind_batch(
        15,
        0,
        UNIFORM_HARD_BOX_MODEL,
        0,
        freeze=freeze,
        batch_factory=_toy_batch_factory(counter),
        method_labels=methods,
    )
    assert len(counter) == 1
    assert len(rows) == len(methods) * 5
    assert {row["sample_count"] for row in rows} == {7, 8, 9, 10, 11}
    assert all(row["batch_full_sample_count"] == 11 for row in rows)
    common = {
        row["sample_count"]: row
        for row in rows
        if row["method"] == COMMON_EXACT_NORM_ENUMERATION
    }
    scored = {
        row["sample_count"]: row
        for row in rows
        if row["method"] == QUOTIENT_GAP_SCORING_ONLY
    }
    assert all(scored[count]["factor_pair"] == common[count]["factor_pair"] for count in common)
    assert all(scored[count]["recovery_object_reused_without_rerun"] for count in scored)
    blind = [row for row in rows if row["method"] == ROOT_BLIND_POSTHOC]
    assert all(row["resource_root_classifications"] == 0 for row in blind)
    assert all(row["root_metadata_used_only_after_search"] for row in blind)
    assert all("sequential_cumulative_factor_success" in row for row in rows)


def test_complete_ldar_uses_common_natural_source_order_in_toy_cell():
    rows = evaluate_factor_blind_batch(
        15,
        0,
        UNIFORM_HARD_BOX_MODEL,
        0,
        freeze=_toy_freeze(),
        batch_factory=_toy_batch_factory([]),
        method_labels=(COMPLETE_SEQUENTIAL_LDAR,),
    )
    assert len(rows) == 5
    assert all(row["method"] == COMPLETE_SEQUENTIAL_LDAR for row in rows)
    completed = [row for row in rows if row["status"] == "completed"]
    assert all(row["source_sample_indices_used"] == tuple(range(row["sample_count"])) for row in completed)
    assert all(row["resource_nodes_visited"] <= 10 for row in completed)
    assert all(row["resource_fourier_precision_bits"] == 3 for row in rows)
    assert all(row["resource_quantum_circuit_equivalent_executions"] == row["sample_count"] for row in rows)


def test_RV_comparator_charges_full_pool_not_selected_target():
    rows = evaluate_factor_blind_batch(
        15,
        0,
        UNIFORM_HARD_BOX_MODEL,
        0,
        freeze=_toy_freeze(),
        batch_factory=_toy_batch_factory([]),
        method_labels=(RV_STRUCTURED_COMPARATOR,),
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["sample_count"] == 11
    assert row["rv_pool_sample_count"] == 11
    assert row["rv_selected_target_count"] == 7
    assert row["resource_quantum_circuit_equivalent_executions"] == 11
    assert row["resource_lattice_dimension"] == 10  # d + selected target count


def test_nested_prefix_helper_never_draws_or_reorders():
    batch = _toy_batch_factory([])(
        type("Family", (), {"N": 15})(), UNIFORM_HARD_BOX_MODEL, 3, _toy_freeze()
    )
    prefixes = nested_prefixes(batch, (7, 8, 9, 10, 11))
    assert prefixes[7] == batch.samples[:7]
    assert prefixes[11] == batch.samples
    assert prefixes[8][:7] == prefixes[7]


def _synthetic_trial_rows():
    rows = []
    for N in (101, 103, 107):
        for method in (COMMON_EXACT_NORM_ENUMERATION, ADAPTIVE_SAMPLING_NO_DEFLATION):
            for replicate in range(5):
                first = 8 if method == ADAPTIVE_SAMPLING_NO_DEFLATION else 9
                for count in (7, 8, 9, 10, 11):
                    cumulative = int(count >= first)
                    rows.append(
                        {
                            "N": N,
                            "model": UNIFORM_HARD_BOX_MODEL,
                            "method": method,
                            "ablation_label": "test",
                            "replicate": replicate,
                            "sample_count": count,
                            "status": "completed",
                            "factor_success": cumulative,
                            "marginal_prefix_factor_success": cumulative,
                            "sequential_cumulative_factor_success": cumulative,
                            "sample_to_first_factor": first,
                            "resource_nodes_visited": 5,
                        }
                    )
    return rows


def test_N_level_target_threshold_bootstrap_and_paired_comparisons_are_deterministic():
    trials = _synthetic_trial_rows()
    per_n = aggregate_per_n_rows(trials, target_probability=Fraction(4, 5))
    adaptive = [
        row
        for row in per_n
        if row["method"] == ADAPTIVE_SAMPLING_NO_DEFLATION
    ]
    assert {row["target_p_sample_threshold"] for row in adaptive} == {8}
    first = n_cluster_bootstrap_mean({101: 1.0, 103: 0.0, 107: 1.0}, resamples=50, seed=9)
    second = n_cluster_bootstrap_mean({101: 1.0, 103: 0.0, 107: 1.0}, resamples=50, seed=9)
    assert first == second
    comparisons = paired_n_level_comparisons(
        per_n, resamples=50, seed=10
    )
    sample_nine = next(
        row
        for row in comparisons
        if row["endpoint"].startswith("paired N-level factor")
        and row["method"] == ADAPTIVE_SAMPLING_NO_DEFLATION
        and row["sample_count"] == 9
    )
    assert sample_nine["N_clusters"] == 3
    assert sample_nine["ties"] == 3


def test_configuration_and_atomic_writers_do_not_claim_holdout_completion(tmp_path):
    configuration = study_configuration(_toy_freeze())
    assert configuration["heldout_executed"] is False
    assert len(configuration["heldout_manifest"]) == 20
    assert set(configuration["source_sha256"]) == {
        "quotient_study",
        "quotient_recovery",
        "quotient_metrics",
        "quotient_experiments",
        "rv_filter",
    }
    write_json_atomic(tmp_path / "configuration.json", configuration)
    write_csv_atomic(tmp_path / "rows.csv", [{"N": 15, "pair": (3, 5)}])
    assert (tmp_path / "configuration.json").exists()
    assert (tmp_path / "rows.csv").read_text().startswith("N,pair")
    study = build_study_outputs(_synthetic_trial_rows(), freeze=_toy_freeze())
    assert study.trial_rows and study.per_n_rows and study.resource_rows

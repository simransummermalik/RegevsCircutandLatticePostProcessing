from fractions import Fraction
import inspect

from regev_research.core import RootedBaseFamily
from regev_research.quotient_recovery import RecoveryBudget
from regev_research.rv_filter import (
    RV_COMPARATOR_ID,
    RV_COMPARATOR_LABEL,
    build_rv_filter_lattice,
    reduce_rv_filter_lattice,
    rv_filter_then_short_combination_recovery,
    rv_structured_finite_filter,
    rv_theorem_status,
)


def _budget():
    return RecoveryBudget(
        enumeration_rows=4,
        coefficient_bound=1,
        max_support=4,
        max_nodes=100,
        max_materialized_nodes=1_000,
    )


def test_exact_rational_clearing_matches_transposed_RV_H():
    pool = [(1, 2), (3, 4), (5, 6)]
    embedding = build_rv_filter_lattice(
        pool, sample_indices=(0, 1), modulus=8, scale=Fraction(3, 2)
    )

    assert embedding.clearing_factor == 16
    assert embedding.integer_row_basis == (
        (24, 0, 0, 0),
        (0, 24, 0, 0),
        (3, 6, 16, 0),
        (9, 12, 0, 16),
    )
    reduction = reduce_rv_filter_lattice(embedding)
    transform = reduction.transform_rows[0]
    assert transform[:2] == reduction.beta
    assert transform[2:] == reduction.sample_coefficients


def test_frozen_11_by_3_filter_is_deterministic_but_not_theorem_guaranteed():
    pool = [(0, 0, 0)] * 11
    first = rv_structured_finite_filter(pool, 64, 13, target_count=7)
    second = rv_structured_finite_filter(pool, 64, 13, target_count=7)

    assert first.success and second.success
    assert first.selected_indices == second.selected_indices
    assert len(first.selected_indices) == 7
    assert first.method == RV_COMPARATOR_ID
    assert first.comparator_label == RV_COMPARATOR_LABEL
    assert first.termination_reason == "target_count_reached"
    assert all(row.E_indices == tuple(sorted(row.E_indices)) for row in first.transcript)
    assert first.resources.reductions == len(first.transcript) > 0
    assert first.resources.peak_memory_estimate_bytes > 0

    theorem = first.theorem_status
    assert theorem.alpha == Fraction(11, 3)
    assert theorem.gamma == Fraction(7, 3)
    assert not theorem.alpha_gamma_combinatorial_inequality
    assert not theorem.asymptotic_guarantee_applicable
    assert not theorem.well_spread_error_model_checked


def test_no_progress_returns_a_finite_failure_reason():
    result = rv_structured_finite_filter(
        [(0, 0, 0)] * 11,
        64,
        Fraction(1, 100),
        target_count=7,
    )

    assert not result.success
    assert result.selected_indices == ()
    assert result.termination_reason == "no_progress_shortest_vector_has_zero_sample_support"
    assert len(result.transcript) == 1
    assert result.transcript[0].sample_coefficients == (0, 0, 0, 0)


def test_filter_api_has_no_factor_root_or_label_side_channel():
    parameters = inspect.signature(rv_structured_finite_filter).parameters
    forbidden = {
        "N",
        "family",
        "factors",
        "roots",
        "orders",
        "relation_oracle",
        "corruption_labels",
    }
    assert not forbidden & set(parameters)
    status = rv_theorem_status(11, 3, 7)
    assert status.comparator_label == "RV-structured finite comparator"
    assert any("inequality is false" in reason for reason in status.reasons)


def test_wrapper_passes_selected_fixed_pool_rows_to_common_recovery():
    family = RootedBaseFamily.from_roots(15, [2])
    pool = [(8,)] * 6
    wrapped = rv_filter_then_short_combination_recovery(
        family,
        pool,
        16,
        16,
        target_count=5,
        budget=_budget(),
    )

    assert wrapped.filter_result.success
    assert wrapped.filter_result.selected_indices == (0, 1, 2, 3, 4)
    assert wrapped.recovery_result is not None
    assert wrapped.recovery_result.factor_pair == (3, 5)
    assert wrapped.recovery_result.resources.input_samples == 5
    assert wrapped.termination_reason == "filter_succeeded_common_recovery_completed"


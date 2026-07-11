from fractions import Fraction

import pytest

from regev_research.core import RootedBaseFamily
from regev_research.quotient import (
    QuotientElement,
    build_l0_quotient,
    classify_quotient_candidate,
    factor_yielding_quotient_gap,
)


def test_smith_invariants_retain_torsion_and_redundancy():
    family = RootedBaseFamily.from_roots(15, [2, 2])
    quotient = build_l0_quotient(family, [(2, -2), (4, -4)])

    assert quotient.rank == 1
    assert quotient.free_rank == 1
    assert quotient.smith_diagonal == (2,)
    assert quotient.torsion_invariant_factors == (2,)
    assert quotient.torsion_order == 2
    assert quotient.torsion_exponent == 2
    assert quotient.saturation_index == 2
    assert quotient.redundant_direction_count == 1
    assert quotient.abstract_decomposition == (1, (2,))

    torsion_generator = quotient.reduce((1, -1))
    assert not quotient.is_zero(torsion_generator)
    assert quotient.is_zero(quotient.add(torsion_generator, torsion_generator))


def test_coset_reduction_witness_lift_and_group_operations_are_exact():
    family = RootedBaseFamily.from_roots(15, [2, 2])
    quotient = build_l0_quotient(family, [(2, -2), (4, -4)])
    vector = (11, -7)
    reduction = quotient.reduce_with_witness(vector)

    assert quotient.lift(reduction.element, reduction.hnf_coefficients) == vector
    assert quotient.equivalent(vector, (17, -13))
    assert quotient.reduce(quotient.lift(reduction.element, [9])) == reduction.element
    assert quotient.is_zero(
        quotient.add(reduction.element, quotient.negate(reduction.element))
    )
    forged = QuotientElement(quotient.quotient_key, (2, -2))
    with pytest.raises(ValueError, match="canonical"):
        quotient.lift(forged)


def test_non_axis_aligned_rank_deficient_Hermite_chart_round_trips():
    # Roots 1 make every ambient vector an L0 direction, allowing a direct
    # stress test of the integer quotient convention.
    family = RootedBaseFamily.from_roots(15, [1, 1, 1])
    quotient = build_l0_quotient(family, [(2, 4, 6), (0, 6, 9)])

    assert quotient.rank == 2
    assert quotient.free_rank == 1
    assert quotient.smith_diagonal == (1, 6)
    assert quotient.torsion_invariant_factors == (6,)
    reduction = quotient.reduce_with_witness((-17, 23, -31))
    assert quotient.lift(reduction.element, reduction.hnf_coefficients) == (
        -17,
        23,
        -31,
    )
    assert all(
        0 <= reduction.element.representative[pivot] < modulus
        for pivot, modulus in zip(
            quotient.hnf_pivot_columns, quotient.hnf_pivot_moduli, strict=True
        )
    )


def test_full_rank_quotient_reports_finite_torsion_group():
    family = RootedBaseFamily.from_roots(15, [2, 2])
    quotient = build_l0_quotient(family, [(4, 0), (0, 4)])

    assert quotient.is_finite
    assert quotient.free_rank == 0
    assert quotient.torsion_invariant_factors == (4, 4)
    assert quotient.torsion_order == 16
    assert quotient.torsion_exponent == 4
    assert quotient.covolume_squared_in_span == 16**2


def test_only_nonzero_verified_L0_directions_can_be_deflated():
    family = RootedBaseFamily.from_roots(15, [2])
    with pytest.raises(ValueError, match="zero"):
        build_l0_quotient(family, [(0,)])
    with pytest.raises(ValueError, match="verified L0"):
        build_l0_quotient(family, [(1,)])  # Not in L.
    with pytest.raises(ValueError, match="verified L0"):
        build_l0_quotient(family, [(2,)])  # In L but factor-yielding.


def test_classification_is_constant_on_L0_cosets_without_known_factors():
    family = RootedBaseFamily.from_roots(15, [2])
    quotient = build_l0_quotient(family, [(4,)])

    invalid = classify_quotient_candidate(quotient, (1,))
    invalid_shift = classify_quotient_candidate(quotient, (5,))
    factor = classify_quotient_candidate(quotient, (2,))
    factor_shift = classify_quotient_candidate(quotient, (6,))
    trivial = classify_quotient_candidate(quotient, (4,))

    assert invalid.category == invalid_shift.category == "invalid"
    assert invalid.element == invalid_shift.element
    assert factor.category == factor_shift.category == "factor_yielding"
    assert factor.element == factor_shift.element
    assert factor.factor_pair == factor_shift.factor_pair == (3, 5)
    assert trivial.category == "L0"
    assert quotient.is_zero(trivial.element)


def test_factor_yielding_gap_is_exact_observed_coset_statistic():
    family = RootedBaseFamily.from_roots(15, [2])
    quotient = build_l0_quotient(family, [(8,)])
    gap = factor_yielding_quotient_gap(
        quotient,
        [
            (10,),  # Same factor-yielding coset as 2, but a longer lift.
            (2,),
            (4,),   # Nonzero L0 coset.
            (8,),   # Known zero coset, excluded.
            (1,),   # Invalid, counted separately.
        ],
    )

    assert gap.shortest_factor_yielding_squared_norm == 4
    assert gap.shortest_nonzero_L0_squared_norm == 16
    assert gap.signed_squared_gap == 12
    assert gap.L0_to_factor_squared_ratio == Fraction(4, 1)
    assert gap.shortest_factor_yielding_lift == (2,)
    assert gap.shortest_nonzero_L0_lift == (4,)
    assert gap.excluded_zero_coset_lifts == 1
    assert gap.invalid_lifts == 1
    assert gap.distinct_nonzero_relation_cosets == 2


def test_empty_deflation_is_supported_and_has_no_torsion():
    family = RootedBaseFamily.from_roots(15, [2, 2])
    quotient = build_l0_quotient(family, [])

    assert quotient.rank == 0
    assert quotient.free_rank == 2
    assert quotient.is_torsion_free
    assert quotient.torsion_order == 1
    assert quotient.reduce((3, -5)).representative == (3, -5)

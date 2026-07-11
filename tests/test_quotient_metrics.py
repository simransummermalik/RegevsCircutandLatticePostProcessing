from fractions import Fraction

import pytest

from regev_research.core import RootedBaseFamily, modular_product
from regev_research.quotient_metrics import (
    POSTHOC_SCOPE,
    bounded_base_lambda_metrics,
    bounded_sample_augmented_quotient_gap,
    exact_l0_hnf,
)


def test_exact_l0_hnf_for_N15_has_verified_signed_image_index():
    family = RootedBaseFamily.from_roots(15, [2])
    result = exact_l0_hnf(family)

    assert result.row_hnf_basis == ((4,),)
    assert result.signed_image_classes == (1, 2, 4, 7)
    assert result.signed_image_size == result.determinant == result.verified_index == 4
    assert result.cayley_edge_count == 8
    assert not result.factors_or_orders_supplied
    assert result.scope == POSTHOC_SCOPE


def test_multidimensional_l0_hnf_rows_are_exact_and_index_checked():
    family = RootedBaseFamily.from_roots(437, [2, 3, 326])
    result = exact_l0_hnf(family)

    assert len(result.row_hnf_basis) == 3
    assert result.determinant == result.signed_image_size
    assert result.signed_image_size <= 437
    for row in result.row_hnf_basis:
        assert modular_product(437, family.roots, row) in (1, 436)
        assert modular_product(437, family.bases, row) == 1


def test_base_only_lambda_metrics_separate_relation_L0_and_useful_minima():
    family = RootedBaseFamily.from_roots(15, [2])
    metrics = bounded_base_lambda_metrics(family, relation_bound=4)

    assert metrics.candidate_count == 4
    assert metrics.relation_count == 2
    assert metrics.L0_count == 1
    assert metrics.useful_count == 1
    assert metrics.shortest_relation_squared_norm == 4
    assert metrics.shortest_relation_witness == (2,)
    assert metrics.shortest_useful_squared_norm == 4
    assert metrics.shortest_useful_witness == (2,)
    assert metrics.shortest_nonzero_L0_squared_norm == 16
    assert metrics.shortest_nonzero_L0_witness == (4,)
    assert metrics.signed_squared_gap == 12
    assert metrics.L0_to_useful_squared_ratio == Fraction(4, 1)
    assert not metrics.shortest_relation_censored
    assert not metrics.shortest_L0_censored
    assert not metrics.shortest_useful_censored
    assert metrics.scope == POSTHOC_SCOPE


def test_sample_augmented_gap_uses_exact_fraction_torus_distances():
    family = RootedBaseFamily.from_roots(15, [2])
    metrics = bounded_sample_augmented_quotient_gap(
        family,
        samples=[(2,)],
        sample_modulus=8,
        scale=Fraction(2, 1),
        relation_bound=4,
    )

    # z=2: 4 + 2^2 * dist(4/8,Z)^2 = 4 + 1 = 5.
    assert metrics.shortest_useful_augmented_squared_norm == Fraction(5, 1)
    assert metrics.shortest_useful_witness == (2,)
    # z=4 has zero torus residual and is the first nonzero L0 relation.
    assert metrics.shortest_nonzero_L0_augmented_squared_norm == Fraction(16, 1)
    assert metrics.shortest_nonzero_L0_witness == (4,)
    assert metrics.shortest_relation_augmented_squared_norm == Fraction(5, 1)
    assert metrics.signed_augmented_squared_gap == Fraction(11, 1)
    assert metrics.L0_to_useful_augmented_squared_ratio == Fraction(16, 5)
    assert metrics.log2_L0_to_useful_ratio is not None
    assert not metrics.shortest_useful_censored
    assert not metrics.shortest_L0_censored


def test_absent_bounded_relations_are_explicitly_censored():
    family = RootedBaseFamily.from_roots(15, [2])
    base = bounded_base_lambda_metrics(family, relation_bound=1)
    augmented = bounded_sample_augmented_quotient_gap(
        family, [(0,)], 8, 1, relation_bound=1
    )

    assert base.relation_count == 0
    assert base.shortest_relation_squared_norm is None
    assert base.shortest_relation_censored
    assert base.shortest_L0_censored
    assert base.shortest_useful_censored
    assert augmented.relation_count == 0
    assert augmented.shortest_relation_augmented_squared_norm is None
    assert augmented.shortest_relation_censored
    assert augmented.shortest_L0_censored
    assert augmented.shortest_useful_censored


def test_metrics_reject_floats_bad_samples_and_unbounded_work():
    family = RootedBaseFamily.from_roots(15, [2])
    with pytest.raises(TypeError, match="Fraction"):
        bounded_sample_augmented_quotient_gap(family, [(0,)], 8, 1.5, 2)
    with pytest.raises(ValueError, match="coordinates"):
        bounded_sample_augmented_quotient_gap(family, [(8,)], 8, 1, 2)
    with pytest.raises(ValueError, match="limit"):
        bounded_base_lambda_metrics(
            RootedBaseFamily.from_roots(15, [2, 7]),
            relation_bound=10,
            max_candidates=10,
        )

from fractions import Fraction

import pytest

from regev_research.core import RootedBase, RootedBaseFamily, classify_square_relation
from regev_research.lattice import (
    LLLReduction,
    build_augmented_lattice,
    claim_5_1_prefix,
    regev_lattice_postprocess,
)


def test_integer_basis_is_exact_clearing_of_regev_column_basis():
    samples = [[1], [3], [5], [7], [0]]
    embedding = build_augmented_lattice(samples, 8, scale=Fraction(3, 2))

    assert embedding.scale == Fraction(3, 2)
    assert embedding.clearing_factor == 16
    assert embedding.integer_row_basis == (
        (16, 3, 9, 15, 21, 0),
        (0, 24, 0, 0, 0, 0),
        (0, 0, 24, 0, 0, 0),
        (0, 0, 0, 24, 0, 0),
        (0, 0, 0, 0, 24, 0),
        (0, 0, 0, 0, 0, 24),
    )


def test_end_to_end_dual_samples_recover_L_minus_L0_and_factor():
    # For a=4 mod 15, L=2Z and L*/Z={0,1/2}.  Five copies of k/M=1/2
    # make z=2 the shortest projected relation in the S=16 embedding.
    family = RootedBaseFamily.from_roots(15, [2])
    result = regev_lattice_postprocess(
        family=family,
        samples=[[8]] * 5,
        modulus=16,
        claim_norm_bound=2,
        scale=16,
    )

    assert result.factor_pair == (3, 5)
    assert result.claim_prefix.prefix_length >= 1
    assert result.claim_prefix_candidates
    assert result.candidates == result.claim_prefix_candidates
    best = result.claim_prefix_candidates[0]
    assert best.relation == (2,)
    assert best.relation_class == "L_minus_L0"
    assert best.root_product == 4
    assert best.factor_pair == (3, 5)
    assert pow(4, best.relation[0], 15) == 1


def test_claim_5_1_cutoff_uses_cleared_scale_and_exact_boundary():
    embedding = build_augmented_lattice([[0]] * 5, 8, scale=1)
    diagonal = (8, 64, 128, 128, 128, 128)
    rows = tuple(
        tuple(value if i == j else 0 for j in range(6))
        for i, value in enumerate(diagonal)
    )
    identity = tuple(
        tuple(1 if i == j else 0 for j in range(6)) for i in range(6)
    )
    reduction = LLLReduction(
        reduced_rows=rows,
        transform_rows=identity,
        delta=Fraction(3, 4),
        backend="controlled-test",
    )

    prefix = claim_5_1_prefix(embedding, reduction, norm_bound=1)
    assert prefix.lattice_dimension == 6
    assert prefix.cleared_cutoff_squared == 8**2 * 2**6
    assert prefix.gram_schmidt_squared_norms[:2] == (8**2, 64**2)
    # Claim 5.1 uses >=, so the row exactly at the cutoff is excluded.
    assert prefix.prefix_length == 1


def test_all_basis_factor_is_diagnostic_not_primary_when_T_is_too_small():
    family = RootedBaseFamily.from_roots(15, [2])
    result = regev_lattice_postprocess(
        family,
        [[8]] * 5,
        16,
        claim_norm_bound=Fraction(1, 1000),
        scale=16,
    )

    assert result.claim_prefix.prefix_length == 0
    assert result.claim_prefix_candidates == ()
    assert result.factor_pair is None
    assert result.all_basis_diagnostic_candidates
    assert result.all_basis_diagnostic_factor_pair == (3, 5)


def test_primary_endpoint_requires_immutable_rooted_family():
    with pytest.raises(TypeError, match="RootedBaseFamily"):
        regev_lattice_postprocess(
            [4], [[8]] * 5, 16, claim_norm_bound=2, scale=16
        )


def test_root_provenance_changes_L0_class_without_changing_bases():
    relation = (1, -1)
    trivial = classify_square_relation(
        RootedBaseFamily.from_roots(15, [2, 2]), relation
    )
    useful = classify_square_relation(
        RootedBaseFamily.from_roots(15, [2, 7]), relation
    )

    assert trivial["class"] == "L0"
    assert trivial["factor"] is None
    assert useful["class"] == "L_minus_L0"
    assert useful["root_product"] == 11
    assert useful["factors"] == [5, 3]


def test_mismatched_stored_root_is_rejected_instead_of_reconstructed():
    with pytest.raises(ValueError, match="stored root squared"):
        RootedBase(N=15, root=4, base=4)


def test_regev_sample_count_and_exact_scale_are_enforced():
    with pytest.raises(ValueError, match=r"d \+ 4"):
        build_augmented_lattice([[8]] * 4, 16, scale=16)
    with pytest.raises(TypeError, match="Fraction"):
        build_augmented_lattice([[8]] * 5, 16, scale=16.0)

    from_delta = build_augmented_lattice(
        [[8]] * 5, 16, noise_bound=Fraction(1, 16)
    )
    assert from_delta.scale == 16

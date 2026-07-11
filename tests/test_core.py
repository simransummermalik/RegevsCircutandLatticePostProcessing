import numpy as np

from regev_research.core import (
    audit_square_base_family,
    base_diagnostics,
    bitstring_to_vector,
    bounded_relations,
    classify_square_relation,
    distribution_metrics,
    extract_factor_from_relation,
    exact_uniform_fourier_distribution,
    notebook_squared_prime_bases,
    relation_signal_energy,
    RootedBase,
    RootedBaseFamily,
    select_dependency_aware_bases,
)


def test_notebook_histogram_N15_is_exactly_two_points():
    p, kernel = exact_uniform_fourier_distribution(15, [4, 4], 16)
    assert np.isclose(p[0, 0], 0.5)
    assert np.isclose(p[8, 8], 0.5)
    assert np.count_nonzero(p > 1e-14) == 2
    assert np.isclose(relation_signal_energy(kernel), 127.0)


def test_notebook_N21_exact_leading_probabilities_match_stored_run():
    p, _ = exact_uniform_fourier_distribution(21, [4, 4, 16], 16)
    assert np.isclose(p[0, 0, 0], 1 / 3, atol=5e-8)
    assert np.isclose(p[11, 11, 5], 0.10709064598386533)
    assert np.isclose(p[5, 5, 11], 0.10709064598386533)


def test_parseval_relation_signal_identity_for_multiple_families():
    for N, bases, M in [
        (15, [4, 4], 16),
        (21, [4, 4, 16], 16),
        (77, [4, 9, 25], 32),
        (91, [36, 58, 5], 32),
    ]:
        p, kernel = exact_uniform_fourier_distribution(N, bases, M)
        metrics = distribution_metrics(p, kernel)
        assert metrics["parseval_absolute_error"] < 2e-12


def test_N437_retained_root_choice_determines_L0_and_factor_extraction():
    N = 437
    relation = (1, 1, 1)
    trivial_family = RootedBaseFamily.from_roots(N, [2, 3, 73])
    useful_family = RootedBaseFamily.from_roots(N, [2, 3, 326])
    assert trivial_family.bases == useful_family.bases == (4, 9, 85)
    trivial = classify_square_relation(trivial_family, relation)
    assert trivial["class"] == "L0"
    assert trivial["in_L"] and trivial["in_L0"]
    assert extract_factor_from_relation(trivial_family, relation) is None
    useful = classify_square_relation(useful_family, relation)
    assert useful["class"] == "L_minus_L0"
    assert useful["in_L"] and not useful["in_L0"]
    assert useful["factor"] == 23
    assert useful["factors"] == [23, 19]
    assert extract_factor_from_relation(useful_family, relation) == 23


def test_root_base_pair_is_validated_and_factor_api_rejects_parallel_lists():
    with np.testing.assert_raises(ValueError):
        RootedBase(N=437, root=73, base=4)
    family = RootedBaseFamily.from_roots(437, [2, 3, 326])
    with np.testing.assert_raises(TypeError):
        classify_square_relation([2, 3, 326], (1, 1, 1))
    outside_L = classify_square_relation(family, (1, 0, 0))
    assert outside_L["class"] == "not_in_L"
    assert outside_L["root_product"] is None
    assert outside_L["factor"] is None


def test_pairwise_bound_three_misses_planted_triple_relation():
    diagnostic = base_diagnostics(437, [4, 9, 85], relation_bound=3)
    assert diagnostic["orders"] == [99, 99, 99]
    assert diagnostic["pairwise_power_collisions"] == []
    assert (1, 1, 1) in bounded_relations(437, [4, 9, 85], 1)


def test_notebook_setup_leaks_are_explicit_and_square_collisions_also_factor():
    fifteen = notebook_squared_prime_bases(15, 2)
    twenty_one = notebook_squared_prime_bases(21, 3)
    assert fifteen["setup_factor_leaks"] == [(3, 3, 5), (5, 5, 3)]
    assert twenty_one["setup_factor_leaks"] == [(3, 3, 7), (7, 7, 3)]
    assert audit_square_base_family(
        RootedBaseFamily.from_roots(15, [2, 7]), 1
    )["setup_factor_leaks"] == [5]
    assert 3 in audit_square_base_family(
        RootedBaseFamily.from_roots(21, [2, 5, 11]), 1
    )["setup_factor_leaks"]


def test_dependency_selector_has_required_outputs_and_never_uses_factors():
    result = select_dependency_aware_bases(
        77, 3, range(2, 40), relation_bound=2, seed=7
    )
    assert set(result) == {
        "family",
        "selected_roots",
        "selected_bases",
        "selected_pairs",
        "rejected_bases",
        "rejection_reasons",
        "collision_statistics",
        "dependency_score",
        "effective_dimension_estimate",
        "effective_dimension_definition",
        "runtime_seconds",
        "scoring_method",
        "seed",
    }
    assert len(result["selected_bases"]) == 3
    assert result["family"].roots == tuple(result["selected_roots"])
    assert result["family"].bases == tuple(result["selected_bases"])
    assert all(
        row["base"] == row["root"] * row["root"] % 77
        for row in result["selected_pairs"]
    )
    assert all(np.gcd(a, 77) == 1 for a in result["selected_bases"])


def test_bitstring_decoder_validates_width_and_qiskit_order():
    assert bitstring_to_vector("10001000", 2, 4) == (8, 8)
    assert bitstring_to_vector("010110111011", 3, 4) == (11, 11, 5)
    try:
        bitstring_to_vector("101", 2, 2)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid width must be rejected")

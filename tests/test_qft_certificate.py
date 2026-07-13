import numpy as np
import pytest

from regev_research.qft_certificate import (
    barrier_excludes_nonexact,
    distribution_tv_certificate,
    feasible_matrix_distances,
    fiber_state_audit,
    fiber_state_certificate,
    first_nonexact_barrier,
    hellinger_affinity,
    original_certificate,
    product_hellinger_certificate,
    slack_factor,
    total_variation_distance,
)
from regev_research.qft_noise import fiber_fourier_distribution
from scripts.run_qft_certificate_gap import (
    exact_sign_flip_p,
    exact_sign_test,
    largest_uniformly_certified_layers,
)


def test_strict_barrier_and_nonstrict_certificate_boundary():
    d, m, M = 1, 1, 128
    delta = 4 * np.pi * d * m / M
    assert first_nonexact_barrier(d, m, delta) == pytest.approx(M)
    assert not barrier_excludes_nonexact(d, M, m, delta)
    assert barrier_excludes_nonexact(d, 64, m, delta)
    decision = original_certificate(d, M, m, 5, delta)
    assert decision.m_shot_bound == pytest.approx(delta)
    assert decision.certified
    with pytest.raises(ValueError):
        barrier_excludes_nonexact(1, 8, 1, 1.0)


def test_barrier_rejects_every_nonexact_cutoff_but_exact_passes():
    d, M, m, budget = 3, 128, 12, 0.05
    assert barrier_excludes_nonexact(d, M, m, budget)
    q = int(np.log2(M))
    assert all(not original_certificate(d, M, m, t, budget).certified for t in range(q - 1))
    assert original_certificate(d, M, m, q - 1, budget).certified


def test_distribution_and_hellinger_certificates_on_equal_laws():
    p = np.asarray([0.1, 0.2, 0.7])
    assert total_variation_distance(p, p) == 0
    assert hellinger_affinity(p, p) == pytest.approx(1)
    assert distribution_tv_certificate(p, p, 12, 0.05).certified
    assert product_hellinger_certificate(p, p, 12, 0.05).certified


def test_distribution_validation_and_slack_edge_cases():
    with pytest.raises(ValueError):
        total_variation_distance(np.asarray([0.5, 0.5]), np.asarray([1.0]))
    with pytest.raises(ValueError):
        total_variation_distance(np.asarray([0.4, 0.4]), np.asarray([0.5, 0.5]))
    assert slack_factor(2.0, 0.5) == 4.0
    assert slack_factor(2.0, 0.0) is None


def test_fiber_state_certificate_and_loose_distribution_example():
    audit = fiber_state_audit(15, (4, 1), 4, np.ones(4), cutoff=0)
    assert audit.exact_norm == pytest.approx(1)
    assert audit.approximate_norm == pytest.approx(1)
    assert 0 <= audit.trace_distance_bound <= 1
    assert fiber_state_certificate(audit, 4, 1.0).m_shot_bound <= 1

    exact = fiber_fourier_distribution(15, (4, 1), 4, cutoff=1)
    approximate = fiber_fourier_distribution(15, (4, 1), 4, cutoff=0)
    assert total_variation_distance(exact, approximate) == pytest.approx(0, abs=1e-12)
    assert not original_certificate(2, 4, 4, 0, 0.05).certified
    assert distribution_tv_certificate(exact, approximate, 4, 0.05).certified


def test_observed_matrix_errors_respect_triangle_bounds():
    distances = feasible_matrix_distances(2, 8, cutoff=1)
    assert distances["one_register_operator_error"] <= distances["one_register_triangle_bound"] + 1e-12
    assert distances["product_operator_error"] <= distances["product_triangle_bound"] + 1e-12


def test_certified_layer_count_is_derived_from_all_configuration_rows():
    rows = [
        {"N": 15, "M": 8, "model": "A", "omitted_layers": 0, "original_certified": True},
        {"N": 21, "M": 8, "model": "A", "omitted_layers": 0, "original_certified": True},
        {"N": 15, "M": 8, "model": "A", "omitted_layers": 1, "original_certified": True},
        {"N": 21, "M": 8, "model": "A", "omitted_layers": 1, "original_certified": False},
    ]
    assert largest_uniformly_certified_layers(rows, 8, "A") == 0
    rows[-1]["original_certified"] = True
    assert largest_uniformly_certified_layers(rows, 8, "A") == 1


def test_exact_paired_sensitivity_statistics_have_known_small_cases():
    values = np.asarray([1.0, 1.0, 1.0])
    sign = exact_sign_test(values)
    assert sign == {
        "nonzero_pairs": 3,
        "positive_pairs": 3,
        "two_sided_p": 0.25,
    }
    assert exact_sign_flip_p(values) == pytest.approx(0.25)
    assert exact_sign_test(np.zeros(3))["two_sided_p"] == 1.0

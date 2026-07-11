import numpy as np
from math import sqrt

from regev_research.core import (
    distribution_metrics,
    exact_uniform_fourier_distribution,
    modular_product,
)
from regev_research.redteam import (
    REDTEAM_METHODS,
    exact_regev_gaussian_distribution,
    exact_weighted_fourier_distribution,
    regev_gaussian_amplitudes,
    select_rooted_ablation_family,
    uniform_amplitudes,
    weighted_chi_square_from_kernel,
)
from regev_research.redteam_experiments import (
    CANDIDATE_ROOT_POOL,
    FINITE_MODULUS,
    GAUSSIAN_RADIUS,
    HELDOUT_INSTANCES,
)


def test_weighted_uniform_formula_matches_existing_hard_box_exactly():
    for N, bases, D in [(15, [4, 4], 16), (21, [4, 4, 16], 16)]:
        expected, expected_kernel = exact_uniform_fourier_distribution(N, bases, D)
        actual, kernel, normalization = exact_weighted_fourier_distribution(
            N, bases, D, uniform_amplitudes(D)
        )
        assert normalization == D ** len(bases)
        assert np.allclose(kernel, expected_kernel)
        assert np.allclose(actual, expected, atol=2e-14)


def test_gaussian_formula_matches_direct_fiber_statevector_sum():
    N, bases, D, radius = 15, [4, 4], 8, 3.0
    probabilities, kernel, normalization = exact_regev_gaussian_distribution(
        N, bases, D, radius
    )
    amplitudes = regev_gaussian_amplitudes(D, radius)
    centered = np.arange(-D // 2, D // 2)
    direct = np.zeros((D, D), dtype=float)
    for residue in {modular_product(N, bases, x) for x in np.ndindex(D, D)}:
        fiber = np.zeros((D, D), dtype=float)
        for i, x1 in enumerate(centered):
            for j, x2 in enumerate(centered):
                if modular_product(N, bases, (int(x1), int(x2))) == residue:
                    fiber[i, j] = amplitudes[i] * amplitudes[j]
        direct += np.abs(np.fft.fftn(fiber)) ** 2
    direct /= D**2 * normalization
    assert np.allclose(probabilities, direct, atol=2e-13)
    metrics = distribution_metrics(probabilities)
    assert np.isclose(
        metrics["chi_square_from_uniform"],
        weighted_chi_square_from_kernel(kernel, normalization),
        atol=2e-12,
    )


def test_every_ablation_retains_the_selected_root_base_pairs():
    N = 1763
    pool = [2, 3, 5, 7, 11, 13, 17, 19]
    for index, method in enumerate(REDTEAM_METHODS):
        family, audit = select_rooted_ablation_family(
            N,
            3,
            pool,
            method,
            relation_bound=2,
            seed=100 + index,
        )
        assert len(family.pairs) == 3
        assert audit["selected_pairs"] == family.as_records()
        assert all(pair.base == pair.root * pair.root % N for pair in family.pairs)


def test_frozen_holdout_has_24_new_factor_safe_N_units():
    Ns = [row["N"] for row in HELDOUT_INSTANCES]
    prior = {15, 21, 57, 169, 247, 289, 299, 323, 361, 391, 437, 1763, 2021, 4199, 7429}
    assert len(Ns) == len(set(Ns)) == 24
    assert not set(Ns) & prior
    for row in HELDOUT_INSTANCES:
        p, q = row["factors"]
        assert p * q == row["N"]
        assert min(p, q) > max(CANDIDATE_ROOT_POOL)


def test_finite_gaussian_parameters_obey_regev_D_interval():
    lower = 2 * sqrt(3) * GAUSSIAN_RADIUS
    upper = 4 * sqrt(3) * GAUSSIAN_RADIUS
    assert lower <= FINITE_MODULUS < upper

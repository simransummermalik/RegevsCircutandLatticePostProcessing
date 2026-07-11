import numpy as np

from regev_research.core import RootedBaseFamily, modular_product
from regev_research.dual import (
    exact_relation_lattice_hnf,
    synthetic_noisy_dual_samples,
)


def test_factor_blind_cayley_hnf_is_a_full_relation_lattice_basis():
    family = RootedBaseFamily.from_roots(1763, [2, 3, 5])
    oracle = exact_relation_lattice_hnf(family.N, family.bases)
    H = np.asarray(oracle.column_hnf, dtype=int)
    assert abs(round(np.linalg.det(H))) == oracle.image_size == oracle.determinant
    for column in H.T:
        assert modular_product(family.N, family.bases, column) == 1


def test_synthetic_dual_batch_satisfies_the_frozen_theoretical_bound():
    family = RootedBaseFamily.from_roots(1763, [2, 3, 5])
    batch = synthetic_noisy_dual_samples(
        family,
        seed=20260710,
        relation_norm_bound_T=8,
        safety=2.0,
    )
    assert batch.sample_count == 7
    assert batch.maximum_realized_torus_error < batch.noise_bound
    assert batch.theorem_sufficient_inequality
    assert batch.modulus & (batch.modulus - 1) == 0
    assert all(
        0 <= coordinate < batch.modulus
        for row in batch.samples
        for coordinate in row
    )


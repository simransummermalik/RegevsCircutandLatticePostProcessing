import numpy as np
import pytest

from regev_research.qft_noise import (
    bitflip_channel,
    coherent_phase_tv_bound,
    embedding_noise_norm_bound,
    exact_qft_matrix,
    fiber_fourier_distribution,
    fiber_qft_tv_distance,
    grid_quantization_bound,
    omitted_rotation_angle_sum,
    qft_gate_counts,
    qft_matrix,
    qft_operator_error_bound,
    qft_tv_bound,
    recovery_success_hybrid_bound,
    select_fiber_qft_cutoff,
    select_qft_cutoff,
)


def test_roots_of_unity_qft_matrix_and_gate_check():
    for M in (2, 4, 8):
        for inverse in (False, True):
            assert np.max(np.abs(qft_matrix(M, inverse=inverse) - exact_qft_matrix(M, inverse=inverse))) < 1e-12


def test_truncation_bound_monotone_and_exact_at_full_cutoff():
    values = [omitted_rotation_angle_sum(5, cutoff) for cutoff in range(5)]
    assert values == sorted(values, reverse=True)
    assert values[-1] == 0.0
    assert qft_operator_error_bound(3, 5, 4) == 0.0
    assert qft_tv_bound(3, 5, 4) == 0.0


def test_gate_count_and_factor_blind_precision_choice():
    counts = qft_gate_counts(2, 4, 2)
    assert counts["controlled_phase"] < counts["exact_controlled_phase"]
    assert counts["omitted_controlled_phase"] == 2
    choice = select_qft_cutoff(2, 16, 8, 0.05)
    assert choice.cutoff == 3
    assert choice.certified
    assert choice.approximate_controlled_phase_gates == choice.exact_controlled_phase_gates


def test_fiber_distribution_and_state_aware_choice():
    exact = fiber_fourier_distribution(15, (4, 7), 4, cutoff=None)
    approx = fiber_fourier_distribution(15, (4, 7), 4, cutoff=0)
    assert np.isclose(exact.sum(), 1.0)
    assert np.isclose(approx.sum(), 1.0)
    assert fiber_qft_tv_distance(15, (4, 7), 4, 3) < 1e-12
    choice = select_fiber_qft_cutoff(15, (4, 7), 4, 4, 0.05)
    assert choice.cutoff == 0
    assert choice.certified


def test_noise_mapping_and_hybrid_bound():
    assert np.isclose(grid_quantization_bound(3, 16), np.sqrt(3) / 32)
    assert np.isclose(embedding_noise_norm_bound(4, 10, 0.01), 0.2)
    assert coherent_phase_tv_bound(0.0) == 0.0
    result = recovery_success_hybrid_bound(0.8, 0.01, 5, target_probability=0.7)
    assert result["lower_bound"] == pytest.approx(0.75)
    assert result["certified_above_target"] is True


def test_bitflip_channel_preserves_mass_and_rejects_invalid():
    probabilities = np.zeros((4, 4))
    probabilities[1, 2] = 1.0
    output = bitflip_channel(probabilities, 0.1)
    assert np.isclose(output.sum(), 1.0)
    assert output.shape == probabilities.shape
    with pytest.raises(ValueError):
        bitflip_channel(probabilities, 1.1)

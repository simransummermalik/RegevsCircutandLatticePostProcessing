import inspect

import numpy as np
import pytest

from regev_research.qft_noise import qft_matrix
from shor_to_regev_study import shor as shor_module
from shor_to_regev_study.shor import (
    apply_inverse_qft_batch,
    build_shor_circuit,
    candidate_orders_from_phase,
    continued_fraction_convergents,
    decoder_boundary_metrics,
    decode_measurement,
    decode_qiskit_phase_bitstring,
    phase_register_bits,
    reduce_verified_order,
    shor_factor,
    shor_phase_distribution,
    verified_factor_pair,
)


def test_continued_fraction_convergents_are_constructed_directly():
    assert continued_fraction_convergents(3, 7) == ((0, 1), (1, 2), (3, 7))
    assert continued_fraction_convergents(355, 113, max_denominator=100) == (
        (3, 1),
        (22, 7),
    )


def test_candidate_denominator_multiples_and_exact_order_verification():
    Q = 1 << phase_register_bits(21)
    convergents, candidates = candidate_orders_from_phase(round(Q / 3), Q, 21)
    assert any(denominator == 3 for _, denominator in convergents)
    assert 6 in candidates
    decoded = decode_measurement(21, 2, round(Q / 3), Q)
    assert decoded.verified_order == 6
    assert decoded.factor_pair == (3, 7)
    assert reduce_verified_order(21, 2, 12) == 6


def test_odd_order_and_trivial_square_root_fail_explicitly():
    Q = 1 << phase_register_bits(21)
    odd = decode_measurement(21, 4, round(Q / 3), Q)
    assert odd.verified_order == 3
    assert odd.factor_pair is None
    assert odd.failure_reason == "odd_order"

    trivial = decode_measurement(21, 5, round(Q / 6), Q)
    assert trivial.verified_order == 6
    assert trivial.factor_pair is None
    assert trivial.failure_reason == "trivial_square_root"


def test_factor_verification_and_gcd_shortcut():
    assert verified_factor_pair(15, (5, 3)) == (3, 5)
    with pytest.raises(ValueError):
        verified_factor_pair(15, (1, 15))
    shortcut = shor_factor(15, 3, shots=4, seed=1)
    assert shortcut.gcd_shortcut
    assert shortcut.factor_pair == (3, 5)


def test_decoder_has_no_order_or_factor_input_and_does_not_call_order_oracle(monkeypatch):
    parameters = inspect.signature(decode_measurement).parameters
    assert "true_order" not in parameters
    assert "factors" not in parameters
    monkeypatch.setattr(
        shor_module,
        "multiplicative_order_for_simulation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("leak")),
    )
    Q = 1 << phase_register_bits(15)
    decoded = decode_measurement(15, 2, Q // 4, Q)
    assert decoded.factor_pair == (3, 5)


def test_inverse_qft_orientation_cutoff_and_swaps_match_roots_of_unity_matrix():
    rng = np.random.default_rng(7)
    for q in (2, 3, 4):
        Q = 1 << q
        vector = rng.normal(size=Q) + 1j * rng.normal(size=Q)
        vector /= np.linalg.norm(vector)
        for cutoff in range(q):
            observed = apply_inverse_qft_batch(vector, cutoff)[0]
            expected = qft_matrix(Q, cutoff=cutoff, inverse=True) @ vector
            assert np.allclose(observed, expected, atol=1e-12)


def test_measurement_bitstring_decoding_and_phase_peaks():
    assert decode_qiskit_phase_bitstring("00101") == 5
    assert decode_qiskit_phase_bitstring("00 101") == 5
    probabilities = shor_phase_distribution(15, 2)
    Q = len(probabilities)
    expected_peaks = {0, Q // 4, Q // 2, 3 * Q // 4}
    observed_peaks = set(np.argsort(probabilities)[-4:])
    assert observed_peaks == expected_peaks


def test_decoder_boundary_metrics_are_factor_blind_and_deterministic():
    exact = shor_phase_distribution(21, 2)
    approximate = shor_phase_distribution(21, 2, qft_cutoff=0)
    first = decoder_boundary_metrics(21, 2, exact, approximate)
    second = decoder_boundary_metrics(21, 2, exact, approximate)
    assert first == second
    assert 0 < first["cf_boundary_fraction"] < 1
    assert 0 <= first["fraction_change_near_cf_boundary"] <= 1
    identical = decoder_boundary_metrics(21, 2, exact, exact)
    assert identical["absolute_change_near_cf_boundary"] == 0
    assert identical["fraction_change_near_cf_boundary"] == 0


def test_modular_circuit_phase_marginal_matches_exact_fiber_distribution():
    from qiskit.quantum_info import Statevector

    circuit = build_shor_circuit(15, 2, measure=False)
    state = Statevector.from_instruction(circuit)
    q = phase_register_bits(15)
    circuit_probabilities = state.probabilities(qargs=range(q))
    analytic = shor_phase_distribution(15, 2)
    assert np.allclose(circuit_probabilities, analytic, atol=1e-10)


def test_shor_factor_is_deterministic_and_records_failure_reasons():
    first = shor_factor(15, 2, shots=8, seed=2026)
    second = shor_factor(15, 2, shots=8, seed=2026)
    assert first == second
    assert first.factor_pair == (3, 5)

    odd = shor_factor(21, 4, shots=16, seed=2026)
    assert odd.order_recovered
    assert not odd.success
    assert odd.failure_reason in {"odd_order", "zero_phase", "no_verified_order"}

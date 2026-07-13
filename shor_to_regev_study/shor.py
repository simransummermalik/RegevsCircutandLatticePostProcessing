"""Small-scale, leakage-free standard Shor factoring implementation.

The quantum distribution is simulated exactly from modular-exponentiation
fibers.  ``build_shor_circuit`` separately constructs the corresponding
Qiskit circuit and is validated against the exact distribution on feasible
sizes.  The continued-fraction decoder receives neither factors nor the true
order.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from fractions import Fraction
from math import ceil, gcd, log2, pi, sqrt
from typing import Sequence

import numpy as np


@dataclass(frozen=True, slots=True)
class PhaseDecodeResult:
    measurement: int
    phase_numerator: int
    phase_denominator: int
    convergents: tuple[tuple[int, int], ...]
    candidate_orders: tuple[int, ...]
    verified_order: int | None
    factor_pair: tuple[int, int] | None
    failure_reason: str | None

    def as_record(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ShorResult:
    N: int
    base: int
    shots: int
    phase_qubits: int
    phase_modulus: int
    qft_cutoff: int
    seed: int | None
    gcd_shortcut: bool
    order_recovered: bool
    recovered_order: int | None
    factor_pair: tuple[int, int] | None
    measurements: tuple[int, ...]
    decodings: tuple[PhaseDecodeResult, ...]
    failure_reason: str | None

    @property
    def success(self) -> bool:
        return self.factor_pair is not None

    def as_record(self) -> dict:
        record = asdict(self)
        record["success"] = self.success
        return record


def phase_register_bits(N: int) -> int:
    if int(N) < 3:
        raise ValueError("N must be at least 3")
    return 2 * ceil(log2(int(N)))


def continued_fraction_convergents(
    numerator: int, denominator: int, *, max_denominator: int | None = None
) -> tuple[tuple[int, int], ...]:
    """Compute reduced convergents of ``numerator/denominator`` directly."""

    numerator = int(numerator)
    denominator = int(denominator)
    if denominator <= 0 or numerator < 0:
        raise ValueError("fraction must have nonnegative numerator and positive denominator")
    common = gcd(numerator, denominator)
    n, d = numerator // common, denominator // common
    terms: list[int] = []
    while d:
        terms.append(n // d)
        n, d = d, n % d

    previous_previous_numerator, previous_numerator = 0, 1
    previous_previous_denominator, previous_denominator = 1, 0
    convergents: list[tuple[int, int]] = []
    for term in terms:
        current_numerator = term * previous_numerator + previous_previous_numerator
        current_denominator = term * previous_denominator + previous_previous_denominator
        if max_denominator is not None and current_denominator > int(max_denominator):
            break
        convergents.append((current_numerator, current_denominator))
        previous_previous_numerator, previous_numerator = (
            previous_numerator,
            current_numerator,
        )
        previous_previous_denominator, previous_denominator = (
            previous_denominator,
            current_denominator,
        )
    return tuple(convergents)


def _prime_divisors(value: int) -> tuple[int, ...]:
    divisors: list[int] = []
    candidate = 2
    remaining = int(value)
    while candidate * candidate <= remaining:
        if remaining % candidate == 0:
            divisors.append(candidate)
            while remaining % candidate == 0:
                remaining //= candidate
        candidate += 1
    if remaining > 1:
        divisors.append(remaining)
    return tuple(divisors)


def reduce_verified_order(N: int, base: int, candidate_order: int) -> int:
    """Reduce a modularly verified multiple to the minimal order."""

    N, base, order = int(N), int(base), int(candidate_order)
    if order <= 0 or pow(base, order, N) != 1:
        raise ValueError("candidate_order is not modularly verified")
    changed = True
    while changed:
        changed = False
        for divisor in _prime_divisors(order):
            if order % divisor == 0 and pow(base, order // divisor, N) == 1:
                order //= divisor
                changed = True
                break
    return order


def verified_factor_pair(N: int, factors: Sequence[int]) -> tuple[int, int]:
    if len(tuple(factors)) != 2:
        raise ValueError("exactly two factors are required")
    left, right = sorted(int(value) for value in factors)
    if left <= 1 or right >= int(N) or left * right != int(N):
        raise ValueError("factors are not a nontrivial verified pair")
    return left, right


def candidate_orders_from_phase(
    measurement: int,
    phase_modulus: int,
    N: int,
    *,
    max_multiple: int = 4,
) -> tuple[tuple[tuple[int, int], ...], tuple[int, ...]]:
    """Return convergents and factor-blind denominator multiples to verify."""

    y, Q, N = int(measurement), int(phase_modulus), int(N)
    if not 0 <= y < Q or Q <= 1:
        raise ValueError("measurement must lie in [0,Q)")
    convergents = continued_fraction_convergents(y, Q, max_denominator=N)
    candidates: list[int] = []
    for _, denominator in convergents:
        if denominator <= 1:
            continue
        for multiple in range(1, int(max_multiple) + 1):
            candidate = denominator * multiple
            if candidate <= N and candidate not in candidates:
                candidates.append(candidate)
    return convergents, tuple(candidates)


def decode_measurement(
    N: int,
    base: int,
    measurement: int,
    phase_modulus: int,
    *,
    max_multiple: int = 4,
) -> PhaseDecodeResult:
    """Run continued fractions, modular verification, and gcd extraction."""

    N, base, y, Q = int(N), int(base), int(measurement), int(phase_modulus)
    if gcd(base, N) != 1:
        raise ValueError("decode_measurement expects a coprime base")
    convergents, candidates = candidate_orders_from_phase(
        y, Q, N, max_multiple=max_multiple
    )
    verified: int | None = None
    for candidate in candidates:
        if pow(base, candidate, N) == 1:
            verified = reduce_verified_order(N, base, candidate)
            break
    if verified is None:
        reason = "zero_phase" if y == 0 else "no_verified_order"
        return PhaseDecodeResult(
            y, y, Q, convergents, candidates, None, None, reason
        )
    if verified % 2:
        return PhaseDecodeResult(
            y, y, Q, convergents, candidates, verified, None, "odd_order"
        )
    square_root = pow(base, verified // 2, N)
    if square_root in (1, N - 1):
        return PhaseDecodeResult(
            y,
            y,
            Q,
            convergents,
            candidates,
            verified,
            None,
            "trivial_square_root",
        )
    factors = sorted({gcd(square_root - 1, N), gcd(square_root + 1, N)})
    nontrivial = [factor for factor in factors if 1 < factor < N and N % factor == 0]
    if not nontrivial:
        return PhaseDecodeResult(
            y, y, Q, convergents, candidates, verified, None, "trivial_gcd"
        )
    factor = nontrivial[0]
    pair = verified_factor_pair(N, (factor, N // factor))
    return PhaseDecodeResult(y, y, Q, convergents, candidates, verified, pair, None)


def multiplicative_order_for_simulation(N: int, base: int) -> int:
    """Factor-blind classical order used only to construct the exact state."""

    if gcd(int(N), int(base)) != 1:
        raise ValueError("multiplicative order requires a coprime base")
    value = 1
    for order in range(1, int(N) + 1):
        value = value * int(base) % int(N)
        if value == 1:
            return order
    raise RuntimeError("order not found within the finite group bound")


def _swap_permutation(size: int, first: int, second: int) -> np.ndarray:
    indices = np.arange(size)
    first_bits = (indices >> first) & 1
    second_bits = (indices >> second) & 1
    toggle = (first_bits ^ second_bits) * ((1 << first) | (1 << second))
    return indices ^ toggle


def apply_inverse_qft_batch(states: np.ndarray, cutoff: int) -> np.ndarray:
    """Apply the declared inverse truncated QFT to row statevectors."""

    values = np.asarray(states, dtype=complex)
    if values.ndim == 1:
        values = values[None, :]
    if values.ndim != 2 or values.shape[1] <= 1:
        raise ValueError("states must contain nontrivial row statevectors")
    Q = values.shape[1]
    q = int(log2(Q))
    if 1 << q != Q or not 0 <= int(cutoff) < q:
        raise ValueError("state length must be a power of two and cutoff valid")
    output = values.copy()
    for first in range(q // 2):
        output = output[:, _swap_permutation(Q, first, q - 1 - first)]
    indices = np.arange(Q)
    for target in range(q):
        for control in range(target):
            separation = target - control
            if separation <= int(cutoff):
                mask = ((indices >> target) & 1) & ((indices >> control) & 1)
                output[:, mask.astype(bool)] *= np.exp(-1j * pi / (2**separation))
        zero = indices[(indices & (1 << target)) == 0]
        one = zero | (1 << target)
        lower = output[:, zero].copy()
        upper = output[:, one].copy()
        output[:, zero] = (lower + upper) / sqrt(2.0)
        output[:, one] = (lower - upper) / sqrt(2.0)
    return output


def apply_readout_bitflips(probabilities: np.ndarray, probability: float) -> np.ndarray:
    """Apply independent classical readout flips to every phase qubit."""

    p = float(probability)
    values = np.asarray(probabilities, dtype=float)
    if values.ndim != 1 or not 0 <= p <= 1 or np.any(values < 0):
        raise ValueError("invalid probability law or readout probability")
    Q = len(values)
    q = int(log2(Q))
    if 1 << q != Q or not np.isclose(values.sum(), 1.0, atol=1e-10):
        raise ValueError("probability law must be normalized with power-of-two length")
    output = values.copy()
    indices = np.arange(Q)
    for bit in range(q):
        output = (1 - p) * output + p * output[indices ^ (1 << bit)]
    return output / output.sum()


def shor_phase_distribution(
    N: int,
    base: int,
    *,
    qft_cutoff: int | None = None,
    readout_bitflip_probability: float = 0.0,
) -> np.ndarray:
    """Exact finite phase law after modular exponentiation and inverse QFT."""

    N, base = int(N), int(base)
    if not 1 < base < N or gcd(base, N) != 1:
        raise ValueError("phase distribution requires 1 < base < N and gcd(base,N)=1")
    q = phase_register_bits(N)
    Q = 1 << q
    cutoff = q - 1 if qft_cutoff is None else int(qft_cutoff)
    if not 0 <= cutoff < q:
        raise ValueError("qft_cutoff must lie in {0,...,q-1}")
    transformed = shor_transformed_fibers(N, base, cutoff)
    probabilities = np.sum(np.abs(transformed) ** 2, axis=0).real
    probabilities = probabilities / probabilities.sum()
    return apply_readout_bitflips(probabilities, readout_bitflip_probability)


def shor_transformed_fibers(N: int, base: int, qft_cutoff: int) -> np.ndarray:
    """Return work-labeled phase rows after the declared inverse QFT."""

    N, base = int(N), int(base)
    q = phase_register_bits(N)
    Q = 1 << q
    cutoff = int(qft_cutoff)
    if gcd(base, N) != 1 or not 0 <= cutoff < q:
        raise ValueError("coprime base and valid cutoff required")
    order = multiplicative_order_for_simulation(N, base)
    fibers = np.zeros((order, Q), dtype=complex)
    x = np.arange(Q)
    fibers[x % order, x] = 1.0 / sqrt(Q)
    return apply_inverse_qft_batch(fibers, cutoff)


def joint_state_metrics_from_fibers(
    exact: np.ndarray, approximate: np.ndarray
) -> dict[str, float]:
    if exact.shape != approximate.shape or exact.ndim != 2:
        raise ValueError("joint fiber arrays must have the same two-dimensional shape")
    if exact is approximate or np.array_equal(exact, approximate):
        return {
            "joint_state_overlap_magnitude": 1.0,
            "joint_state_trace_distance": 0.0,
            "joint_state_vector_norm_error": 0.0,
        }
    overlap = sum(np.vdot(left, right) for left, right in zip(exact, approximate, strict=True))
    norm_error = sqrt(
        max(
            0.0,
            sum(
                float(np.vdot(left - right, left - right).real)
                for left, right in zip(exact, approximate, strict=True)
            ),
        )
    )
    overlap_magnitude = float(np.clip(abs(overlap), 0.0, 1.0))
    return {
        "joint_state_overlap_magnitude": overlap_magnitude,
        "joint_state_trace_distance": sqrt(max(0.0, 1.0 - overlap_magnitude**2)),
        "joint_state_vector_norm_error": norm_error,
    }


def shor_joint_state_metrics(N: int, base: int, qft_cutoff: int) -> dict[str, float]:
    """Exact pure joint-state error before phase/work measurement."""

    N, base = int(N), int(base)
    q = phase_register_bits(N)
    Q = 1 << q
    cutoff = int(qft_cutoff)
    if gcd(base, N) != 1 or not 0 <= cutoff < q:
        raise ValueError("coprime base and valid cutoff required")
    exact = shor_transformed_fibers(N, base, q - 1)
    approximate = shor_transformed_fibers(N, base, cutoff)
    return joint_state_metrics_from_fibers(exact, approximate)


def shor_factor(
    N: int,
    base: int,
    shots: int,
    qft_cutoff: int | None = None,
    seed: int | None = None,
    *,
    readout_bitflip_probability: float = 0.0,
) -> ShorResult:
    """Execute the complete finite Shor sampling and decoding pipeline."""

    N, base, shots = int(N), int(base), int(shots)
    if N < 3 or N % 2 == 0 or not 1 < base < N or shots <= 0:
        raise ValueError("require odd N>=3, 1<base<N, and positive shots")
    q = phase_register_bits(N)
    Q = 1 << q
    cutoff = q - 1 if qft_cutoff is None else int(qft_cutoff)
    if not 0 <= cutoff < q:
        raise ValueError("qft_cutoff must lie in {0,...,q-1}")
    shortcut = gcd(base, N)
    if shortcut > 1:
        pair = verified_factor_pair(N, (shortcut, N // shortcut))
        return ShorResult(
            N, base, shots, q, Q, cutoff, seed, True, False, None, pair, (), (), None
        )

    probabilities = shor_phase_distribution(
        N,
        base,
        qft_cutoff=cutoff,
        readout_bitflip_probability=readout_bitflip_probability,
    )
    rng = np.random.default_rng(seed)
    measurements = tuple(
        int(value) for value in rng.choice(Q, size=shots, p=probabilities)
    )
    decodings = tuple(decode_measurement(N, base, y, Q) for y in measurements)
    factor_result = next((item for item in decodings if item.factor_pair is not None), None)
    order_result = next((item for item in decodings if item.verified_order is not None), None)
    reasons = [item.failure_reason for item in decodings if item.failure_reason]
    failure = None
    if factor_result is None:
        failure = (
            order_result.failure_reason
            if order_result is not None
            else Counter(reasons).most_common(1)[0][0]
            if reasons
            else "no_factor_after_shots"
        )
    return ShorResult(
        N=N,
        base=base,
        shots=shots,
        phase_qubits=q,
        phase_modulus=Q,
        qft_cutoff=cutoff,
        seed=seed,
        gcd_shortcut=False,
        order_recovered=order_result is not None,
        recovered_order=None if order_result is None else order_result.verified_order,
        factor_pair=None if factor_result is None else factor_result.factor_pair,
        measurements=measurements,
        decodings=decodings,
        failure_reason=failure,
    )


def modular_multiplication_matrix(N: int, multiplier: int) -> np.ndarray:
    """Permutation matrix for reversible multiplication on the work register."""

    N, multiplier = int(N), int(multiplier) % int(N)
    if gcd(N, multiplier) != 1:
        raise ValueError("multiplier must be invertible modulo N")
    work_qubits = ceil(log2(N))
    dimension = 1 << work_qubits
    matrix = np.zeros((dimension, dimension), dtype=complex)
    for value in range(dimension):
        target = value * multiplier % N if value < N else value
        matrix[target, value] = 1.0
    return matrix


def build_shor_circuit(
    N: int,
    base: int,
    *,
    qft_cutoff: int | None = None,
    measure: bool = True,
):
    """Construct the standard modular-exponentiation/QFT Qiskit circuit."""

    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
    from qiskit.circuit.library import UnitaryGate

    N, base = int(N), int(base)
    if not 1 < base < N or gcd(base, N) != 1:
        raise ValueError("circuit construction requires a coprime nontrivial base")
    q = phase_register_bits(N)
    cutoff = q - 1 if qft_cutoff is None else int(qft_cutoff)
    if not 0 <= cutoff < q:
        raise ValueError("qft_cutoff must lie in {0,...,q-1}")
    phase = QuantumRegister(q, "phase")
    work = QuantumRegister(ceil(log2(N)), "work")
    classical = ClassicalRegister(q, "phase_bits") if measure else None
    circuit = QuantumCircuit(phase, work, classical) if measure else QuantumCircuit(phase, work)
    circuit.x(work[0])
    circuit.h(phase)
    for bit in range(q):
        multiplier = pow(base, 1 << bit, N)
        gate = UnitaryGate(
            modular_multiplication_matrix(N, multiplier),
            label=f"x{multiplier}_mod_{N}",
        ).control(1)
        circuit.append(gate, [phase[bit], *work])
    for first in range(q // 2):
        circuit.swap(phase[first], phase[q - 1 - first])
    for target in range(q):
        for control in range(target):
            separation = target - control
            if separation <= cutoff:
                circuit.cp(-pi / (2**separation), phase[target], phase[control])
        circuit.h(phase[target])
    if measure:
        circuit.measure(phase, classical)
    return circuit


def decode_qiskit_phase_bitstring(bitstring: str) -> int:
    """Decode Qiskit's most-significant-classical-bit-first count key."""

    compact = bitstring.replace(" ", "")
    if not compact or any(bit not in "01" for bit in compact):
        raise ValueError("bitstring must contain only binary digits and spaces")
    return int(compact, 2)


def total_variation(exact: np.ndarray, approximate: np.ndarray) -> float:
    p, q = np.asarray(exact, dtype=float), np.asarray(approximate, dtype=float)
    if p.shape != q.shape or not np.isclose(p.sum(), 1) or not np.isclose(q.sum(), 1):
        raise ValueError("laws must have equal shape and unit mass")
    return float(0.5 * np.abs(p - q).sum())


def hellinger_affinity(exact: np.ndarray, approximate: np.ndarray) -> float:
    p, q = np.asarray(exact, dtype=float), np.asarray(approximate, dtype=float)
    if p.shape != q.shape or np.any(p < 0) or np.any(q < 0):
        raise ValueError("laws must have equal shape and nonnegative mass")
    return float(np.clip(np.sqrt(p * q).sum(), 0.0, 1.0))


def continued_fraction_signature(measurement: int, Q: int, N: int) -> tuple[int, ...]:
    convergents = continued_fraction_convergents(measurement, Q, max_denominator=N)
    return tuple(denominator for _, denominator in convergents if denominator > 1)


def decoder_boundary_metrics(
    N: int,
    base: int,
    exact: np.ndarray,
    approximate: np.ndarray,
) -> dict[str, float]:
    """Measure probability near continued-fraction decision boundaries.

    Fields prefixed ``order_dependent`` are analysis-only and are excluded
    from the empirical predictor.  No known factor is used.
    """

    Q = len(exact)
    if len(approximate) != Q:
        raise ValueError("distribution lengths differ")
    signatures = [continued_fraction_signature(y, Q, N) for y in range(Q)]
    boundary = np.zeros(Q, dtype=bool)
    for y in range(Q - 1):
        if signatures[y] != signatures[y + 1]:
            boundary[y] = True
            boundary[y + 1] = True
    near = boundary.copy()
    near |= np.roll(boundary, 1) | np.roll(boundary, -1)
    exact_values = np.asarray(exact, dtype=float)
    approximate_values = np.asarray(approximate, dtype=float)
    changed = np.abs(exact_values - approximate_values)
    order = multiplicative_order_for_simulation(N, base)
    valid_points = np.asarray([round(s * Q / order) % Q for s in range(order)])
    torus_distance = np.asarray([
        min(min((y - point) % Q, (point - y) % Q) for point in valid_points) / Q
        for y in range(Q)
    ])
    return {
        "cf_boundary_fraction": float(np.mean(boundary)),
        "exact_mass_near_cf_boundary": float(exact_values[near].sum()),
        "approximate_mass_near_cf_boundary": float(approximate_values[near].sum()),
        "absolute_change_near_cf_boundary": float(changed[near].sum()),
        "fraction_change_near_cf_boundary": (
            0.0 if changed.sum() == 0 else float(changed[near].sum() / changed.sum())
        ),
        "order_dependent_exact_mean_valid_phase_distance": float(
            np.dot(exact_values, torus_distance)
        ),
        "order_dependent_approximate_mean_valid_phase_distance": float(
            np.dot(approximate_values, torus_distance)
        ),
    }


def qft_resources(phase_qubits: int, cutoff: int) -> dict[str, int]:
    q, cutoff = int(phase_qubits), int(cutoff)
    if q <= 0 or not 0 <= cutoff < q:
        raise ValueError("invalid phase qubits or cutoff")
    exact_cp = q * (q - 1) // 2
    kept_cp = sum(1 for target in range(q) for control in range(target) if target - control <= cutoff)
    return {
        "exact_controlled_phase": exact_cp,
        "controlled_phase": kept_cp,
        "controlled_phase_saving": exact_cp - kept_cp,
        "qft_qubits": q,
    }

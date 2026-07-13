r"""Finite-parameter QFT error bounds and small-state validation utilities.

This module treats the product QFT as the mathematical object

    F_M^{\otimes d}[k,x] = M^{-d/2} exp(2 pi i <k,x>/M),

with the sign changed for the inverse transform.  Qiskit is used only by
``qft_matrix`` as an implementation check; none of the bounds depend on a
simulator or on a gate decomposition.

The central certified statement is deliberately narrow.  If one shot's
measurement distribution is within total variation distance ``delta`` of the
ideal distribution, then any event based on ``m`` independent shots changes
by at most ``m*delta``.  Approximate-QFT controlled-phase truncation supplies a
factor-blind finite bound for ``delta``.  This is a hybrid bound, not a new
generic Fourier theorem; its contribution here is the explicit finite
parameter instantiation and precision rule for the Regev endpoint.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import log2, pi, sqrt
from typing import Sequence

import numpy as np


@dataclass(frozen=True, slots=True)
class QFTPrecisionChoice:
    """A factor-blind approximate-QFT choice with a certified shot budget."""

    dimension: int
    M: int
    register_bits: int
    sample_count: int
    cutoff: int
    omitted_angle_bound_per_register: float
    operator_error_bound: float
    per_shot_tv_bound: float
    m_shot_recovery_loss_bound: float
    recovery_loss_budget: float
    exact_controlled_phase_gates: int
    approximate_controlled_phase_gates: int
    exact_two_qubit_qft_gates: int
    approximate_two_qubit_qft_gates: int
    certified: bool
    selection_reason: str

    def as_record(self) -> dict[str, int | float | bool | str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FiberPrecisionChoice:
    """Small-state, factor-blind precision choice from an exact fiber law.

    Unlike the worst-case operator bound, this diagnostic is evaluated on the
    known modular-exponentiation fibers and never on factors, relation labels,
    or a recovery outcome.  It is therefore a non-circular QFT-design metric,
    but it is computationally practical only for the explicitly reported
    small-state validation instances.
    """

    dimension: int
    N: int
    M: int
    sample_count: int
    cutoff: int
    per_shot_tv: float
    m_shot_tv_union_bound: float
    budget: float
    controlled_phase_gates: int
    exact_controlled_phase_gates: int
    certified: bool
    selection_reason: str


def register_bits(M: int) -> int:
    """Return ``q`` for ``M=2**q``."""

    if not isinstance(M, (int, np.integer)) or isinstance(M, bool):
        raise TypeError("M must be an integer")
    M = int(M)
    if M <= 1 or M & (M - 1):
        raise ValueError("M must be a power of two greater than one")
    return int(log2(M))


def omitted_rotation_angle_sum(q: int, cutoff: int) -> float:
    """Bound the one-register operator error from omitted QFT phases.

    With separation ``r`` there are ``q-r`` controlled rotations, each of
    angle ``pi/2**r``.  ``cutoff`` retains separations at most that value.
    The returned sum is zero for an exact decomposition.
    """

    q = int(q)
    cutoff = int(cutoff)
    if q <= 0:
        raise ValueError("q must be positive")
    if cutoff < 0:
        raise ValueError("cutoff must be nonnegative")
    return float(
        pi * sum((q - r) / (2**r) for r in range(cutoff + 1, q))
    )


def omitted_rotation_angle_sum_closed_form(q: int, cutoff: int) -> float:
    """Closed form for ``omitted_rotation_angle_sum``.

    For ``s=q-cutoff`` the finite tail is
    ``pi * 2**(-cutoff) * (s-2+2**(-(s-1)))``.  The form is useful for scaling
    studies because it avoids summing over all omitted rotations.
    """

    q, cutoff = int(q), int(cutoff)
    if q <= 0 or cutoff < 0:
        raise ValueError("q must be positive and cutoff nonnegative")
    if cutoff >= q - 1:
        return 0.0
    s = q - cutoff
    return float(pi * 2.0 ** (-cutoff) * (s - 2 + 2.0 ** (-(s - 1))))


def dimensionless_precision_ratio(
    d: int, M: int, sample_count: int, cutoff: int, loss_budget: float
) -> float:
    """The normalized m-shot truncation certificate ``m*delta/Delta``."""

    if not 0 < float(loss_budget):
        raise ValueError("loss_budget must be positive")
    q = register_bits(M)
    return float(
        int(sample_count)
        * qft_tv_bound(int(d), q, int(cutoff))
        / float(loss_budget)
    )


def qft_operator_error_bound(d: int, q: int, cutoff: int) -> float:
    """Telescoping operator-norm bound for ``F_t**d-F**d``."""

    if int(d) <= 0:
        raise ValueError("d must be positive")
    return float(int(d) * omitted_rotation_angle_sum(int(q), int(cutoff)))


def qft_tv_bound(d: int, q: int, cutoff: int) -> float:
    """Conservative one-shot total-variation bound.

    For a unitary perturbation of norm ``e``, measurement probabilities are
    bounded by ``2e`` in total variation.  The result is clipped at one.
    """

    return min(1.0, 2.0 * qft_operator_error_bound(d, q, cutoff))


def qft_gate_counts(d: int, q: int, cutoff: int) -> dict[str, int]:
    """Logical QFT gate counts, excluding modular arithmetic."""

    d, q, cutoff = int(d), int(q), int(cutoff)
    if d <= 0 or q <= 0 or cutoff < 0:
        raise ValueError("d and q must be positive and cutoff nonnegative")
    retained_separations = min(cutoff, q - 1)
    cp_per_register = sum(q - r for r in range(1, retained_separations + 1))
    exact_cp = q * (q - 1) // 2
    return {
        "hadamard": d * q,
        "swap": d * (q // 2),
        "controlled_phase": d * cp_per_register,
        "exact_controlled_phase": d * exact_cp,
        "omitted_controlled_phase": d * (exact_cp - cp_per_register),
        "two_qubit_qft_gates": d * (q // 2 + cp_per_register),
        "exact_two_qubit_qft_gates": d * (q // 2 + exact_cp),
    }


def select_qft_cutoff(
    d: int,
    M: int,
    sample_count: int,
    recovery_loss_budget: float = 0.05,
) -> QFTPrecisionChoice:
    """Choose the least precision certified by the finite-shot hybrid bound.

    The rule uses only ``(d,M,m)`` and a declared loss budget.  It never
    observes factors, relation labels, lattice outcomes, or recovery success.
    If no non-exact cutoff satisfies the budget, the exact cutoff is returned
    and the record states that no saving is certified.
    """

    d, M, sample_count = int(d), int(M), int(sample_count)
    if d <= 0 or sample_count <= 0:
        raise ValueError("d and sample_count must be positive")
    if not 0 < float(recovery_loss_budget) <= 1:
        raise ValueError("recovery_loss_budget must lie in (0,1]")
    q = register_bits(M)
    chosen = q - 1
    for cutoff in range(0, q):
        loss = sample_count * qft_tv_bound(d, q, cutoff)
        if loss <= recovery_loss_budget:
            chosen = cutoff
            break
    tv = qft_tv_bound(d, q, chosen)
    loss = min(1.0, sample_count * tv)
    counts = qft_gate_counts(d, q, chosen)
    exact_counts = qft_gate_counts(d, q, q - 1)
    certified = loss <= recovery_loss_budget
    reason = (
        "least cutoff satisfying m-shot hybrid bound"
        if chosen < q - 1 and certified
        else "exact QFT required by declared finite-shot budget"
    )
    return QFTPrecisionChoice(
        dimension=d,
        M=M,
        register_bits=q,
        sample_count=sample_count,
        cutoff=chosen,
        omitted_angle_bound_per_register=omitted_rotation_angle_sum(q, chosen),
        operator_error_bound=qft_operator_error_bound(d, q, chosen),
        per_shot_tv_bound=tv,
        m_shot_recovery_loss_bound=loss,
        recovery_loss_budget=float(recovery_loss_budget),
        exact_controlled_phase_gates=exact_counts["controlled_phase"],
        approximate_controlled_phase_gates=counts["controlled_phase"],
        exact_two_qubit_qft_gates=exact_counts["two_qubit_qft_gates"],
        approximate_two_qubit_qft_gates=counts["two_qubit_qft_gates"],
        certified=certified,
        selection_reason=reason,
    )


def recovery_success_hybrid_bound(
    ideal_success_probability: float,
    per_shot_tv: float,
    sample_count: int,
    target_probability: float | None = None,
) -> dict[str, float | bool]:
    """Finite-shot event bound for any downstream recovery procedure."""

    p0 = float(ideal_success_probability)
    delta = min(1.0, float(per_shot_tv))
    m = int(sample_count)
    if not 0 <= p0 <= 1 or not 0 <= delta <= 1 or m <= 0:
        raise ValueError("invalid probability, distance, or sample count")
    loss = min(1.0, m * delta)
    lower = max(0.0, p0 - loss)
    upper = min(1.0, p0 + loss)
    result: dict[str, float | bool] = {
        "ideal_success_probability": p0,
        "per_shot_tv": delta,
        "sample_count": float(m),
        "absolute_success_probability_error_bound": loss,
        "lower_bound": lower,
        "upper_bound": upper,
    }
    if target_probability is not None:
        target = float(target_probability)
        if not 0 <= target <= 1:
            raise ValueError("target_probability must lie in [0,1]")
        result["certified_above_target"] = bool(lower >= target)
    return result


def fiber_qft_tv_distance(
    N: int,
    bases: Sequence[int],
    M: int,
    cutoff: int,
    *,
    inverse: bool = True,
) -> float:
    """Total variation distance between exact and truncated fiber laws."""

    exact = fiber_fourier_distribution(N, bases, M, cutoff=None, inverse=inverse)
    approx = fiber_fourier_distribution(N, bases, M, cutoff=cutoff, inverse=inverse)
    return float(0.5 * np.abs(exact - approx).sum())


def weighted_fiber_qft_tv_distance(
    N: int,
    bases: Sequence[int],
    M: int,
    amplitudes: Sequence[float],
    cutoff: int,
    *,
    inverse: bool = True,
) -> float:
    """TV distance for a separable finite amplitude state."""

    exact = weighted_fiber_fourier_distribution(
        N, bases, M, amplitudes, cutoff=None, inverse=inverse
    )
    approx = weighted_fiber_fourier_distribution(
        N, bases, M, amplitudes, cutoff=cutoff, inverse=inverse
    )
    return float(0.5 * np.abs(exact - approx).sum())


def select_fiber_qft_cutoff(
    N: int,
    bases: Sequence[int],
    M: int,
    sample_count: int,
    budget: float = 0.05,
    *,
    inverse: bool = True,
) -> FiberPrecisionChoice:
    """Choose the least cutoff whose *fiber-law* error meets a shot budget.

    This is an optional state-aware refinement of ``select_qft_cutoff``.  It
    remains factor-blind because the only data used are ``N``, the selected
    circuit bases, and the modular-product fibers; it is not a recovery
    optimizer.  The routine is intentionally restricted to small exact laws
    and is not used to make claims about large Regev Gaussian states.
    """

    d = len(tuple(bases))
    if d <= 0 or int(sample_count) <= 0:
        raise ValueError("bases and sample_count must be nonempty/positive")
    if not 0 < float(budget) <= 1:
        raise ValueError("budget must lie in (0,1]")
    q = register_bits(M)
    chosen = q - 1
    chosen_tv = fiber_qft_tv_distance(N, bases, M, chosen, inverse=inverse)
    for cutoff in range(0, q):
        tv = fiber_qft_tv_distance(N, bases, M, cutoff, inverse=inverse)
        if int(sample_count) * tv <= float(budget):
            chosen, chosen_tv = cutoff, tv
            break
    counts = qft_gate_counts(d, q, chosen)
    exact_counts = qft_gate_counts(d, q, q - 1)
    union = min(1.0, int(sample_count) * chosen_tv)
    certified = union <= float(budget)
    return FiberPrecisionChoice(
        dimension=d,
        N=int(N),
        M=int(M),
        sample_count=int(sample_count),
        cutoff=int(chosen),
        per_shot_tv=float(chosen_tv),
        m_shot_tv_union_bound=float(union),
        budget=float(budget),
        controlled_phase_gates=counts["controlled_phase"],
        exact_controlled_phase_gates=exact_counts["controlled_phase"],
        certified=bool(certified),
        selection_reason="least cutoff satisfying exact fiber-law m-shot bound",
    )


def grid_quantization_bound(d: int, M: int) -> float:
    """Euclidean torus error from rounding each coordinate to an ``M`` grid."""

    if int(d) <= 0:
        raise ValueError("d must be positive")
    register_bits(M)
    return sqrt(int(d)) / (2.0 * int(M))


def embedding_noise_norm_bound(
    sample_count: int, scale: float, coordinate_error: float
) -> float:
    """Bottom-block norm contributed by bounded coordinate errors."""

    if int(sample_count) <= 0 or float(scale) < 0 or float(coordinate_error) < 0:
        raise ValueError("sample_count, scale, and coordinate_error are invalid")
    return float(scale) * sqrt(int(sample_count)) * float(coordinate_error)


def coherent_phase_tv_bound(max_phase_error: float) -> float:
    """One-shot TV bound for a bounded coherent input phase error."""

    if float(max_phase_error) < 0:
        raise ValueError("max_phase_error must be nonnegative")
    # || exp(i theta)|psi> - |psi> || <= max |exp(i theta)-1|.
    return min(1.0, 2.0 * np.sin(min(float(max_phase_error), pi) / 2.0))


def bitflip_channel(
    probabilities: np.ndarray, bitflip_probability: float
) -> np.ndarray:
    """Apply independent computational-basis bit flips to a tensor law."""

    p = float(bitflip_probability)
    if not 0 <= p <= 1:
        raise ValueError("bitflip_probability must lie in [0,1]")
    arr = np.asarray(probabilities, dtype=float)
    if arr.ndim == 0 or any(size <= 0 or size & (size - 1) for size in arr.shape):
        raise ValueError("each outcome axis must have a power-of-two length")
    out = np.zeros_like(arr)
    for index in np.ndindex(arr.shape):
        mass = arr[index]
        if mass == 0:
            continue
        for mask in range(1 << arr.ndim):
            target = list(index)
            flips = mask.bit_count()
            for axis, size in enumerate(arr.shape):
                if mask & (1 << axis):
                    bit_width = int(log2(size))
                    target[axis] ^= 1 << (bit_width - 1)
            out[tuple(target)] += mass * p**flips * (1 - p) ** (arr.ndim - flips)
    return out / out.sum()


def exact_qft_matrix(M: int, *, inverse: bool = True) -> np.ndarray:
    """The mathematical roots-of-unity matrix on one ``M``-point register."""

    q = register_bits(M)
    indices = np.arange(M, dtype=float)
    sign = -1.0 if inverse else 1.0
    return np.exp(sign * 2j * pi * np.outer(indices, indices) / M) / sqrt(M)


def qft_matrix(M: int, cutoff: int | None = None, *, inverse: bool = True) -> np.ndarray:
    """Return an exact or truncated-QFT matrix using Qiskit's gate convention.

    This is an implementation check, not the definition used by the bounds.
    The returned matrix is compared with ``exact_qft_matrix`` at full cutoff
    in the test suite.
    """

    q = register_bits(M)
    if cutoff is None:
        cutoff = q - 1
    cutoff = int(cutoff)
    if cutoff < 0:
        raise ValueError("cutoff must be nonnegative")
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import QFTGate
    from qiskit.quantum_info import Operator

    if cutoff >= q - 1:
        circuit = QuantumCircuit(q)
        circuit.append(QFTGate(q).inverse() if inverse else QFTGate(q), range(q))
        return np.asarray(Operator(circuit).data, dtype=complex)

    # Use the same standard decomposition as QFTGate, omitting phases whose
    # qubit separation exceeds cutoff.  Inverse is applied after construction
    # so the approximation remains the adjoint of the forward approximation.
    circuit = QuantumCircuit(q)
    for j in range(q):
        circuit.h(j)
        for k in range(j + 1, q):
            separation = k - j
            if separation <= cutoff:
                circuit.cp(pi / (2**separation), k, j)
    for j in range(q // 2):
        circuit.swap(j, q - 1 - j)
    if inverse:
        circuit = circuit.inverse()
    return np.asarray(Operator(circuit).data, dtype=complex)


def uniform_fiber_vectors(
    N: int, bases: Sequence[int], M: int
) -> dict[int, np.ndarray]:
    """Return unnormalised computational fibers of modular exponentiation."""

    register_bits(M)
    bases = tuple(int(a) % int(N) for a in bases)
    d = len(bases)
    if d <= 0:
        raise ValueError("bases must be nonempty")
    fibers: dict[int, np.ndarray] = {}
    for x in np.ndindex((M,) * d):
        residue = 1
        for a, exponent in zip(bases, x, strict=True):
            residue = residue * pow(a, int(exponent), int(N)) % int(N)
        vector = fibers.setdefault(residue, np.zeros(M**d, dtype=complex))
        vector[np.ravel_multi_index(x, (M,) * d)] = 1.0
    return fibers


def weighted_fiber_fourier_distribution(
    N: int,
    bases: Sequence[int],
    M: int,
    amplitudes: Sequence[float],
    *,
    cutoff: int | None = None,
    inverse: bool = True,
    phase_errors: np.ndarray | None = None,
) -> np.ndarray:
    """Finite exact fiber law for a separable amplitude state.

    The amplitude on ``x`` is ``prod_i amplitudes[x_i]``.  This covers the
    notebook hard box (all amplitudes one) and Regev's centered truncated
    discrete-Gaussian amplitude state.
    """

    weights = np.asarray(amplitudes, dtype=float)
    if weights.shape != (int(M),) or not np.all(np.isfinite(weights)):
        raise ValueError("amplitudes must be a finite vector of length M")
    if not np.any(weights):
        raise ValueError("amplitudes must not be identically zero")
    bases = tuple(int(a) % int(N) for a in bases)
    d = len(bases)
    if d <= 0:
        raise ValueError("bases must be nonempty")
    register_bits(M)
    fibers: dict[int, np.ndarray] = {}
    shape = (int(M),) * d
    for x in np.ndindex(shape):
        residue = 1
        amplitude = 1.0
        for a, exponent, weight in zip(bases, x, (weights[value] for value in x), strict=True):
            residue = residue * pow(a, int(exponent), int(N)) % int(N)
            amplitude *= float(weight)
        vector = fibers.setdefault(residue, np.zeros(int(M) ** d, dtype=complex))
        vector[np.ravel_multi_index(x, shape)] = amplitude
    transform = qft_matrix(int(M), cutoff=cutoff, inverse=inverse)
    product_transform = transform
    for _ in range(d - 1):
        product_transform = np.kron(product_transform, transform)
    if phase_errors is not None:
        phase = np.asarray(phase_errors, dtype=float).reshape(int(M) ** d)
        phase_factor = np.exp(1j * phase)
    else:
        phase_factor = np.ones(int(M) ** d, dtype=complex)
    normalization = float(np.sum(np.abs(np.concatenate(tuple(vector for vector in fibers.values()))) ** 2))
    # The concatenation above repeats no coordinate: fibers partition the box.
    probabilities = np.zeros(int(M) ** d, dtype=float)
    for vector in fibers.values():
        output = product_transform @ (vector * phase_factor / sqrt(normalization))
        probabilities += np.abs(output) ** 2
    probabilities = probabilities.reshape(shape)
    probabilities /= probabilities.sum()
    return probabilities


def fiber_fourier_distribution(
    N: int,
    bases: Sequence[int],
    M: int,
    *,
    cutoff: int | None = None,
    inverse: bool = True,
    phase_errors: np.ndarray | None = None,
) -> np.ndarray:
    """Exact small-state output law after tracing out modular arithmetic.

    For every arithmetic fiber ``F_y={x:h_A(x)=y}``, the circuit has a
    uniform amplitude vector on that fiber.  The product QFT is applied to the
    vector, and probabilities are summed over ``y``.  This makes the
    roots-of-unity interference explicit without constructing the arithmetic
    oracle matrix.
    """

    bases = tuple(int(a) % int(N) for a in bases)
    d = len(bases)
    amplitudes = np.ones(int(M), dtype=float)
    return weighted_fiber_fourier_distribution(
        N,
        bases,
        M,
        amplitudes,
        cutoff=cutoff,
        inverse=inverse,
        phase_errors=phase_errors,
    )


def roots_of_unity_amplitude(
    fiber: Sequence[Sequence[int]], outcome: Sequence[int], M: int, *, inverse: bool = True
) -> complex:
    """Return the unnormalised character sum for one arithmetic fiber."""

    sign = -1.0 if inverse else 1.0
    total = 0.0j
    k = np.asarray(tuple(outcome), dtype=int)
    for x in fiber:
        total += np.exp(sign * 2j * pi * int(np.dot(k, np.asarray(x, dtype=int))) / M)
    return total

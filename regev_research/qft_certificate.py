"""Factor-blind certificates and slack audits for truncated product QFTs.

This module separates four logically different statements:

* a theorem/certificate approves a cutoff;
* a particular recovery algorithm succeeds empirically;
* the measured distribution has lost information;
* no possible postprocessor could recover the desired relation.

Only the first two are evaluated here.  Distribution equality can refute an
information-loss explanation, but distribution distance alone never proves
that no classical postprocessor can succeed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pi, sqrt
from typing import Sequence

import numpy as np

from .qft_noise import (
    omitted_rotation_angle_sum,
    qft_matrix,
    qft_operator_error_bound,
    qft_tv_bound,
    register_bits,
)


@dataclass(frozen=True, slots=True)
class CertificateDecision:
    name: str
    per_shot_bound: float
    m_shot_bound: float
    loss_budget: float
    certified: bool
    meaning: str

    def as_record(self) -> dict[str, str | float | bool]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FiberStateAudit:
    trace_distance_bound: float
    state_vector_norm_error: float
    overlap_magnitude: float
    exact_norm: float
    approximate_norm: float
    fiber_count: int


def _validate_probability_array(probabilities: np.ndarray, name: str) -> np.ndarray:
    values = np.asarray(probabilities, dtype=float)
    if values.ndim == 0 or np.any(~np.isfinite(values)) or np.any(values < -1e-14):
        raise ValueError(f"{name} must be a finite nonnegative probability array")
    values = np.maximum(values, 0.0)
    mass = float(values.sum())
    if not np.isclose(mass, 1.0, atol=1e-10):
        raise ValueError(f"{name} must have total mass one")
    return values / mass


def total_variation_distance(exact: np.ndarray, approximate: np.ndarray) -> float:
    p = _validate_probability_array(exact, "exact")
    q = _validate_probability_array(approximate, "approximate")
    if p.shape != q.shape:
        raise ValueError("probability arrays must have the same shape")
    return float(0.5 * np.abs(p - q).sum())


def hellinger_affinity(exact: np.ndarray, approximate: np.ndarray) -> float:
    """Return the Bhattacharyya/Hellinger affinity ``sum sqrt(p*q)``."""

    p = _validate_probability_array(exact, "exact")
    q = _validate_probability_array(approximate, "approximate")
    if p.shape != q.shape:
        raise ValueError("probability arrays must have the same shape")
    return float(np.clip(np.sqrt(p * q).sum(), 0.0, 1.0))


def original_certificate(
    d: int, M: int, sample_count: int, cutoff: int, loss_budget: float
) -> CertificateDecision:
    """Worst-case operator/tensor/hybrid certificate used by the first study.

    ``certified`` uses a non-strict comparison: equality with the declared
    budget is approved.  The barrier therefore uses a strict ``M <``.
    """

    if int(d) <= 0 or int(sample_count) <= 0 or not 0 < float(loss_budget) <= 1:
        raise ValueError("d and sample_count must be positive; loss_budget must lie in (0,1]")
    q = register_bits(M)
    if not 0 <= int(cutoff) < q:
        raise ValueError("cutoff must lie in {0,...,q-1}")
    per_shot = qft_tv_bound(int(d), q, int(cutoff))
    m_shot = min(1.0, int(sample_count) * per_shot)
    return CertificateDecision(
        name="worst_case_operator_hybrid",
        per_shot_bound=per_shot,
        m_shot_bound=m_shot,
        loss_budget=float(loss_budget),
        certified=bool(m_shot <= float(loss_budget)),
        meaning=(
            "all-input operator bound, product-QFT telescoping, measurement "
            "conversion, and m-sample hybrid bound"
        ),
    )


def first_nonexact_barrier(d: int, sample_count: int, loss_budget: float) -> float:
    """Return ``4*pi*d*m/Delta`` for the first omitted QFT phase layer."""

    if int(d) <= 0 or int(sample_count) <= 0 or not 0 < float(loss_budget) < 1:
        raise ValueError("the strict barrier requires positive d,m and loss_budget in (0,1)")
    return float(4 * pi * int(d) * int(sample_count) / float(loss_budget))


def barrier_excludes_nonexact(
    d: int, M: int, sample_count: int, loss_budget: float
) -> bool:
    """Whether the strict analytic barrier rejects every non-exact cutoff."""

    register_bits(M)
    if not 0 < float(loss_budget) < 1:
        raise ValueError("the strict barrier requires loss_budget in (0,1)")
    return bool(int(M) < first_nonexact_barrier(d, sample_count, loss_budget))


def distribution_tv_certificate(
    exact: np.ndarray,
    approximate: np.ndarray,
    sample_count: int,
    loss_budget: float,
) -> CertificateDecision:
    """State/model-specific certificate from the exact measured laws."""

    if int(sample_count) <= 0 or not 0 < float(loss_budget) <= 1:
        raise ValueError("sample_count must be positive and loss_budget must lie in (0,1]")
    tv = total_variation_distance(exact, approximate)
    bound = min(1.0, int(sample_count) * tv)
    return CertificateDecision(
        name="exact_distribution_tv_hybrid",
        per_shot_bound=tv,
        m_shot_bound=bound,
        loss_budget=float(loss_budget),
        certified=bool(bound <= float(loss_budget)),
        meaning="exact finite measured laws followed by the m-sample hybrid bound",
    )


def product_hellinger_certificate(
    exact: np.ndarray,
    approximate: np.ndarray,
    sample_count: int,
    loss_budget: float,
) -> CertificateDecision:
    """Direct product-law bound from multiplicative Hellinger affinity.

    If ``A=sum sqrt(pq)``, the affinity of independent m-sample product laws
    is ``A**m`` and their TV distance is at most ``sqrt(1-A**(2m))``.
    """

    if int(sample_count) <= 0 or not 0 < float(loss_budget) <= 1:
        raise ValueError("sample_count must be positive and loss_budget must lie in (0,1]")
    affinity = hellinger_affinity(exact, approximate)
    product_bound = sqrt(max(0.0, 1.0 - affinity ** (2 * int(sample_count))))
    one_shot = sqrt(max(0.0, 1.0 - affinity**2))
    return CertificateDecision(
        name="product_hellinger",
        per_shot_bound=one_shot,
        m_shot_bound=product_bound,
        loss_budget=float(loss_budget),
        certified=bool(product_bound <= float(loss_budget)),
        meaning="exact finite distribution affinity with independent product composition",
    )


def _weighted_fibers(
    N: int, bases: Sequence[int], M: int, amplitudes: Sequence[float]
) -> tuple[dict[int, np.ndarray], float]:
    weights = np.asarray(amplitudes, dtype=float)
    if weights.shape != (M,) or np.any(~np.isfinite(weights)) or not np.any(weights):
        raise ValueError("amplitudes must be a finite nonzero vector of length M")
    bases = tuple(int(value) % int(N) for value in bases)
    if not bases:
        raise ValueError("bases must be nonempty")
    shape = (M,) * len(bases)
    fibers: dict[int, np.ndarray] = {}
    normalization = 0.0
    for x in np.ndindex(shape):
        residue = 1
        amplitude = 1.0
        for base, exponent in zip(bases, x, strict=True):
            residue = residue * pow(base, int(exponent), int(N)) % int(N)
            amplitude *= float(weights[exponent])
        vector = fibers.setdefault(residue, np.zeros(M ** len(bases), dtype=complex))
        vector[np.ravel_multi_index(x, shape)] = amplitude
        normalization += amplitude * amplitude
    return fibers, float(normalization)


def fiber_state_audit(
    N: int,
    bases: Sequence[int],
    M: int,
    amplitudes: Sequence[float],
    cutoff: int,
) -> FiberStateAudit:
    """Compare exact/approximate QFT only on the prepared joint fiber state."""

    q = register_bits(M)
    if not 0 <= int(cutoff) < q:
        raise ValueError("cutoff must lie in {0,...,q-1}")
    d = len(tuple(bases))
    fibers, normalization = _weighted_fibers(N, bases, M, amplitudes)
    exact_one = qft_matrix(M, cutoff=q - 1, inverse=True)
    approximate_one = qft_matrix(M, cutoff=cutoff, inverse=True)
    exact_transform = exact_one
    approximate_transform = approximate_one
    for _ in range(d - 1):
        exact_transform = np.kron(exact_transform, exact_one)
        approximate_transform = np.kron(approximate_transform, approximate_one)
    overlap = 0.0j
    squared_norm_error = 0.0
    exact_norm = 0.0
    approximate_norm = 0.0
    for vector in fibers.values():
        normalized = vector / sqrt(normalization)
        exact_output = exact_transform @ normalized
        approximate_output = approximate_transform @ normalized
        overlap += np.vdot(exact_output, approximate_output)
        squared_norm_error += float(np.vdot(exact_output - approximate_output, exact_output - approximate_output).real)
        exact_norm += float(np.vdot(exact_output, exact_output).real)
        approximate_norm += float(np.vdot(approximate_output, approximate_output).real)
    overlap_magnitude = float(min(1.0, abs(overlap)))
    trace = sqrt(max(0.0, 1.0 - overlap_magnitude**2))
    return FiberStateAudit(
        trace_distance_bound=trace,
        state_vector_norm_error=sqrt(max(0.0, squared_norm_error)),
        overlap_magnitude=overlap_magnitude,
        exact_norm=exact_norm,
        approximate_norm=approximate_norm,
        fiber_count=len(fibers),
    )


def fiber_state_certificate(
    audit: FiberStateAudit, sample_count: int, loss_budget: float
) -> CertificateDecision:
    if int(sample_count) <= 0 or not 0 < float(loss_budget) <= 1:
        raise ValueError("sample_count must be positive and loss_budget must lie in (0,1]")
    bound = min(1.0, int(sample_count) * audit.trace_distance_bound)
    return CertificateDecision(
        name="prepared_fiber_state_trace_hybrid",
        per_shot_bound=audit.trace_distance_bound,
        m_shot_bound=bound,
        loss_budget=float(loss_budget),
        certified=bool(bound <= float(loss_budget)),
        meaning="trace distance on the prepared arithmetic-fiber joint state",
    )


def feasible_matrix_distances(d: int, M: int, cutoff: int, max_dimension: int = 512) -> dict[str, float | None]:
    """Observed one-register and product operator distances where feasible."""

    q = register_bits(M)
    exact = qft_matrix(M, cutoff=q - 1, inverse=True)
    approximate = qft_matrix(M, cutoff=cutoff, inverse=True)
    one_error = float(np.linalg.norm(exact - approximate, 2))
    product_dimension = M**int(d)
    product_error: float | None = None
    if product_dimension <= int(max_dimension):
        exact_product = exact
        approximate_product = approximate
        for _ in range(int(d) - 1):
            exact_product = np.kron(exact_product, exact)
            approximate_product = np.kron(approximate_product, approximate)
        product_error = float(np.linalg.norm(exact_product - approximate_product, 2))
    return {
        "one_register_operator_error": one_error,
        "product_operator_error": product_error,
        "one_register_triangle_bound": omitted_rotation_angle_sum(q, cutoff),
        "product_triangle_bound": qft_operator_error_bound(d, q, cutoff),
    }


def slack_factor(theoretical: float, observed: float) -> float | None:
    """Return bound/observed; ``None`` denotes zero observed denominator."""

    if theoretical < 0 or observed < 0:
        raise ValueError("slack values must be nonnegative")
    if observed == 0:
        return None
    return float(theoretical / observed)

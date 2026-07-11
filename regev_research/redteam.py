"""Red-team sampling models and factor-blind rooted-base ablations.

This module deliberately separates the selected roots ``b_i`` from their
derived circuit bases ``a_i = b_i**2 mod N`` by returning only immutable
``RootedBaseFamily`` objects.  The selectors never receive a factorization,
group order, or modular square root.

The exact weighted Fourier evaluator covers both the notebook's uniform box
and Regev's finite, truncated discrete-Gaussian *amplitude* state.  It uses the
autocorrelation/character formula rather than a statevector arithmetic
simulation.  It is exact up to floating-point evaluation of Gaussian weights
and FFT roundoff; the finite sum being evaluated is exact and explicit.
"""

from __future__ import annotations

from functools import lru_cache
from itertools import product
from math import gcd, pi
from typing import Sequence

import numpy as np

from .core import (
    RootedBase,
    RootedBaseFamily,
    bounded_product_diversity,
    bounded_relations,
    modular_product,
)


REDTEAM_METHODS = (
    "residue_deduplication_only",
    "short_relation_rejection_only",
    "subgroup_overlap_only",
    "complete_selector",
    "random_coprime_roots",
    "regev_small_prime_roots",
)


def centered_coordinates(modulus: int) -> np.ndarray:
    """Return the integer labels used by Regev's centered finite register."""
    if modulus <= 0 or modulus % 2:
        raise ValueError("modulus must be a positive even integer")
    return np.arange(-modulus // 2, modulus // 2, dtype=np.int64)


def regev_gaussian_amplitudes(modulus: int, radius: float) -> np.ndarray:
    """Return ``rho_R(z)=exp(-pi*z^2/R^2)`` on ``[-D/2,D/2)``.

    These are amplitudes, not probabilities.  Consequently their squared norm
    is a discrete Gaussian with parameter ``R/sqrt(2)``, as in Regev's Fourier
    calculation.
    """
    if not np.isfinite(radius) or radius <= 0:
        raise ValueError("radius must be finite and positive")
    z = centered_coordinates(modulus).astype(float)
    return np.exp(-pi * z * z / (radius * radius))


def uniform_amplitudes(modulus: int) -> np.ndarray:
    if modulus <= 0:
        raise ValueError("modulus must be positive")
    return np.ones(modulus, dtype=float)


def amplitude_autocorrelation(amplitudes: Sequence[float]) -> np.ndarray:
    """Finite, non-circular autocorrelation indexed by lags ``-(D-1)..D-1``."""
    values = np.asarray(amplitudes, dtype=float)
    if values.ndim != 1 or not len(values):
        raise ValueError("amplitudes must be a nonempty one-dimensional sequence")
    if not np.all(np.isfinite(values)):
        raise ValueError("amplitudes must be finite")
    # np.correlate returns the desired symmetric lag ordering for real values.
    return np.correlate(values, values, mode="full")


def exact_weighted_fourier_distribution(
    N: int,
    bases: Sequence[int],
    modulus: int,
    one_dimensional_amplitudes: Sequence[float],
    *,
    max_difference_points: int = 2_500_000,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Evaluate the exact finite weighted-oracle/QFT law.

    Let ``g(x)=prod_i w[x_i]`` be the initial real amplitude on a Cartesian
    register box and let ``h_A(x)=prod_i a_i**x_i mod N``.  After computing and
    discarding ``h_A(x)`` and applying the tensor QFT, define

    ``C(z)=prod_i sum_x w[x]w[x+z_i]``

    on the valid overlap.  The folded kernel is

    ``K(r)=sum_{z in L, z=r mod D} C(z)``.

    If ``Z=(sum_x w[x]^2)^d``, then

    ``P(k)=DFT(K)(k)/(D^d Z)``.

    The returned scalar is ``Z``.  For uniform amplitudes, ``C(z)`` is the
    triangular weight and this reduces to the notebook hard-box formula.
    """
    if N <= 2:
        raise ValueError("N must exceed two")
    residues_bases = tuple(int(a) % N for a in bases)
    if not residues_bases or any(gcd(a, N) != 1 for a in residues_bases):
        raise ValueError("bases must be a nonempty sequence of units modulo N")
    weights = np.asarray(one_dimensional_amplitudes, dtype=float)
    if weights.shape != (modulus,):
        raise ValueError("amplitude vector length must equal modulus")
    autocorrelation = amplitude_autocorrelation(weights)
    d = len(residues_bases)
    width = 2 * modulus - 1
    difference_points = width**d
    if difference_points > max_difference_points:
        raise ValueError(
            f"difference box has {difference_points} points; "
            f"limit is {max_difference_points}"
        )

    differences = np.arange(-(modulus - 1), modulus, dtype=np.int64)
    shape = (width,) * d
    product_residues = np.ones(shape, dtype=np.int64)
    pair_weights = np.ones(shape, dtype=float)
    for axis, a in enumerate(residues_bases):
        powers = np.asarray([pow(a, int(z), N) for z in differences], dtype=np.int64)
        axis_shape = [1] * d
        axis_shape[axis] = width
        product_residues = product_residues * powers.reshape(axis_shape) % N
        pair_weights *= autocorrelation.reshape(axis_shape)

    locations = np.argwhere(product_residues == 1)
    signed = locations - (modulus - 1)
    folded = signed % modulus
    kernel = np.zeros((modulus,) * d, dtype=float)
    np.add.at(kernel, tuple(folded.T), pair_weights[tuple(locations.T)])

    normalization = float(np.sum(weights * weights) ** d)
    probabilities = np.fft.fftn(kernel).real / float(modulus**d * normalization)
    probabilities[np.abs(probabilities) < 2e-15] = 0.0
    if float(probabilities.min()) < -1e-9:
        raise ArithmeticError("weighted Fourier law has a material negative value")
    probabilities = np.maximum(probabilities, 0.0)
    # Only roundoff is corrected here; a material normalization error is fatal.
    mass = float(probabilities.sum())
    if abs(mass - 1.0) > 1e-8:
        raise ArithmeticError(f"weighted Fourier law has mass {mass}")
    probabilities /= mass
    return probabilities, kernel, normalization


def exact_regev_gaussian_distribution(
    N: int,
    bases: Sequence[int],
    modulus: int,
    radius: float,
    *,
    max_difference_points: int = 2_500_000,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Exact finite output law for Regev's centered ``rho_R`` amplitude state."""
    return exact_weighted_fourier_distribution(
        N,
        bases,
        modulus,
        regev_gaussian_amplitudes(modulus, radius),
        max_difference_points=max_difference_points,
    )


def weighted_chi_square_from_kernel(kernel: np.ndarray, normalization: float) -> float:
    """Parseval form of ``chi^2(P || uniform)`` for a weighted state."""
    if normalization <= 0:
        raise ValueError("normalization must be positive")
    origin = (0,) * kernel.ndim
    if not np.isclose(kernel[origin], normalization, rtol=2e-12, atol=2e-12):
        raise ValueError("kernel origin must equal the amplitude squared norm")
    return float((np.sum(kernel * kernel) - normalization**2) / normalization**2)


@lru_cache(maxsize=None)
def cyclic_subgroup(N: int, base: int) -> frozenset[int]:
    """Enumerate ``<base>`` by multiplication; no factorization/order oracle."""
    base %= N
    if gcd(base, N) != 1:
        raise ValueError("base must be a unit")
    values = {1}
    value = base
    while value not in values:
        values.add(value)
        value = value * base % N
    if value != 1:
        raise ArithmeticError("unit orbit did not close at one")
    return frozenset(values)


def subgroup_overlap_score(N: int, bases: Sequence[int]) -> float:
    """Mean normalized pairwise cyclic-subgroup intersection in ``[0,1]``."""
    subgroups = [cyclic_subgroup(N, int(a) % N) for a in bases]
    if len(subgroups) < 2:
        return 0.0
    overlaps = []
    for i in range(len(subgroups)):
        for j in range(i + 1, len(subgroups)):
            overlaps.append(
                len(subgroups[i] & subgroups[j])
                / min(len(subgroups[i]), len(subgroups[j]))
            )
    return float(np.mean(overlaps))


def _validated_root_candidates(
    N: int, candidate_pool: Sequence[int]
) -> tuple[list[RootedBase], list[dict]]:
    valid: list[RootedBase] = []
    rejected: list[dict] = []
    seen_roots: set[int] = set()
    for raw in candidate_pool:
        root = int(raw) % N
        g = gcd(root, N)
        if g != 1:
            rejected.append(
                {
                    "candidate_root": int(raw),
                    "root": root,
                    "reason": "noncoprime",
                    "factor_discovered": g if 1 < g < N else None,
                }
            )
            continue
        if root in seen_roots:
            rejected.append(
                {"candidate_root": int(raw), "root": root, "reason": "duplicate_root"}
            )
            continue
        seen_roots.add(root)
        valid.append(RootedBase.from_root(N, root))
    return valid, rejected


def _relation_count(N: int, pairs: Sequence[RootedBase], bound: int) -> int:
    return len(bounded_relations(N, [pair.base for pair in pairs], bound))


def select_rooted_ablation_family(
    N: int,
    d: int,
    candidate_pool: Sequence[int],
    method: str,
    *,
    relation_bound: int,
    seed: int,
) -> tuple[RootedBaseFamily, dict]:
    """Apply one frozen factor-blind selector/ablation to candidate roots.

    The six methods differ only in their scoring rule.  All ultimately return
    an immutable family retaining each chosen ``(b_i,a_i)`` pair.
    """
    if method not in REDTEAM_METHODS:
        raise ValueError(f"unknown method {method!r}")
    valid, rejected = _validated_root_candidates(N, candidate_pool)
    if len(valid) < d:
        raise ValueError("candidate pool contains too few coprime roots")
    rng = np.random.default_rng(seed)
    pool_position = {pair.root: i for i, pair in enumerate(valid)}

    if method == "regev_small_prime_roots":
        selected = valid[:d]
    elif method == "random_coprime_roots":
        order = rng.permutation(len(valid))
        selected = [valid[int(i)] for i in order[:d]]
    elif method == "residue_deduplication_only":
        selected = []
        seen_bases: dict[int, RootedBase] = {}
        for pair in valid:
            if pair.base in seen_bases:
                previous = seen_bases[pair.base]
                factors = [
                    value
                    for value in (gcd(pair.root - previous.root, N), gcd(pair.root + previous.root, N))
                    if 1 < value < N
                ]
                rejected.append(
                    {
                        **pair.as_record(),
                        "reason": "duplicate_squared_base",
                        "collides_with_root": previous.root,
                        "factor_discovered": factors[0] if factors else None,
                    }
                )
                continue
            seen_bases[pair.base] = pair
            selected.append(pair)
            if len(selected) == d:
                break
    else:
        selected = []
        while len(selected) < d:
            options = []
            for pair in valid:
                if pair in selected:
                    continue
                trial = [*selected, pair]
                relation_count = _relation_count(N, trial, relation_bound)
                overlap = subgroup_overlap_score(N, [item.base for item in trial])
                diversity = bounded_product_diversity(
                    N, [item.base for item in trial], relation_bound
                )
                tie = pool_position[pair.root]
                if method == "short_relation_rejection_only":
                    key = (relation_count, tie)
                elif method == "subgroup_overlap_only":
                    key = (overlap, tie)
                else:
                    # Frozen lexicographic complete rule: bounded relations
                    # first, then subgroup overlap, then product diversity.
                    key = (relation_count, overlap, -diversity, tie)
                options.append((key, pair))
            selected.append(min(options, key=lambda item: item[0])[1])

    if len(selected) != d:
        raise ValueError("selector failed to produce d roots")
    family = RootedBaseFamily(N, tuple(selected))
    selected_set = set(selected)
    for pair in valid:
        if pair not in selected_set and not any(
            row.get("root") == pair.root for row in rejected
        ):
            rejected.append({**pair.as_record(), "reason": "not_selected"})
    diagnostics = {
        "method": method,
        "seed": int(seed),
        "candidate_pool": [int(x) for x in candidate_pool],
        "relation_bound": int(relation_bound),
        "selected_pairs": family.as_records(),
        "selected_roots": list(family.roots),
        "selected_bases": list(family.bases),
        "rejected": rejected,
        "bounded_relation_count": _relation_count(N, family.pairs, relation_bound),
        "bounded_product_diversity": bounded_product_diversity(
            N, family.bases, relation_bound
        ),
        "subgroup_overlap_score": subgroup_overlap_score(N, family.bases),
    }
    return family, diagnostics


def sample_exact_distribution(
    probabilities: np.ndarray, sample_count: int, seed: int
) -> np.ndarray:
    if sample_count <= 0:
        raise ValueError("sample_count must be positive")
    rng = np.random.default_rng(seed)
    flat = rng.choice(probabilities.size, size=sample_count, p=probabilities.ravel())
    return np.column_stack(np.unravel_index(flat, probabilities.shape)).astype(int)


def relation_is_short(
    family: RootedBaseFamily, relation: Sequence[int], bound: int
) -> bool:
    """Post-hoc audit helper; never used by a selector or LLL endpoint."""
    z = tuple(int(x) for x in relation)
    return (
        any(z)
        and max(abs(x) for x in z) <= bound
        and modular_product(family.N, family.bases, z) == 1
    )


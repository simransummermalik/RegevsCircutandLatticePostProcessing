"""Immutable inputs for the factor-or-fuse held-out study.

This file was written before executing factor-or-fuse on any modulus in
``HELDOUT_MODULI``.  The method-side API receives a modulus only.  The factor
manifest is accessed solely after raw outputs have been sealed, to audit the
returned divisors.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, gcd, isqrt, sqrt

from regev_research.core import RootedBaseFamily


PROTOCOL_ID = "factor-or-fuse-holdout-v1"
MAX_POWER = 64
TRANSPILER_SEED = 2_026_080_101
BOOTSTRAP_SEED = 2_026_080_102
EQUIVALENCE_SEED = 2_026_080_103
BOOTSTRAP_RESAMPLES = 5_000
EXACT_PARTITION_LIMIT = 12
ADVERSARIAL_RANDOM_VECTORS = 256


# These are the first 24 lexicographic products of distinct primes in
# [163, 211].  This tuple is the only case list passed to the experiment.
HELDOUT_MODULI = (
    27221,
    28199,
    29177,
    29503,
    31133,
    31459,
    32111,
    32437,
    34393,
    28891,
    29893,
    30227,
    31897,
    32231,
    32899,
    33233,
    35237,
    30967,
    31313,
    33043,
    33389,
    34081,
    34427,
    36503,
)


ARMS = (
    "serial_baseline",
    "factor_only_K64",
    "duplicate_fusion_only",
    "orbit_fusion_only_K64",
    "greedy_factor_or_fuse_K64",
    "complete_cost_optimal_factor_or_fuse_K64",
)


PUBLISHED_BENCHMARKS = (
    # label, modulus, specifically retained roots, exponent width
    ("Falco_2026_N15", 15, (2, 7), 4),
    ("Pawlitko_2026_N15", 15, (2, 7), 4),
    ("Pawlitko_2026_N21", 21, (2, 5, 11), 4),
    ("Yang_2025_N35", 35, (2, 3), 5),
)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value == 2:
        return True
    if value % 2 == 0:
        return False
    return all(value % divisor for divisor in range(3, isqrt(value) + 1, 2))


def _prime_stream():
    value = 2
    while True:
        if _is_prime(value):
            yield value
        value += 1


@dataclass(frozen=True, slots=True)
class MethodInput:
    """Everything the method may learn before returning its raw result."""

    N: int
    n: int
    dimension: int
    exponent_width: int
    family: RootedBaseFamily | None
    setup_factor: tuple[int, int] | None


def method_input_from_modulus(N: int) -> MethodInput:
    """Apply the frozen factor-blind parameter and small-prime root rules."""

    N = int(N)
    n = N.bit_length()
    dimension = ceil(sqrt(n))
    exponent_width = ceil(2 * n / dimension)
    roots: list[int] = []
    setup_factor = None
    for candidate in _prime_stream():
        divisor = gcd(candidate, N)
        if 1 < divisor < N:
            setup_factor = tuple(sorted((divisor, N // divisor)))
            break
        roots.append(candidate)
        if len(roots) == dimension:
            break
    if setup_factor is not None:
        # A dummy family must never be manufactured after setup already wins.
        return MethodInput(N, n, dimension, exponent_width, None, setup_factor)
    family = RootedBaseFamily.from_roots(N, roots)
    return MethodInput(N, n, dimension, exponent_width, family, None)


def validate_freeze() -> bool:
    primes = tuple(value for value in range(163, 212) if _is_prime(value))
    expected = tuple(
        p * q
        for offset, p in enumerate(primes)
        for q in primes[offset + 1 :]
    )[:24]
    if HELDOUT_MODULI != expected:
        return False
    if len(set(HELDOUT_MODULI)) != 24:
        return False
    return all(
        method_input_from_modulus(N).family is not None and
        method_input_from_modulus(N).family.N == N and
        method_input_from_modulus(N).dimension == 4 and
        method_input_from_modulus(N).exponent_width == 8
        for N in HELDOUT_MODULI
    )


if not validate_freeze():
    raise AssertionError("factor-or-fuse protocol freeze is internally inconsistent")

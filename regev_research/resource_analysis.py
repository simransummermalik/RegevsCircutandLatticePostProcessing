"""Exact source-level resource accounting for the supplied factoring circuits.

The notebook builds a low-width circuit by giving all exponent registers one
shared ``y`` register and one shared arithmetic workspace.  This module counts
the gates that are hidden inside those nested arithmetic ``Gate`` objects.  It
does not claim a hardware cost: routing, fault tolerance, and rotation
synthesis are deliberately outside the model.

The primitive accounting level is ``x``, ``cx``, ``ccx``, ``cswap``, ``h``,
``cp``, ``swap``, and ``measure``.  ``canonical_cx_count`` then applies the
exact decompositions used by the frozen Qiskit basis audit:

* CCX -> 6 CX,
* CSWAP -> 8 CX,
* CP -> 2 CX, and
* SWAP -> 3 CX.

This is reproducible and gate-set explicit, but it is not a physical-qubit or
surface-code estimate.
"""

from __future__ import annotations

from collections import Counter
from math import gcd, isqrt, log2
from typing import Iterable, Mapping, Sequence


GateCounts = Counter[str]


def _scaled(counts: Mapping[str, int], multiplier: int) -> GateCounts:
    return Counter({name: int(multiplier) * int(value) for name, value in counts.items()})


def _ceil_sqrt(value: int) -> int:
    root = isqrt(int(value))
    return root if root * root == value else root + 1


def notebook_parameters(n: int, mode: str = "cover_2n") -> dict[str, int | str]:
    """Return the exact parameter rule embedded in the supplied notebook.

    ``n`` is the bit length of ``N``.  Both notebook modes use
    ``d=ceil(sqrt(n))``.  The default ``cover_2n`` mode takes
    ``q=ceil(2n/d)``; the alternative labelled ``notebook`` in the artifact
    takes ``q=floor(n/d+d)``.  Both have ``d*q=2n+O(sqrt(n))``.
    """

    n = int(n)
    if n <= 0:
        raise ValueError("n must be positive")
    d = _ceil_sqrt(n)
    if mode == "cover_2n":
        q = (2 * n + d - 1) // d
    elif mode == "notebook":
        q = n // d + d
    elif mode == "external_ceil_ceil":
        q = (n + d - 1) // d + d
    else:
        raise ValueError("unknown parameter mode")
    return {
        "n": n,
        "mode": mode,
        "d": d,
        "q": q,
        "M": 1 << q,
        "exponent_qubits": d * q,
        "total_qubits": d * q + 2 * n + 1,
    }


def shor_parameters(n: int) -> dict[str, int | str]:
    """Return the register sizes of the supplied coherent Shor circuit.

    This is the non-semiclassical implementation in
    ``external/regev-quantum-algorithm/implementations/shor.py``.  It has a
    ``2n``-qubit exponent register, an ``n``-qubit result register, and an
    ``n+1``-qubit arithmetic workspace.
    """

    n = int(n)
    if n <= 0:
        raise ValueError("n must be positive")
    return {
        "n": n,
        "algorithm": "supplied_coherent_shor",
        "exponent_qubits": 2 * n,
        "result_qubits": n,
        "workspace_qubits": n + 1,
        "total_qubits": 4 * n + 1,
        "controlled_modular_multiplier_invocations": 2 * n,
    }


def qft_source_counts(d: int, q: int, cutoff: int | None = None) -> GateCounts:
    """Count the product-QFT primitives used by the notebook circuit."""

    d, q = int(d), int(q)
    if d <= 0 or q <= 0:
        raise ValueError("d and q must be positive")
    retained = q - 1 if cutoff is None else min(int(cutoff), q - 1)
    if retained < 0:
        raise ValueError("cutoff must be nonnegative")
    cp_per_register = retained * q - retained * (retained + 1) // 2
    return Counter({
        "h": d * q,
        "cp": d * cp_per_register,
        "swap": d * (q // 2),
    })


def qft_closed_form(d: int, q: int, cutoff: int | None = None) -> dict[str, int]:
    """Return exact logical and canonical-CX QFT counts."""

    counts = qft_source_counts(d, q, cutoff)
    exact = qft_source_counts(d, q, q - 1)
    return {
        "hadamard": counts["h"],
        "controlled_phase": counts["cp"],
        "swap": counts["swap"],
        "canonical_cx": canonical_cx_count(counts),
        "omitted_controlled_phase": exact["cp"] - counts["cp"],
        "saved_canonical_cx": canonical_cx_count(exact) - canonical_cx_count(counts),
    }


def _controlled_adder_counts(n: int) -> GateCounts:
    """Counts for ``gates.haner.adder.controlled_adder``."""

    n = int(n)
    if n <= 0:
        raise ValueError("n must be positive")
    return Counter({"cx": max(0, 4 * n - 6), "ccx": 3 * n - 2})


def _controlled_incrementer_counts(n: int) -> GateCounts:
    counts = _scaled(_controlled_adder_counts(n), 2)
    counts["x"] += 2 * int(n)
    return counts


def _carry_body_counts(constant: int, n: int) -> GateCounts:
    if n < 2:
        raise ValueError("the carry body exists only for n >= 2")
    constant = int(constant) & ((1 << n) - 1)
    nonleast_weight = (constant >> 1).bit_count()
    return Counter({
        "ccx": 2 * (n - 2) + (constant & 1),
        "cx": nonleast_weight,
        "x": nonleast_weight,
    })


def _controlled_carry_counts(constant: int, n: int, controls: int) -> GateCounts:
    """Count controlled or double-controlled Häner carry."""

    n, controls = int(n), int(controls)
    constant = int(constant) & ((1 << n) - 1)
    if controls not in (1, 2):
        raise ValueError("controls must be one or two")
    if n == 1:
        if constant != 1:
            return Counter()
        # The double-controlled wrapper uses the supplied four-CCX CCCX.
        return Counter({"ccx": 1 if controls == 1 else 4})
    body = _scaled(_carry_body_counts(constant, n), 2)
    body["ccx"] += 2 if controls == 1 else 8
    return body


def _double_controlled_comparator_counts(constant: int, n: int) -> GateCounts:
    counts = _controlled_carry_counts(constant, n, controls=2)
    counts["x"] += 2 * int(n)
    return counts


def _controlled_constant_adder_counts(constant: int, n: int) -> GateCounts:
    """Recursively count ``controlled_constant_adder`` exactly."""

    n = int(n)
    if n <= 0:
        raise ValueError("n must be positive")
    constant = int(constant) & ((1 << n) - 1)
    if n == 1:
        return Counter({"cx": 1}) if constant == 1 else Counter()

    mid = n // 2 + n % 2
    high_width = n - mid
    low = constant & ((1 << mid) - 1)
    high = constant >> mid

    counts = _scaled(_controlled_incrementer_counts(high_width), 2)
    counts["cx"] += 2 * high_width
    counts.update(_scaled(_controlled_carry_counts(low, mid, controls=1), 2))
    counts.update(_controlled_constant_adder_counts(low, mid))
    counts.update(_controlled_constant_adder_counts(high, high_width))
    return counts


def _double_controlled_modular_adder_counts(constant: int, N: int, n: int) -> GateCounts:
    constant, N, n = int(constant), int(N), int(n)
    counts = _double_controlled_comparator_counts(N - constant, n)
    counts.update(_controlled_constant_adder_counts(constant, n))
    counts["ccx"] += 1
    counts.update(_controlled_constant_adder_counts(N - constant, n))
    counts.update(_double_controlled_comparator_counts(constant, n))
    return counts


def _controlled_constant_modular_multiplier_counts(
    constant: int, N: int, n: int
) -> GateCounts:
    counts: GateCounts = Counter()
    for bit in reversed(range(int(n))):
        partial = (pow(2, bit) * int(constant)) % int(N)
        counts.update(_double_controlled_modular_adder_counts(partial, N, n))
    return counts


def controlled_modular_multiplier_counts(constant: int, N: int, n: int) -> GateCounts:
    """Count one controlled multiplication, including uncomputation."""

    constant, N, n = int(constant) % int(N), int(N), int(n)
    if N <= 2 or n != N.bit_length() or gcd(constant, N) != 1:
        raise ValueError("constant must be a unit and n must equal N.bit_length()")
    counts = _controlled_constant_modular_multiplier_counts(constant, N, n)
    counts["cswap"] += n
    inverse = pow(constant, -1, N)
    counts.update(_controlled_constant_modular_multiplier_counts(inverse, N, n))
    return counts


def modular_exponentiation_counts(constant: int, N: int, n: int, q: int) -> GateCounts:
    """Count the repeated-square modular exponentiation in one dimension."""

    counts: GateCounts = Counter()
    for bit in range(int(q)):
        partial = pow(int(constant), 1 << bit, int(N))
        counts.update(controlled_modular_multiplier_counts(partial, N, n))
    return counts


def full_circuit_source_counts(
    N: int,
    bases: Sequence[int],
    q: int,
    *,
    qft_cutoff: int | None = None,
    measure: bool = True,
) -> GateCounts:
    """Flatten the complete implemented circuit to the declared primitives."""

    N, q = int(N), int(q)
    n = N.bit_length()
    bases = tuple(int(base) % N for base in bases)
    if not bases or any(gcd(base, N) != 1 for base in bases):
        raise ValueError("bases must be a nonempty sequence of units modulo N")
    counts: GateCounts = Counter({"h": len(bases) * q, "x": 1})
    for base in bases:
        counts.update(modular_exponentiation_counts(base, N, n, q))
    counts.update(qft_source_counts(len(bases), q, qft_cutoff))
    if measure:
        counts["measure"] += len(bases) * q
    return counts


def shor_full_circuit_source_counts(
    N: int,
    base: int,
    *,
    qft_cutoff: int | None = None,
    measure: bool = True,
) -> GateCounts:
    """Flatten the supplied coherent Shor circuit to declared primitives.

    The arithmetic functions called by the supplied Shor and Regev builders
    are structurally identical.  The only differences counted here are the
    number of exponent bits and the QFT layout.
    """

    N, base = int(N), int(base)
    n = N.bit_length()
    base %= N
    if N <= 2 or gcd(base, N) != 1:
        raise ValueError("base must be a unit modulo N")
    q = 2 * n
    counts: GateCounts = Counter({"h": q, "x": 1})
    counts.update(modular_exponentiation_counts(base, N, n, q))
    counts.update(qft_source_counts(1, q, qft_cutoff))
    if measure:
        counts["measure"] += q
    return counts


def complexity_fidelity_certificate(
    n: int,
    mode: str = "cover_2n",
    *,
    regev_runs: int | None = None,
) -> dict[str, int | float | str | bool]:
    """Certify whether this binary architecture preserves Regev's scaling.

    The certificate is static: it follows loop bounds and exact gate
    contracts and does not fit a slope to timing data.  It applies to this
    repository's repeated-squaring implementation, not to Regev's published
    arithmetic circuit.
    """

    n = int(n)
    regev = notebook_parameters(n, mode)
    shor = shor_parameters(n)
    d, q = int(regev["d"]), int(regev["q"])
    regev_invocations = d * q
    shor_invocations = 2 * n
    runs = d + 4 if regev_runs is None else int(regev_runs)
    if runs <= 0:
        raise ValueError("regev_runs must be positive")
    regev_qft = qft_closed_form(d, q)["canonical_cx"]
    shor_qft = qft_closed_form(1, 2 * n)["canonical_cx"]
    return {
        "n": n,
        "mode": mode,
        "d": d,
        "q": q,
        "regev_total_qubits": int(regev["total_qubits"]),
        "shor_total_qubits": int(shor["total_qubits"]),
        "regev_controlled_multiplier_invocations_per_run": regev_invocations,
        "shor_controlled_multiplier_invocations_per_run": shor_invocations,
        "per_run_invocation_ratio_regev_over_shor": (
            regev_invocations / shor_invocations
        ),
        "regev_runs_reference": runs,
        "run_adjusted_invocation_ratio_vs_one_shor_run": (
            runs * regev_invocations / shor_invocations
        ),
        "regev_qft_canonical_cx": regev_qft,
        "shor_qft_canonical_cx": shor_qft,
        "qft_ratio_regev_over_shor": regev_qft / shor_qft,
        "controlled_additions_per_controlled_multiplier": 2 * n,
        "regev_controlled_modular_additions_per_run": 2 * n * regev_invocations,
        "shor_controlled_modular_additions_per_run": 4 * n * n,
        "actual_arithmetic_source_ccx_class": "Theta(n^3 log2(n))",
        "actual_arithmetic_source_ccx_leading_constant": 80.0,
        "regev_target_gate_class": "soft-O(n^(3/2))",
        "preserves_regev_target_gate_class": False,
        "verdict": "FAILS_REGEV_COMPLEXITY_FIDELITY",
        "scope": (
            "static certificate for the supplied serial binary repeated-squaring "
            "architecture; not a lower bound for Regev-style factoring"
        ),
    }


def canonical_cx_count(counts: Mapping[str, int]) -> int:
    """Map source primitives to the frozen all-to-all CX basis exactly."""

    return int(
        counts.get("cx", 0)
        + 6 * counts.get("ccx", 0)
        + 8 * counts.get("cswap", 0)
        + 2 * counts.get("cp", 0)
        + 3 * counts.get("swap", 0)
    )


def first_coprime_prime_square_bases(N: int, d: int) -> tuple[int, ...]:
    """Reproduce the factor-blind small-prime-square base rule."""

    N, d = int(N), int(d)
    if N <= 2 or d <= 0:
        raise ValueError("invalid N or d")
    roots: list[int] = []
    candidate = 2
    while len(roots) < d:
        prime = candidate >= 2 and all(
            candidate % divisor for divisor in range(2, isqrt(candidate) + 1)
        )
        if prime and gcd(candidate, N) == 1:
            roots.append(candidate)
        candidate += 1
    return tuple(pow(root, 2, N) for root in roots)


def asymptotic_leading_constants() -> dict[str, float | str]:
    """Leading constants proved for the supplied shared-workspace circuit.

    The CX interval reflects the data-dependent CNOTs in the recursive
    constant adder.  It is an interval, not an uncertainty estimate.
    """

    return {
        "parameter_rule": "d=ceil(sqrt(n)), q=2*sqrt(n)+O(1)",
        "qubits_over_n": 4.0,
        "qft_cp_over_n_to_3_over_2": 2.0,
        "qft_canonical_cx_over_n_to_3_over_2": 4.0,
        "arithmetic_ccx_over_n_cubed_log2_n": 80.0,
        "full_canonical_cx_lower_over_n_cubed_log2_n": 552.0,
        "full_canonical_cx_upper_over_n_cubed_log2_n": 568.0,
        "scope": "source implementation; all-to-all exact basis expansion; no routing or fault tolerance",
    }


def normalized_scaling_record(
    N: int, mode: str = "cover_2n", cutoff: int | None = None
) -> dict[str, int | float | str]:
    """Return one reproducible synthetic-scaling row."""

    N = int(N)
    n = N.bit_length()
    parameters = notebook_parameters(n, mode)
    d, q = int(parameters["d"]), int(parameters["q"])
    bases = first_coprime_prime_square_bases(N, d)
    counts = full_circuit_source_counts(N, bases, q, qft_cutoff=cutoff)
    denominator = n**3 * log2(n) if n > 1 else 1.0
    qft = qft_closed_form(d, q, cutoff)
    return {
        **parameters,
        "N": N,
        "bases": " ".join(str(value) for value in bases),
        "source_ccx": counts["ccx"],
        "source_cx": counts["cx"],
        "source_cswap": counts["cswap"],
        "qft_cp": qft["controlled_phase"],
        "qft_canonical_cx": qft["canonical_cx"],
        "canonical_cx": canonical_cx_count(counts),
        "normalized_ccx_n3log2n": counts["ccx"] / denominator,
        "normalized_canonical_cx_n3log2n": canonical_cx_count(counts) / denominator,
        "normalized_qft_cx_n3over2": qft["canonical_cx"] / (n ** 1.5),
        "normalized_qubits_n": int(parameters["total_qubits"]) / n,
    }


def sum_counts(rows: Iterable[Mapping[str, int]]) -> GateCounts:
    """Small public helper used by validation tests."""

    total: GateCounts = Counter()
    for row in rows:
        total.update(row)
    return total

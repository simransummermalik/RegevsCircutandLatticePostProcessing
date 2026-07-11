"""Finite-parameter comparator structured like Ragavan--Vaikuntanathan 6.1.

Algorithm 6.1 of Ragavan and Vaikuntanathan constructs, for an index set
``E``, the column lattice

    H = [[S I_d, S W],
         [0,       I_E]],

where column ``i`` of ``W`` is the torus sample ``w_i``.  An LLL-short vector
has coefficients ``(beta, a)`` and sample ``i`` is selected when ``a_i != 0``.

For integer samples ``k_i`` on an ``M``-grid and exact ``S=p/q``, this module
reduces the integer *row* basis

    (q M H).T = [[p M I_d, 0],
                  [p K,       q M I_E]].

SymPy's unimodular LLL transform recovers ``beta`` and ``a`` exactly.  Every
reduced-vector coordinate is checked against those coefficients before its
support is used.

This is named an **RV-structured finite comparator**, not guaranteed RV
filtering.  In particular, the frozen stress cell ``d=3, m=11, target=7``
fails RV's asymptotic alpha/gamma combinatorial inequality, and this module
does not certify the well-spread corruption model, the asymptotic scale
condition, or the special recovery inequality.  It never receives factors,
roots, a relation-lattice oracle, or corruption labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import e
from operator import index
from time import perf_counter
from typing import Sequence


RV_COMPARATOR_ID = "RV_structured_finite_comparator"
RV_COMPARATOR_LABEL = "RV-structured finite comparator"


@dataclass(frozen=True, slots=True)
class RVFilterEmbedding:
    """Exact integer clearing of one Algorithm-6.1-style lattice."""

    samples: tuple[tuple[int, ...], ...]
    sample_indices: tuple[int, ...]
    modulus: int
    scale: Fraction
    dimension: int
    clearing_factor: int
    integer_row_basis: tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class RVFilterReduction:
    """LLL output with exact coefficient recovery for its first vector."""

    reduced_rows: tuple[tuple[int, ...], ...]
    transform_rows: tuple[tuple[int, ...], ...]
    beta: tuple[int, ...]
    sample_coefficients: tuple[int, ...]
    first_reduced_vector: tuple[int, ...]
    first_squared_norm: int
    delta: Fraction
    backend: str


@dataclass(frozen=True, slots=True)
class RVTheoremStatus:
    """Explicit separation between structural fidelity and theorem coverage."""

    comparator_label: str
    alpha: Fraction
    gamma: Fraction
    gamma_below_alpha_minus_one: bool
    alpha_gamma_expression: float
    alpha_gamma_combinatorial_inequality: bool
    finite_dimension: int
    scale_A_hypothesis_checked: bool
    well_spread_error_model_checked: bool
    special_recovery_inequality_checked: bool
    asymptotic_guarantee_applicable: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RVFilterIteration:
    iteration: int
    selected_before: tuple[int, ...]
    E_indices: tuple[int, ...]
    beta: tuple[int, ...]
    sample_coefficients: tuple[int, ...]
    nonzero_support_indices: tuple[int, ...]
    newly_selected_indices: tuple[int, ...]
    selected_after: tuple[int, ...]
    first_reduced_vector: tuple[int, ...]
    first_squared_norm: int
    embedding: RVFilterEmbedding
    reduction_backend: str
    runtime_seconds: float


@dataclass(frozen=True, slots=True)
class RVFilterResources:
    iterations: int
    reductions: int
    runtime_seconds: float
    peak_memory_estimate_bytes: int
    memory_estimate_method: str
    maximum_lattice_dimension: int
    maximum_integer_entry_bits: int


@dataclass(frozen=True, slots=True)
class RVFilterResult:
    method: str
    comparator_label: str
    success: bool
    pool_size: int
    dimension: int
    target_count: int
    E_size: int
    selected_indices: tuple[int, ...]
    all_supported_indices_before_truncation: tuple[int, ...]
    transcript: tuple[RVFilterIteration, ...]
    theorem_status: RVTheoremStatus
    resources: RVFilterResources
    termination_reason: str


@dataclass(frozen=True, slots=True)
class RVFilteredRecoveryResult:
    """Filtering transcript plus the unchanged common recovery result."""

    filter_result: RVFilterResult
    recovery_result: object | None
    termination_reason: str


def _as_integer(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, not bool")
    try:
        return int(index(value))
    except TypeError as exc:
        raise TypeError(f"{name} must be an integer") from exc


def _as_fraction(value: int | Fraction, name: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise TypeError(f"{name} must be an int or fractions.Fraction")
    result = Fraction(value)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _normalize_pool(
    samples: Sequence[Sequence[int]], modulus: int
) -> tuple[tuple[int, ...], ...]:
    rows = tuple(
        tuple(_as_integer(value, f"samples[{i}][{j}]") for j, value in enumerate(row))
        for i, row in enumerate(samples)
    )
    if not rows or not rows[0]:
        raise ValueError("samples must be a nonempty m-by-d pool")
    dimension = len(rows[0])
    if any(len(row) != dimension for row in rows):
        raise ValueError("all sample rows must have the same dimension")
    if any(value < 0 or value >= modulus for row in rows for value in row):
        raise ValueError("sample coordinates must lie in {0, ..., modulus - 1}")
    return rows


def build_rv_filter_lattice(
    samples: Sequence[Sequence[int]],
    sample_indices: Sequence[int],
    modulus: int,
    scale: int | Fraction,
) -> RVFilterEmbedding:
    """Build ``(q M H).T`` exactly for a deterministic subset ``E``."""

    modulus = _as_integer(modulus, "modulus")
    if modulus <= 1:
        raise ValueError("modulus must exceed one")
    scale = _as_fraction(scale, "scale")
    pool = _normalize_pool(samples, modulus)
    indices = tuple(
        _as_integer(value, f"sample_indices[{i}]")
        for i, value in enumerate(sample_indices)
    )
    if not indices or len(set(indices)) != len(indices):
        raise ValueError("sample_indices must be nonempty and unique")
    if any(value < 0 or value >= len(pool) for value in indices):
        raise IndexError("sample index is outside the fixed pool")

    selected = tuple(pool[i] for i in indices)
    dimension = len(pool[0])
    E_size = len(indices)
    p, q = scale.numerator, scale.denominator
    clearing_factor = q * modulus
    lattice_dimension = dimension + E_size
    basis: list[tuple[int, ...]] = []

    # Rows 0..d-1 are the transposed beta columns of q*M*H.
    for coordinate in range(dimension):
        row = [0] * lattice_dimension
        row[coordinate] = p * modulus
        basis.append(tuple(row))
    # Remaining rows are the transposed sample-coefficient columns.
    for local_index, sample in enumerate(selected):
        row = [p * value for value in sample] + [0] * E_size
        row[dimension + local_index] = q * modulus
        basis.append(tuple(row))

    return RVFilterEmbedding(
        samples=selected,
        sample_indices=indices,
        modulus=modulus,
        scale=scale,
        dimension=dimension,
        clearing_factor=clearing_factor,
        integer_row_basis=tuple(basis),
    )


def reduce_rv_filter_lattice(
    embedding: RVFilterEmbedding,
    delta: Fraction = Fraction(3, 4),
) -> RVFilterReduction:
    """Run exact row-LLL and recover ``beta`` and ``a_i`` from its transform."""

    delta = _as_fraction(delta, "delta")
    if not Fraction(1, 4) < delta < 1:
        raise ValueError("LLL delta must lie strictly between 1/4 and 1")
    try:
        from sympy import Matrix, Rational
    except ImportError as exc:  # pragma: no cover - project requirements pin SymPy.
        raise RuntimeError("SymPy is required for exact RV comparator LLL") from exc

    basis = Matrix(embedding.integer_row_basis)
    reduced, transform = basis.lll_transform(
        delta=Rational(delta.numerator, delta.denominator)
    )
    if transform * basis != reduced:
        raise ArithmeticError("LLL transform does not reconstruct its reduced basis")
    reduced_rows = tuple(
        tuple(int(value) for value in row) for row in reduced.tolist()
    )
    transform_rows = tuple(
        tuple(int(value) for value in row) for row in transform.tolist()
    )
    first = reduced_rows[0]
    coefficients = transform_rows[0]
    d = embedding.dimension
    beta = coefficients[:d]
    sample_coefficients = coefficients[d:]
    p, q = embedding.scale.numerator, embedding.scale.denominator
    M = embedding.modulus
    expected_top = tuple(
        p * M * beta[coordinate]
        + p
        * sum(
            sample_coefficients[i] * embedding.samples[i][coordinate]
            for i in range(len(embedding.samples))
        )
        for coordinate in range(d)
    )
    expected_bottom = tuple(q * M * value for value in sample_coefficients)
    if first != expected_top + expected_bottom:
        raise ArithmeticError("recovered beta/a coefficients disagree with the LLL vector")
    return RVFilterReduction(
        reduced_rows=reduced_rows,
        transform_rows=transform_rows,
        beta=beta,
        sample_coefficients=sample_coefficients,
        first_reduced_vector=first,
        first_squared_norm=sum(value * value for value in first),
        delta=delta,
        backend="sympy.Matrix.lll_transform:first_reduced_row",
    )


def rv_theorem_status(pool_size: int, dimension: int, target_count: int) -> RVTheoremStatus:
    """Evaluate the alpha/gamma conditions that can be checked from finite sizes."""

    pool_size = _as_integer(pool_size, "pool_size")
    dimension = _as_integer(dimension, "dimension")
    target_count = _as_integer(target_count, "target_count")
    if pool_size <= 0 or dimension <= 0 or not 0 < target_count < pool_size:
        raise ValueError("pool, dimension, and target count are inconsistent")
    alpha = Fraction(pool_size, dimension)
    gamma = Fraction(target_count, dimension)
    gap = alpha - gamma
    gamma_condition = gamma < alpha - 1
    expression = (e * float(alpha) / float(gap)) ** float(gap) * 2 ** (
        -float(gamma) + 1
    )
    combinatorial = expression < 1.0
    reasons: list[str] = []
    if not gamma_condition:
        reasons.append("gamma < alpha - 1 is false")
    if not combinatorial:
        reasons.append("RV alpha/gamma combinatorial inequality is false")
    reasons.extend(
        (
            "finite d is not an asymptotic certificate",
            "scale exponent A hypothesis was not certified",
            "well-spread corruption model was not certified",
            "special recovery inequality was not certified",
        )
    )
    return RVTheoremStatus(
        comparator_label=RV_COMPARATOR_LABEL,
        alpha=alpha,
        gamma=gamma,
        gamma_below_alpha_minus_one=gamma_condition,
        alpha_gamma_expression=expression,
        alpha_gamma_combinatorial_inequality=combinatorial,
        finite_dimension=dimension,
        scale_A_hypothesis_checked=False,
        well_spread_error_model_checked=False,
        special_recovery_inequality_checked=False,
        asymptotic_guarantee_applicable=False,
        reasons=tuple(reasons),
    )


def _integer_storage_bytes(rows: Sequence[Sequence[int]]) -> int:
    return 64 + sum(
        64
        + 8 * len(row)
        + sum(28 + max(1, (abs(value).bit_length() + 7) // 8) for value in row)
        for row in rows
    )


def rv_structured_finite_filter(
    samples: Sequence[Sequence[int]],
    modulus: int,
    scale: int | Fraction,
    target_count: int,
    *,
    lll_delta: Fraction = Fraction(3, 4),
    max_iterations: int | None = None,
) -> RVFilterResult:
    """Select fixed-pool rows using deterministic Algorithm-6.1 structure.

    ``E`` is always the lexicographically first ``pool_size-target_count``
    indices not already supported.  No randomness or hidden sample label is
    consulted.  When LLL's first vector has zero ``a`` support, the finite
    comparator returns a failure instead of claiming theorem-backed progress.
    """

    start = perf_counter()
    modulus = _as_integer(modulus, "modulus")
    if modulus <= 1:
        raise ValueError("modulus must exceed one")
    scale = _as_fraction(scale, "scale")
    pool = _normalize_pool(samples, modulus)
    m = len(pool)
    d = len(pool[0])
    target_count = _as_integer(target_count, "target_count")
    if not d + 4 <= target_count < m:
        raise ValueError("target_count must satisfy d+4 <= target_count < pool size")
    E_size = m - target_count
    if max_iterations is None:
        iteration_limit = target_count
    else:
        iteration_limit = _as_integer(max_iterations, "max_iterations")
        if iteration_limit <= 0:
            raise ValueError("max_iterations must be positive")
    theorem = rv_theorem_status(m, d, target_count)

    supported: set[int] = set()
    transcript: list[RVFilterIteration] = []
    peak_memory = 0
    maximum_dimension = 0
    maximum_bits = 0
    termination_reason = "iteration_limit_reached"
    success = False

    while len(supported) < target_count and len(transcript) < iteration_limit:
        iteration_start = perf_counter()
        selected_before = tuple(sorted(supported))
        eligible = tuple(index for index in range(m) if index not in supported)
        if len(eligible) < E_size:
            termination_reason = "insufficient_unselected_indices_for_E"
            break
        E_indices = eligible[:E_size]
        embedding = build_rv_filter_lattice(pool, E_indices, modulus, scale)
        reduction = reduce_rv_filter_lattice(embedding, delta=lll_delta)
        support = tuple(
            E_indices[i]
            for i, coefficient in enumerate(reduction.sample_coefficients)
            if coefficient != 0
        )
        newly_selected = tuple(index for index in support if index not in supported)
        supported.update(newly_selected)
        selected_after = tuple(sorted(supported))
        matrix_memory = (
            _integer_storage_bytes(embedding.integer_row_basis)
            + _integer_storage_bytes(reduction.reduced_rows)
            + _integer_storage_bytes(reduction.transform_rows)
        )
        peak_memory = max(peak_memory, matrix_memory)
        maximum_dimension = max(maximum_dimension, len(embedding.integer_row_basis))
        maximum_bits = max(
            maximum_bits,
            max(
                abs(value).bit_length()
                for matrix in (
                    embedding.integer_row_basis,
                    reduction.reduced_rows,
                    reduction.transform_rows,
                )
                for row in matrix
                for value in row
            ),
        )
        transcript.append(
            RVFilterIteration(
                iteration=len(transcript),
                selected_before=selected_before,
                E_indices=E_indices,
                beta=reduction.beta,
                sample_coefficients=reduction.sample_coefficients,
                nonzero_support_indices=support,
                newly_selected_indices=newly_selected,
                selected_after=selected_after,
                first_reduced_vector=reduction.first_reduced_vector,
                first_squared_norm=reduction.first_squared_norm,
                embedding=embedding,
                reduction_backend=reduction.backend,
                runtime_seconds=perf_counter() - iteration_start,
            )
        )
        if not newly_selected:
            termination_reason = "no_progress_shortest_vector_has_zero_sample_support"
            break

    if len(supported) >= target_count:
        success = True
        termination_reason = "target_count_reached"
    selected_indices = tuple(sorted(supported)[:target_count]) if success else ()
    resources = RVFilterResources(
        iterations=len(transcript),
        reductions=len(transcript),
        runtime_seconds=perf_counter() - start,
        peak_memory_estimate_bytes=peak_memory,
        memory_estimate_method=(
            "deterministic structural estimate for exact basis, reduced basis, "
            "unimodular transform, and Python integer magnitudes; not process RSS"
        ),
        maximum_lattice_dimension=maximum_dimension,
        maximum_integer_entry_bits=maximum_bits,
    )
    return RVFilterResult(
        method=RV_COMPARATOR_ID,
        comparator_label=RV_COMPARATOR_LABEL,
        success=success,
        pool_size=m,
        dimension=d,
        target_count=target_count,
        E_size=E_size,
        selected_indices=selected_indices,
        all_supported_indices_before_truncation=tuple(sorted(supported)),
        transcript=tuple(transcript),
        theorem_status=theorem,
        resources=resources,
        termination_reason=termination_reason,
    )


def rv_filter_then_short_combination_recovery(
    family,
    samples: Sequence[Sequence[int]],
    modulus: int,
    scale: int | Fraction,
    target_count: int,
    *,
    budget,
    lll_delta: Fraction = Fraction(3, 4),
    max_iterations: int | None = None,
) -> RVFilteredRecoveryResult:
    """Filter blindly, then pass selected raw rows to the common recovery.

    The filtering call is completed before this wrapper inspects ``family``;
    the filter itself has no family/root/factor argument.  ``budget`` is
    mandatory so comparisons cannot silently use a larger recovery search.
    """

    filtered = rv_structured_finite_filter(
        samples,
        modulus,
        scale,
        target_count,
        lll_delta=lll_delta,
        max_iterations=max_iterations,
    )
    if not filtered.success:
        return RVFilteredRecoveryResult(
            filter_result=filtered,
            recovery_result=None,
            termination_reason=f"filter_failed:{filtered.termination_reason}",
        )
    from .core import RootedBaseFamily
    from .quotient_recovery import RecoveryBudget, short_combination_recovery

    if not isinstance(family, RootedBaseFamily):
        raise TypeError("common recovery requires a RootedBaseFamily")
    if not isinstance(budget, RecoveryBudget):
        raise TypeError("budget must be a RecoveryBudget")
    selected_samples = tuple(samples[index] for index in filtered.selected_indices)
    recovery = short_combination_recovery(
        family,
        selected_samples,
        modulus,
        scale=scale,
        lll_delta=lll_delta,
        budget=budget,
    )
    return RVFilteredRecoveryResult(
        filter_result=filtered,
        recovery_result=recovery,
        termination_reason="filter_succeeded_common_recovery_completed",
    )


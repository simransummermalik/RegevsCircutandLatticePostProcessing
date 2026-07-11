"""Exact, factor-blind *post-hoc* diagnostics for ``L`` versus ``L0``.

For a :class:`~regev_research.core.RootedBaseFamily`, this module studies

``L  = {z in Z^d : prod_i a_i**z_i == 1 (mod N)}``

and

``L0 = {z in L : prod_i b_i**z_i in {+1, -1} (mod N)}``,

where every circuit base ``a_i`` permanently retains its selected root
``b_i``.  The exact ``L0`` basis is constructed as the kernel of the map to
the signed Cayley image ``<b_1, ..., b_d> / {+1, -1}``.  This requires no
factorization of ``N`` and no supplied group orders.  Its determinant is
checked against an independent enumeration of that signed image.

The bounded lambda and sample-augmented gap routines deliberately enumerate
candidate relations and classify them with exact modular arithmetic.  They
are oracle-side, post-hoc mechanism diagnostics.  They must never be used as
the selector's tuning objective, as a replacement for sample-to-lattice
recovery, or as evidence of scalable recovery.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from fractions import Fraction
from math import log2
from operator import index
from typing import Sequence

from .core import RootedBaseFamily, canonical_vectors, modular_product


POSTHOC_SCOPE = (
    "oracle-side post-hoc diagnostic only; never selector tuning or recovery"
)


@dataclass(frozen=True, slots=True)
class ExactL0HNF:
    """A factor-blind exact row-HNF basis of ``L0``."""

    N: int
    roots: tuple[int, ...]
    dimension: int
    row_hnf_basis: tuple[tuple[int, ...], ...]
    determinant: int
    signed_image_classes: tuple[int, ...]
    signed_image_size: int
    verified_index: int
    cayley_edge_count: int
    cycle_relation_count: int
    construction: str
    factors_or_orders_supplied: bool
    scope: str


@dataclass(frozen=True, slots=True)
class BoundedBaseLambdaMetrics:
    """Bounded Euclidean minima in ``L``, ``L0``, and ``L \\ L0``."""

    relation_bound: int
    candidate_count: int
    relation_count: int
    L0_count: int
    useful_count: int
    shortest_relation_squared_norm: int | None
    shortest_relation_witness: tuple[int, ...] | None
    shortest_nonzero_L0_squared_norm: int | None
    shortest_nonzero_L0_witness: tuple[int, ...] | None
    shortest_useful_squared_norm: int | None
    shortest_useful_witness: tuple[int, ...] | None
    signed_squared_gap: int | None
    L0_to_useful_squared_ratio: Fraction | None
    shortest_relation_censored: bool
    shortest_L0_censored: bool
    shortest_useful_censored: bool
    outside_box_squared_norm_lower_bound: int
    norm_definition: str
    scope: str


@dataclass(frozen=True, slots=True)
class BoundedSampleAugmentedQuotientGap:
    """Bounded factor-useful versus ``L0`` gap in Regev's embedding norm."""

    relation_bound: int
    sample_modulus: int
    scale: Fraction
    sample_count: int
    dimension: int
    candidate_count: int
    relation_count: int
    L0_count: int
    useful_count: int
    shortest_relation_augmented_squared_norm: Fraction | None
    shortest_relation_witness: tuple[int, ...] | None
    shortest_nonzero_L0_augmented_squared_norm: Fraction | None
    shortest_nonzero_L0_witness: tuple[int, ...] | None
    shortest_useful_augmented_squared_norm: Fraction | None
    shortest_useful_witness: tuple[int, ...] | None
    signed_augmented_squared_gap: Fraction | None
    L0_to_useful_augmented_squared_ratio: Fraction | None
    log2_L0_to_useful_ratio: float | None
    shortest_relation_censored: bool
    shortest_L0_censored: bool
    shortest_useful_censored: bool
    outside_box_squared_norm_lower_bound: int
    norm_definition: str
    scope: str


def _as_integer(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, not bool")
    try:
        return int(index(value))
    except TypeError as exc:
        raise TypeError(f"{name} must be an integer") from exc


def _as_positive_fraction(value: int | Fraction, name: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise TypeError(f"{name} must be an int or fractions.Fraction")
    result = Fraction(value)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _validate_family(family: RootedBaseFamily) -> RootedBaseFamily:
    if not isinstance(family, RootedBaseFamily):
        raise TypeError("an exact RootedBaseFamily is required")
    return family


def _signed_class(value: int, N: int) -> int:
    """Canonical representative of ``{value, -value} modulo N``."""

    residue = value % N
    return min(residue, (-residue) % N)


def _row_hnf(relations: Sequence[Sequence[int]], dimension: int) -> tuple[tuple[int, ...], ...]:
    try:
        from sympy import Matrix
        from sympy.matrices.normalforms import hermite_normal_form
    except ImportError as exc:  # pragma: no cover - SymPy is pinned by the project.
        raise RuntimeError("SymPy is required for exact Hermite normal form") from exc

    if not relations:
        raise ArithmeticError("Cayley enumeration produced no kernel relations")
    hnf = hermite_normal_form(Matrix(relations).T).T
    if hnf.rows != dimension or hnf.cols != dimension:
        raise ArithmeticError("the enumerated L0 kernel is not full rank")
    return tuple(tuple(int(value) for value in row) for row in hnf.tolist())


def exact_l0_hnf(
    family: RootedBaseFamily,
    *,
    max_signed_image_size: int = 1_000_000,
) -> ExactL0HNF:
    """Construct the exact full-rank lattice ``L0`` without factors or orders.

    A breadth-first traversal enumerates the image of ``Z^d`` in
    ``(Z/NZ)^* / {+1,-1}``.  Each non-tree Cayley edge supplies an integer
    kernel relation.  Fundamental edge relations span the full kernel: a walk
    for any kernel vector telescopes into these relations.  The determinant of
    the resulting row HNF must equal the enumerated image cardinality by the
    first isomorphism theorem; disagreement is treated as an implementation
    error.
    """

    family = _validate_family(family)
    max_signed_image_size = _as_integer(
        max_signed_image_size, "max_signed_image_size"
    )
    if max_signed_image_size < 1:
        raise ValueError("max_signed_image_size must be positive")

    N = family.N
    d = len(family.pairs)
    identity = _signed_class(1, N)
    zero = (0,) * d
    representatives: dict[int, tuple[int, ...]] = {identity: zero}
    queue: deque[int] = deque([identity])
    steps: list[tuple[int, int, int]] = []
    for coordinate, root in enumerate(family.roots):
        steps.append((coordinate, 1, root))
        steps.append((coordinate, -1, pow(root, -1, N)))

    relations: list[tuple[int, ...]] = []
    edge_count = 0
    while queue:
        state = queue.popleft()
        representative = representatives[state]
        for coordinate, sign, multiplier in steps:
            edge_count += 1
            target = _signed_class(state * multiplier, N)
            candidate = list(representative)
            candidate[coordinate] += sign
            candidate_tuple = tuple(candidate)
            if target not in representatives:
                if len(representatives) >= max_signed_image_size:
                    raise ValueError(
                        "signed Cayley image exceeds max_signed_image_size"
                    )
                representatives[target] = candidate_tuple
                queue.append(target)
            else:
                relation = tuple(
                    left - right
                    for left, right in zip(
                        candidate_tuple, representatives[target], strict=True
                    )
                )
                if any(relation):
                    relations.append(relation)

    basis = _row_hnf(relations, d)
    try:
        from sympy import Matrix
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("SymPy is required for determinant verification") from exc
    determinant = abs(int(Matrix(basis).det()))
    signed_classes = tuple(sorted(representatives))
    image_size = len(signed_classes)
    if determinant != image_size:
        raise ArithmeticError(
            "L0 HNF determinant disagrees with the signed Cayley image size"
        )
    for row in basis:
        root_product = modular_product(N, family.roots, row)
        if root_product not in (1, N - 1):
            raise ArithmeticError("an HNF row escaped L0")
        if modular_product(N, family.bases, row) != 1:
            raise ArithmeticError("an HNF row escaped L")

    return ExactL0HNF(
        N=N,
        roots=family.roots,
        dimension=d,
        row_hnf_basis=basis,
        determinant=determinant,
        signed_image_classes=signed_classes,
        signed_image_size=image_size,
        verified_index=image_size,
        cayley_edge_count=edge_count,
        cycle_relation_count=len(relations),
        construction=(
            "row HNF of signed-Cayley fundamental edge relations; determinant "
            "verified against |<b_i>/{+1,-1}|"
        ),
        factors_or_orders_supplied=False,
        scope=POSTHOC_SCOPE,
    )


def _validate_bound(bound: int, dimension: int, max_candidates: int) -> tuple[int, int]:
    bound = _as_integer(bound, "relation_bound")
    max_candidates = _as_integer(max_candidates, "max_candidates")
    if bound < 1:
        raise ValueError("relation_bound must be positive")
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    candidate_count = ((2 * bound + 1) ** dimension - 1) // 2
    if candidate_count > max_candidates:
        raise ValueError(
            f"bounded enumeration has {candidate_count} candidates; "
            f"limit is {max_candidates}"
        )
    return bound, candidate_count


def _classify_relation(
    family: RootedBaseFamily, vector: tuple[int, ...]
) -> str | None:
    if modular_product(family.N, family.bases, vector) != 1:
        return None
    beta = modular_product(family.N, family.roots, vector)
    if beta * beta % family.N != 1:
        raise ArithmeticError("a squared-base relation violated beta^2 = 1")
    return "L0" if beta in (1, family.N - 1) else "useful"


def _minimum_is_censored(
    value: int | Fraction | None, outside_box_lower_bound: int
) -> bool:
    # Any integer vector outside [-B,B]^d has squared Euclidean norm at
    # least (B+1)^2.  The augmented norm only adds a nonnegative term.
    return value is None or value > outside_box_lower_bound


def bounded_base_lambda_metrics(
    family: RootedBaseFamily,
    relation_bound: int,
    *,
    max_candidates: int = 2_000_000,
) -> BoundedBaseLambdaMetrics:
    """Enumerate bounded relations and report base-only Euclidean minima.

    ``shortest_useful`` estimates the relative minimum often denoted
    ``lambda_{L0}(L)``.  Although no factorization or order is supplied, the
    exact root products make this an oracle-side evaluation statistic rather
    than a recovery algorithm.
    """

    family = _validate_family(family)
    d = len(family.pairs)
    bound, candidate_count = _validate_bound(
        relation_bound, d, max_candidates
    )

    shortest_relation: tuple[int, tuple[int, ...]] | None = None
    shortest_l0: tuple[int, tuple[int, ...]] | None = None
    shortest_useful: tuple[int, tuple[int, ...]] | None = None
    relation_count = l0_count = useful_count = 0

    for vector in canonical_vectors(d, bound):
        category = _classify_relation(family, vector)
        if category is None:
            continue
        relation_count += 1
        squared_norm = sum(value * value for value in vector)
        row = (squared_norm, vector)
        if shortest_relation is None or row < shortest_relation:
            shortest_relation = row
        if category == "L0":
            l0_count += 1
            if shortest_l0 is None or row < shortest_l0:
                shortest_l0 = row
        else:
            useful_count += 1
            if shortest_useful is None or row < shortest_useful:
                shortest_useful = row

    if shortest_l0 is not None and shortest_useful is not None:
        signed_gap = shortest_l0[0] - shortest_useful[0]
        ratio = Fraction(shortest_l0[0], shortest_useful[0])
    else:
        signed_gap = None
        ratio = None
    outside_lower_bound = (bound + 1) ** 2

    return BoundedBaseLambdaMetrics(
        relation_bound=bound,
        candidate_count=candidate_count,
        relation_count=relation_count,
        L0_count=l0_count,
        useful_count=useful_count,
        shortest_relation_squared_norm=(
            shortest_relation[0] if shortest_relation else None
        ),
        shortest_relation_witness=(
            shortest_relation[1] if shortest_relation else None
        ),
        shortest_nonzero_L0_squared_norm=shortest_l0[0] if shortest_l0 else None,
        shortest_nonzero_L0_witness=shortest_l0[1] if shortest_l0 else None,
        shortest_useful_squared_norm=(
            shortest_useful[0] if shortest_useful else None
        ),
        shortest_useful_witness=shortest_useful[1] if shortest_useful else None,
        signed_squared_gap=signed_gap,
        L0_to_useful_squared_ratio=ratio,
        shortest_relation_censored=_minimum_is_censored(
            shortest_relation[0] if shortest_relation else None,
            outside_lower_bound,
        ),
        shortest_L0_censored=_minimum_is_censored(
            shortest_l0[0] if shortest_l0 else None, outside_lower_bound
        ),
        shortest_useful_censored=_minimum_is_censored(
            shortest_useful[0] if shortest_useful else None,
            outside_lower_bound,
        ),
        outside_box_squared_norm_lower_bound=outside_lower_bound,
        norm_definition="squared Euclidean norm of integer relation z",
        scope=POSTHOC_SCOPE,
    )


def _normalize_samples(
    samples: Sequence[Sequence[int]], modulus: int, dimension: int
) -> tuple[tuple[int, ...], ...]:
    rows = tuple(
        tuple(
            _as_integer(value, f"samples[{i}][{j}]")
            for j, value in enumerate(row)
        )
        for i, row in enumerate(samples)
    )
    if not rows:
        raise ValueError("samples must be nonempty")
    if any(len(row) != dimension for row in rows):
        raise ValueError(f"every sample must have dimension {dimension}")
    if any(value < 0 or value >= modulus for row in rows for value in row):
        raise ValueError("sample coordinates must lie in {0, ..., D - 1}")
    return rows


def _torus_distance(numerator: int, denominator: int) -> Fraction:
    residue = numerator % denominator
    return Fraction(min(residue, denominator - residue), denominator)


def _augmented_squared_norm(
    vector: tuple[int, ...],
    samples: tuple[tuple[int, ...], ...],
    modulus: int,
    scale: Fraction,
) -> Fraction:
    euclidean = sum(value * value for value in vector)
    residual_energy = Fraction(0)
    for sample in samples:
        numerator = sum(
            sample_value * vector_value
            for sample_value, vector_value in zip(sample, vector, strict=True)
        )
        distance = _torus_distance(numerator, modulus)
        residual_energy += distance * distance
    return Fraction(euclidean) + scale * scale * residual_energy


def bounded_sample_augmented_quotient_gap(
    family: RootedBaseFamily,
    samples: Sequence[Sequence[int]],
    sample_modulus: int,
    scale: int | Fraction,
    relation_bound: int,
    *,
    max_candidates: int = 2_000_000,
) -> BoundedSampleAugmentedQuotientGap:
    """Compute the bounded gap under the exact sample-augmented norm.

    For measured rows ``k_j`` representing ``w_j = k_j / D``, this evaluates

    ``c_W(z)^2 = ||z||_2^2 + S^2 sum_j dist(<w_j,z>, Z)^2``.

    All arithmetic up to the optional displayed base-2 logarithm is exact
    :class:`fractions.Fraction` arithmetic.  Candidate relations are obtained
    by exhaustive enumeration and exact root-product classification, so this
    function is strictly a post-hoc oracle diagnostic.
    """

    family = _validate_family(family)
    D = _as_integer(sample_modulus, "sample_modulus")
    if D <= 1:
        raise ValueError("sample_modulus must exceed one")
    S = _as_positive_fraction(scale, "scale")
    d = len(family.pairs)
    rows = _normalize_samples(samples, D, d)
    bound, candidate_count = _validate_bound(
        relation_bound, d, max_candidates
    )

    shortest_relation: tuple[Fraction, tuple[int, ...]] | None = None
    shortest_l0: tuple[Fraction, tuple[int, ...]] | None = None
    shortest_useful: tuple[Fraction, tuple[int, ...]] | None = None
    relation_count = l0_count = useful_count = 0

    for vector in canonical_vectors(d, bound):
        category = _classify_relation(family, vector)
        if category is None:
            continue
        relation_count += 1
        squared_norm = _augmented_squared_norm(vector, rows, D, S)
        row = (squared_norm, vector)
        if shortest_relation is None or row < shortest_relation:
            shortest_relation = row
        if category == "L0":
            l0_count += 1
            if shortest_l0 is None or row < shortest_l0:
                shortest_l0 = row
        else:
            useful_count += 1
            if shortest_useful is None or row < shortest_useful:
                shortest_useful = row

    if shortest_l0 is not None and shortest_useful is not None:
        signed_gap = shortest_l0[0] - shortest_useful[0]
        ratio = shortest_l0[0] / shortest_useful[0]
        log_ratio = log2(float(ratio))
    else:
        signed_gap = None
        ratio = None
        log_ratio = None
    outside_lower_bound = (bound + 1) ** 2

    return BoundedSampleAugmentedQuotientGap(
        relation_bound=bound,
        sample_modulus=D,
        scale=S,
        sample_count=len(rows),
        dimension=d,
        candidate_count=candidate_count,
        relation_count=relation_count,
        L0_count=l0_count,
        useful_count=useful_count,
        shortest_relation_augmented_squared_norm=(
            shortest_relation[0] if shortest_relation else None
        ),
        shortest_relation_witness=(
            shortest_relation[1] if shortest_relation else None
        ),
        shortest_nonzero_L0_augmented_squared_norm=(
            shortest_l0[0] if shortest_l0 else None
        ),
        shortest_nonzero_L0_witness=shortest_l0[1] if shortest_l0 else None,
        shortest_useful_augmented_squared_norm=(
            shortest_useful[0] if shortest_useful else None
        ),
        shortest_useful_witness=shortest_useful[1] if shortest_useful else None,
        signed_augmented_squared_gap=signed_gap,
        L0_to_useful_augmented_squared_ratio=ratio,
        log2_L0_to_useful_ratio=log_ratio,
        shortest_relation_censored=_minimum_is_censored(
            shortest_relation[0] if shortest_relation else None,
            outside_lower_bound,
        ),
        shortest_L0_censored=_minimum_is_censored(
            shortest_l0[0] if shortest_l0 else None, outside_lower_bound
        ),
        shortest_useful_censored=_minimum_is_censored(
            shortest_useful[0] if shortest_useful else None,
            outside_lower_bound,
        ),
        outside_box_squared_norm_lower_bound=outside_lower_bound,
        norm_definition=(
            "c_W(z)^2 = ||z||_2^2 + S^2 sum_j "
            "dist(<k_j/D,z>, Z)^2"
        ),
        scope=POSTHOC_SCOPE,
    )

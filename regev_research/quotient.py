"""Exact deflation of verified ``L0`` directions.

For an ordered :class:`~regev_research.core.RootedBaseFamily`, let

``L  = {z in Z^d : prod_i a_i**z_i = 1 mod N}``

and let ``L0`` contain those vectors for which the product of the stored roots
is ``+1`` or ``-1``.  This module accepts an integer row lattice ``U`` whose
generators are verified to lie in ``L0`` and represents ``Z^d / U`` exactly.

The transposed SymPy Hermite normal form gives a canonical row basis for
``U``.  Back-substitution at its pivot columns provides deterministic coset
reduction and an integer witness ``z = representative + c H``.  Smith normal
form is used separately for proof-relevant abstract invariants:

    Z^d / U  ~=  Z^(d-r) direct_sum_i Z/s_i Z.

SymPy 1.14 does not expose the Smith transformation matrices.  Keeping the
Hermite reduction map and the Smith invariants separate preserves all exact
group operations without inventing a floating-point projection.

No function accepts a factorization or order of ``N``.  The only factors
reported are discovered at the final ``gcd(beta +/- 1, N)`` step from the
roots permanently stored in ``RootedBaseFamily``.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import gcd, prod
from operator import index
from typing import Sequence

from .core import RootedBaseFamily, modular_product


@dataclass(frozen=True, slots=True)
class QuotientElement:
    """A canonical ambient lift tagged with the quotient that owns it."""

    quotient_key: tuple
    representative: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CosetReduction:
    """A canonical reduction and an exact row-Hermite reconstruction witness."""

    original: tuple[int, ...]
    element: QuotientElement
    hnf_coefficients: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class QuotientCandidateClassification:
    """Factor-blind-input classification of one quotient candidate."""

    original_lift: tuple[int, ...]
    element: QuotientElement
    category: str
    base_product: int
    root_product: int | None
    gcd_minus: int | None
    gcd_plus: int | None
    factor_pair: tuple[int, int] | None


@dataclass(frozen=True, slots=True)
class FactorYieldingQuotientGap:
    """Observed lift-norm separation after quotienting verified ``L0`` rows."""

    shortest_factor_yielding_squared_norm: int | None
    shortest_nonzero_L0_squared_norm: int | None
    signed_squared_gap: int | None
    L0_to_factor_squared_ratio: Fraction | None
    shortest_factor_yielding_lift: tuple[int, ...] | None
    shortest_nonzero_L0_lift: tuple[int, ...] | None
    distinct_nonzero_relation_cosets: int
    excluded_zero_coset_lifts: int
    invalid_lifts: int
    inconclusive_lifts: int
    norm_definition: str


@dataclass(frozen=True, slots=True)
class IntegerQuotient:
    """Exact presentation of ``Z^d / U`` for verified ``U <= L0``."""

    family: RootedBaseFamily
    input_directions: tuple[tuple[int, ...], ...]
    hnf_basis: tuple[tuple[int, ...], ...]
    hnf_pivot_columns: tuple[int, ...]
    hnf_pivot_moduli: tuple[int, ...]
    rank: int
    free_rank: int
    smith_diagonal: tuple[int, ...]
    torsion_invariant_factors: tuple[int, ...]
    torsion_order: int
    torsion_exponent: int
    saturation_index: int
    covolume_squared_in_span: int
    redundant_direction_count: int

    @property
    def dimension(self) -> int:
        return len(self.family.pairs)

    @property
    def quotient_key(self) -> tuple:
        return (self.family.N, self.family.roots, self.hnf_basis)

    @property
    def is_finite(self) -> bool:
        return self.free_rank == 0

    @property
    def is_torsion_free(self) -> bool:
        return not self.torsion_invariant_factors

    @property
    def abstract_decomposition(self) -> tuple[int, tuple[int, ...]]:
        """Return ``(free_rank, nontrivial Smith invariant factors)``."""

        return self.free_rank, self.torsion_invariant_factors

    def _normalize_vector(self, vector: Sequence[int], name: str) -> tuple[int, ...]:
        normalized = tuple(
            _as_integer(value, f"{name}[{i}]") for i, value in enumerate(vector)
        )
        if len(normalized) != self.dimension:
            raise ValueError(f"{name} must have ambient dimension {self.dimension}")
        return normalized

    def _validate_element(self, element: QuotientElement) -> None:
        if not isinstance(element, QuotientElement):
            raise TypeError("expected a QuotientElement")
        if element.quotient_key != self.quotient_key:
            raise ValueError("quotient element belongs to a different quotient")
        canonical, _ = self._reduce_coordinates(element.representative)
        if canonical != element.representative:
            raise ValueError("quotient element is not in canonical Hermite form")

    def _reduce_coordinates(
        self, original: Sequence[int]
    ) -> tuple[tuple[int, ...], tuple[int, ...]]:
        remainder = list(original)
        coefficients = [0] * self.rank
        for row_index in reversed(range(self.rank)):
            row = self.hnf_basis[row_index]
            pivot_column = self.hnf_pivot_columns[row_index]
            pivot_modulus = self.hnf_pivot_moduli[row_index]
            quotient_coefficient, canonical_residue = divmod(
                remainder[pivot_column], pivot_modulus
            )
            coefficients[row_index] = quotient_coefficient
            if quotient_coefficient:
                remainder = [
                    value - quotient_coefficient * basis_value
                    for value, basis_value in zip(remainder, row, strict=True)
                ]
            if remainder[pivot_column] != canonical_residue:
                raise ArithmeticError("Hermite reduction failed at a pivot")
        return tuple(remainder), tuple(coefficients)

    def reduce_with_witness(self, vector: Sequence[int]) -> CosetReduction:
        """Reduce ``vector`` and prove ``vector-representative`` lies in ``U``."""

        original = self._normalize_vector(vector, "vector")
        representative, coefficients = self._reduce_coordinates(original)
        element = QuotientElement(self.quotient_key, representative)
        reconstructed = self.lift(element, coefficients)
        if reconstructed != original:
            raise ArithmeticError("Hermite reduction witness does not reconstruct the input")
        return CosetReduction(original, element, tuple(coefficients))

    def reduce(self, vector: Sequence[int]) -> QuotientElement:
        return self.reduce_with_witness(vector).element

    def lift(
        self,
        element: QuotientElement,
        hnf_coefficients: Sequence[int] | None = None,
    ) -> tuple[int, ...]:
        """Return the canonical lift, or another exact lift using HNF rows."""

        if not isinstance(element, QuotientElement):
            raise TypeError("expected a QuotientElement")
        self._validate_element(element)
        if hnf_coefficients is None:
            coefficients = (0,) * self.rank
        else:
            coefficients = tuple(
                _as_integer(value, f"hnf_coefficients[{i}]")
                for i, value in enumerate(hnf_coefficients)
            )
            if len(coefficients) != self.rank:
                raise ValueError("one coefficient is required for each HNF row")
        result = list(element.representative)
        for coefficient, row in zip(coefficients, self.hnf_basis, strict=True):
            result = [
                value + coefficient * basis_value
                for value, basis_value in zip(result, row, strict=True)
            ]
        return tuple(result)

    def equivalent(self, left: Sequence[int], right: Sequence[int]) -> bool:
        return self.reduce(left) == self.reduce(right)

    def zero(self) -> QuotientElement:
        return self.reduce((0,) * self.dimension)

    def is_zero(self, element: QuotientElement) -> bool:
        self._validate_element(element)
        return element == self.zero()

    def add(self, left: QuotientElement, right: QuotientElement) -> QuotientElement:
        self._validate_element(left)
        self._validate_element(right)
        return self.reduce(
            tuple(
                x + y
                for x, y in zip(left.representative, right.representative, strict=True)
            )
        )

    def negate(self, element: QuotientElement) -> QuotientElement:
        self._validate_element(element)
        return self.reduce(tuple(-value for value in element.representative))

    def scalar_multiply(self, scalar: int, element: QuotientElement) -> QuotientElement:
        self._validate_element(element)
        scalar = _as_integer(scalar, "scalar")
        return self.reduce(tuple(scalar * value for value in element.representative))


def _as_integer(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, not bool")
    try:
        return int(index(value))
    except TypeError as exc:
        raise TypeError(f"{name} must be an integer") from exc


def _normalize_directions(
    family: RootedBaseFamily, directions: Sequence[Sequence[int]]
) -> tuple[tuple[int, ...], ...]:
    if not isinstance(family, RootedBaseFamily):
        raise TypeError("quotient construction requires a RootedBaseFamily")
    dimension = len(family.pairs)
    normalized = tuple(
        tuple(_as_integer(value, f"directions[{i}][{j}]") for j, value in enumerate(row))
        for i, row in enumerate(directions)
    )
    for i, row in enumerate(normalized):
        if len(row) != dimension:
            raise ValueError(f"directions[{i}] must have dimension {dimension}")
        if not any(row):
            raise ValueError("zero is not a useful deflation direction")
        base_product = modular_product(family.N, family.bases, row)
        root_product = modular_product(family.N, family.roots, row)
        if base_product != 1 or root_product not in (1, family.N - 1):
            raise ValueError(f"directions[{i}] is not a verified L0 direction")
    return normalized


def _row_hnf_and_pivots(
    directions: tuple[tuple[int, ...], ...], dimension: int
) -> tuple[tuple[tuple[int, ...], ...], tuple[int, ...], tuple[int, ...]]:
    if not directions:
        return (), (), ()
    try:
        from sympy import Matrix
        from sympy.matrices.normalforms import hermite_normal_form
    except ImportError as exc:  # pragma: no cover - SymPy is pinned by the project.
        raise RuntimeError("SymPy is required for exact Hermite normal form") from exc

    row_hnf_matrix = hermite_normal_form(Matrix(directions).T).T
    rows = [tuple(int(value) for value in row) for row in row_hnf_matrix.tolist()]
    if any(len(row) != dimension for row in rows):
        raise ArithmeticError("row Hermite basis has the wrong ambient dimension")

    normalized_rows: list[tuple[int, ...]] = []
    pivot_rows: list[tuple[int, tuple[int, ...]]] = []
    for row in rows:
        nonzero = [i for i, value in enumerate(row) if value]
        if not nonzero:
            raise ArithmeticError("row Hermite basis unexpectedly contains zero")
        pivot = nonzero[-1]
        if row[pivot] < 0:
            row = tuple(-value for value in row)
        pivot_rows.append((pivot, row))
    pivot_rows.sort(key=lambda item: item[0])
    pivots = tuple(item[0] for item in pivot_rows)
    if len(set(pivots)) != len(pivots):
        raise ArithmeticError("row Hermite pivots are not distinct")
    normalized_rows = [item[1] for item in pivot_rows]
    moduli = tuple(row[pivot] for row, pivot in zip(normalized_rows, pivots, strict=True))
    if any(modulus <= 0 for modulus in moduli):
        raise ArithmeticError("row Hermite pivots must be positive")
    return tuple(normalized_rows), pivots, moduli


def _smith_invariants(
    hnf_basis: tuple[tuple[int, ...], ...], rank: int
) -> tuple[int, ...]:
    if rank == 0:
        return ()
    try:
        from sympy import Matrix, ZZ
        from sympy.matrices.normalforms import smith_normal_form
    except ImportError as exc:  # pragma: no cover - SymPy is pinned by the project.
        raise RuntimeError("SymPy is required for exact Smith normal form") from exc
    smith = smith_normal_form(Matrix(hnf_basis), domain=ZZ)
    diagonal = tuple(abs(int(smith[i, i])) for i in range(rank))
    if any(value == 0 for value in diagonal):
        raise ArithmeticError("Smith form rank disagrees with Hermite form")
    if any(right % left for left, right in zip(diagonal, diagonal[1:])):
        raise ArithmeticError("Smith invariant factors do not form a divisibility chain")
    return diagonal


def build_l0_quotient(
    family: RootedBaseFamily, l0_directions: Sequence[Sequence[int]]
) -> IntegerQuotient:
    """Construct ``Z^d/U`` after verifying every supplied row lies in ``L0``."""

    directions = _normalize_directions(family, l0_directions)
    dimension = len(family.pairs)
    hnf_basis, pivots, pivot_moduli = _row_hnf_and_pivots(directions, dimension)
    rank = len(hnf_basis)
    smith_diagonal = _smith_invariants(hnf_basis, rank)
    torsion_factors = tuple(value for value in smith_diagonal if value > 1)
    torsion_order = prod(torsion_factors, start=1)
    torsion_exponent = torsion_factors[-1] if torsion_factors else 1
    if rank:
        from sympy import Matrix

        hnf_matrix = Matrix(hnf_basis)
        covolume_squared = int((hnf_matrix * hnf_matrix.T).det())
    else:
        covolume_squared = 1

    quotient = IntegerQuotient(
        family=family,
        input_directions=directions,
        hnf_basis=hnf_basis,
        hnf_pivot_columns=pivots,
        hnf_pivot_moduli=pivot_moduli,
        rank=rank,
        free_rank=dimension - rank,
        smith_diagonal=smith_diagonal,
        torsion_invariant_factors=torsion_factors,
        torsion_order=torsion_order,
        torsion_exponent=torsion_exponent,
        saturation_index=torsion_order,
        covolume_squared_in_span=covolume_squared,
        redundant_direction_count=len(directions) - rank,
    )

    for direction in directions:
        if quotient.reduce(direction) != quotient.zero():
            raise ArithmeticError("an input direction survived quotient reduction")
    for hnf_row in hnf_basis:
        root_product = modular_product(family.N, family.roots, hnf_row)
        if (
            modular_product(family.N, family.bases, hnf_row) != 1
            or root_product not in (1, family.N - 1)
        ):
            raise ArithmeticError("Hermite basis escaped L0")
    return quotient


def classify_quotient_candidate(
    quotient: IntegerQuotient,
    candidate: Sequence[int] | QuotientElement,
) -> QuotientCandidateClassification:
    """Classify a lift as invalid, ``L0``, factor-yielding, or inconclusive.

    The classification is constant on cosets because ``U <= L0``.  No known
    factors are accepted; ``factor_pair`` is populated only by GCDs of the
    nontrivial stored-root product.
    """

    if not isinstance(quotient, IntegerQuotient):
        raise TypeError("classification requires an IntegerQuotient")
    if isinstance(candidate, QuotientElement):
        quotient._validate_element(candidate)
        original = quotient.lift(candidate)
        element = candidate
    else:
        original = quotient._normalize_vector(candidate, "candidate")
        element = quotient.reduce(original)

    family = quotient.family
    base_product = modular_product(family.N, family.bases, original)
    if base_product != 1:
        return QuotientCandidateClassification(
            original,
            element,
            "invalid",
            base_product,
            None,
            None,
            None,
            None,
        )

    beta = modular_product(family.N, family.roots, original)
    if beta * beta % family.N != 1:
        raise ArithmeticError("a verified squared-base relation violated beta^2 = 1")
    if beta in (1, family.N - 1):
        return QuotientCandidateClassification(
            original,
            element,
            "L0",
            base_product,
            beta,
            None,
            None,
            None,
        )

    gcd_minus = gcd(beta - 1, family.N)
    gcd_plus = gcd(beta + 1, family.N)
    factor = next(
        (value for value in (gcd_minus, gcd_plus) if 1 < value < family.N),
        None,
    )
    if factor is None:
        category = "inconclusive"
        factor_pair = None
    else:
        category = "factor_yielding"
        first, second = sorted((factor, family.N // factor))
        factor_pair = (first, second)
    return QuotientCandidateClassification(
        original,
        element,
        category,
        base_product,
        beta,
        gcd_minus,
        gcd_plus,
        factor_pair,
    )


def factor_yielding_quotient_gap(
    quotient: IntegerQuotient, candidates: Sequence[Sequence[int]]
) -> FactorYieldingQuotientGap:
    """Compute an exact, observed factor-vs-``L0`` quotient gap.

    For each distinct nonzero quotient coset represented in ``candidates``,
    the statistic uses the smallest squared Euclidean norm among the supplied
    ambient lifts of that coset.  It then reports

    ``shortest_nonzero_L0_norm^2 - shortest_factor_yielding_norm^2``.

    Positive values mean a supplied factor-yielding lift is shorter.  This is
    an *observed-candidate* statistic, not the exact quotient norm (which would
    require a closest-vector computation), and it is deliberately named as
    such in ``norm_definition``.
    """

    if not isinstance(quotient, IntegerQuotient):
        raise TypeError("gap computation requires an IntegerQuotient")
    zero = quotient.zero()
    by_coset: dict[QuotientElement, tuple[str, int, tuple[int, ...]]] = {}
    excluded_zero = 0
    invalid_lifts = 0
    inconclusive_lifts = 0

    for raw_candidate in candidates:
        lift = quotient._normalize_vector(raw_candidate, "candidate")
        classified = classify_quotient_candidate(quotient, lift)
        if classified.category == "invalid":
            invalid_lifts += 1
            continue
        if classified.category == "inconclusive":
            inconclusive_lifts += 1
            continue
        if classified.element == zero:
            excluded_zero += 1
            continue
        squared_norm = sum(value * value for value in lift)
        existing = by_coset.get(classified.element)
        if existing is not None and existing[0] != classified.category:
            raise ArithmeticError("candidate category changed within an L0 quotient coset")
        if existing is None or squared_norm < existing[1]:
            by_coset[classified.element] = (
                classified.category,
                squared_norm,
                lift,
            )

    factor_rows = [row for row in by_coset.values() if row[0] == "factor_yielding"]
    l0_rows = [row for row in by_coset.values() if row[0] == "L0"]
    shortest_factor = min(factor_rows, key=lambda row: row[1]) if factor_rows else None
    shortest_l0 = min(l0_rows, key=lambda row: row[1]) if l0_rows else None
    if shortest_factor is not None and shortest_l0 is not None:
        gap = shortest_l0[1] - shortest_factor[1]
        ratio = Fraction(shortest_l0[1], shortest_factor[1])
    else:
        gap = None
        ratio = None
    return FactorYieldingQuotientGap(
        shortest_factor_yielding_squared_norm=(
            shortest_factor[1] if shortest_factor else None
        ),
        shortest_nonzero_L0_squared_norm=shortest_l0[1] if shortest_l0 else None,
        signed_squared_gap=gap,
        L0_to_factor_squared_ratio=ratio,
        shortest_factor_yielding_lift=shortest_factor[2] if shortest_factor else None,
        shortest_nonzero_L0_lift=shortest_l0[2] if shortest_l0 else None,
        distinct_nonzero_relation_cosets=len(by_coset),
        excluded_zero_coset_lifts=excluded_zero,
        invalid_lifts=invalid_lifts,
        inconclusive_lifts=inconclusive_lifts,
        norm_definition=(
            "minimum squared Euclidean norm among supplied ambient lifts per "
            "distinct nonzero Hermite-reduced quotient coset; not an exact CVP quotient norm"
        ),
    )

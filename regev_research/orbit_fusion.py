"""Factor-or-fuse preprocessing for Regev-style modular exponentiation.

The supplied circuit evaluates

    product_i a_i**x_i (mod N)

with one binary modular-exponentiation block for every selected base ``a_i``.
If public modular arithmetic proves that several bases lie in one power orbit,
say ``a_i = g**k_i (mod N)``, then the same oracle can instead compute the
ordinary integer sum ``s = sum_i k_i*x_i`` in a clean accumulator and evaluate
``g**s`` once.  The accumulator is uncomputed afterwards, so the exponent
registers and all work qubits are returned unchanged.

The low-level orbit planner deliberately receives only ``N`` and the
already-selected circuit bases.  The high-level factor-or-fuse preprocessor
receives the immutable roots that generated those bases, but never receives
factors or group orders.  A detected public relation is either a nontrivial
square root of one (and therefore an immediate classical factor certificate)
or a verified ``L0`` direction that may be used for oracle-preserving fusion.

The optimization is conditional: generic base families need not contain a
short power relation.  The planner therefore minimizes an exact source-level
canonical-CX objective and falls back to the original block for every group
whose accumulator overhead would erase the saving.
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from math import gcd, log2
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import QFTGate

from .resource_analysis import (
    _controlled_constant_adder_counts,
    canonical_cx_count,
    modular_exponentiation_counts,
    qft_source_counts,
)
from .core import RootedBaseFamily, is_prime, modular_product


_EXTERNAL = Path(__file__).resolve().parents[1] / "external" / "regev-quantum-algorithm"
if str(_EXTERNAL) not in sys.path:
    sys.path.insert(0, str(_EXTERNAL))

from gates.haner.constant_adder import controlled_constant_adder  # noqa: E402
from gates.r_haner.modular_exponentiation import modular_exponentiation_gate  # noqa: E402


GateCounts = Counter[str]


@dataclass(frozen=True, slots=True)
class PublicRelationClassification:
    """Exact, factor-free-input classification of one public integer relation."""

    vector: tuple[int, ...]
    base_product: int
    root_product: int | None
    category: str
    gcd_minus: int | None
    gcd_plus: int | None
    factor_pair: tuple[int, int] | None


@dataclass(frozen=True, slots=True)
class PowerOrbitRelation:
    """A relation ``a_target = a_anchor**power`` and its root classification."""

    anchor_index: int
    target_index: int
    power: int
    classification: PublicRelationClassification


@dataclass(frozen=True, slots=True)
class PositivePowerNoWrapCertificate:
    """Sufficient certificate excluding positive pair powers through ``K``."""

    N: int
    roots: tuple[int, ...]
    max_power: int
    distinct_prime_roots: bool
    largest_integer_power_bit_length: int
    modulus_bit_length: int
    certified: bool

    def verify(self) -> bool:
        prime_roots = len(set(self.roots)) == len(self.roots) and all(
            is_prime(root) for root in self.roots
        )
        largest = max(pow(root, 2 * self.max_power) for root in self.roots)
        return (
            self.max_power > 0
            and self.distinct_prime_roots == prime_roots
            and self.largest_integer_power_bit_length == largest.bit_length()
            and self.modulus_bit_length == self.N.bit_length()
            and self.certified == (prime_roots and largest < self.N)
        )


@dataclass(frozen=True, slots=True)
class FactorOrFuseResult:
    """Auditable result of the factor-or-fuse pre-circuit pass."""

    family: RootedBaseFamily
    exponent_width: int
    max_power: int
    witness_policy: str
    relations: tuple[PowerOrbitRelation, ...]
    outcome: str
    factor_pair: tuple[int, int] | None
    plan: "OrbitFusionPlan | None"
    public_power_steps: int

    @property
    def l0_relation_count(self) -> int:
        return sum(row.classification.category == "L0" for row in self.relations)

    @property
    def factor_relation_count(self) -> int:
        return sum(
            row.classification.category == "factor_yielding" for row in self.relations
        )

    def verify(self) -> bool:
        if self.exponent_width <= 0 or self.max_power <= 0:
            return False
        if self.witness_policy not in ("least_per_ordered_pair", "all_within_bound"):
            return False
        if self.public_power_steps != len(self.family.pairs) * self.max_power:
            return False
        for row in self.relations:
            i, j, power = row.anchor_index, row.target_index, row.power
            if i == j or not (0 <= i < len(self.family.pairs)):
                return False
            if not (0 <= j < len(self.family.pairs)) or not (1 <= power <= self.max_power):
                return False
            if pow(self.family.bases[i], power, self.family.N) != self.family.bases[j]:
                return False
            vector = [0] * len(self.family.pairs)
            vector[i] = power
            vector[j] -= 1
            if classify_public_relation(self.family, vector) != row.classification:
                return False
        factor_rows = [
            row
            for row in self.relations
            if row.classification.category == "factor_yielding"
        ]
        if factor_rows:
            return (
                self.outcome == "classical_factor"
                and self.plan is None
                and self.factor_pair == factor_rows[0].classification.factor_pair
            )
        if self.factor_pair is not None or self.plan is None or not self.plan.verify():
            return False
        if self.plan.N != self.family.N or self.plan.bases != self.family.bases:
            return False
        allowed: dict[tuple[int, int], set[int]] = {}
        for row in self.relations:
            if row.classification.category == "L0":
                allowed.setdefault((row.anchor_index, row.target_index), set()).add(row.power)
        for group in self.plan.groups:
            if not group.fused:
                continue
            for index, weight in zip(group.member_indices, group.weights, strict=True):
                if index == group.anchor_index:
                    if weight != 1:
                        return False
                elif weight not in allowed.get((group.anchor_index, index), set()):
                    return False
        expected = (
            "l0_orbit_fusion" if any(group.fused for group in self.plan.groups)
            else "baseline_fallback"
        )
        return self.outcome == expected


def _count_tuple(counts: Mapping[str, int]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((str(name), int(value)) for name, value in counts.items() if value))


def _as_counter(counts: Iterable[tuple[str, int]]) -> GateCounts:
    return Counter({str(name): int(value) for name, value in counts})


@lru_cache(maxsize=None)
def _cached_modular_exponentiation_counts(
    base: int, N: int, exponent_width: int
) -> tuple[tuple[str, int], ...]:
    """Memoize immutable exact counts reused across candidate partitions."""

    return _count_tuple(
        modular_exponentiation_counts(base, N, int(N).bit_length(), exponent_width)
    )


@lru_cache(maxsize=None)
def _cached_controlled_constant_adder_counts(
    constant: int, width: int
) -> tuple[tuple[str, int], ...]:
    return _count_tuple(_controlled_constant_adder_counts(constant, width))


def classify_public_relation(
    family: RootedBaseFamily, vector: Sequence[int]
) -> PublicRelationClassification:
    """Classify ``z`` using only ``N``, public bases, and their stored roots.

    For ``z`` in the squared-base relation lattice ``L``, the root product
    ``R = product_i b_i**z_i`` satisfies ``R**2 = 1 (mod N)``.  The values
    ``R = +/-1`` are exactly the repository's definition of ``L0``.  Any
    other value yields a proper divisor through ``gcd(R +/- 1, N)``.
    """

    if not isinstance(family, RootedBaseFamily):
        raise TypeError("classification requires a RootedBaseFamily")
    normalized = tuple(int(value) for value in vector)
    if len(normalized) != len(family.pairs):
        raise ValueError("relation vector has the wrong dimension")
    base_product = modular_product(family.N, family.bases, normalized)
    if base_product != 1:
        return PublicRelationClassification(
            normalized, base_product, None, "invalid", None, None, None
        )
    root_product = modular_product(family.N, family.roots, normalized)
    if root_product * root_product % family.N != 1:
        raise ArithmeticError("squared-base relation did not produce a square root of one")
    gcd_minus = gcd(root_product - 1, family.N)
    gcd_plus = gcd(root_product + 1, family.N)
    if root_product in (1, family.N - 1):
        return PublicRelationClassification(
            normalized,
            base_product,
            root_product,
            "L0",
            gcd_minus,
            gcd_plus,
            None,
        )
    proper = next(
        (value for value in (gcd_minus, gcd_plus) if 1 < value < family.N),
        None,
    )
    if proper is None:
        raise ArithmeticError("nontrivial square root failed to split the modulus")
    pair = tuple(sorted((proper, family.N // proper)))
    return PublicRelationClassification(
        normalized,
        base_product,
        root_product,
        "factor_yielding",
        gcd_minus,
        gcd_plus,
        pair,
    )


def positive_power_no_wrap_certificate(
    family: RootedBaseFamily, *, max_power: int = 64
) -> PositivePowerNoWrapCertificate:
    """Certify that no distinct standard-prime pair satisfies ``a_j=a_i^k``.

    This is a sufficient certificate only.  If the retained roots are
    distinct positive primes and ``max_i b_i**(2*K) < N``, then for every
    ``1 <= k <= K`` both ``b_i**(2*k)`` and ``b_j**2`` lie in ``(0,N)``.
    Congruence modulo ``N`` would therefore imply integer equality, which is
    impossible for distinct primes by unique factorization.
    """

    if not isinstance(family, RootedBaseFamily):
        raise TypeError("no-wrap certification requires a RootedBaseFamily")
    max_power = int(max_power)
    if max_power <= 0:
        raise ValueError("max_power must be positive")
    prime_roots = len(set(family.roots)) == len(family.roots) and all(
        is_prime(root) for root in family.roots
    )
    largest = max(pow(root, 2 * max_power) for root in family.roots)
    result = PositivePowerNoWrapCertificate(
        N=family.N,
        roots=family.roots,
        max_power=max_power,
        distinct_prime_roots=prime_roots,
        largest_integer_power_bit_length=largest.bit_length(),
        modulus_bit_length=family.N.bit_length(),
        certified=prime_roots and largest < family.N,
    )
    if not result.verify():
        raise AssertionError("internal no-wrap certificate failed")
    return result


def detect_pair_power_relations(
    family: RootedBaseFamily, *, max_power: int = 64
) -> tuple[PowerOrbitRelation, ...]:
    """Find the first public power relation for every ordered base pair.

    The search performs exactly ``d * max_power`` modular multiplications and
    dictionary lookups.  It uses neither the factorization nor a group order.
    """

    if not isinstance(family, RootedBaseFamily):
        raise TypeError("relation detection requires a RootedBaseFamily")
    max_power = int(max_power)
    if max_power <= 0:
        raise ValueError("max_power must be positive")
    relations: list[PowerOrbitRelation] = []
    for anchor_index, anchor in enumerate(family.bases):
        lookup = _power_lookup(anchor, family.N, max_power)
        for target_index, target in enumerate(family.bases):
            if target_index == anchor_index or target not in lookup:
                continue
            power = lookup[target]
            vector = [0] * len(family.pairs)
            vector[anchor_index] = power
            vector[target_index] -= 1
            relations.append(
                PowerOrbitRelation(
                    anchor_index=anchor_index,
                    target_index=target_index,
                    power=power,
                    classification=classify_public_relation(family, vector),
                )
            )
    return tuple(relations)


def detect_all_pair_power_relations(
    family: RootedBaseFamily, *, max_power: int = 64
) -> tuple[PowerOrbitRelation, ...]:
    """Return every directed pair-power witness inside the public bound.

    Unlike :func:`detect_pair_power_relations`, this scan does not discard a
    later exponent after the same target residue was reached once.  This is
    necessary because two witnesses can have different root-level ``L0``
    classifications even though they have the same squared-base endpoint.
    """

    if not isinstance(family, RootedBaseFamily):
        raise TypeError("relation detection requires a RootedBaseFamily")
    max_power = int(max_power)
    if max_power <= 0:
        raise ValueError("max_power must be positive")
    targets: dict[int, list[int]] = {}
    for index, base in enumerate(family.bases):
        targets.setdefault(base, []).append(index)
    relations: list[PowerOrbitRelation] = []
    for anchor_index, anchor in enumerate(family.bases):
        value = 1
        for power in range(1, max_power + 1):
            value = value * anchor % family.N
            for target_index in targets.get(value, ()):
                if target_index == anchor_index:
                    continue
                vector = [0] * len(family.pairs)
                vector[anchor_index] = power
                vector[target_index] -= 1
                relations.append(
                    PowerOrbitRelation(
                        anchor_index=anchor_index,
                        target_index=target_index,
                        power=power,
                        classification=classify_public_relation(family, vector),
                    )
                )
    return tuple(relations)


@dataclass(frozen=True, slots=True)
class OrbitFusionGroup:
    """One direct block or one certified power-orbit fusion block."""

    member_indices: tuple[int, ...]
    anchor_index: int
    weights: tuple[int, ...]
    accumulator_width: int
    fused: bool
    baseline_counts: tuple[tuple[str, int], ...]
    selected_counts: tuple[tuple[str, int], ...]

    @property
    def baseline_canonical_cx(self) -> int:
        return canonical_cx_count(_as_counter(self.baseline_counts))

    @property
    def selected_canonical_cx(self) -> int:
        return canonical_cx_count(_as_counter(self.selected_counts))

    @property
    def canonical_cx_saved(self) -> int:
        return self.baseline_canonical_cx - self.selected_canonical_cx


@dataclass(frozen=True, slots=True)
class OrbitFusionPlan:
    """Immutable, executable certificate for an orbit-fused oracle."""

    N: int
    bases: tuple[int, ...]
    exponent_width: int
    max_power: int
    groups: tuple[OrbitFusionGroup, ...]
    planner: str

    @property
    def dimension(self) -> int:
        return len(self.bases)

    @property
    def max_accumulator_width(self) -> int:
        return max((group.accumulator_width for group in self.groups if group.fused), default=0)

    @property
    def extra_qubits(self) -> int:
        # One shared accumulator and one clean carry/garbage bit are reused.
        return self.max_accumulator_width + (1 if self.max_accumulator_width else 0)

    @property
    def baseline_arithmetic_counts(self) -> GateCounts:
        total: GateCounts = Counter()
        for group in self.groups:
            total.update(_as_counter(group.baseline_counts))
        return total

    @property
    def selected_arithmetic_counts(self) -> GateCounts:
        total: GateCounts = Counter()
        for group in self.groups:
            total.update(_as_counter(group.selected_counts))
        return total

    @property
    def baseline_canonical_cx(self) -> int:
        return canonical_cx_count(self.baseline_arithmetic_counts)

    @property
    def selected_canonical_cx(self) -> int:
        return canonical_cx_count(self.selected_arithmetic_counts)

    @property
    def canonical_cx_saved(self) -> int:
        return self.baseline_canonical_cx - self.selected_canonical_cx

    @property
    def canonical_cx_saving_fraction(self) -> float:
        if not self.baseline_canonical_cx:
            return 0.0
        return self.canonical_cx_saved / self.baseline_canonical_cx

    def verify(self) -> bool:
        """Recheck coverage, relations, accumulator bounds, and no-regression."""

        covered: list[int] = []
        n = self.N.bit_length()
        q = self.exponent_width
        for group in self.groups:
            if len(group.member_indices) != len(group.weights):
                return False
            if tuple(sorted(group.member_indices)) != group.member_indices:
                return False
            if not group.member_indices or group.anchor_index not in group.member_indices:
                return False
            anchor = self.bases[group.anchor_index]
            for index, weight in zip(group.member_indices, group.weights, strict=True):
                if weight <= 0 or weight > self.max_power:
                    return False
                if pow(anchor, weight, self.N) != self.bases[index]:
                    return False
            covered.extend(group.member_indices)
            if group.fused:
                maximum = ((1 << q) - 1) * sum(group.weights)
                if group.accumulator_width != max(1, maximum.bit_length()):
                    return False
                if maximum >= 1 << group.accumulator_width:
                    return False
                expected = _fused_group_counts(
                    self.N,
                    self.bases,
                    q,
                    group.member_indices,
                    group.anchor_index,
                    group.weights,
                )
            else:
                if len(group.member_indices) != 1 or group.accumulator_width != 0:
                    return False
                index = group.member_indices[0]
                expected = modular_exponentiation_counts(self.bases[index], self.N, n, q)
            if _count_tuple(expected) != group.selected_counts:
                return False
            baseline = _direct_group_counts(self.N, self.bases, q, group.member_indices)
            if _count_tuple(baseline) != group.baseline_counts:
                return False
            if group.selected_canonical_cx > group.baseline_canonical_cx:
                return False
        return sorted(covered) == list(range(self.dimension))


def _direct_group_counts(
    N: int, bases: Sequence[int], exponent_width: int, indices: Sequence[int]
) -> GateCounts:
    total: GateCounts = Counter()
    for index in indices:
        total.update(
            _as_counter(
                _cached_modular_exponentiation_counts(
                    int(bases[index]), int(N), int(exponent_width)
                )
            )
        )
    return total


def _fused_group_counts(
    N: int,
    bases: Sequence[int],
    exponent_width: int,
    member_indices: Sequence[int],
    anchor_index: int,
    weights: Sequence[int],
) -> GateCounts:
    """Count one fused group, including accumulator compute/uncompute."""

    N = int(N)
    q = int(exponent_width)
    maximum = ((1 << q) - 1) * sum(int(weight) for weight in weights)
    width = max(1, maximum.bit_length())
    total: GateCounts = Counter()
    for weight in weights:
        for bit in range(q):
            adder = _as_counter(
                _cached_controlled_constant_adder_counts(int(weight) << bit, width)
            )
            total.update({name: 2 * value for name, value in adder.items()})
    total.update(
        _as_counter(
            _cached_modular_exponentiation_counts(int(bases[anchor_index]), N, width)
        )
    )
    return total


def _power_lookup(anchor: int, N: int, max_power: int) -> dict[int, int]:
    """Map each reached residue to its smallest positive public exponent."""

    lookup: dict[int, int] = {}
    value = 1
    for exponent in range(1, int(max_power) + 1):
        value = (value * int(anchor)) % int(N)
        lookup.setdefault(value, exponent)
    return lookup


def _candidate_groups(
    N: int,
    bases: tuple[int, ...],
    exponent_width: int,
    max_power: int,
    allowed_relations: Mapping[tuple[int, int], int] | None = None,
) -> tuple[OrbitFusionGroup, ...]:
    dimension = len(bases)
    direct_singletons = {
        index: _direct_group_counts(N, bases, exponent_width, (index,))
        for index in range(dimension)
    }
    candidates: list[OrbitFusionGroup] = []
    for index in range(dimension):
        direct = direct_singletons[index]
        candidates.append(
            OrbitFusionGroup(
                member_indices=(index,),
                anchor_index=index,
                weights=(1,),
                accumulator_width=0,
                fused=False,
                baseline_counts=_count_tuple(direct),
                selected_counts=_count_tuple(direct),
            )
        )

    lookups = (
        [_power_lookup(base, N, max_power) for base in bases]
        if allowed_relations is None
        else None
    )
    for mask in range(1, 1 << dimension):
        indices = tuple(index for index in range(dimension) if mask & (1 << index))
        if len(indices) < 2:
            continue
        baseline = _direct_group_counts(N, bases, exponent_width, indices)
        baseline_cx = canonical_cx_count(baseline)
        for anchor_index in indices:
            if allowed_relations is None:
                if lookups is None:
                    raise AssertionError("unconstrained search requires power lookups")
                lookup = lookups[anchor_index]
                if any(bases[index] not in lookup for index in indices):
                    continue
                weights = tuple(lookup[bases[index]] for index in indices)
            else:
                weights_or_none = tuple(
                    1
                    if index == anchor_index
                    else allowed_relations.get((anchor_index, index))
                    for index in indices
                )
                if any(weight is None for weight in weights_or_none):
                    continue
                weights = tuple(int(weight) for weight in weights_or_none if weight is not None)
            selected = _fused_group_counts(
                N,
                bases,
                exponent_width,
                indices,
                anchor_index,
                weights,
            )
            if canonical_cx_count(selected) >= baseline_cx:
                continue
            maximum = ((1 << exponent_width) - 1) * sum(weights)
            candidates.append(
                OrbitFusionGroup(
                    member_indices=indices,
                    anchor_index=anchor_index,
                    weights=weights,
                    accumulator_width=max(1, maximum.bit_length()),
                    fused=True,
                    baseline_counts=_count_tuple(baseline),
                    selected_counts=_count_tuple(selected),
                )
            )
    return tuple(candidates)


def plan_power_orbit_fusion(
    N: int,
    bases: Sequence[int],
    exponent_width: int,
    *,
    max_power: int = 64,
    exact_partition_limit: int = 12,
    allowed_relations: Mapping[tuple[int, int], int] | None = None,
) -> OrbitFusionPlan:
    """Return the minimum-canonical-CX certified orbit cover.

    The exact set-partition dynamic program is used through
    ``exact_partition_limit`` dimensions.  Larger instances use a deterministic
    savings-first disjoint cover and retain the same exact relation and cost
    certificates.  Singleton groups are the original implementation, making
    the planner an automatic no-regression transformation in its declared
    source-level objective.
    """

    N = int(N)
    q = int(exponent_width)
    max_power = int(max_power)
    exact_partition_limit = int(exact_partition_limit)
    normalized = tuple(int(base) % N for base in bases)
    if N <= 2 or not normalized or q <= 0 or max_power <= 0:
        raise ValueError("invalid modulus, bases, exponent width, or power bound")
    if any(gcd(base, N) != 1 for base in normalized):
        raise ValueError("all circuit bases must be units modulo N")
    if exact_partition_limit <= 0:
        raise ValueError("exact_partition_limit must be positive")

    normalized_allowed: dict[tuple[int, int], int] | None = None
    if allowed_relations is not None:
        normalized_allowed = {}
        for raw_pair, raw_power in allowed_relations.items():
            if len(raw_pair) != 2:
                raise ValueError("allowed relation keys must be (anchor, target) pairs")
            anchor_index, target_index = (int(raw_pair[0]), int(raw_pair[1]))
            power = int(raw_power)
            if anchor_index == target_index:
                raise ValueError("an allowed relation must use distinct indices")
            if not (0 <= anchor_index < len(normalized)) or not (
                0 <= target_index < len(normalized)
            ):
                raise ValueError("allowed relation index is out of range")
            if not (1 <= power <= max_power):
                raise ValueError("allowed relation power is outside the declared bound")
            if pow(normalized[anchor_index], power, N) != normalized[target_index]:
                raise ValueError("allowed relation does not hold modulo N")
            normalized_allowed[(anchor_index, target_index)] = power

    candidates = _candidate_groups(N, normalized, q, max_power, normalized_allowed)
    dimension = len(normalized)
    if dimension <= exact_partition_limit:
        by_first: dict[int, list[OrbitFusionGroup]] = {i: [] for i in range(dimension)}
        for candidate in candidates:
            for index in candidate.member_indices:
                by_first[index].append(candidate)

        @lru_cache(maxsize=None)
        def solve(remaining: int) -> tuple[int, int, tuple[OrbitFusionGroup, ...]]:
            if remaining == 0:
                return (0, 0, ())
            first = (remaining & -remaining).bit_length() - 1
            best: tuple[int, int, tuple[OrbitFusionGroup, ...]] | None = None
            for candidate in by_first[first]:
                mask = sum(1 << index for index in candidate.member_indices)
                if mask & remaining != mask:
                    continue
                tail_cost, tail_extra, tail = solve(remaining ^ mask)
                proposal = (
                    candidate.selected_canonical_cx + tail_cost,
                    max(candidate.accumulator_width, tail_extra),
                    (candidate, *tail),
                )
                key = (
                    proposal[0],
                    proposal[1],
                    len(proposal[2]),
                    tuple(group.member_indices for group in proposal[2]),
                )
                if best is None:
                    best = proposal
                else:
                    best_key = (
                        best[0],
                        best[1],
                        len(best[2]),
                        tuple(group.member_indices for group in best[2]),
                    )
                    if key < best_key:
                        best = proposal
            if best is None:
                raise AssertionError("singleton candidates must cover every mask")
            return best

        groups = solve((1 << dimension) - 1)[2]
        planner = "exact_set_partition_dp"
    else:
        selected: list[OrbitFusionGroup] = []
        unused = set(range(dimension))
        fused = sorted(
            (candidate for candidate in candidates if candidate.fused),
            key=lambda group: (
                -group.canonical_cx_saved,
                group.accumulator_width,
                group.member_indices,
                group.anchor_index,
            ),
        )
        for candidate in fused:
            if set(candidate.member_indices) <= unused:
                selected.append(candidate)
                unused.difference_update(candidate.member_indices)
        singleton_by_index = {
            group.member_indices[0]: group
            for group in candidates
            if not group.fused
        }
        selected.extend(singleton_by_index[index] for index in sorted(unused))
        groups = tuple(selected)
        planner = "deterministic_savings_first_greedy"

    groups = tuple(sorted(groups, key=lambda group: group.member_indices[0]))
    plan = OrbitFusionPlan(
        N=N,
        bases=normalized,
        exponent_width=q,
        max_power=max_power,
        groups=groups,
        planner=planner,
    )
    if not plan.verify():
        raise AssertionError("internal orbit-fusion certificate failed")
    return plan


def factor_or_fuse(
    family: RootedBaseFamily,
    exponent_width: int,
    *,
    max_power: int = 64,
    exact_partition_limit: int = 12,
) -> FactorOrFuseResult:
    """Return a factor, an ``L0``-certified fusion, or the exact baseline.

    Relation discovery is bounded and incomplete by design.  The method never
    receives known factors or group orders.  When it finds a factor-bearing
    relation, no quantum circuit is needed.  Otherwise the low-level cost
    planner may use only relations classified exactly as ``L0``; if none is
    profitable it returns the original circuit unchanged.
    """

    if not isinstance(family, RootedBaseFamily):
        raise TypeError("factor-or-fuse requires a RootedBaseFamily")
    q = int(exponent_width)
    max_power = int(max_power)
    if q <= 0 or max_power <= 0:
        raise ValueError("exponent_width and max_power must be positive")
    relations = detect_pair_power_relations(family, max_power=max_power)
    return _factor_or_fuse_from_relations(
        family,
        q,
        max_power,
        exact_partition_limit,
        relations,
        witness_policy="least_per_ordered_pair",
    )


def factor_or_fuse_all_witnesses(
    family: RootedBaseFamily,
    exponent_width: int,
    *,
    max_power: int = 64,
    exact_partition_limit: int = 12,
) -> FactorOrFuseResult:
    """Factor-first variant that retains every witness inside the bound.

    The public power walk is the same length as the least-witness scan.  If
    several exponents reach one target, all are root-classified before any
    fusion decision.  This prevents an early ``L0`` witness from hiding a
    later factor-yielding witness.  When every witness is in ``L0``, the least
    exponent for each directed pair is passed to the exact cost planner.
    """

    if not isinstance(family, RootedBaseFamily):
        raise TypeError("factor-or-fuse requires a RootedBaseFamily")
    q = int(exponent_width)
    max_power = int(max_power)
    if q <= 0 or max_power <= 0:
        raise ValueError("exponent_width and max_power must be positive")
    relations = detect_all_pair_power_relations(family, max_power=max_power)
    return _factor_or_fuse_from_relations(
        family,
        q,
        max_power,
        int(exact_partition_limit),
        relations,
        witness_policy="all_within_bound",
    )


def _factor_or_fuse_from_relations(
    family: RootedBaseFamily,
    exponent_width: int,
    max_power: int,
    exact_partition_limit: int,
    relations: tuple[PowerOrbitRelation, ...],
    *,
    witness_policy: str,
) -> FactorOrFuseResult:
    q = int(exponent_width)
    factor_rows = [
        row for row in relations if row.classification.category == "factor_yielding"
    ]
    if factor_rows:
        result = FactorOrFuseResult(
            family=family,
            exponent_width=q,
            max_power=max_power,
            witness_policy=witness_policy,
            relations=relations,
            outcome="classical_factor",
            factor_pair=factor_rows[0].classification.factor_pair,
            plan=None,
            public_power_steps=len(family.pairs) * max_power,
        )
    else:
        allowed: dict[tuple[int, int], int] = {}
        for row in relations:
            if row.classification.category != "L0":
                continue
            key = (row.anchor_index, row.target_index)
            allowed[key] = min(row.power, allowed.get(key, row.power))
        plan = plan_power_orbit_fusion(
            family.N,
            family.bases,
            q,
            max_power=max_power,
            exact_partition_limit=exact_partition_limit,
            allowed_relations=allowed,
        )
        outcome = (
            "l0_orbit_fusion"
            if any(group.fused for group in plan.groups)
            else "baseline_fallback"
        )
        result = FactorOrFuseResult(
            family=family,
            exponent_width=q,
            max_power=max_power,
            witness_policy=witness_policy,
            relations=relations,
            outcome=outcome,
            factor_pair=None,
            plan=plan,
            public_power_steps=len(family.pairs) * max_power,
        )
    if not result.verify():
        raise AssertionError("internal factor-or-fuse certificate failed")
    return result


def factor_or_fuse_record(result: FactorOrFuseResult) -> dict[str, object]:
    """Return a JSON/CSV-friendly summary without any known factor input."""

    if not isinstance(result, FactorOrFuseResult) or not result.verify():
        raise ValueError("a valid FactorOrFuseResult is required")
    plan = result.plan
    return {
        "N": result.family.N,
        "n": result.family.N.bit_length(),
        "dimension": len(result.family.pairs),
        "exponent_width": result.exponent_width,
        "roots": list(result.family.roots),
        "bases": list(result.family.bases),
        "max_power": result.max_power,
        "witness_policy": result.witness_policy,
        "outcome": result.outcome,
        "verified": result.verify(),
        "factor_pair": list(result.factor_pair) if result.factor_pair else None,
        "detected_relation_count": len(result.relations),
        "l0_relation_count": result.l0_relation_count,
        "factor_relation_count": result.factor_relation_count,
        "relations": [
            {
                "anchor_index": row.anchor_index,
                "target_index": row.target_index,
                "power": row.power,
                "vector": list(row.classification.vector),
                "root_product": row.classification.root_product,
                "category": row.classification.category,
                "factor_pair": (
                    list(row.classification.factor_pair)
                    if row.classification.factor_pair
                    else None
                ),
            }
            for row in result.relations
        ],
        "public_power_steps": result.public_power_steps,
        "quantum_circuit_avoided": result.outcome == "classical_factor",
        "baseline_canonical_cx": plan.baseline_canonical_cx if plan else None,
        "selected_canonical_cx": plan.selected_canonical_cx if plan else 0,
        "canonical_cx_saved": plan.canonical_cx_saved if plan else None,
        "canonical_cx_saving_fraction": (
            plan.canonical_cx_saving_fraction if plan else None
        ),
        "extra_qubits": plan.extra_qubits if plan else 0,
        "factor_information_used": False,
        "group_order_used": False,
    }


def orbit_fusion_source_counts(
    plan: OrbitFusionPlan,
    *,
    qft_cutoff: int | None = None,
    measure: bool = True,
) -> GateCounts:
    """Count the complete selected circuit at the repository source level."""

    if not isinstance(plan, OrbitFusionPlan) or not plan.verify():
        raise ValueError("a valid OrbitFusionPlan is required")
    total = Counter({"h": plan.dimension * plan.exponent_width, "x": 1})
    total.update(plan.selected_arithmetic_counts)
    total.update(qft_source_counts(plan.dimension, plan.exponent_width, qft_cutoff))
    if measure:
        total["measure"] += plan.dimension * plan.exponent_width
    return total


def _append_orbit_oracle(
    circuit: QuantumCircuit,
    plan: OrbitFusionPlan,
    x_registers: Sequence[QuantumRegister],
    y: QuantumRegister,
    aux: QuantumRegister,
    accumulator: QuantumRegister | None,
    carry: QuantumRegister | None,
) -> None:
    n = plan.N.bit_length()
    q = plan.exponent_width
    for group in plan.groups:
        if not group.fused:
            index = group.member_indices[0]
            gate = modular_exponentiation_gate(plan.bases[index], plan.N, n, q)
            circuit.append(gate, [*x_registers[index], *y, *aux])
            continue
        if accumulator is None or carry is None:
            raise AssertionError("fused groups require allocated accumulator workspace")
        width = group.accumulator_width
        operations: list[tuple[int, int]] = []
        for index, weight in zip(group.member_indices, group.weights, strict=True):
            for bit in range(q):
                constant = int(weight) << bit
                gate = controlled_constant_adder(constant, width)
                circuit.append(gate, [x_registers[index][bit], *accumulator[:width], carry[0]])
                operations.append((index, bit))
        anchor = plan.bases[group.anchor_index]
        gate = modular_exponentiation_gate(anchor, plan.N, n, width)
        circuit.append(gate, [*accumulator[:width], *y, *aux])
        for index, bit in reversed(operations):
            weight = group.weights[group.member_indices.index(index)]
            constant = int(weight) << bit
            gate = controlled_constant_adder(constant, width).inverse()
            circuit.append(gate, [x_registers[index][bit], *accumulator[:width], carry[0]])


def build_orbit_fused_oracle(plan: OrbitFusionPlan) -> QuantumCircuit:
    """Build only the exact arithmetic oracle, with every workspace exposed."""

    if not isinstance(plan, OrbitFusionPlan) or not plan.verify():
        raise ValueError("a valid OrbitFusionPlan is required")
    q = plan.exponent_width
    n = plan.N.bit_length()
    x_registers = [QuantumRegister(q, name=f"x{i + 1}") for i in range(plan.dimension)]
    y = QuantumRegister(n, name="y")
    aux = QuantumRegister(n + 1, name="aux")
    registers: list = [*x_registers, y, aux]
    accumulator = carry = None
    if plan.max_accumulator_width:
        accumulator = QuantumRegister(plan.max_accumulator_width, name="orbit_sum")
        carry = QuantumRegister(1, name="orbit_carry")
        registers.extend((accumulator, carry))
    circuit = QuantumCircuit(*registers, name=f"OrbitFusionOracle_N_{plan.N}")
    _append_orbit_oracle(circuit, plan, x_registers, y, aux, accumulator, carry)
    return circuit


def build_orbit_fused_circuit(
    plan: OrbitFusionPlan,
    *,
    inverse_qft: bool = True,
    measure: bool = True,
) -> QuantumCircuit:
    """Build the full uniform-state sampler with the optimized exact oracle."""

    if not isinstance(plan, OrbitFusionPlan) or not plan.verify():
        raise ValueError("a valid OrbitFusionPlan is required")
    q = plan.exponent_width
    n = plan.N.bit_length()
    x_registers = [QuantumRegister(q, name=f"x{i + 1}") for i in range(plan.dimension)]
    y = QuantumRegister(n, name="y")
    aux = QuantumRegister(n + 1, name="aux")
    registers: list = [*x_registers, y, aux]
    accumulator = carry = None
    if plan.max_accumulator_width:
        accumulator = QuantumRegister(plan.max_accumulator_width, name="orbit_sum")
        carry = QuantumRegister(1, name="orbit_carry")
        registers.extend((accumulator, carry))
    classical = ClassicalRegister(plan.dimension * q, name="c") if measure else None
    if classical is not None:
        registers.append(classical)
    circuit = QuantumCircuit(*registers, name=f"OrbitFusedRegev_N_{plan.N}")
    for register in x_registers:
        circuit.h(register)
    circuit.x(y[0])
    circuit.barrier(label="orbit_fused_modexp")
    _append_orbit_oracle(circuit, plan, x_registers, y, aux, accumulator, carry)
    circuit.barrier(label="qft")
    for register in x_registers:
        qft = QFTGate(q).inverse() if inverse_qft else QFTGate(q)
        circuit.append(qft, register)
    if classical is not None:
        circuit.barrier(label="measure")
        circuit.measure([qubit for register in x_registers for qubit in register], classical)
    return circuit


def plan_record(plan: OrbitFusionPlan) -> dict[str, object]:
    """Return a JSON/CSV-friendly exact certificate summary."""

    return {
        "N": plan.N,
        "n": plan.N.bit_length(),
        "dimension": plan.dimension,
        "exponent_width": plan.exponent_width,
        "bases": list(plan.bases),
        "max_power": plan.max_power,
        "planner": plan.planner,
        "verified": plan.verify(),
        "fused_group_count": sum(group.fused for group in plan.groups),
        "fused_dimension_count": sum(len(group.member_indices) for group in plan.groups if group.fused),
        "groups": [
            {
                "members": list(group.member_indices),
                "anchor_index": group.anchor_index,
                "anchor": plan.bases[group.anchor_index],
                "weights": list(group.weights),
                "accumulator_width": group.accumulator_width,
                "fused": group.fused,
                "canonical_cx_saved": group.canonical_cx_saved,
            }
            for group in plan.groups
        ],
        "baseline_source_ccx": plan.baseline_arithmetic_counts["ccx"],
        "selected_source_ccx": plan.selected_arithmetic_counts["ccx"],
        "baseline_canonical_cx": plan.baseline_canonical_cx,
        "selected_canonical_cx": plan.selected_canonical_cx,
        "canonical_cx_saved": plan.canonical_cx_saved,
        "canonical_cx_saving_fraction": plan.canonical_cx_saving_fraction,
        "extra_qubits": plan.extra_qubits,
        "max_accumulator_width": plan.max_accumulator_width,
        "baseline_full_width_multiplier_calls": plan.dimension * plan.exponent_width,
        "selected_full_width_multiplier_calls": sum(
            group.accumulator_width if group.fused else plan.exponent_width
            for group in plan.groups
        ),
        "qft_canonical_cx": canonical_cx_count(
            qft_source_counts(plan.dimension, plan.exponent_width)
        ),
        "baseline_total_qubits": plan.dimension * plan.exponent_width + 2 * plan.N.bit_length() + 1,
        "selected_total_qubits": (
            plan.dimension * plan.exponent_width
            + 2 * plan.N.bit_length()
            + 1
            + plan.extra_qubits
        ),
        "log2_lookup_free_search_space": log2(max(1, plan.max_power)),
        "factor_information_used": False,
    }

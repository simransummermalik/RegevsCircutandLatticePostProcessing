"""Core mathematics and experiments for the notebook audit.

Nothing in this module uses a factorization of ``N``.  Some audit routines can
*discover* a factor (for example from a collision of two known square roots).
Those discoveries are returned explicitly as setup leaks and must not be
counted as quantum sample-based factor recovery.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from math import ceil, gcd, log2, prod, sqrt
from time import perf_counter
from typing import Iterable, Sequence

import numpy as np


@dataclass(frozen=True, slots=True)
class RootedBase:
    """One immutable root/base pair for a fixed modulus.

    ``root`` is the specifically selected value :math:`b_i`; ``base`` is not
    independently selectable and must equal the residue of :math:`b_i^2`
    modulo ``N``.  Keeping
    the pair immutable prevents post-processing from silently substituting a
    different modular square root of the same circuit base.
    """

    N: int
    root: int
    base: int

    def __post_init__(self) -> None:
        if self.N <= 2:
            raise ValueError("N must exceed 2")
        if not 0 <= self.root < self.N:
            raise ValueError("root must be the canonical residue in [0, N)")
        if not 0 <= self.base < self.N:
            raise ValueError("base must be the canonical residue in [0, N)")
        if gcd(self.root, self.N) != 1:
            raise ValueError("root must be coprime to N")
        if self.base != self.root * self.root % self.N:
            raise ValueError("base must equal the stored root squared modulo N")

    @classmethod
    def from_root(cls, N: int, root: int) -> "RootedBase":
        canonical_root = int(root) % int(N)
        return cls(
            N=int(N),
            root=canonical_root,
            base=canonical_root * canonical_root % int(N),
        )

    def as_record(self) -> dict[str, int]:
        return {"root": self.root, "base": self.base}


@dataclass(frozen=True, slots=True)
class RootedBaseFamily:
    """An ordered, immutable family of selected ``(b_i, a_i)`` pairs."""

    N: int
    pairs: tuple[RootedBase, ...]

    def __post_init__(self) -> None:
        if not self.pairs:
            raise ValueError("a rooted base family must be nonempty")
        if any(pair.N != self.N for pair in self.pairs):
            raise ValueError("all root/base pairs must use the family modulus")

    @classmethod
    def from_roots(cls, N: int, roots: Sequence[int]) -> "RootedBaseFamily":
        return cls(int(N), tuple(RootedBase.from_root(N, root) for root in roots))

    @property
    def roots(self) -> tuple[int, ...]:
        return tuple(pair.root for pair in self.pairs)

    @property
    def bases(self) -> tuple[int, ...]:
        return tuple(pair.base for pair in self.pairs)

    def as_records(self) -> list[dict[str, int]]:
        return [pair.as_record() for pair in self.pairs]


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    return all(n % p for p in range(3, int(sqrt(n)) + 1, 2))


def notebook_parameters(N: int, mode: str = "cover_2n") -> dict[str, int]:
    n = N.bit_length()
    d = ceil(sqrt(n))
    if mode == "cover_2n":
        nd = ceil(2 * n / d)
    elif mode == "notebook":
        nd = int(n / d + d)
    else:
        raise ValueError("mode must be 'cover_2n' or 'notebook'")
    return {"N": N, "n": n, "d": d, "nd": nd, "M": 1 << nd}


def _prime_stream() -> Iterable[int]:
    p = 2
    while True:
        if is_prime(p):
            yield p
        p += 1


def notebook_squared_prime_bases(N: int, d: int) -> dict:
    """Reproduce the notebook's base generator, including its factor leaks."""
    roots: list[int] = []
    leaks: list[tuple[int, int, int]] = []
    for p in _prime_stream():
        g = gcd(p, N)
        if 1 < g < N:
            leaks.append((p, g, N // g))
            continue
        roots.append(p)
        if len(roots) == d:
            break
    family = RootedBaseFamily.from_roots(N, roots)
    return {
        "family": family,
        "pairs": family.as_records(),
        "roots": list(family.roots),
        "bases": list(family.bases),
        "setup_factor_leaks": leaks,
    }


def deduplicated_squared_prime_bases(N: int, d: int) -> dict:
    """Scan prime roots until ``d`` distinct squared residues are obtained."""
    roots: list[int] = []
    bases: list[int] = []
    rejected: list[dict] = []
    leaks: list[tuple[int, int, int]] = []
    for p in _prime_stream():
        g = gcd(p, N)
        if 1 < g < N:
            leaks.append((p, g, N // g))
            rejected.append({"candidate_root": p, "reason": "gcd_factor"})
            continue
        a = p * p % N
        if a in bases:
            j = bases.index(a)
            collision_gcds = sorted({gcd(p - roots[j], N), gcd(p + roots[j], N)})
            found = [x for x in collision_gcds if 1 < x < N]
            rejected.append(
                {
                    "candidate_root": p,
                    "residue": a,
                    "reason": "duplicate_residue",
                    "collides_with_root": roots[j],
                    "factor_discovered": found[0] if found else None,
                }
            )
            if found:
                leaks.append((p, found[0], N // found[0]))
            continue
        roots.append(p)
        bases.append(a)
        if len(bases) == d:
            break
    family = RootedBaseFamily.from_roots(N, roots)
    return {
        "family": family,
        "pairs": family.as_records(),
        "roots": list(family.roots),
        "bases": list(family.bases),
        "rejected": rejected,
        "setup_factor_leaks": leaks,
    }


def random_coprime_residues(
    N: int, d: int, seed: int, candidate_pool: Sequence[int] | None = None
) -> list[int]:
    """Choose units without silently requiring an exhaustive unit scan.

    Controlled experiments pass a frozen small candidate pool and separately
    record every GCD.  The exhaustive default is retained only for toy use.
    """
    raw_pool = range(2, N) if candidate_pool is None else candidate_pool
    pool = [int(a) % N for a in raw_pool if gcd(int(a), N) == 1]
    if len(pool) < d:
        raise ValueError("candidate pool is too small")
    rng = np.random.default_rng(seed)
    return [int(x) for x in rng.choice(pool, size=d, replace=False)]


def modular_product(N: int, bases: Sequence[int], exponents: Sequence[int]) -> int:
    value = 1
    for a, e in zip(bases, exponents, strict=True):
        value = value * pow(int(a), int(e), N) % N
    return value


def canonical_vectors(d: int, bound: int) -> list[tuple[int, ...]]:
    """One representative of each nonzero pair ``{u,-u}`` in a box."""
    vectors: list[tuple[int, ...]] = []
    for u in product(range(-bound, bound + 1), repeat=d):
        if not any(u):
            continue
        first = next(x for x in u if x)
        if first > 0:
            vectors.append(tuple(int(x) for x in u))
    return vectors


def bounded_relations(N: int, bases: Sequence[int], bound: int) -> list[tuple[int, ...]]:
    return [u for u in canonical_vectors(len(bases), bound) if modular_product(N, bases, u) == 1]


def vector_rank(vectors: Sequence[Sequence[int]], d: int) -> int:
    if not vectors:
        return 0
    return int(np.linalg.matrix_rank(np.asarray(vectors, dtype=float).reshape(-1, d)))


def multiplicative_order(a: int, N: int) -> int:
    """Factor-free trial order computation, intended only for small audit inputs."""
    if gcd(a, N) != 1:
        raise ValueError("multiplicative order requires a unit modulo N")
    x = 1
    for r in range(1, N + 1):
        x = x * a % N
        if x == 1:
            return r
    raise RuntimeError("order was not found within N steps")


def generated_subgroup(N: int, bases: Sequence[int]) -> set[int]:
    """Enumerate the generated subgroup without factoring ``N``."""
    subgroup = {1}
    frontier = [1]
    generators = [int(a) % N for a in bases]
    while frontier:
        x = frontier.pop()
        for a in generators:
            y = x * a % N
            if y not in subgroup:
                subgroup.add(y)
                frontier.append(y)
    return subgroup


def bounded_product_diversity(N: int, bases: Sequence[int], bound: int) -> float:
    values = {
        modular_product(N, bases, u)
        for u in product(range(-bound, bound + 1), repeat=len(bases))
    }
    return len(values) / (2 * bound + 1) ** len(bases)


def pairwise_power_collisions(
    N: int, bases: Sequence[int], relation_bound: int
) -> list[dict]:
    collisions: list[dict] = []
    for i in range(len(bases)):
        for j in range(i + 1, len(bases)):
            for k in range(1, relation_bound + 1):
                left = pow(int(bases[i]), k, N)
                for ell in range(1, relation_bound + 1):
                    if left == pow(int(bases[j]), ell, N):
                        collisions.append({"i": i, "j": j, "k": k, "ell": ell})
    return collisions


def base_diagnostics(N: int, bases: Sequence[int], relation_bound: int = 3) -> dict:
    residues = [int(a) % N for a in bases]
    relations = bounded_relations(N, residues, relation_bound)
    norms = [float(np.linalg.norm(u)) for u in relations]
    subgroup = generated_subgroup(N, residues)
    orders = [multiplicative_order(a, N) for a in residues]
    return {
        "N": N,
        "d": len(residues),
        "bases": residues,
        "unique_residues": len(set(residues)),
        "duplicate_count": len(residues) - len(set(residues)),
        "orders": orders,
        "distinct_order_count": len(set(orders)),
        "subgroup_size": len(subgroup),
        "relation_lattice_determinant": len(subgroup),
        "bounded_product_diversity": bounded_product_diversity(
            N, residues, relation_bound
        ),
        "bounded_relation_count": len(relations),
        "bounded_relation_rank": vector_rank(relations, len(residues)),
        "shortest_relation_norm": min(norms) if norms else None,
        "relations": relations,
        "pairwise_power_collisions": pairwise_power_collisions(
            N, residues, relation_bound
        ),
    }


@dataclass
class BaseSelectionResult:
    selected_roots: list[int]
    selected_bases: list[int]
    selected_pairs: list[dict[str, int]]
    rejected_bases: list[dict]
    rejection_reasons: dict[str, int]
    collision_statistics: dict
    dependency_score: float
    effective_dimension_estimate: int
    effective_dimension_definition: str
    runtime_seconds: float
    scoring_method: str
    seed: int


def select_dependency_aware_bases(
    N: int,
    d: int,
    candidate_pool: Sequence[int],
    relation_bound: int = 2,
    scoring_method: str = "bounded_product_diversity",
    seed: int = 0,
) -> dict:
    """Select roots while scoring their paired squared circuit bases.

    This is the high-priority intervention requested in the prompt.  It is not
    called "independence preserving": all bases in a finite group satisfy
    multiplicative relations, and Regev post-processing needs short relations.

    ``candidate_pool`` contains candidate roots, not already-squared residues.
    Every selected circuit base remains paired with the exact root that
    generated it.  Candidate roots with the same squared residue are rejected;
    any factor revealed by that congruence of squares is reported as a setup
    leak.
    """
    if scoring_method != "bounded_product_diversity":
        raise ValueError("only bounded_product_diversity is implemented")
    start = perf_counter()
    rng = np.random.default_rng(seed)
    rejected: list[dict] = []
    valid: list[RootedBase] = []
    seen_roots: set[int] = set()
    seen_bases: dict[int, RootedBase] = {}
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
        elif root in seen_roots:
            rejected.append(
                {
                    "candidate_root": int(raw),
                    "root": root,
                    "base": root * root % N,
                    "reason": "duplicate_root",
                }
            )
        else:
            seen_roots.add(root)
            pair = RootedBase.from_root(N, root)
            if pair.base in seen_bases:
                previous = seen_bases[pair.base]
                collision_gcds = sorted(
                    {gcd(pair.root - previous.root, N), gcd(pair.root + previous.root, N)}
                )
                found = next((x for x in collision_gcds if 1 < x < N), None)
                rejected.append(
                    {
                        "candidate_root": int(raw),
                        **pair.as_record(),
                        "reason": "duplicate_squared_base",
                        "collides_with_root": previous.root,
                        "factor_discovered": found,
                    }
                )
            else:
                seen_bases[pair.base] = pair
                valid.append(pair)
    if len(valid) < d:
        raise ValueError("not enough distinct coprime squared bases from candidate roots")

    # Random tie-breaking is reproducible and prevents a systematic low-value bias.
    tie_order = {pair.root: float(rng.random()) for pair in valid}
    selected: list[RootedBase] = []
    while len(selected) < d:
        scored = []
        for pair in valid:
            if pair in selected:
                continue
            trial = [item.base for item in selected] + [pair.base]
            score = bounded_product_diversity(N, trial, relation_bound)
            scored.append((score, tie_order[pair.root], pair))
        _, _, winner = max(scored)
        selected.append(winner)

    for pair in valid:
        if pair not in selected:
            rejected.append(
                {
                    "candidate_root": pair.root,
                    **pair.as_record(),
                    "reason": "lower_score",
                }
            )

    family = RootedBaseFamily(N, tuple(selected))
    diagnostic = base_diagnostics(N, family.bases, relation_bound)
    reasons: dict[str, int] = {}
    for row in rejected:
        reasons[row["reason"]] = reasons.get(row["reason"], 0) + 1
    result = BaseSelectionResult(
        selected_roots=list(family.roots),
        selected_bases=list(family.bases),
        selected_pairs=family.as_records(),
        rejected_bases=rejected,
        rejection_reasons=reasons,
        collision_statistics={
            "duplicate_residues": diagnostic["duplicate_count"],
            "pairwise_power_relations": len(diagnostic["pairwise_power_collisions"]),
            "bounded_relations": diagnostic["bounded_relation_count"],
        },
        dependency_score=diagnostic["bounded_product_diversity"],
        effective_dimension_estimate=d - diagnostic["bounded_relation_rank"],
        effective_dimension_definition=(
            "d minus the real rank of relations found in the stated bounded box; "
            "not group-generator rank or global multiplicative independence"
        ),
        runtime_seconds=perf_counter() - start,
        scoring_method=scoring_method,
        seed=seed,
    )
    serializable = asdict(result)
    # The immutable object is the factor-extraction API.  The parallel lists
    # remain only as explicit reporting fields for the originally requested
    # selector schema.
    return {**serializable, "family": family}


def classify_square_relation(
    family: RootedBaseFamily, relation: Sequence[int]
) -> dict:
    """Classify a candidate using the roots permanently paired to its bases.

    ``L`` is the kernel of the squared-base map and ``L0`` is the subset for
    which the stored-root product is ``+1`` or ``-1`` modulo ``N``.  A vector
    outside ``L`` is rejected before any GCD is attempted.  No modular square
    root is computed here, and callers cannot provide roots independently of
    the circuit bases.
    """
    if not isinstance(family, RootedBaseFamily):
        raise TypeError("classification requires a RootedBaseFamily")
    if len(relation) != len(family.pairs):
        raise ValueError("relation dimension must match the rooted base family")
    relation = tuple(int(value) for value in relation)
    base_product = modular_product(family.N, family.bases, relation)
    if base_product != 1:
        return {
            "base_product": base_product,
            "root_product": None,
            "in_L": False,
            "in_L0": False,
            "class": "not_in_L",
            "factor": None,
            "factors": [],
        }

    beta = modular_product(family.N, family.roots, relation)
    if beta * beta % family.N != 1:
        raise AssertionError("paired roots violate beta^2 = 1 for a relation in L")
    if beta in (1, family.N - 1):
        return {
            "base_product": base_product,
            "root_product": beta,
            "in_L": True,
            "in_L0": True,
            "class": "L0",
            "factor": None,
            "factors": [],
        }
    proper_factors = []
    for candidate in (gcd(beta - 1, family.N), gcd(beta + 1, family.N)):
        if 1 < candidate < family.N and candidate not in proper_factors:
            proper_factors.append(candidate)
    return {
        "base_product": base_product,
        "root_product": beta,
        "in_L": True,
        "in_L0": False,
        "class": "L_minus_L0",
        "factor": proper_factors[0] if proper_factors else None,
        "factors": proper_factors,
    }


def extract_factor_from_relation(
    family: RootedBaseFamily, relation: Sequence[int]
) -> int | None:
    """Return a proper factor only from ``L \\ L0`` using stored roots."""
    return classify_square_relation(family, relation)["factor"]


def audit_square_base_family(
    family: RootedBaseFamily, relation_bound: int = 3
) -> dict:
    if not isinstance(family, RootedBaseFamily):
        raise TypeError("audit requires a RootedBaseFamily")
    relations = bounded_relations(family.N, family.bases, relation_bound)
    classified = []
    leaked_factors: set[int] = set()
    for u in relations:
        row = {"relation": u, **classify_square_relation(family, u)}
        classified.append(row)
        if row["factor"] is not None:
            leaked_factors.add(int(row["factor"]))
    return {
        "N": family.N,
        "pairs": family.as_records(),
        "roots": list(family.roots),
        "bases": list(family.bases),
        "relation_bound": relation_bound,
        "relations": classified,
        "L0_count": sum(row["class"] == "L0" for row in classified),
        "L_minus_L0_count": sum(row["class"] == "L_minus_L0" for row in classified),
        "setup_factor_leaks": sorted(leaked_factors),
    }


def exact_uniform_fourier_distribution(
    N: int, bases: Sequence[int], M: int, max_difference_points: int = 2_500_000
) -> tuple[np.ndarray, np.ndarray]:
    """Exact output law of the notebook's uniform-box sampler.

    For ``L = {z : prod_i a_i**z_i == 1 (mod N)}``, define the folded
    triangular relation kernel

        K[r] = sum_{z in L, z=r (mod M), |z_i|<M} prod_i (M-|z_i|).

    The measured probability is ``FFT(K) / M**(2*d)``.  This evaluates the
    implemented circuit distribution without simulating arithmetic gates.
    """
    bases = [int(a) % N for a in bases]
    d = len(bases)
    width = 2 * M - 1
    difference_points = width**d
    if difference_points > max_difference_points:
        raise ValueError(
            f"difference box has {difference_points} points; "
            f"limit is {max_difference_points}"
        )
    z_values = np.arange(-(M - 1), M, dtype=np.int64)
    shape = (width,) * d
    residues = np.ones(shape, dtype=np.int64)
    weights = np.ones(shape, dtype=np.int64)
    for axis, a in enumerate(bases):
        powers = np.asarray([pow(a, int(z), N) for z in z_values], dtype=np.int64)
        triangular = M - np.abs(z_values)
        axis_shape = [1] * d
        axis_shape[axis] = width
        residues = residues * powers.reshape(axis_shape) % N
        weights *= triangular.reshape(axis_shape)

    locations = np.argwhere(residues == 1)
    signed = locations - (M - 1)
    folded = signed % M
    relation_weights = weights[tuple(locations.T)]
    kernel = np.zeros((M,) * d, dtype=np.float64)
    np.add.at(kernel, tuple(folded.T), relation_weights)
    probabilities = np.fft.fftn(kernel).real / float(M ** (2 * d))
    probabilities[np.abs(probabilities) < 1e-15] = 0.0
    if probabilities.min() < -1e-10:
        raise ArithmeticError("Fourier probabilities contain a material negative value")
    probabilities = np.maximum(probabilities, 0.0)
    probabilities /= probabilities.sum()
    return probabilities, kernel


def relation_signal_energy(kernel: np.ndarray) -> float:
    """The exact chi-square divergence from uniform, by Parseval's identity."""
    M = kernel.shape[0]
    d = kernel.ndim
    origin = (0,) * d
    return float((np.sum(kernel * kernel) - kernel[origin] ** 2) / M ** (2 * d))


def _entropy(probabilities: np.ndarray) -> float:
    p = probabilities[probabilities > 0]
    return float(-np.sum(p * np.log2(p)))


def distribution_metrics(probabilities: np.ndarray, kernel: np.ndarray | None = None) -> dict:
    M = probabilities.shape[0]
    d = probabilities.ndim
    joint_entropy = _entropy(probabilities)
    marginal_entropies = []
    marginals = []
    for axis in range(d):
        sum_axes = tuple(i for i in range(d) if i != axis)
        marginal = probabilities.sum(axis=sum_axes)
        marginals.append(marginal)
        marginal_entropies.append(_entropy(marginal))
    pairwise_mi = []
    for i in range(d):
        for j in range(i + 1, d):
            sum_axes = tuple(k for k in range(d) if k not in (i, j))
            pair = probabilities.sum(axis=sum_axes) if sum_axes else probabilities
            pairwise_mi.append(marginal_entropies[i] + marginal_entropies[j] - _entropy(pair))

    coords = np.indices(probabilities.shape, dtype=float).reshape(d, -1).T
    p_flat = probabilities.ravel()
    mean = np.sum(coords * p_flat[:, None], axis=0)
    centered = coords - mean
    covariance = (centered * p_flat[:, None]).T @ centered
    eigenvalues = np.maximum(np.linalg.eigvalsh(covariance), 0.0)
    if eigenvalues.sum() > 0:
        normalized = eigenvalues / eigenvalues.sum()
        covariance_effective_rank = float(np.exp(-np.sum(normalized[normalized > 0] * np.log(normalized[normalized > 0]))))
    else:
        covariance_effective_rank = 0.0

    uniform = 1.0 / probabilities.size
    chi_square = float(np.sum((probabilities - uniform) ** 2 / uniform))
    result = {
        "joint_entropy_bits": joint_entropy,
        "max_entropy_bits": d * log2(M),
        "entropy_deficit_bits": d * log2(M) - joint_entropy,
        "marginal_entropies_bits": marginal_entropies,
        "total_correlation_bits": float(sum(marginal_entropies) - joint_entropy),
        "mean_pairwise_mutual_information_bits": float(np.mean(pairwise_mi)) if pairwise_mi else 0.0,
        "covariance_rank": int(np.linalg.matrix_rank(covariance, tol=1e-10)),
        "covariance_effective_rank": covariance_effective_rank,
        "support_size": int(np.count_nonzero(probabilities > 1e-14)),
        "chi_square_from_uniform": chi_square,
    }
    if kernel is not None:
        result["relation_signal_energy"] = relation_signal_energy(kernel)
        result["parseval_absolute_error"] = abs(
            chi_square - result["relation_signal_energy"]
        )
    return result


def sample_distribution(
    probabilities: np.ndarray, shots: int, seed: int
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    flat = rng.choice(probabilities.size, size=shots, p=probabilities.ravel())
    return np.column_stack(np.unravel_index(flat, probabilities.shape)).astype(int)


def sample_metrics(samples: np.ndarray, M: int) -> dict:
    """Finite-shot analogues of the effective-dimension summary metrics."""
    samples = np.asarray(samples, dtype=int)
    shots, d = samples.shape

    def empirical_entropy(columns: Sequence[int]) -> float:
        _, counts = np.unique(samples[:, columns], axis=0, return_counts=True)
        p = counts / shots
        return float(-np.sum(p * np.log2(p)))

    joint = empirical_entropy(list(range(d)))
    marginal = [empirical_entropy([i]) for i in range(d)]
    pairwise = [
        marginal[i] + marginal[j] - empirical_entropy([i, j])
        for i in range(d)
        for j in range(i + 1, d)
    ]
    covariance = np.atleast_2d(np.cov(samples, rowvar=False, ddof=1))
    eigenvalues = np.maximum(np.linalg.eigvalsh(covariance), 0.0)
    if eigenvalues.sum() > 0:
        normalized = eigenvalues / eigenvalues.sum()
        positive = normalized[normalized > 0]
        effective_rank = float(np.exp(-np.sum(positive * np.log(positive))))
    else:
        effective_rank = 0.0
    return {
        "joint_entropy_bits": joint,
        "entropy_deficit_from_empirical_max_bits": min(log2(shots), d * log2(M)) - joint,
        "total_correlation_bits": float(sum(marginal) - joint),
        "mean_pairwise_mutual_information_bits": float(np.mean(pairwise)) if pairwise else 0.0,
        "covariance_rank": int(np.linalg.matrix_rank(covariance, tol=1e-10)),
        "covariance_effective_rank": effective_rank,
        "observed_support_size": int(len(np.unique(samples, axis=0))),
    }


def fourier_relation_diagnostic(
    samples: np.ndarray, M: int, relation_bound: int, alpha: float = 0.05
) -> dict:
    """Estimate bounded relation signal from multidimensional samples only.

    For each candidate ``u``, the circular moment estimates
    ``E[cos(2*pi*<k,u>/M)] = K[u mod M]/M**d``.  A simultaneous Hoeffding
    threshold is used as a conservative, factor-free signal flag.
    """
    samples = np.asarray(samples, dtype=int)
    shots, d = samples.shape
    candidates = canonical_vectors(d, relation_bound)
    moments = []
    for u in candidates:
        phase = 2 * np.pi * (samples @ np.asarray(u, dtype=int)) / M
        moments.append(float(np.mean(np.cos(phase))))
    count = max(len(candidates), 1)
    threshold = sqrt(2 * np.log(2 * count / alpha) / shots)
    selected = [u for u, moment in zip(candidates, moments, strict=True) if moment > threshold]
    # Bias correction for |sample mean of unit phasors|^2 under no signal.
    complex_energy = []
    for u in candidates:
        phase = 2 * np.pi * (samples @ np.asarray(u, dtype=int)) / M
        c = np.mean(np.exp(1j * phase))
        complex_energy.append(max(0.0, (shots * abs(c) ** 2 - 1) / (shots - 1)))
    return {
        "relation_bound": relation_bound,
        "candidate_count": len(candidates),
        "hoeffding_threshold": threshold,
        "vectors": candidates,
        "cosine_moments": moments,
        "selected_vectors": selected,
        "selected_rank": vector_rank(selected, d),
        "bounded_spectral_dimension": d - vector_rank(selected, d),
        "bias_corrected_signal_energy": float(sum(complex_energy)),
    }


def relation_recovery_trial(
    N: int,
    bases: Sequence[int],
    samples: np.ndarray,
    M: int,
    relation_bound: int,
    rooted_family: RootedBaseFamily | None = None,
) -> dict:
    """Bounded-search endpoint; this is a diagnostic, not scalable LLL."""
    bases = tuple(int(a) % N for a in bases)
    if rooted_family is not None:
        if rooted_family.N != N or rooted_family.bases != bases:
            raise ValueError("rooted family must exactly match N and the circuit bases")
    samples = np.asarray(samples, dtype=int)
    candidates = canonical_vectors(len(bases), relation_bound)
    scored = []
    for u in candidates:
        phase = 2 * np.pi * (samples @ np.asarray(u, dtype=int)) / M
        score = float(np.mean(np.cos(phase)))
        is_relation = modular_product(N, bases, u) == 1
        row = {"vector": u, "score": score, "is_relation": is_relation}
        if rooted_family is not None and is_relation:
            row.update(classify_square_relation(rooted_family, u))
        scored.append(row)
    scored.sort(key=lambda row: (-row["score"], np.linalg.norm(row["vector"]), row["vector"]))
    best = scored[0]
    relation_scores = [row["score"] for row in scored if row["is_relation"]]
    nonrelation_scores = [row["score"] for row in scored if not row["is_relation"]]
    return {
        "top_vector": best["vector"],
        "top_score": best["score"],
        "top_is_relation": best["is_relation"],
        "top_relation_class": best.get("class"),
        "top_factor": best.get("factor"),
        "relation_exists_in_box": bool(relation_scores),
        "relation_separation": (
            max(relation_scores) - max(nonrelation_scores)
            if relation_scores and nonrelation_scores
            else None
        ),
    }


def bitstring_to_vector(bitstring: str, d: int, nd: int) -> tuple[int, ...]:
    raw = bitstring.replace(" ", "")
    if len(raw) != d * nd or set(raw) - {"0", "1"}:
        raise ValueError("bitstring does not match d * nd classical bits")
    little_endian = raw[::-1]
    return tuple(
        int(little_endian[i * nd : (i + 1) * nd][::-1], 2) for i in range(d)
    )


def logical_resources(N: int, d: int, M: int) -> dict:
    nd = int(log2(M))
    if 1 << nd != M:
        raise ValueError("M must be a power of two")
    n = N.bit_length()
    return {
        "n": n,
        "d": d,
        "nd": nd,
        "M": M,
        "x_qubits": d * nd,
        "work_qubits": 2 * n + 1,
        "total_qubits": d * nd + 2 * n + 1,
        "modular_exponentiation_blocks": d,
        "controlled_modular_multiplication_blocks": d * nd,
        "qft_blocks": d,
    }

"""Factor-blind relation-lattice construction for controlled sample generation.

The routines here are *oracle-side experiment generators*, never recovery
inputs.  They enumerate the image of the modular-product homomorphism using
only multiplication modulo ``N`` and derive a Hermite basis for its kernel.
No factorization or group order is supplied.  The resulting basis is used to
draw uniform points of ``L*/Z^d`` for the synthetic theoretical model C.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import product
from math import ceil, log2, sqrt
from typing import Sequence

import numpy as np

from .core import RootedBaseFamily, modular_product


@dataclass(frozen=True)
class RelationLatticeOracle:
    """Ground truth held exclusively by the synthetic-data generator."""

    column_hnf: tuple[tuple[int, ...], ...]
    determinant: int
    image_size: int
    enumerated_image: tuple[int, ...]
    construction: str


@dataclass(frozen=True)
class SyntheticDualBatch:
    samples: tuple[tuple[int, ...], ...]
    modulus: int
    scale: int
    noise_bound: float
    maximum_realized_torus_error: float
    sample_count: int
    relation_norm_bound_T: int
    theorem_sufficient_inequality: bool
    oracle: RelationLatticeOracle


def exact_relation_lattice_hnf(
    N: int, bases: Sequence[int]
) -> RelationLatticeOracle:
    """Return a column-HNF basis of ``ker(z -> prod a_i^z_i)``.

    A breadth-first spanning tree of the generated subgroup assigns an integer
    representative to each image element.  Every non-tree Cayley edge gives a
    kernel relation.  Those edge relations generate the full kernel; column
    Hermite normal form reduces them to a square basis.  Its determinant is
    checked against the enumerated image size by the first isomorphism theorem.
    """
    bases = tuple(int(a) % N for a in bases)
    if not bases:
        raise ValueError("bases must be nonempty")
    d = len(bases)
    zero = (0,) * d
    representatives: dict[int, tuple[int, ...]] = {1: zero}
    frontier: deque[int] = deque([1])
    relations: list[tuple[int, ...]] = []
    while frontier:
        residue = frontier.popleft()
        representative = representatives[residue]
        for coordinate, base in enumerate(bases):
            advanced = list(representative)
            advanced[coordinate] += 1
            advanced_tuple = tuple(advanced)
            target = residue * base % N
            if target not in representatives:
                representatives[target] = advanced_tuple
                frontier.append(target)
            else:
                relation = tuple(
                    advanced_tuple[j] - representatives[target][j]
                    for j in range(d)
                )
                if any(relation):
                    if modular_product(N, bases, relation) != 1:
                        raise ArithmeticError("Cayley edge did not produce a kernel relation")
                    relations.append(relation)

    try:
        from sympy import Matrix
        from sympy.matrices.normalforms import hermite_normal_form
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("SymPy is required for exact Hermite normal form") from exc
    relation_columns = Matrix(relations).T
    if relation_columns.rank() != d:
        raise ArithmeticError("enumerated kernel relations did not have full rank")
    hnf = hermite_normal_form(relation_columns)
    if hnf.shape != (d, d):
        raise ArithmeticError("kernel Hermite normal form was not square")
    determinant = abs(int(hnf.det()))
    image_size = len(representatives)
    if determinant != image_size:
        raise ArithmeticError(
            f"kernel determinant {determinant} != image size {image_size}"
        )
    return RelationLatticeOracle(
        column_hnf=tuple(tuple(int(value) for value in row) for row in hnf.tolist()),
        determinant=determinant,
        image_size=image_size,
        enumerated_image=tuple(sorted(representatives)),
        construction="factor-blind Cayley enumeration followed by column HNF",
    )


def _uniform_dual_coset(
    oracle: RelationLatticeOracle, rng: np.random.Generator
) -> np.ndarray:
    """Draw uniformly from ``L*/Z^d`` using triangular HNF representatives."""
    H = np.asarray(oracle.column_hnf, dtype=float)
    diagonal = np.diag(H).astype(int)
    if np.any(diagonal <= 0) or int(np.prod(diagonal)) != oracle.determinant:
        raise ArithmeticError("unexpected Hermite normal form diagonal")
    q = np.asarray([rng.integers(0, value) for value in diagonal], dtype=float)
    # L = H Z^d, so L* = H^{-T} Z^d.
    return np.mod(np.linalg.solve(H.T, q), 1.0)


def _theorem_scale(N: int, d: int, sample_count: int, T: int, safety: float) -> int:
    if safety <= 1:
        raise ValueError("safety must exceed one")
    lattice_dimension = d + sample_count
    lhs = (
        sqrt(lattice_dimension)
        * 2 ** (lattice_dimension / 2)
        * sqrt(sample_count + 1)
        * T
    )
    # Regev's sufficient inequality with det(L) <= N:
    # lhs < S * (4N)^(-1/m) / 6.
    return ceil(safety * 6 * lhs * (4 * N) ** (1 / sample_count))


def _smallest_power_of_two_at_least(value: float) -> int:
    return 1 << max(1, ceil(log2(value)))


def synthetic_noisy_dual_samples(
    family: RootedBaseFamily,
    *,
    seed: int,
    sample_count: int | None = None,
    relation_norm_bound_T: int | None = None,
    safety: float = 2.0,
    oracle: RelationLatticeOracle | None = None,
) -> SyntheticDualBatch:
    """Generate model-C samples satisfying Regev's bounded-noise premise.

    The oracle draws ``v`` uniformly from ``L*/Z^d`` and adds a random vector
    of norm at most ``delta/2``.  It then rounds to a power-of-two grid chosen
    so quantization contributes at most ``delta/4``.  Hence every returned
    grid sample is within ``3 delta/4 < delta`` of its generating dual coset.

    The recovery algorithm receives only ``samples``, ``modulus``, and
    ``scale=1/delta``.  The oracle basis and image are returned solely for
    auditing and must not be passed to reconstruction.
    """
    d = len(family.pairs)
    m = d + 4 if sample_count is None else int(sample_count)
    if m < d + 4:
        raise ValueError("sample_count must be at least d + 4")
    if relation_norm_bound_T is None:
        n = family.N.bit_length()
        T = ceil(sqrt(d) * 2 ** (n / d))
    else:
        T = int(relation_norm_bound_T)
    if T <= 0:
        raise ValueError("relation_norm_bound_T must be positive")

    if oracle is None:
        oracle = exact_relation_lattice_hnf(family.N, family.bases)
    else:
        H = np.asarray(oracle.column_hnf, dtype=int)
        if H.shape != (d, d):
            raise ValueError("oracle dimension does not match the rooted family")
        if any(modular_product(family.N, family.bases, column) != 1 for column in H.T):
            raise ValueError("oracle basis is not contained in this family's L")
        if oracle.determinant != oracle.image_size:
            raise ValueError("oracle determinant/image-size certificate is inconsistent")
    scale = _theorem_scale(family.N, d, m, T, safety)
    delta = 1.0 / scale
    modulus = _smallest_power_of_two_at_least(2 * sqrt(d) * scale)
    rng = np.random.default_rng(seed)
    rows: list[tuple[int, ...]] = []
    realized_errors: list[float] = []
    for _ in range(m):
        dual = _uniform_dual_coset(oracle, rng)
        direction = rng.normal(size=d)
        norm = float(np.linalg.norm(direction))
        if norm == 0:  # probability zero, retained for total correctness.
            direction[0] = 1.0
            norm = 1.0
        radius = (float(rng.random()) ** (1 / d)) * (delta / 2)
        noisy = np.mod(dual + direction / norm * radius, 1.0)
        integers = np.rint(modulus * noisy).astype(np.int64) % modulus
        quantized = integers.astype(float) / modulus
        torus_difference = np.mod(quantized - dual + 0.5, 1.0) - 0.5
        error = float(np.linalg.norm(torus_difference))
        if not error < delta:
            raise ArithmeticError("quantized synthetic sample violated noise bound")
        realized_errors.append(error)
        rows.append(tuple(int(value) for value in integers))

    lattice_dimension = d + m
    lhs = sqrt(lattice_dimension) * 2 ** (lattice_dimension / 2) * sqrt(m + 1) * T
    rhs = scale * (4 * family.N) ** (-1 / m) / 6
    return SyntheticDualBatch(
        samples=tuple(rows),
        modulus=modulus,
        scale=scale,
        noise_bound=delta,
        maximum_realized_torus_error=max(realized_errors),
        sample_count=m,
        relation_norm_bound_T=T,
        theorem_sufficient_inequality=bool(lhs < rhs),
        oracle=oracle,
    )

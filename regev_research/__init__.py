"""Reproducible diagnostics for the supplied Regev-style factoring notebook."""

from .core import (
    audit_square_base_family,
    base_diagnostics,
    bitstring_to_vector,
    exact_uniform_fourier_distribution,
    extract_factor_from_relation,
    fourier_relation_diagnostic,
    notebook_squared_prime_bases,
    relation_recovery_trial,
    RootedBase,
    RootedBaseFamily,
    select_dependency_aware_bases,
)
from .lattice import (
    build_augmented_lattice,
    claim_5_1_prefix,
    lll_reduce_augmented_lattice,
    regev_lattice_postprocess,
)
from .quotient import (
    build_l0_quotient,
    classify_quotient_candidate,
    factor_yielding_quotient_gap,
)

__all__ = [
    "audit_square_base_family",
    "base_diagnostics",
    "bitstring_to_vector",
    "exact_uniform_fourier_distribution",
    "extract_factor_from_relation",
    "fourier_relation_diagnostic",
    "notebook_squared_prime_bases",
    "relation_recovery_trial",
    "RootedBase",
    "RootedBaseFamily",
    "select_dependency_aware_bases",
    "build_augmented_lattice",
    "claim_5_1_prefix",
    "lll_reduce_augmented_lattice",
    "regev_lattice_postprocess",
    "build_l0_quotient",
    "classify_quotient_candidate",
    "factor_yielding_quotient_gap",
]

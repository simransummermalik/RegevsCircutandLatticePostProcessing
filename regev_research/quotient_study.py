"""Serial, reproducible runner for the frozen quotient-recovery holdout.

Importing this module does not execute the holdout.  The execution entry point
is :func:`run_heldout_quotient_study`, which writes a pre-run configuration and
factor manifest, runs factor-blind cells using only ``N``, and creates a final
completion marker only after all raw and summary outputs have been replaced.

Each ``(N, model, replicate)`` cell generates exactly one eleven-row batch.
All fixed-prefix and sequential non-random methods see the nested prefixes
``7,8,9,10,11`` in the same source-row order.  Model C is generated once at
``m=11``; its theorem-derived grid modulus ``D`` and scale ``S`` are reused for
every prefix.  Known manifest factors never enter family selection, sampling,
recovery, scoring, tuning, or bootstrap code.
"""

from __future__ import annotations

import csv
import hashlib
import importlib
import importlib.metadata
import json
import platform
import sys
from dataclasses import asdict, dataclass, fields, is_dataclass
from fractions import Fraction
from functools import lru_cache
from math import ceil, sqrt
from pathlib import Path
from time import perf_counter
from typing import Callable, Iterable, Mapping, Sequence

import numpy as np

from .core import (
    RootedBaseFamily,
    bounded_product_diversity,
    classify_square_relation,
    distribution_metrics,
    sample_metrics,
)
from .dual import exact_relation_lattice_hnf
from .lattice import regev_lattice_postprocess
from .quotient_experiments import (
    CIRCUIT_SURROGATE_MODEL,
    DEVELOPMENT_SEMIPRIMES,
    FINITE_GAUSSIAN_MODEL,
    FROZEN_QUOTIENT_EXPERIMENT,
    HELDOUT_SEMIPRIMES,
    QUOTIENT_MODEL_LABELS,
    THEOREM_NOISY_DUAL_MODEL,
    UNIFORM_HARD_BOX_MODEL,
    FrozenSampleBatch,
    QuotientExperimentFreeze,
    deterministic_model_seed,
    deterministic_small_prime_family,
    exact_finite_discrete_gaussian_model,
    exact_uniform_hard_box_model,
    sample_circuit_derived_readout_corruption_surrogate,
    sample_exact_finite_discrete_gaussian,
    sample_exact_uniform_hard_box,
    sample_theorem_consistent_noisy_dual,
)
from .quotient_metrics import (
    bounded_base_lambda_metrics,
    bounded_sample_augmented_quotient_gap,
)
from .quotient_recovery import (
    RecoveryCandidate,
    RecoveryResources,
    RecoveryResult,
    bkz_or_deterministic_surrogate_baseline,
    exact_augmented_basis_deflation_recovery,
    exact_quotient_deduplicated_recovery,
    sequential_ldar_recovery,
    short_combination_recovery,
)


STANDARD_REGEV_LLL = "standard_regev_LLL_basis_endpoint"
COMMON_EXACT_NORM_ENUMERATION = "common_exact_norm_LLL_bounded_enumeration"
VERIFIED_BKZ_ENUMERATION = "verified_fpylll_BKZ_same_enumeration"
EXACT_AUGMENTED_ROW_DEFLATION = "exact_augmented_row_deflation"
COMPLETE_SEQUENTIAL_LDAR = "complete_sequential_LDAR"
ADAPTIVE_SAMPLING_NO_DEFLATION = "adaptive_sampling_without_deflation"
ROOT_BLIND_POSTHOC = "root_blind_search_posthoc_roots"
QUOTIENT_GAP_SCORING_ONLY = "quotient_gap_scoring_only"
RANDOM_GENUINE_EXTRA_SAMPLES = "random_genuine_extra_sample_acquisition"
RV_STRUCTURED_COMPARATOR = "RV_structured_finite_comparator"

PRIMARY_METHODS = (
    STANDARD_REGEV_LLL,
    COMMON_EXACT_NORM_ENUMERATION,
    VERIFIED_BKZ_ENUMERATION,
    EXACT_AUGMENTED_ROW_DEFLATION,
    COMPLETE_SEQUENTIAL_LDAR,
    ADAPTIVE_SAMPLING_NO_DEFLATION,
    ROOT_BLIND_POSTHOC,
    QUOTIENT_GAP_SCORING_ONLY,
    RANDOM_GENUINE_EXTRA_SAMPLES,
)

ABLATION_LABELS = {
    STANDARD_REGEV_LLL: "baseline_standard_claim_5_1_LLL_rows_only",
    COMMON_EXACT_NORM_ENUMERATION: "A_short_combinations_no_deflation",
    VERIFIED_BKZ_ENUMERATION: "compute_matched_stronger_reduction",
    EXACT_AUGMENTED_ROW_DEFLATION: "B_exact_augmented_free_row_deletion",
    COMPLETE_SEQUENTIAL_LDAR: "complete_A_plus_B_plus_C_plus_new_samples",
    ADAPTIVE_SAMPLING_NO_DEFLATION: "remove_B_and_C_keep_nested_A",
    ROOT_BLIND_POSTHOC: "remove_roots_during_search_posthoc_evaluation_only",
    QUOTIENT_GAP_SCORING_ONLY: "score_only_identical_recovery_no_deflation",
    RANDOM_GENUINE_EXTRA_SAMPLES: "replace_natural_acquisition_by_random_permutation",
    RV_STRUCTURED_COMPARATOR: "finite_RV_structured_comparator_not_theorem_backed",
}

BatchFactory = Callable[
    [RootedBaseFamily, str, int, QuotientExperimentFreeze], FrozenSampleBatch
]


@dataclass(frozen=True, slots=True)
class StudyOutputs:
    trial_rows: tuple[dict, ...]
    per_n_rows: tuple[dict, ...]
    resource_rows: tuple[dict, ...]
    paired_comparisons: tuple[dict, ...]


def _jsonable(value):
    if isinstance(value, Fraction):
        return f"{value.numerator}/{value.denominator}"
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if is_dataclass(value):
        return {field.name: _jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    return value


def _csv_value(value):
    converted = _jsonable(value)
    if isinstance(converted, (dict, list)):
        return json.dumps(converted, sort_keys=True, separators=(",", ":"))
    return converted


def write_json_atomic(path: Path, value) -> None:
    """Replace a JSON file only after its complete temporary file is written."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(_jsonable(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_csv_atomic(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    """Replace a CSV only after its complete temporary file is written."""

    if not rows:
        raise ValueError(f"refusing to write empty CSV {path}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = sorted({key for row in rows for key in row})
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in columns})
    temporary.replace(path)


def _source_sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _dependency_versions() -> dict[str, str | None]:
    result = {"python": platform.python_version()}
    for package in ("numpy", "scipy", "sympy", "fpylll", "qiskit", "qiskit-aer"):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = None
    return result


def study_configuration(
    freeze: QuotientExperimentFreeze = FROZEN_QUOTIENT_EXPERIMENT,
) -> dict:
    """Return the pre-run configuration; it never claims execution completed."""

    package_dir = Path(__file__).resolve().parent
    source_names = {
        "quotient_study": package_dir / "quotient_study.py",
        "quotient_recovery": package_dir / "quotient_recovery.py",
        "quotient_metrics": package_dir / "quotient_metrics.py",
        "quotient_experiments": package_dir / "quotient_experiments.py",
        "rv_filter": package_dir / "rv_filter.py",
    }
    return {
        "status": "configuration written before held-out trial loop",
        "heldout_executed": False,
        "freeze": _jsonable(freeze),
        "development_manifest": [_jsonable(case) for case in DEVELOPMENT_SEMIPRIMES],
        "heldout_manifest": [_jsonable(case) for case in HELDOUT_SEMIPRIMES],
        "methods": list(PRIMARY_METHODS),
        "optional_method": RV_STRUCTURED_COMPARATOR,
        "ablation_labels": ABLATION_LABELS,
        "source_sha256": {
            name: _source_sha256(path) for name, path in source_names.items()
        },
        "dependency_versions": _dependency_versions(),
        "command_python": sys.executable,
        "nested_batch_rule": (
            "one m=11 batch per N/model/replicate; immutable source-order prefixes 7..11"
        ),
        "factor_firewall": (
            "trial functions receive N only; manifest p,q are used only after a trial "
            "to validate a returned factor pair and are written separately"
        ),
    }


def write_factor_manifest(
    output_path: Path,
    cases: Sequence = HELDOUT_SEMIPRIMES,
) -> None:
    write_json_atomic(
        output_path,
        {
            "scope": "posthoc product validation only; never recovery input",
            "cases": [_jsonable(case) for case in cases],
        },
    )


def generate_full_frozen_batch(
    family: RootedBaseFamily,
    model_label: str,
    seed: int,
    freeze: QuotientExperimentFreeze = FROZEN_QUOTIENT_EXPERIMENT,
) -> FrozenSampleBatch:
    """Generate exactly one full frozen batch; callers take nested prefixes."""

    full_count = max(freeze.sample_counts)
    if model_label == UNIFORM_HARD_BOX_MODEL:
        batch = sample_exact_uniform_hard_box(family, full_count, seed, freeze)
    elif model_label == FINITE_GAUSSIAN_MODEL:
        batch = sample_exact_finite_discrete_gaussian(family, full_count, seed, freeze)
    elif model_label == THEOREM_NOISY_DUAL_MODEL:
        batch = sample_theorem_consistent_noisy_dual(family, full_count, seed, freeze)
    elif model_label == CIRCUIT_SURROGATE_MODEL:
        batch = sample_circuit_derived_readout_corruption_surrogate(
            family, full_count, seed, freeze
        )
    else:
        raise ValueError("unknown frozen quotient model")
    if batch.sample_count != full_count or len(batch.samples) != full_count:
        raise ArithmeticError("sampler did not return the one frozen full batch")
    return batch


def nested_prefixes(
    batch: FrozenSampleBatch,
    sample_counts: Sequence[int],
) -> dict[int, tuple[tuple[int, ...], ...]]:
    """Return source-order prefixes without drawing or shuffling any row."""

    counts = tuple(int(value) for value in sample_counts)
    if not counts or tuple(sorted(counts)) != counts:
        raise ValueError("sample_counts must be nonempty and increasing")
    if counts[-1] > len(batch.samples):
        raise ValueError("a prefix exceeds the generated full batch")
    return {count: tuple(batch.samples[:count]) for count in counts}


def factor_blind_relation_bound(N: int, dimension: int) -> int:
    """Frozen Claim-5.1 relation scale; depends only on ``N`` and ``d``."""

    return ceil(sqrt(dimension) * 2 ** (int(N).bit_length() / dimension))


def factor_blind_claim_bound(N: int, dimension: int) -> int:
    return ceil(sqrt(dimension + 5) * factor_blind_relation_bound(N, dimension))


@lru_cache(maxsize=None)
def _cached_base_predictors(
    N: int,
    roots: tuple[int, ...],
    diversity_bound: int,
    lambda_bound: int,
) -> dict:
    """Frozen post-hoc/base-only predictors; accepts no factors or orders."""

    family = RootedBaseFamily.from_roots(N, roots)
    oracle = exact_relation_lattice_hnf(N, family.bases)
    minima = bounded_base_lambda_metrics(family, lambda_bound)
    return {
        "predictor_base_diversity_relation_bound": diversity_bound,
        "predictor_bounded_product_diversity": bounded_product_diversity(
            N, family.bases, diversity_bound
        ),
        "predictor_relation_lattice_determinant": oracle.determinant,
        "predictor_relation_lattice_image_size": oracle.image_size,
        "predictor_ordinary_shortest_relation_squared_norm": (
            minima.shortest_relation_squared_norm
        ),
        "predictor_ordinary_shortest_relation_censored": (
            minima.shortest_relation_censored
        ),
        "predictor_base_shortest_L0_squared_norm": (
            minima.shortest_nonzero_L0_squared_norm
        ),
        "predictor_base_shortest_useful_squared_norm": (
            minima.shortest_useful_squared_norm
        ),
        "predictor_base_lambda_scope": minima.scope,
    }


@lru_cache(maxsize=None)
def _cached_exact_fourier_predictors(
    N: int, roots: tuple[int, ...], model_label: str
) -> dict:
    """Exact distribution predictors where the frozen model exposes its law."""

    family = RootedBaseFamily.from_roots(N, roots)
    if model_label == UNIFORM_HARD_BOX_MODEL:
        probability_model = exact_uniform_hard_box_model(family)
    elif model_label == FINITE_GAUSSIAN_MODEL:
        probability_model = exact_finite_discrete_gaussian_model(family)
    else:
        return {
            "predictor_exact_fourier_metrics_available": False,
            "predictor_exact_fourier_scope": (
                "not available for this frozen model; empirical prefix metrics used"
            ),
        }
    metrics = distribution_metrics(probability_model.probabilities)
    return {
        "predictor_exact_fourier_metrics_available": True,
        "predictor_exact_fourier_joint_entropy_bits": metrics[
            "joint_entropy_bits"
        ],
        "predictor_exact_fourier_entropy_deficit_bits": metrics[
            "entropy_deficit_bits"
        ],
        "predictor_exact_fourier_covariance_rank": metrics["covariance_rank"],
        "predictor_exact_fourier_covariance_effective_rank": metrics[
            "covariance_effective_rank"
        ],
        "predictor_exact_fourier_scope": "exact finite output probability tensor",
    }


def _prefix_predictors(
    family: RootedBaseFamily,
    model_label: str,
    samples: Sequence[Sequence[int]],
    modulus: int,
    freeze: QuotientExperimentFreeze,
) -> dict:
    empirical = sample_metrics(np.asarray(samples, dtype=int), modulus)
    return {
        **_cached_base_predictors(
            family.N,
            family.roots,
            freeze.predictor_diversity_relation_bound,
            freeze.quotient_relation_box_bound,
        ),
        **_cached_exact_fourier_predictors(family.N, family.roots, model_label),
        "predictor_sample_count": len(samples),
        "predictor_empirical_fourier_joint_entropy_bits": empirical[
            "joint_entropy_bits"
        ],
        "predictor_empirical_fourier_total_correlation_bits": empirical[
            "total_correlation_bits"
        ],
        "predictor_empirical_fourier_covariance_rank": empirical[
            "covariance_rank"
        ],
        "predictor_empirical_fourier_covariance_effective_rank": empirical[
            "covariance_effective_rank"
        ],
        "predictor_empirical_fourier_scope": (
            "same nested raw Fourier-sample prefix; post-hoc, never recovery input"
        ),
    }


def _method_seed(batch_seed: int, method: str) -> int:
    ordered = (*PRIMARY_METHODS, RV_STRUCTURED_COMPARATOR)
    return int(batch_seed) + 70_000 + 1_009 * ordered.index(method)


def _integer_matrix_bytes(rows: Sequence[Sequence[int]]) -> int:
    return 64 + sum(
        64
        + 8 * len(row)
        + sum(28 + max(1, (abs(int(value)).bit_length() + 7) // 8) for value in row)
        for row in rows
    )


def _resource_columns(resources) -> dict:
    if resources is None:
        return {}
    values = _jsonable(resources)
    if not isinstance(values, dict):
        raise TypeError("resource record must serialize to a mapping")
    return {f"resource_{key}": value for key, value in values.items()}


def _candidate_payload(candidates: Sequence[RecoveryCandidate]) -> tuple:
    return tuple(
        {
            "relation": candidate.relation,
            "class": candidate.relation_class,
            "factor_pair": candidate.factor_pair,
            "root_product": candidate.root_product,
            "discovery_node": candidate.discovery_node,
            "cleared_embedding_squared_norm": candidate.cleared_embedding_squared_norm,
        }
        for candidate in candidates
    )


def _base_trial_row(
    *,
    N: int,
    model_label: str,
    replicate: int,
    method: str,
    sample_count: int,
    batch: FrozenSampleBatch,
    batch_seed: int,
) -> dict:
    return {
        "N": int(N),
        "split": "heldout",
        "model": model_label,
        "replicate": int(replicate),
        "method": method,
        "ablation_label": ABLATION_LABELS[method],
        "sample_count": int(sample_count),
        "batch_seed": int(batch_seed),
        "sample_modulus_D": int(batch.modulus),
        "reconstruction_scale_S": batch.reconstruction_scale,
        "batch_full_sample_count": int(batch.sample_count),
        "batch_prefix_is_source_order": True,
        "model_metadata": dict(batch.metadata),
        "status": "completed",
        "factor_success": 0,
        "factor_pair": None,
        "valid_L_relation_success": 0,
        "L0_candidate_count": 0,
        "L_minus_L0_candidate_count": 0,
        "candidate_count": 0,
        "candidates": (),
        "candidate_classes": (),
        "sample_to_first_factor": None,
        "resource_fourier_precision_bits": int(batch.modulus).bit_length() - 1,
        "resource_lattice_dimension": len(batch.samples[0]) + int(sample_count),
        "resource_quantum_circuit_equivalent_executions": int(sample_count),
    }


def _row_from_recovery(
    result: RecoveryResult,
    **base_arguments,
) -> dict:
    row = _base_trial_row(**base_arguments)
    payload = _candidate_payload(result.candidates)
    row.update(
        {
            "recovery_strategy": result.strategy,
            "factor_success": int(result.factor_pair is not None),
            "factor_pair": result.factor_pair,
            "valid_L_relation_success": int(bool(result.candidates)),
            "L0_candidate_count": sum(
                candidate.relation_class == "L0" for candidate in result.candidates
            ),
            "L_minus_L0_candidate_count": sum(
                candidate.relation_class == "L_minus_L0"
                for candidate in result.candidates
            ),
            "candidate_count": len(result.candidates),
            "candidates": payload,
            "candidate_classes": tuple(
                candidate.relation_class for candidate in result.candidates
            ),
            "recovery_interpretation": result.interpretation,
            **_resource_columns(result.resources),
        }
    )
    return row


def _run_standard_regev_row(
    family: RootedBaseFamily,
    samples: Sequence[Sequence[int]],
    batch: FrozenSampleBatch,
    *,
    N: int,
    model_label: str,
    replicate: int,
    sample_count: int,
    batch_seed: int,
) -> dict:
    start = perf_counter()
    result = regev_lattice_postprocess(
        family,
        samples,
        batch.modulus,
        claim_norm_bound=factor_blind_claim_bound(N, len(family.pairs)),
        scale=batch.reconstruction_scale,
    )
    runtime = perf_counter() - start
    candidates = result.claim_prefix_candidates
    payload = tuple(
        {
            "relation": candidate.relation,
            "class": candidate.relation_class,
            "factor_pair": candidate.factor_pair,
            "root_product": candidate.root_product,
            "source_row": candidate.source_row,
            "cleared_embedding_squared_norm": candidate.cleared_squared_norm,
        }
        for candidate in candidates
    )
    row = _base_trial_row(
        N=N,
        model_label=model_label,
        replicate=replicate,
        method=STANDARD_REGEV_LLL,
        sample_count=sample_count,
        batch=batch,
        batch_seed=batch_seed,
    )
    row.update(
        {
            "factor_success": int(result.factor_pair is not None),
            "factor_pair": result.factor_pair,
            "valid_L_relation_success": int(bool(candidates)),
            "L0_candidate_count": sum(c.relation_class == "L0" for c in candidates),
            "L_minus_L0_candidate_count": sum(
                c.relation_class == "L_minus_L0" for c in candidates
            ),
            "candidate_count": len(candidates),
            "candidates": payload,
            "candidate_classes": tuple(c.relation_class for c in candidates),
            "claim_prefix_length": result.claim_prefix.prefix_length,
            "claim_norm_bound": result.claim_prefix.embedding_norm_bound,
            "all_basis_diagnostic_factor_pair": result.all_basis_diagnostic_factor_pair,
            "resource_nodes_generated": result.claim_prefix.prefix_length,
            "resource_nodes_visited": result.claim_prefix.prefix_length,
            "resource_reductions": 1,
            "resource_reduction_backend": result.reduction.backend,
            "resource_runtime_seconds": runtime,
            "resource_peak_memory_estimate_bytes": (
                _integer_matrix_bytes(result.embedding.integer_row_basis)
                + _integer_matrix_bytes(result.reduction.reduced_rows)
                + _integer_matrix_bytes(result.reduction.transform_rows)
            ),
            "resource_memory_estimate_method": (
                "structural exact integer matrices; not process RSS"
            ),
        }
    )
    return row


def _run_augmented_deflation_row(
    family: RootedBaseFamily,
    samples: Sequence[Sequence[int]],
    batch: FrozenSampleBatch,
    freeze: QuotientExperimentFreeze,
    **base_arguments,
) -> dict:
    result = exact_augmented_basis_deflation_recovery(
        family,
        samples,
        batch.modulus,
        scale=batch.reconstruction_scale,
        max_deletions=freeze.max_augmented_deflation_deletions,
    )
    row = _base_trial_row(method=EXACT_AUGMENTED_ROW_DEFLATION, batch=batch, **base_arguments)
    deleted_payload = tuple(
        {
            "relation": deleted.projected_l0_relation,
            "class": "L0",
            "root_product": deleted.root_product,
            "cleared_embedding_squared_norm": deleted.cleared_squared_norm,
            "deleted_actual_augmented_basis_row": True,
        }
        for deleted in result.deleted_rows
    )
    factor_payload = (
        ({"relation": result.factor_relation, "class": "L_minus_L0", "factor_pair": result.factor_pair},)
        if result.factor_relation is not None
        else ()
    )
    payload = deleted_payload + factor_payload
    row.update(
        {
            "recovery_strategy": result.strategy,
            "factor_success": int(result.factor_pair is not None),
            "factor_pair": result.factor_pair,
            "valid_L_relation_success": int(bool(payload)),
            "L0_candidate_count": len(result.deleted_rows),
            "L_minus_L0_candidate_count": int(result.factor_relation is not None),
            "candidate_count": len(payload),
            "candidates": payload,
            "candidate_classes": tuple(item["class"] for item in payload),
            "deleted_augmented_rows": tuple(asdict(item) for item in result.deleted_rows),
            "relation_U": result.relation_u,
            "quotient_invariants": result.quotient_invariants,
            "termination_reason": result.termination_reason,
            **_resource_columns(result.resources),
        }
    )
    row["resource_nodes_generated"] = result.resources.projected_rows_checked
    row["resource_nodes_visited"] = result.resources.projected_rows_checked
    row["resource_reduction_backend"] = result.resources.reduction_backends
    return row


def _posthoc_root_classification(
    family: RootedBaseFamily,
    candidates: Sequence[RecoveryCandidate],
) -> tuple[tuple[dict, ...], tuple[int, int] | None]:
    rows = []
    factor_pair = None
    for candidate in candidates:
        classified = classify_square_relation(family, candidate.relation)
        factor = classified["factor"]
        pair = tuple(sorted((factor, family.N // factor))) if factor is not None else None
        rows.append(
            {
                "relation": candidate.relation,
                "class": classified["class"],
                "root_product": classified["root_product"],
                "factor_pair": pair,
            }
        )
        if factor_pair is None and pair is not None:
            factor_pair = pair
    return tuple(rows), factor_pair


def _copy_as_method(row: Mapping[str, object], method: str) -> dict:
    copied = dict(row)
    copied["method"] = method
    copied["ablation_label"] = ABLATION_LABELS[method]
    return copied


def _zero_incremental_resources(row: dict) -> None:
    for key in tuple(row):
        if key.startswith("resource_") and key not in (
            "resource_memory_estimate_method",
            "resource_reduction_backend",
        ):
            if isinstance(row[key], (int, float)):
                row[key] = 0


def _make_sequentially_absorbing(rows: Sequence[dict]) -> list[dict]:
    """Stop a sequential method after its first factor and propagate success."""

    ordered = [dict(row) for row in sorted(rows, key=lambda item: item["sample_count"])]
    first_pair = None
    first_count = None
    for row in ordered:
        if first_pair is None and row.get("factor_success"):
            first_pair = row["factor_pair"]
            first_count = row["sample_count"]
            continue
        if first_pair is not None:
            row["factor_success"] = 1
            row["factor_pair"] = first_pair
            row["status"] = "absorbed_after_first_factor_no_further_recovery_call"
            row["absorbed_from_sample_count"] = first_count
            row["candidate_count"] = 0
            row["candidates"] = ()
            row["candidate_classes"] = ()
            row["L0_candidate_count"] = 0
            row["L_minus_L0_candidate_count"] = 0
            _zero_incremental_resources(row)
    return ordered


def _run_root_blind_row(
    family: RootedBaseFamily,
    samples: Sequence[Sequence[int]],
    batch: FrozenSampleBatch,
    freeze: QuotientExperimentFreeze,
    **base_arguments,
) -> dict:
    search = exact_quotient_deduplicated_recovery(
        family,
        samples,
        batch.modulus,
        verified_l0_directions=(),
        scale=batch.reconstruction_scale,
        budget=freeze.recovery_budget,
        root_blind=True,
    )
    if search.resources.root_classifications != 0:
        raise ArithmeticError("root-blind search classified roots before evaluation")
    posthoc_start = perf_counter()
    posthoc, factor_pair = _posthoc_root_classification(family, search.candidates)
    posthoc_runtime = perf_counter() - posthoc_start
    row = _row_from_recovery(
        search,
        method=ROOT_BLIND_POSTHOC,
        batch=batch,
        **base_arguments,
    )
    row.update(
        {
            "factor_success": int(factor_pair is not None),
            "factor_pair": factor_pair,
            "posthoc_candidates": posthoc,
            "posthoc_candidate_classes": tuple(item["class"] for item in posthoc),
            "posthoc_root_classifications": len(posthoc),
            "resource_posthoc_root_classification_runtime_seconds": posthoc_runtime,
            "resource_runtime_seconds": (
                search.resources.runtime_seconds + posthoc_runtime
            ),
            "L0_candidate_count": sum(item["class"] == "L0" for item in posthoc),
            "L_minus_L0_candidate_count": sum(
                item["class"] == "L_minus_L0" for item in posthoc
            ),
            "root_metadata_available_during_search": False,
            "root_metadata_used_only_after_search": True,
        }
    )
    return row


def _run_rv_row_if_available(
    family: RootedBaseFamily,
    batch: FrozenSampleBatch,
    freeze: QuotientExperimentFreeze,
    **base_arguments,
) -> dict:
    row = _base_trial_row(
        method=RV_STRUCTURED_COMPARATOR,
        sample_count=freeze.rv_pool_sample_count,
        batch=batch,
        **base_arguments,
    )
    row["rv_selected_target_count"] = freeze.rv_target_sample_count
    row["rv_pool_sample_count"] = freeze.rv_pool_sample_count
    try:
        module = importlib.import_module("regev_research.rv_filter")
        comparator = getattr(module, "rv_filter_then_short_combination_recovery")
    except (ImportError, AttributeError) as exc:
        row.update(
            {
                "status": "optional_RV_comparator_unavailable",
                "rv_available": False,
                "rv_failure": f"{type(exc).__name__}: {exc}",
            }
        )
        return row

    try:
        result = comparator(
            family,
            batch.samples,
            batch.modulus,
            batch.reconstruction_scale,
            target_count=freeze.rv_target_sample_count,
            budget=freeze.recovery_budget,
        )
    except (ArithmeticError, RuntimeError, TypeError, ValueError) as exc:
        row.update(
            {
                "status": "RV_comparator_failed_cleanly",
                "rv_available": True,
                "rv_failure": f"{type(exc).__name__}: {exc}",
                "rv_asymptotic_guarantee_applicable": False,
            }
        )
        return row
    filtered = result.filter_result
    theorem = filtered.theorem_status
    row.update(
        {
            "rv_available": True,
            "rv_selected_target_count": freeze.rv_target_sample_count,
            "rv_filter_success": filtered.success,
            "rv_selected_indices": filtered.selected_indices,
            "rv_filter_termination_reason": filtered.termination_reason,
            "rv_wrapper_termination_reason": result.termination_reason,
            "rv_comparator_label": filtered.comparator_label,
            "rv_asymptotic_guarantee_applicable": theorem.asymptotic_guarantee_applicable,
            "rv_alpha_gamma_combinatorial_inequality": (
                theorem.alpha_gamma_combinatorial_inequality
            ),
            "rv_theorem_reasons": theorem.reasons,
            "resource_rv_filter_iterations": filtered.resources.iterations,
            "resource_rv_filter_reductions": filtered.resources.reductions,
            "resource_rv_filter_runtime_seconds": filtered.resources.runtime_seconds,
            "resource_rv_filter_peak_memory_estimate_bytes": (
                filtered.resources.peak_memory_estimate_bytes
            ),
        }
    )
    recovery = result.recovery_result
    if recovery is None:
        row["status"] = "RV_filter_failed_no_recovery_call"
        return row
    if not isinstance(recovery, RecoveryResult):
        raise TypeError("RV comparator returned an unknown recovery result")
    recovered_row = _row_from_recovery(
        recovery,
        method=RV_STRUCTURED_COMPARATOR,
        sample_count=freeze.rv_pool_sample_count,
        batch=batch,
        **base_arguments,
    )
    combined = dict(row)
    combined.update(recovered_row)
    combined["factor_success"] = int(recovery.factor_pair is not None)
    combined["factor_pair"] = recovery.factor_pair
    return combined


def _natural_order_ldar_pool(
    natural_fresh_rows: Sequence[Sequence[int]],
    seed: int,
) -> tuple[tuple[tuple[int, ...], ...], dict[int, int]]:
    """Arrange the pool so LDAR's frozen permutation acquires source rows naturally."""

    rows = tuple(tuple(int(value) for value in row) for row in natural_fresh_rows)
    permutation = tuple(int(value) for value in np.random.default_rng(seed).permutation(len(rows)))
    arranged: list[tuple[int, ...] | None] = [None] * len(rows)
    internal_to_source: dict[int, int] = {}
    for natural_position, internal_index in enumerate(permutation):
        arranged[internal_index] = rows[natural_position]
        internal_to_source[internal_index] = natural_position
    if any(row is None for row in arranged):
        raise ArithmeticError("failed to construct the natural LDAR acquisition adapter")
    return tuple(row for row in arranged if row is not None), internal_to_source


def _run_complete_ldar_rows(
    family: RootedBaseFamily,
    batch: FrozenSampleBatch,
    freeze: QuotientExperimentFreeze,
    *,
    N: int,
    model_label: str,
    replicate: int,
    batch_seed: int,
) -> list[dict]:
    initial_count = min(freeze.sample_counts)
    seed = _method_seed(batch_seed, COMPLETE_SEQUENTIAL_LDAR)
    arranged_pool, internal_to_natural = _natural_order_ldar_pool(
        batch.samples[initial_count:], seed
    )
    result = sequential_ldar_recovery(
        family,
        batch.samples[:initial_count],
        arranged_pool,
        batch.modulus,
        frozen_max_sample_count=max(freeze.sample_counts),
        fresh_sample_seed=seed,
        samples_per_acquisition=1,
        max_deflation_rounds_per_sample_count=freeze.max_ldar_rounds_per_sample_count,
        scale=batch.reconstruction_scale,
        budget=freeze.ldar_stage_budget,
    )
    actual_acquisition_order = tuple(
        initial_count + internal_to_natural[index]
        for index in result.selected_fresh_sample_indices
    )
    expected_prefix = tuple(range(initial_count, result.final_sample_count))
    if actual_acquisition_order != expected_prefix:
        raise ArithmeticError("LDAR did not consume the common natural nested-prefix order")

    stages_by_count: dict[int, list] = {}
    for stage in result.stages:
        stages_by_count.setdefault(stage.sample_count, []).append(stage)
    rows = []
    found_pair = None
    found_count = None
    for count in freeze.sample_counts:
        base = _base_trial_row(
            N=N,
            model_label=model_label,
            replicate=replicate,
            method=COMPLETE_SEQUENTIAL_LDAR,
            sample_count=count,
            batch=batch,
            batch_seed=batch_seed,
        )
        stages = stages_by_count.get(count, [])
        if stages:
            candidates = tuple(
                relation for stage in stages for relation in stage.candidate_relations
            )
            classes = tuple(
                relation_class
                for stage in stages
                for relation_class in stage.candidate_classes
            )
            pair = next((stage.factor_pair for stage in stages if stage.factor_pair), None)
            if pair is not None and found_pair is None:
                found_pair, found_count = pair, count
            base.update(
                {
                    "factor_success": int(pair is not None),
                    "factor_pair": pair,
                    "valid_L_relation_success": int(bool(candidates)),
                    "L0_candidate_count": sum(value == "L0" for value in classes),
                    "L_minus_L0_candidate_count": sum(
                        value == "L_minus_L0" for value in classes
                    ),
                    "candidate_count": len(candidates),
                    "candidates": candidates,
                    "candidate_classes": classes,
                    "ldar_stage_count_at_sample_count": len(stages),
                    "ldar_stage_transcript": stages,
                    "ldar_quotient_after": stages[-1].quotient_after,
                    "ldar_U_after": stages[-1].quotient_after.hnf_basis,
                    "resource_nodes_generated": sum(
                        stage.resources.nodes_generated for stage in stages
                    ),
                    "resource_nodes_visited": sum(
                        stage.resources.nodes_visited for stage in stages
                    ),
                    "resource_modular_relation_checks": sum(
                        stage.resources.modular_relation_checks for stage in stages
                    ),
                    "resource_root_classifications": sum(
                        stage.resources.root_classifications for stage in stages
                    ),
                    "resource_suppressed_l0_nodes": sum(
                        stage.resources.suppressed_l0_nodes for stage in stages
                    ),
                    "resource_reductions": sum(
                        stage.resources.reductions for stage in stages
                    ),
                    "resource_runtime_seconds": sum(
                        stage.resources.runtime_seconds for stage in stages
                    ),
                    "resource_peak_memory_estimate_bytes": max(
                        stage.resources.peak_memory_estimate_bytes for stage in stages
                    ),
                    "resource_reduction_backend": tuple(
                        stage.resources.reduction_backend for stage in stages
                    ),
                    "resource_memory_estimate_method": (
                        stages[-1].resources.memory_estimate_method
                    ),
                    "source_sample_indices_used": tuple(range(count)),
                }
            )
        elif found_pair is not None:
            base.update(
                {
                    "factor_success": 1,
                    "factor_pair": found_pair,
                    "status": "absorbed_after_first_factor_no_further_recovery_call",
                    "absorbed_from_sample_count": found_count,
                    "source_sample_indices_used": tuple(range(count)),
                    "resource_nodes_generated": 0,
                    "resource_nodes_visited": 0,
                    "resource_reductions": 0,
                    "resource_runtime_seconds": 0.0,
                }
            )
        else:
            raise ArithmeticError("LDAR transcript omitted a required prefix before success")
        rows.append(base)
    return rows


def _attach_stopping_metrics(rows: Sequence[dict]) -> list[dict]:
    """Attach first-factor sample and cumulative classical time through stopping."""

    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (row["N"], row["model"], row["replicate"], row["method"])
        grouped.setdefault(key, []).append(row)
    output = []
    for group in grouped.values():
        ordered = sorted(group, key=lambda item: item["sample_count"])
        first = next((row for row in ordered if row.get("factor_success")), None)
        first_count = first["sample_count"] if first is not None else None
        stopping_count = first_count if first_count is not None else max(
            row["sample_count"] for row in ordered
        )
        total_time = sum(
            float(row.get("resource_runtime_seconds") or 0.0)
            + float(row.get("resource_rv_filter_runtime_seconds") or 0.0)
            for row in ordered
            if row["sample_count"] <= stopping_count
        )
        for row in ordered:
            copied = dict(row)
            copied["sample_to_first_factor"] = first_count
            copied["resource_total_classical_time_to_factor_or_censor_seconds"] = total_time
            copied["sample_to_first_factor_censored"] = first_count is None
            copied["marginal_prefix_factor_success"] = int(
                bool(row.get("factor_success"))
            )
            copied["sequential_cumulative_factor_success"] = int(
                first_count is not None and int(row["sample_count"]) >= first_count
            )
            copied["success_curve_estimand"] = (
                "primary sequential cumulative success from nested-prefix first hit; "
                "marginal static-prefix success retained separately"
            )
            output.append(copied)
    return output


def evaluate_factor_blind_batch(
    N: int,
    case_index: int,
    model_label: str,
    replicate: int,
    *,
    freeze: QuotientExperimentFreeze = FROZEN_QUOTIENT_EXPERIMENT,
    batch_factory: BatchFactory = generate_full_frozen_batch,
    method_labels: Sequence[str] = (*PRIMARY_METHODS, RV_STRUCTURED_COMPARATOR),
) -> list[dict]:
    """Run one factor-blind cell from ``N`` only.

    The signature intentionally has no factor, order, or planted-relation
    input.  Tests may inject a toy ``batch_factory``; the heldout driver uses
    the frozen sampler factory.
    """

    N = int(N)
    methods = tuple(method_labels)
    allowed = {*PRIMARY_METHODS, RV_STRUCTURED_COMPARATOR}
    unknown = set(methods) - allowed
    if unknown:
        raise ValueError(f"unknown study methods: {sorted(unknown)}")
    family = deterministic_small_prime_family(N, freeze.dimension)
    full_count = max(freeze.sample_counts)
    batch_seed = deterministic_model_seed(
        case_index, model_label, full_count, replicate, freeze
    )
    batch_start = perf_counter()
    batch = batch_factory(family, model_label, batch_seed, freeze)
    batch_generation_runtime = perf_counter() - batch_start
    if batch.model_label != model_label:
        raise ValueError("batch factory returned the wrong model label")
    if batch.sample_count != full_count or len(batch.samples) != full_count:
        raise ValueError("each cell must contain exactly one full eleven-row batch")
    if len({len(row) for row in batch.samples}) != 1 or len(batch.samples[0]) != freeze.dimension:
        raise ValueError("batch dimension disagrees with the frozen family")
    prefixes = nested_prefixes(batch, freeze.sample_counts)
    predictors_by_count = {
        count: _prefix_predictors(
            family, model_label, samples, batch.modulus, freeze
        )
        for count, samples in prefixes.items()
    }

    rows: list[dict] = []
    common_results: dict[int, RecoveryResult] = {}
    common_rows: dict[int, dict] = {}
    needs_common = bool(
        set(methods)
        & {
            COMMON_EXACT_NORM_ENUMERATION,
            ADAPTIVE_SAMPLING_NO_DEFLATION,
            QUOTIENT_GAP_SCORING_ONLY,
        }
    )

    for count, samples in prefixes.items():
        base_arguments = {
            "N": N,
            "model_label": model_label,
            "replicate": replicate,
            "sample_count": count,
            "batch_seed": batch_seed,
        }
        if needs_common:
            recovery = short_combination_recovery(
                family,
                samples,
                batch.modulus,
                scale=batch.reconstruction_scale,
                budget=freeze.recovery_budget,
            )
            common_results[count] = recovery
            common_rows[count] = _row_from_recovery(
                recovery,
                method=COMMON_EXACT_NORM_ENUMERATION,
                batch=batch,
                **base_arguments,
            )
        if STANDARD_REGEV_LLL in methods:
            rows.append(
                _run_standard_regev_row(
                    family, samples, batch, **base_arguments
                )
            )
        if VERIFIED_BKZ_ENUMERATION in methods:
            recovery = bkz_or_deterministic_surrogate_baseline(
                family,
                samples,
                batch.modulus,
                block_size=freeze.bkz_block_size,
                scale=batch.reconstruction_scale,
                budget=freeze.recovery_budget,
            )
            if "verified_fpylll_BKZ" not in recovery.strategy:
                raise RuntimeError(
                    "frozen primary BKZ arm requires transform-verified fpylll; "
                    "the deterministic surrogate is not accepted as that arm"
                )
            rows.append(
                _row_from_recovery(
                    recovery,
                    method=VERIFIED_BKZ_ENUMERATION,
                    batch=batch,
                    **base_arguments,
                )
            )
        if EXACT_AUGMENTED_ROW_DEFLATION in methods:
            rows.append(
                _run_augmented_deflation_row(
                    family,
                    samples,
                    batch,
                    freeze,
                    **base_arguments,
                )
            )
        if ROOT_BLIND_POSTHOC in methods:
            rows.append(
                _run_root_blind_row(
                    family,
                    samples,
                    batch,
                    freeze,
                    **base_arguments,
                )
            )

    if COMMON_EXACT_NORM_ENUMERATION in methods:
        rows.extend(common_rows[count] for count in freeze.sample_counts)

    if ADAPTIVE_SAMPLING_NO_DEFLATION in methods:
        adaptive_rows = []
        for count in freeze.sample_counts:
            row = _copy_as_method(common_rows[count], ADAPTIVE_SAMPLING_NO_DEFLATION)
            row["source_sample_indices_used"] = tuple(range(count))
            row["sequential_acquisition_order"] = "common natural source order"
            adaptive_rows.append(row)
        rows.extend(_make_sequentially_absorbing(adaptive_rows))

    if QUOTIENT_GAP_SCORING_ONLY in methods:
        threshold = float(freeze.quotient_gap_log2_threshold)
        for count in freeze.sample_counts:
            # Reuse the exact recovery object and row.  The post-hoc metric is
            # deliberately computed afterward and cannot affect candidates.
            row = _copy_as_method(common_rows[count], QUOTIENT_GAP_SCORING_ONLY)
            gap_start = perf_counter()
            metric = bounded_sample_augmented_quotient_gap(
                family,
                prefixes[count],
                batch.modulus,
                batch.reconstruction_scale,
                freeze.quotient_relation_box_bound,
            )
            gap_runtime = perf_counter() - gap_start
            row.update(
                {
                    "recovery_identical_to_method": COMMON_EXACT_NORM_ENUMERATION,
                    "recovery_object_reused_without_rerun": True,
                    "quotient_gap_scope": metric.scope,
                    "quotient_gap_relation_bound": metric.relation_bound,
                    "quotient_gap_log2_L0_to_useful_ratio": metric.log2_L0_to_useful_ratio,
                    "quotient_gap_L0_to_useful_ratio": metric.L0_to_useful_augmented_squared_ratio,
                    "quotient_gap_signed_squared_gap": metric.signed_augmented_squared_gap,
                    "quotient_gap_shortest_L0_augmented_squared_norm": (
                        metric.shortest_nonzero_L0_augmented_squared_norm
                    ),
                    "quotient_gap_shortest_useful_augmented_squared_norm": (
                        metric.shortest_useful_augmented_squared_norm
                    ),
                    "quotient_gap_outside_box_squared_norm_lower_bound": (
                        metric.outside_box_squared_norm_lower_bound
                    ),
                    "quotient_gap_L0_censored": metric.shortest_L0_censored,
                    "quotient_gap_useful_censored": metric.shortest_useful_censored,
                    "quotient_gap_precommitted_log2_threshold": threshold,
                    "quotient_gap_score_positive": (
                        metric.log2_L0_to_useful_ratio is not None
                        and metric.log2_L0_to_useful_ratio > threshold
                    ),
                    "resource_posthoc_gap_candidates": metric.candidate_count,
                    "resource_posthoc_gap_runtime_seconds": gap_runtime,
                    "resource_runtime_seconds": (
                        common_results[count].resources.runtime_seconds + gap_runtime
                    ),
                }
            )
            if row["factor_pair"] != common_rows[count]["factor_pair"]:
                raise ArithmeticError("scoring-only arm changed recovery")
            rows.append(row)

    if COMPLETE_SEQUENTIAL_LDAR in methods:
        rows.extend(
            _run_complete_ldar_rows(
                family,
                batch,
                freeze,
                N=N,
                model_label=model_label,
                replicate=replicate,
                batch_seed=batch_seed,
            )
        )

    if RANDOM_GENUINE_EXTRA_SAMPLES in methods:
        initial_count = min(freeze.sample_counts)
        random_seed = _method_seed(batch_seed, RANDOM_GENUINE_EXTRA_SAMPLES)
        fresh_indices = tuple(
            int(value)
            for value in np.random.default_rng(random_seed).permutation(
                np.arange(initial_count, full_count)
            )
        )
        random_rows = []
        for count in freeze.sample_counts:
            source_indices = tuple(range(initial_count)) + fresh_indices[: count - initial_count]
            samples = tuple(batch.samples[index] for index in source_indices)
            recovery = short_combination_recovery(
                family,
                samples,
                batch.modulus,
                scale=batch.reconstruction_scale,
                budget=freeze.recovery_budget,
            )
            row = _row_from_recovery(
                recovery,
                N=N,
                model_label=model_label,
                replicate=replicate,
                method=RANDOM_GENUINE_EXTRA_SAMPLES,
                sample_count=count,
                batch=batch,
                batch_seed=batch_seed,
            )
            row["source_sample_indices_used"] = source_indices
            row["random_fresh_source_order"] = fresh_indices
            row["fresh_samples_without_replacement"] = True
            random_rows.append(row)
        rows.extend(_make_sequentially_absorbing(random_rows))

    if RV_STRUCTURED_COMPARATOR in methods:
        rv_row = _run_rv_row_if_available(
            family,
            batch,
            freeze,
            N=N,
            model_label=model_label,
            replicate=replicate,
            batch_seed=batch_seed,
        )
        rv_row["resource_quantum_circuit_equivalent_executions"] = full_count
        rv_row["resource_lattice_dimension"] = freeze.dimension + freeze.rv_target_sample_count
        rows.append(rv_row)

    for row in rows:
        row["resource_batch_generation_runtime_seconds_shared_cell"] = (
            batch_generation_runtime
        )
    for row in rows:
        row.update(predictors_by_count[int(row["sample_count"])])
    rows = _attach_stopping_metrics(rows)
    return sorted(rows, key=lambda row: (row["method"], row["sample_count"]))


def aggregate_per_n_rows(
    trial_rows: Sequence[Mapping[str, object]],
    *,
    target_probability: Fraction | float = Fraction(4, 5),
) -> list[dict]:
    """Aggregate replicates with ``N`` retained as the generalization unit."""

    target = float(target_probability)
    if not 0 < target < 1:
        raise ValueError("target_probability must lie in (0,1)")
    grouped: dict[tuple, list[Mapping[str, object]]] = {}
    for row in trial_rows:
        key = (int(row["N"]), str(row["model"]), str(row["method"]), int(row["sample_count"]))
        grouped.setdefault(key, []).append(row)

    rows = []
    numeric_resource_keys = sorted(
        {
            key
            for row in trial_rows
            for key, value in row.items()
            if key.startswith("resource_")
            and isinstance(value, (int, float, np.integer, np.floating))
            and not isinstance(value, bool)
        }
    )
    for (N, model, method, sample_count), group in sorted(grouped.items()):
        completed = [row for row in group if row.get("status") != "optional_RV_comparator_unavailable"]
        if not completed:
            continue
        success = np.asarray(
            [int(row.get("sequential_cumulative_factor_success", 0)) for row in completed],
            dtype=float,
        )
        marginal_success = np.asarray(
            [int(row.get("marginal_prefix_factor_success", 0)) for row in completed],
            dtype=float,
        )
        first_samples = [
            int(row["sample_to_first_factor"])
            for row in completed
            if row.get("sample_to_first_factor") is not None
        ]
        out = {
            "N": N,
            "model": model,
            "method": method,
            "ablation_label": ABLATION_LABELS[method],
            "sample_count": sample_count,
            "replicates": len(completed),
            "factor_successes": int(success.sum()),
            "factor_success_rate": float(success.mean()),
            "factor_success_curve": "sequential cumulative nested-prefix",
            "marginal_prefix_factor_success_rate": float(marginal_success.mean()),
            "factor_success_standard_error": (
                float(success.std(ddof=1) / sqrt(len(success))) if len(success) > 1 else 0.0
            ),
            "mean_sample_to_first_factor_among_successes": (
                float(np.mean(first_samples)) if first_samples else None
            ),
            "target_recovery_probability": target,
        }
        for key in numeric_resource_keys:
            values = [float(row[key]) for row in completed if row.get(key) is not None]
            out[f"mean_{key}"] = float(np.mean(values)) if values else None
        rows.append(out)

    by_curve: dict[tuple, list[dict]] = {}
    for row in rows:
        by_curve.setdefault((row["N"], row["model"], row["method"]), []).append(row)
    censor = max(int(row["sample_count"]) for row in rows) + 1 if rows else None
    for curve in by_curve.values():
        threshold_row = next(
            (
                row
                for row in sorted(curve, key=lambda item: item["sample_count"])
                if row["factor_success_rate"] >= target
            ),
            None,
        )
        threshold = threshold_row["sample_count"] if threshold_row is not None else None
        for row in curve:
            row["target_p_sample_threshold"] = threshold
            row["target_p_sample_threshold_censored"] = threshold is None
            row["target_p_sample_threshold_censor_value"] = (
                threshold if threshold is not None else censor
            )
    return rows


def n_cluster_bootstrap_mean(
    values_by_n: Mapping[int, float],
    *,
    resamples: int,
    seed: int,
) -> dict:
    """Bootstrap a mean by resampling whole ``N`` clusters."""

    Ns = tuple(sorted(int(value) for value in values_by_n))
    if not Ns:
        raise ValueError("at least one N cluster is required")
    resamples = int(resamples)
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    values = np.asarray([float(values_by_n[N]) for N in Ns], dtype=float)
    rng = np.random.default_rng(int(seed))
    draws = np.empty(resamples, dtype=float)
    for index in range(resamples):
        selected = rng.integers(0, len(values), size=len(values))
        draws[index] = float(values[selected].mean())
    return {
        "N_clusters": len(Ns),
        "cluster_N": Ns,
        "mean": float(values.mean()),
        "bootstrap_ci_low": float(np.quantile(draws, 0.025)),
        "bootstrap_ci_high": float(np.quantile(draws, 0.975)),
        "bootstrap_resamples": resamples,
        "bootstrap_seed": int(seed),
    }


def paired_n_level_comparisons(
    per_n_rows: Sequence[Mapping[str, object]],
    *,
    reference_method: str = COMMON_EXACT_NORM_ENUMERATION,
    resamples: int = 5_000,
    seed: int = 2_026_071_203,
) -> list[dict]:
    """Paired method-reference comparisons with N-cluster bootstrap CIs."""

    lookup = {
        (int(row["N"]), str(row["model"]), str(row["method"]), int(row["sample_count"])): row
        for row in per_n_rows
    }
    models = sorted({str(row["model"]) for row in per_n_rows})
    methods = sorted({str(row["method"]) for row in per_n_rows if row["method"] != reference_method})
    counts = sorted({int(row["sample_count"]) for row in per_n_rows})
    output = []
    comparison_index = 0
    for model in models:
        for method in methods:
            for count in counts:
                differences = {}
                for N in sorted({int(row["N"]) for row in per_n_rows}):
                    proposed = lookup.get((N, model, method, count))
                    reference = lookup.get((N, model, reference_method, count))
                    if proposed is None or reference is None:
                        continue
                    differences[N] = float(proposed["factor_success_rate"]) - float(
                        reference["factor_success_rate"]
                    )
                if not differences:
                    continue
                bootstrap = n_cluster_bootstrap_mean(
                    differences,
                    resamples=resamples,
                    seed=seed + comparison_index,
                )
                values = np.asarray(list(differences.values()))
                output.append(
                    {
                        "endpoint": "paired N-level factor-success-rate difference",
                        "model": model,
                        "sample_count": count,
                        "method": method,
                        "reference_method": reference_method,
                        "paired_differences_by_N": differences,
                        "wins": int(np.count_nonzero(values > 0)),
                        "ties": int(np.count_nonzero(values == 0)),
                        "losses": int(np.count_nonzero(values < 0)),
                        **bootstrap,
                    }
                )
                comparison_index += 1

    # Target-p threshold is one censored scalar per N/model/method.  Use one
    # row per curve and retain failures at the declared max+1 censor value.
    curve_rows = {}
    for row in per_n_rows:
        curve_rows.setdefault((row["N"], row["model"], row["method"]), row)
    for model in models:
        for method in methods:
            differences = {}
            for N in sorted({int(row["N"]) for row in per_n_rows}):
                proposed = curve_rows.get((N, model, method))
                reference = curve_rows.get((N, model, reference_method))
                if proposed is None or reference is None:
                    continue
                differences[N] = float(proposed["target_p_sample_threshold_censor_value"]) - float(
                    reference["target_p_sample_threshold_censor_value"]
                )
            if not differences:
                continue
            bootstrap = n_cluster_bootstrap_mean(
                differences,
                resamples=resamples,
                seed=seed + comparison_index,
            )
            output.append(
                {
                    "endpoint": "paired N-level target-p sample-threshold difference; max+1 censor",
                    "model": model,
                    "sample_count": None,
                    "method": method,
                    "reference_method": reference_method,
                    "paired_differences_by_N": differences,
                    **bootstrap,
                }
            )
            comparison_index += 1
    return output


def resource_rows_from_trials(trial_rows: Sequence[Mapping[str, object]]) -> list[dict]:
    identifiers = (
        "N",
        "model",
        "replicate",
        "method",
        "ablation_label",
        "sample_count",
        "status",
        "factor_success",
        "marginal_prefix_factor_success",
        "sequential_cumulative_factor_success",
        "sample_to_first_factor",
    )
    rows = []
    for trial in trial_rows:
        row = {key: trial.get(key) for key in identifiers}
        row.update({key: value for key, value in trial.items() if key.startswith("resource_")})
        rows.append(row)
    return rows


def build_study_outputs(
    trial_rows: Sequence[Mapping[str, object]],
    *,
    freeze: QuotientExperimentFreeze = FROZEN_QUOTIENT_EXPERIMENT,
) -> StudyOutputs:
    trials = tuple(dict(row) for row in trial_rows)
    per_n = tuple(
        aggregate_per_n_rows(
            trials, target_probability=freeze.target_recovery_probability
        )
    )
    comparisons = tuple(
        paired_n_level_comparisons(
            per_n,
            reference_method=COMMON_EXACT_NORM_ENUMERATION,
            resamples=freeze.bootstrap_resamples_at_N_level,
            seed=freeze.master_seed + 900_000,
        )
    )
    return StudyOutputs(
        trial_rows=trials,
        per_n_rows=per_n,
        resource_rows=tuple(resource_rows_from_trials(trials)),
        paired_comparisons=comparisons,
    )


def _validate_factors_posthoc(rows: Sequence[Mapping[str, object]], case) -> None:
    """Use manifest factors only after recovery returned, never inside a cell."""

    expected = (int(case.p), int(case.q))
    for row in rows:
        pair = row.get("factor_pair")
        if pair is None:
            continue
        normalized = tuple(sorted(int(value) for value in pair))
        if normalized[0] * normalized[1] != int(case.N):
            raise ArithmeticError("recovery returned a pair whose product is not N")
        if normalized != expected:
            raise ArithmeticError("recovery pair disagrees with the sealed factor manifest")


def _file_hashes(paths: Sequence[Path]) -> dict[str, str]:
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def run_heldout_quotient_study(
    output_directory: Path,
    *,
    freeze: QuotientExperimentFreeze = FROZEN_QUOTIENT_EXPERIMENT,
    cases: Sequence = HELDOUT_SEMIPRIMES,
    model_labels: Sequence[str] = QUOTIENT_MODEL_LABELS,
    replicates: int | None = None,
) -> StudyOutputs:
    """Execute the frozen serial holdout and atomically publish its tables.

    This function is intentionally not called by unit tests or on import.
    ``configuration.json`` and ``factor_manifest.json`` are written before the
    first trial.  The sole ``heldout_executed: true`` value is written to
    ``completion.json`` only after all final CSV/JSON files exist.
    """

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    write_json_atomic(output / "configuration.json", study_configuration(freeze))
    write_factor_manifest(output / "factor_manifest.json", cases)
    count = freeze.trials_per_case_model_count if replicates is None else int(replicates)
    if not 1 <= count <= freeze.trials_per_case_model_count:
        raise ValueError("replicates must lie within the frozen replicate budget")
    if set(model_labels) - set(QUOTIENT_MODEL_LABELS):
        raise ValueError("model_labels contains a non-frozen model")

    all_trials: list[dict] = []
    checkpoints = output / "checkpoints"
    checkpoints.mkdir(exist_ok=True)
    for case_index, case in enumerate(cases):
        # The factor-blind loop receives N and its public index only.
        case_rows: list[dict] = []
        for model_label in model_labels:
            for replicate in range(count):
                case_rows.extend(
                    evaluate_factor_blind_batch(
                        int(case.N),
                        case_index,
                        model_label,
                        replicate,
                        freeze=freeze,
                    )
                )
        _validate_factors_posthoc(case_rows, case)
        write_json_atomic(
            checkpoints / f"N{int(case.N)}.json",
            {
                "N": int(case.N),
                "posthoc_factor_manifest_validation": "passed",
                "rows": case_rows,
            },
        )
        all_trials.extend(case_rows)

    study = build_study_outputs(all_trials, freeze=freeze)
    trial_path = output / "trial_rows.csv"
    per_n_path = output / "per_N_rows.csv"
    resource_path = output / "resource_rows.csv"
    comparison_path = output / "paired_N_comparisons.json"
    write_csv_atomic(trial_path, study.trial_rows)
    write_csv_atomic(per_n_path, study.per_n_rows)
    write_csv_atomic(resource_path, study.resource_rows)
    write_json_atomic(comparison_path, study.paired_comparisons)
    output_paths = (trial_path, per_n_path, resource_path, comparison_path)
    write_json_atomic(
        output / "completion.json",
        {
            "heldout_executed": True,
            "freeze_version": freeze.version,
            "completed_case_count": len(cases),
            "completed_model_count": len(model_labels),
            "replicates_per_case_model": count,
            "trial_row_count": len(study.trial_rows),
            "per_N_row_count": len(study.per_n_rows),
            "resource_row_count": len(study.resource_rows),
            "paired_comparison_count": len(study.paired_comparisons),
            "output_sha256": _file_hashes(output_paths),
            "posthoc_factor_manifest_validation": "passed for every returned pair",
        },
    )
    return study

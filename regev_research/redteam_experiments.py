"""Frozen held-out red-team experiments with N as the generalization unit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import warnings
from collections import defaultdict
from fractions import Fraction
from math import ceil, sqrt
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import ConstantInputWarning, spearmanr

from .core import distribution_metrics
from .dual import exact_relation_lattice_hnf, synthetic_noisy_dual_samples
from .lattice import regev_lattice_postprocess
from .redteam import (
    REDTEAM_METHODS,
    exact_regev_gaussian_distribution,
    exact_weighted_fourier_distribution,
    sample_exact_distribution,
    select_rooted_ablation_family,
    uniform_amplitudes,
    weighted_chi_square_from_kernel,
)


MASTER_SEED = 2_026_071_101
TRIALS_PER_CELL = 32
DIMENSION = 3
SAMPLES_PER_TRIAL = DIMENSION + 4
SELECTOR_RELATION_BOUND = 2
CANDIDATE_ROOT_POOL = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)

# A and B use the same finite register and reconstruction scale.  D=64 and
# R=16 satisfy Regev's required D interval for d=3:
# 2*sqrt(d)*R <= D < 4*sqrt(d)*R.
FINITE_MODULUS = 64
GAUSSIAN_RADIUS = 16.0
FINITE_RECONSTRUCTION_SCALE = Fraction(13, 1)

# N=1763 was used only for pre-freeze feasibility checks and is excluded.
# N=2021 appears in the supplied notebook and is also excluded.  The 24 values
# below were not used to choose or tune any selector rule or parameter.
HELDOUT_INSTANCES = (
    {"N": 1927, "factors": (41, 47)},
    {"N": 2173, "factors": (41, 53)},
    {"N": 2279, "factors": (43, 53)},
    {"N": 2419, "factors": (41, 59)},
    {"N": 2491, "factors": (47, 53)},
    {"N": 2501, "factors": (41, 61)},
    {"N": 2537, "factors": (43, 59)},
    {"N": 2623, "factors": (43, 61)},
    {"N": 2747, "factors": (41, 67)},
    {"N": 2773, "factors": (47, 59)},
    {"N": 2867, "factors": (47, 61)},
    {"N": 2881, "factors": (43, 67)},
    {"N": 2911, "factors": (41, 71)},
    {"N": 2993, "factors": (41, 73)},
    {"N": 3053, "factors": (43, 71)},
    {"N": 3127, "factors": (53, 59)},
    {"N": 3139, "factors": (43, 73)},
    {"N": 3149, "factors": (47, 67)},
    {"N": 3233, "factors": (53, 61)},
    {"N": 3337, "factors": (47, 71)},
    {"N": 3431, "factors": (47, 73)},
    {"N": 3551, "factors": (53, 67)},
    {"N": 3599, "factors": (59, 61)},
    {"N": 3763, "factors": (53, 71)},
)

MODELS = ("A_uniform_hard_box", "B_exact_gaussian_state", "C_theoretical_noisy_dual")


def _json_default(value):
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Fraction):
        return f"{value.numerator}/{value.denominator}"
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(type(value).__name__)


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=_json_default) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table {path}")
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def relation_norm_bound(N: int) -> int:
    """Frozen factor-blind Minkowski/pigeonhole-scale relation bound."""
    return ceil(sqrt(DIMENSION) * 2 ** (N.bit_length() / DIMENSION))


def augmented_norm_bound(T: int) -> int:
    """Integer upper bound on ``sqrt(d+5)*T`` for Claim 5.1."""
    return ceil(sqrt(DIMENSION + 5) * T)


def _seed(instance_index: int, method_index: int, model_index: int, trial: int) -> int:
    return (
        MASTER_SEED
        + 10_000_000 * instance_index
        + 100_000 * method_index
        + 1_000 * model_index
        + trial
    )


def _probability_hash(probabilities: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(probabilities).tobytes()).hexdigest()


def _trial_record(result, *, N: int, method: str, model: str, trial: int, seed: int) -> dict:
    factor_pair = result.factor_pair
    if factor_pair is not None and factor_pair[0] * factor_pair[1] != N:
        raise ArithmeticError("post-processing returned an invalid factor pair")
    candidates = result.claim_prefix_candidates
    return {
        "N": N,
        "method": method,
        "model": model,
        "trial": trial,
        "seed": seed,
        "factor_success": int(factor_pair is not None),
        "factor_pair": json.dumps(factor_pair),
        "valid_L_relation_success": int(bool(candidates)),
        "L_minus_L0_candidate_success": int(
            any(candidate.relation_class == "L_minus_L0" for candidate in candidates)
        ),
        "L0_candidate_count": sum(candidate.relation_class == "L0" for candidate in candidates),
        "L_minus_L0_candidate_count": sum(
            candidate.relation_class == "L_minus_L0" for candidate in candidates
        ),
        "claim_prefix_length": result.claim_prefix.prefix_length,
        "claim_prefix_candidate_count": len(candidates),
        "claim_prefix_rejected_nonrelation_rows": result.claim_prefix_rejected_nonrelation_rows,
        "all_basis_diagnostic_factor_success": int(
            result.all_basis_diagnostic_factor_pair is not None
        ),
        "all_basis_diagnostic_candidate_count": len(
            result.all_basis_diagnostic_candidates
        ),
        "candidate_relations": json.dumps([candidate.relation for candidate in candidates]),
    }


def run_frozen_experiment() -> tuple[list[dict], list[dict], list[dict]]:
    family_rows: list[dict] = []
    exact_rows: list[dict] = []
    trial_rows: list[dict] = []

    for instance_index, instance in enumerate(HELDOUT_INSTANCES):
        N = int(instance["N"])
        if any(N % root == 0 for root in CANDIDATE_ROOT_POOL):
            raise AssertionError("held-out factor entered the frozen candidate pool")
        T = relation_norm_bound(N)
        claim_bound = augmented_norm_bound(T)
        for method_index, method in enumerate(REDTEAM_METHODS):
            selection_seed = _seed(instance_index, method_index, 99, 0)
            family, audit = select_rooted_ablation_family(
                N,
                DIMENSION,
                CANDIDATE_ROOT_POOL,
                method,
                relation_bound=SELECTOR_RELATION_BOUND,
                seed=selection_seed,
            )
            discovered = [
                row.get("factor_discovered")
                for row in audit["rejected"]
                if row.get("factor_discovered")
            ]
            if discovered:
                raise AssertionError("held-out selector discovered a factor during setup")
            family_rows.append(
                {
                    "N": N,
                    "known_factors_posthoc": json.dumps(instance["factors"]),
                    "method": method,
                    "selection_seed": selection_seed,
                    "candidate_pool": json.dumps(CANDIDATE_ROOT_POOL),
                    "selected_roots": json.dumps(family.roots),
                    "selected_bases": json.dumps(family.bases),
                    "selected_pairs": json.dumps(family.as_records()),
                    "bounded_relation_count_B2": audit["bounded_relation_count"],
                    "bounded_product_diversity_B2": audit["bounded_product_diversity"],
                    "subgroup_overlap_score": audit["subgroup_overlap_score"],
                    "selector_setup_factor_leak": False,
                    "relation_norm_bound_T": T,
                    "claim_augmented_norm_bound": claim_bound,
                }
            )

            model_probabilities = {
                "A_uniform_hard_box": exact_weighted_fourier_distribution(
                    N, family.bases, FINITE_MODULUS, uniform_amplitudes(FINITE_MODULUS)
                ),
                "B_exact_gaussian_state": exact_regev_gaussian_distribution(
                    N, family.bases, FINITE_MODULUS, GAUSSIAN_RADIUS
                ),
            }
            for model_index, model in enumerate(MODELS[:2]):
                probabilities, kernel, normalization = model_probabilities[model]
                metrics = distribution_metrics(probabilities)
                chi_kernel = weighted_chi_square_from_kernel(kernel, normalization)
                exact_rows.append(
                    {
                        "N": N,
                        "method": method,
                        "model": model,
                        "roots": json.dumps(family.roots),
                        "bases": json.dumps(family.bases),
                        "modulus_D": FINITE_MODULUS,
                        "gaussian_radius_R": GAUSSIAN_RADIUS if model.startswith("B_") else None,
                        "amplitude_squared_norm": normalization,
                        "probability_sha256": _probability_hash(probabilities),
                        "chi_square_from_probabilities": metrics["chi_square_from_uniform"],
                        "chi_square_from_parseval_kernel": chi_kernel,
                        "parseval_absolute_error": abs(
                            metrics["chi_square_from_uniform"] - chi_kernel
                        ),
                        "joint_entropy_bits": metrics["joint_entropy_bits"],
                        "total_correlation_bits": metrics["total_correlation_bits"],
                        "support_size": metrics["support_size"],
                        "reconstruction_scale": str(FINITE_RECONSTRUCTION_SCALE),
                    }
                )
                for trial in range(TRIALS_PER_CELL):
                    seed = _seed(instance_index, method_index, model_index, trial)
                    samples = sample_exact_distribution(
                        probabilities, SAMPLES_PER_TRIAL, seed
                    )
                    result = regev_lattice_postprocess(
                        family,
                        samples,
                        FINITE_MODULUS,
                        claim_norm_bound=claim_bound,
                        scale=FINITE_RECONSTRUCTION_SCALE,
                    )
                    trial_rows.append(
                        {
                            **_trial_record(
                                result,
                                N=N,
                                method=method,
                                model=model,
                                trial=trial,
                                seed=seed,
                            ),
                            "sample_count": SAMPLES_PER_TRIAL,
                            "sample_modulus": FINITE_MODULUS,
                            "reconstruction_scale": str(FINITE_RECONSTRUCTION_SCALE),
                            "theorem_sufficient_inequality": False,
                        }
                    )

            # C is generated from ground-truth L only on the simulator side.
            # Recovery receives neither this oracle nor a factor/order.
            oracle = exact_relation_lattice_hnf(N, family.bases)
            for trial in range(TRIALS_PER_CELL):
                seed = _seed(instance_index, method_index, 2, trial)
                batch = synthetic_noisy_dual_samples(
                    family,
                    seed=seed,
                    sample_count=SAMPLES_PER_TRIAL,
                    relation_norm_bound_T=T,
                    safety=2.0,
                    oracle=oracle,
                )
                if not batch.theorem_sufficient_inequality:
                    raise AssertionError("model C failed its frozen sufficient inequality")
                result = regev_lattice_postprocess(
                    family,
                    batch.samples,
                    batch.modulus,
                    claim_norm_bound=claim_bound,
                    scale=batch.scale,
                )
                trial_rows.append(
                    {
                        **_trial_record(
                            result,
                            N=N,
                            method=method,
                            model="C_theoretical_noisy_dual",
                            trial=trial,
                            seed=seed,
                        ),
                        "sample_count": batch.sample_count,
                        "sample_modulus": batch.modulus,
                        "reconstruction_scale": batch.scale,
                        "noise_bound": batch.noise_bound,
                        "maximum_realized_torus_error": batch.maximum_realized_torus_error,
                        "theorem_sufficient_inequality": True,
                        "generator_L_determinant": oracle.determinant,
                        "generator_uses_factors_or_orders": False,
                    }
                )
    return family_rows, exact_rows, trial_rows


def aggregate_to_N(trial_rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[int, str, str], list[dict]] = defaultdict(list)
    for row in trial_rows:
        grouped[(row["N"], row["method"], row["model"])].append(row)
    output = []
    binary_keys = (
        "factor_success",
        "valid_L_relation_success",
        "L_minus_L0_candidate_success",
        "all_basis_diagnostic_factor_success",
    )
    numeric_keys = (
        "claim_prefix_length",
        "claim_prefix_candidate_count",
        "claim_prefix_rejected_nonrelation_rows",
    )
    for (N, method, model), rows in sorted(grouped.items()):
        if len(rows) != TRIALS_PER_CELL:
            raise AssertionError("incomplete trial cell")
        record = {
            "N": N,
            "method": method,
            "model": model,
            "trials": len(rows),
        }
        for key in (*binary_keys, *numeric_keys):
            record[f"{key}_rate" if key in binary_keys else f"{key}_mean"] = float(
                np.mean([row[key] for row in rows])
            )
        output.append(record)
    return output


def _safe_spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConstantInputWarning)
        value = float(spearmanr(x, y).statistic)
    return value if np.isfinite(value) else None


def model_statistics(
    family_rows: list[dict], n_rows: list[dict], resamples: int = 10_000
) -> dict:
    family_lookup = {(row["N"], row["method"]): row for row in family_rows}
    rng = np.random.default_rng(MASTER_SEED + 909_090)
    result = {
        "primary_unit": "N",
        "heldout_N_count": len(HELDOUT_INSTANCES),
        "trials_are_within_N_monte_carlo_not_generalization_units": True,
        "resamples": resamples,
        "models": {},
    }
    for model in MODELS:
        rows = [row for row in n_rows if row["model"] == model]
        Ns = sorted({row["N"] for row in rows})
        response = np.asarray([row["factor_success_rate"] for row in rows], dtype=float)
        diversity = np.asarray(
            [family_lookup[(row["N"], row["method"])]["bounded_product_diversity_B2"] for row in rows],
            dtype=float,
        )
        observed = _safe_spearman(diversity, response)
        cluster_indices = [np.flatnonzero(np.asarray([row["N"] for row in rows]) == N) for N in Ns]
        permutation: list[float] = []
        bootstrap: list[float] = []
        if observed is not None:
            for _ in range(resamples):
                permuted = response.copy()
                for indices in cluster_indices:
                    permuted[indices] = rng.permutation(permuted[indices])
                value = _safe_spearman(diversity, permuted)
                if value is not None:
                    permutation.append(value)
                chosen = rng.integers(0, len(cluster_indices), len(cluster_indices))
                sampled_indices = np.concatenate([cluster_indices[index] for index in chosen])
                value = _safe_spearman(diversity[sampled_indices], response[sampled_indices])
                if value is not None:
                    bootstrap.append(value)

        method_summary = {}
        for method in REDTEAM_METHODS:
            values = np.asarray(
                [row["factor_success_rate"] for row in rows if row["method"] == method],
                dtype=float,
            )
            boot = np.asarray(
                [float(np.mean(rng.choice(values, size=len(values), replace=True))) for _ in range(resamples)]
            )
            method_summary[method] = {
                "N_count": len(values),
                "mean_factor_success_across_N": float(values.mean()),
                "N_bootstrap_ci_low": float(np.quantile(boot, 0.025)),
                "N_bootstrap_ci_high": float(np.quantile(boot, 0.975)),
            }

        lookup = {(row["N"], row["method"]): row for row in rows}
        differences = np.asarray(
            [
                lookup[(N, "complete_selector")]["factor_success_rate"]
                - lookup[(N, "regev_small_prime_roots")]["factor_success_rate"]
                for N in Ns
            ],
            dtype=float,
        )
        difference_boot = np.asarray(
            [float(np.mean(rng.choice(differences, size=len(differences), replace=True))) for _ in range(resamples)]
        )
        sign_flips = np.asarray(
            [
                float(np.mean(differences * rng.choice((-1.0, 1.0), size=len(differences))))
                for _ in range(resamples)
            ]
        )
        observed_difference = float(differences.mean())
        model_result = {
            "diversity_vs_lattice_factor_success_spearman": observed,
            "within_N_permutation_p": (
                float(
                    (1 + np.count_nonzero(np.abs(permutation) >= abs(observed)))
                    / (1 + len(permutation))
                )
                if observed is not None and permutation
                else None
            ),
            "N_cluster_bootstrap_ci_low": float(np.quantile(bootstrap, 0.025)) if bootstrap else None,
            "N_cluster_bootstrap_ci_high": float(np.quantile(bootstrap, 0.975)) if bootstrap else None,
            "negative_relationship_persists": bool(
                observed is not None
                and bootstrap
                and observed < 0
                and np.quantile(bootstrap, 0.975) < 0
            ),
            "method_summary": method_summary,
            "complete_minus_small_prime_mean": observed_difference,
            "complete_minus_small_prime_N_bootstrap_ci_low": float(np.quantile(difference_boot, 0.025)),
            "complete_minus_small_prime_N_bootstrap_ci_high": float(np.quantile(difference_boot, 0.975)),
            "complete_minus_small_prime_sign_flip_p": float(
                (1 + np.count_nonzero(np.abs(sign_flips) >= abs(observed_difference)))
                / (1 + len(sign_flips))
            ),
            "paired_N_differences": [
                {"N": N, "difference": float(value)}
                for N, value in zip(Ns, differences, strict=True)
            ],
        }
        result["models"][model] = model_result
    return result


def configuration() -> dict:
    return {
        "status": "frozen before held-out execution",
        "master_seed": MASTER_SEED,
        "heldout_instances": HELDOUT_INSTANCES,
        "heldout_N_count": len(HELDOUT_INSTANCES),
        "development_and_excluded_inputs": {
            "prior_primary_or_notebook": [15, 21, 57, 169, 247, 289, 299, 323, 361, 391, 437, 2021, 4199, 7429],
            "pre_freeze_feasibility_only": [1763],
            "exclusion_rules": [
                "exclude every input used in the original analysis or notebook diagrams",
                "exclude N=1763 used to select feasible D/R and validate code",
                "require every prime factor to exceed max candidate root 37",
                "exclude even N and prime N",
            ],
        },
        "dimension": DIMENSION,
        "samples_per_trial": SAMPLES_PER_TRIAL,
        "trials_per_N_method_model": TRIALS_PER_CELL,
        "primary_generalization_unit": "N",
        "candidate_root_pool": CANDIDATE_ROOT_POOL,
        "selector_relation_bound": SELECTOR_RELATION_BOUND,
        "methods": REDTEAM_METHODS,
        "models": MODELS,
        "finite_modulus_D": FINITE_MODULUS,
        "gaussian_radius_R": GAUSSIAN_RADIUS,
        "finite_scale_S": str(FINITE_RECONSTRUCTION_SCALE),
        "parameter_tuning": {
            "selector_weights": "none; lexicographic rule frozen in redteam.py",
            "development_input": 1763,
            "heldout_outputs_used_for_tuning": False,
            "D_and_R_rule": "D=64,R=16 satisfy 2*sqrt(d)R <= D < 4*sqrt(d)R and exact-enumeration budget",
            "finite_S_rule": "integer approximation 13 to sqrt(2)R/sqrt(d), shared by A and B",
            "T_rule": "ceil(sqrt(d)*2**(bit_length(N)/d)), uses N only",
            "C_noise_rule": "factor-blind det(L)<=N sufficient inequality with safety factor 2",
        },
        "factor_blindness": {
            "selection_receives": ["N", "candidate roots", "d", "relation bound", "seed"],
            "reconstruction_receives": ["rooted family", "raw samples", "D", "S", "T bound"],
            "selection_never_receives": ["factors", "group orders", "arbitrary square roots", "planted relations"],
            "model_C_generator_oracle_not_passed_to_reconstruction": True,
            "known_factors_used_only_for_posthoc_validation": True,
        },
    }


def make_plots(
    output: Path,
    family_rows: list[dict],
    n_rows: list[dict],
    statistics: dict,
) -> None:
    figure_directory = output.parent.parent / "figures"
    figure_directory.mkdir(parents=True, exist_ok=True)
    family_lookup = {(row["N"], row["method"]): row for row in family_rows}
    colors = {
        "A_uniform_hard_box": "#4c78a8",
        "B_exact_gaussian_state": "#f58518",
        "C_theoretical_noisy_dual": "#54a24b",
    }
    labels = {
        "A_uniform_hard_box": "A: uniform hard box",
        "B_exact_gaussian_state": "B: exact finite Gaussian",
        "C_theoretical_noisy_dual": "C: bounded noisy dual",
    }

    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for axis, model in zip(axes, MODELS, strict=True):
        rows = [row for row in n_rows if row["model"] == model]
        axis.scatter(
            [family_lookup[(row["N"], row["method"])]["bounded_product_diversity_B2"] for row in rows],
            [row["factor_success_rate"] for row in rows],
            s=20,
            alpha=0.7,
            color=colors[model],
        )
        rho = statistics["models"][model]["diversity_vs_lattice_factor_success_spearman"]
        axis.set_title(f"{labels[model]}\nSpearman rho={rho:.3f}" if rho is not None else labels[model])
        axis.set_xlabel("bounded-product diversity (B=2)")
        axis.grid(alpha=0.2)
    axes[0].set_ylabel("Claim 5.1 lattice factor-success rate per N")
    fig.tight_layout()
    fig.savefig(figure_directory / "redteam_diversity_vs_lattice_success.png", dpi=180)
    plt.close(fig)

    x = np.arange(len(REDTEAM_METHODS), dtype=float)
    width = 0.24
    fig, axis = plt.subplots(figsize=(12, 5))
    for model_index, model in enumerate(MODELS):
        summaries = statistics["models"][model]["method_summary"]
        means = np.asarray([summaries[method]["mean_factor_success_across_N"] for method in REDTEAM_METHODS])
        lows = np.asarray([summaries[method]["N_bootstrap_ci_low"] for method in REDTEAM_METHODS])
        highs = np.asarray([summaries[method]["N_bootstrap_ci_high"] for method in REDTEAM_METHODS])
        position = x + (model_index - 1) * width
        axis.bar(position, means, width=width, color=colors[model], label=labels[model])
        axis.errorbar(position, means, yerr=np.vstack((means - lows, highs - means)), fmt="none", color="black", capsize=2, linewidth=0.8)
    axis.set_xticks(x)
    axis.set_xticklabels([method.replace("_", "\n") for method in REDTEAM_METHODS], fontsize=8)
    axis.set_ylabel("mean factor-success rate across 24 held-out N")
    axis.set_ylim(0, 1.05)
    axis.legend()
    axis.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(figure_directory / "redteam_model_ablation.png", dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results/redteam"))
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "configuration.json", configuration())
    family_rows, exact_rows, trial_rows = run_frozen_experiment()
    n_rows = aggregate_to_N(trial_rows)
    statistics = model_statistics(family_rows, n_rows)
    write_csv(output / "families.csv", family_rows)
    write_csv(output / "exact_models.csv", exact_rows)
    write_csv(output / "trials.csv", trial_rows)
    write_csv(output / "n_level.csv", n_rows)
    write_json(output / "model_statistics.json", statistics)
    make_plots(output, family_rows, n_rows, statistics)
    hashes = {}
    for path in sorted(output.iterdir()):
        if path.name != "artifact_hashes.json" and path.is_file():
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(output / "artifact_hashes.json", hashes)


if __name__ == "__main__":
    main()

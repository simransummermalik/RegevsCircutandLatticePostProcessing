"""Controlled experiment suite for the finite-window Regev notebook audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import warnings
from collections import defaultdict
from math import gcd, sqrt
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import ConstantInputWarning, spearmanr, t

from .circuits import compiled_resources
from .core import (
    audit_square_base_family,
    base_diagnostics,
    bounded_product_diversity,
    bounded_relations,
    classify_square_relation,
    deduplicated_squared_prime_bases,
    distribution_metrics,
    exact_uniform_fourier_distribution,
    fourier_relation_diagnostic,
    logical_resources,
    modular_product,
    notebook_squared_prime_bases,
    random_coprime_residues,
    relation_recovery_trial,
    RootedBaseFamily,
    sample_distribution,
    sample_metrics,
    select_dependency_aware_bases,
)


MASTER_SEED = 20_260_710
SHOTS = 128
BATCHES = 200
RELATION_BOUND = 2
CANDIDATE_POOL = [2, 3, 5, 7, 11]

# Fixed holdout: every primary factor exceeds the largest candidate (11), so no
# selector can encounter a factor.  N=15 and 21 reproduce the notebook in a
# separate leak stratum.  We keep d=3 and M=32 in the primary set to isolate
# base-family effects at fixed exponent-register resources.
INSTANCES = [
    {"N": 169, "d": 3, "M": 32, "class": "prime_power", "primary": True},
    {"N": 247, "d": 3, "M": 32, "class": "semiprime", "primary": True},
    {"N": 289, "d": 3, "M": 32, "class": "prime_power", "primary": True},
    {"N": 299, "d": 3, "M": 32, "class": "semiprime", "primary": True},
    {"N": 323, "d": 3, "M": 32, "class": "semiprime", "primary": True},
    {"N": 361, "d": 3, "M": 32, "class": "prime_power", "primary": True},
    {"N": 391, "d": 3, "M": 32, "class": "semiprime", "primary": True},
    {"N": 437, "d": 3, "M": 32, "class": "semiprime", "primary": True},
    {"N": 4199, "d": 3, "M": 32, "class": "three_prime", "primary": True},
    {"N": 7429, "d": 3, "M": 32, "class": "three_prime", "primary": True},
    {"N": 15, "d": 2, "M": 16, "class": "semiprime_setup_leak", "primary": False},
    {"N": 21, "d": 3, "M": 16, "class": "semiprime_setup_leak", "primary": False},
]

METHODS = [
    "notebook_squared_primes",
    "squared_primes_deduplicated",
    "random_coprime_residues",
    "random_coprime_squares",
    "dependency_aware",
]


def _json_default(value):
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(type(value).__name__)


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=_json_default) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_family(N: int, d: int, method: str, seed: int) -> dict:
    if method == "notebook_squared_primes":
        data = notebook_squared_prime_bases(N, d)
        return {
            "bases": data["bases"],
            "roots": data["roots"],
            "rooted_family": data["family"],
            "selection": data,
        }
    if method == "squared_primes_deduplicated":
        data = deduplicated_squared_prime_bases(N, d)
        return {
            "bases": data["bases"],
            "roots": data["roots"],
            "rooted_family": data["family"],
            "selection": data,
        }
    if method in ("random_coprime_residues", "random_coprime_squares"):
        rng = np.random.default_rng(seed)
        accepted = []
        rejected = []
        for raw in rng.permutation(CANDIDATE_POOL):
            g = gcd(int(raw), N)
            if g == 1:
                accepted.append(int(raw))
                if len(accepted) == d:
                    break
            else:
                rejected.append(
                    {
                        "candidate": int(raw),
                        "reason": "noncoprime",
                        "factor_discovered": g if 1 < g < N else None,
                    }
                )
        if len(accepted) < d:
            raise ValueError("frozen candidate pool did not provide enough units")
        leaks = [row["factor_discovered"] for row in rejected if row["factor_discovered"]]
        selection = {
            "seed": seed,
            "candidate_pool": CANDIDATE_POOL,
            "accepted": accepted,
            "rejected": rejected,
            "setup_factor_leaks": leaks,
        }
        if method == "random_coprime_squares":
            rooted_family = RootedBaseFamily.from_roots(N, accepted)
            return {
                "bases": list(rooted_family.bases),
                "roots": list(rooted_family.roots),
                "rooted_family": rooted_family,
                "selection": selection,
            }
        # Raw residues are retained only as a sampling-only diagnostic.  They
        # are not a square-base factoring family and have no factor endpoint.
        return {
            "bases": accepted,
            "roots": None,
            "rooted_family": None,
            "selection": selection,
        }
    if method == "dependency_aware":
        # The notebook's N=21 leak stratum needs root 13 to provide three
        # distinct squared residues; this does not alter the primary holdout.
        candidate_roots = [*CANDIDATE_POOL, *([13] if N == 21 else [])]
        selection = select_dependency_aware_bases(
            N=N,
            d=d,
            candidate_pool=candidate_roots,
            relation_bound=RELATION_BOUND,
            scoring_method="bounded_product_diversity",
            seed=seed,
        )
        selection["setup_factor_leaks"] = [
            row["factor_discovered"]
            for row in selection["rejected_bases"]
            if row.get("factor_discovered")
        ]
        selection["candidate_pool"] = candidate_roots
        rooted_family = selection["family"]
        return {
            "bases": list(rooted_family.bases),
            "roots": list(rooted_family.roots),
            "rooted_family": rooted_family,
            "selection": selection,
        }
    raise ValueError(method)


def exact_and_batch_experiments(output: Path) -> tuple[list[dict], list[dict], list[dict]]:
    exact_rows: list[dict] = []
    batch_rows: list[dict] = []
    artifacts: list[dict] = []
    for instance_index, instance in enumerate(INSTANCES):
        N, d, M = instance["N"], instance["d"], instance["M"]
        for method_index, method in enumerate(METHODS):
            family_seed = MASTER_SEED + 10_000 * instance_index + method_index
            family = build_family(N, d, method, family_seed)
            bases, roots = family["bases"], family["roots"]
            rooted_family = family["rooted_family"]
            probabilities, kernel = exact_uniform_fourier_distribution(N, bases, M)
            distribution = distribution_metrics(probabilities, kernel)
            diagnostic = base_diagnostics(N, bases, RELATION_BOUND)
            logical = logical_resources(N, d, M)
            leaks = family["selection"].get("setup_factor_leaks", [])
            posthoc_root_audit = (
                audit_square_base_family(rooted_family, RELATION_BOUND)
                if rooted_family is not None
                else None
            )
            artifact_id = f"N{N}_{method}"
            np.savez_compressed(
                output / "raw" / f"{artifact_id}_distribution.npz",
                probabilities=probabilities,
                relation_kernel=kernel,
                bases=np.asarray(bases, dtype=int),
            )
            artifacts.append(
                {
                    "artifact_id": artifact_id,
                    "sha256": hashlib.sha256(
                        (output / "raw" / f"{artifact_id}_distribution.npz").read_bytes()
                    ).hexdigest(),
                }
            )
            exact_rows.append(
                {
                    "N": N,
                    "instance_class": instance["class"],
                    "primary": instance["primary"],
                    "method": method,
                    "d": d,
                    "M": M,
                    "bases": json.dumps(bases),
                    "roots": json.dumps(roots),
                    "setup_factor_leak": bool(leaks),
                    "setup_factor_leaks": json.dumps(leaks, default=_json_default),
                    "posthoc_bounded_root_audit_factors": json.dumps(
                        posthoc_root_audit["setup_factor_leaks"]
                        if posthoc_root_audit is not None
                        else []
                    ),
                    "subgroup_size": diagnostic["subgroup_size"],
                    "unique_residues": diagnostic["unique_residues"],
                    "distinct_order_count": diagnostic["distinct_order_count"],
                    "bounded_product_diversity": diagnostic["bounded_product_diversity"],
                    "bounded_relation_count": diagnostic["bounded_relation_count"],
                    "bounded_relation_rank": diagnostic["bounded_relation_rank"],
                    "shortest_relation_norm": diagnostic["shortest_relation_norm"],
                    **{key: value for key, value in distribution.items() if not isinstance(value, list)},
                    **{f"resource_{key}": value for key, value in logical.items()},
                }
            )
            for batch in range(BATCHES):
                batch_seed = (
                    MASTER_SEED
                    + 1_000_000 * instance_index
                    + 10_000 * method_index
                    + batch
                )
                samples = sample_distribution(probabilities, SHOTS, batch_seed)
                metrics = sample_metrics(samples, M)
                recovery = relation_recovery_trial(
                    N,
                    bases,
                    samples,
                    M,
                    RELATION_BOUND,
                    rooted_family=rooted_family,
                )
                spectral = fourier_relation_diagnostic(samples, M, RELATION_BOUND)
                batch_rows.append(
                    {
                        "N": N,
                        "instance_class": instance["class"],
                        "primary": instance["primary"],
                        "method": method,
                        "batch": batch,
                        "seed": batch_seed,
                        "shots": SHOTS,
                        **metrics,
                        "top_is_relation": int(recovery["top_is_relation"]),
                        "top_yields_factor": int(recovery["top_factor"] is not None),
                        "relation_exists_in_box": int(recovery["relation_exists_in_box"]),
                        "relation_separation": recovery["relation_separation"],
                        "top_relation_class": recovery["top_relation_class"],
                        "top_factor": recovery["top_factor"],
                        "selected_relation_rank": spectral["selected_rank"],
                        "bounded_spectral_dimension": spectral["bounded_spectral_dimension"],
                        "estimated_signal_energy": spectral["bias_corrected_signal_energy"],
                    }
                )
    return exact_rows, batch_rows, artifacts


def summarize_batches(batch_rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in batch_rows:
        grouped[(row["N"], row["method"])].append(row)
    keys = [
        "joint_entropy_bits",
        "total_correlation_bits",
        "mean_pairwise_mutual_information_bits",
        "covariance_effective_rank",
        "observed_support_size",
        "top_is_relation",
        "top_yields_factor",
        "relation_separation",
        "selected_relation_rank",
        "bounded_spectral_dimension",
        "estimated_signal_energy",
    ]
    summaries = []
    for (N, method), rows in grouped.items():
        out = {"N": N, "method": method, "batches": len(rows), "shots_per_batch": SHOTS}
        for key in keys:
            values = np.asarray(
                [row[key] for row in rows if row.get(key) not in (None, "")], dtype=float
            )
            if not len(values):
                out[f"{key}_mean"] = None
                out[f"{key}_ci_low"] = None
                out[f"{key}_ci_high"] = None
                continue
            mean = float(values.mean())
            if key in ("top_is_relation", "top_yields_factor"):
                z = 1.959963984540054
                n = len(values)
                denominator = 1 + z * z / n
                center = (mean + z * z / (2 * n)) / denominator
                half = z * sqrt(mean * (1 - mean) / n + z * z / (4 * n * n)) / denominator
                low, high = center - half, center + half
            elif len(values) > 1:
                half = float(t.ppf(0.975, len(values) - 1) * values.std(ddof=1) / sqrt(len(values)))
                low, high = mean - half, mean + half
            else:
                low = high = mean
            out[f"{key}_mean"] = mean
            out[f"{key}_ci_low"] = float(low)
            out[f"{key}_ci_high"] = float(high)
        summaries.append(out)
    return summaries


def synthetic_validation() -> dict:
    # Pairwise checks through exponent three miss this genuinely
    # three-coordinate relation.  The bases all have order 99.
    N = 437
    roots_L0 = [2, 3, 73]
    roots_useful = [2, 3, 326]
    family_L0 = RootedBaseFamily.from_roots(N, roots_L0)
    family_useful = RootedBaseFamily.from_roots(N, roots_useful)
    bases = list(family_L0.bases)
    triple = (1, 1, 1)
    triple_case = {
        "N": N,
        "bases": bases,
        "orders": base_diagnostics(N, bases, 2)["orders"],
        "pairwise_power_collisions_through_3": base_diagnostics(N, bases, 3)["pairwise_power_collisions"],
        "planted_relation": triple,
        "relation_check": modular_product(N, bases, triple),
        "L0_roots": roots_L0,
        "L0_classification": classify_square_relation(family_L0, triple),
        "useful_roots": roots_useful,
        "useful_classification": classify_square_relation(family_useful, triple),
    }

    # Validate collision, power, multivariate, progressive, and out-of-bound cases
    # over a large semiprime.  Factors are not used to create the ordinary cases.
    large_N = 1_000_003 * 1_000_033
    rows = []
    for seed in range(20):
        rng = np.random.default_rng(MASTER_SEED + seed)
        units = []
        while len(units) < 6:
            b = int(rng.integers(2, large_N - 1))
            if gcd(b, large_N) == 1 and b not in units:
                units.append(b)
        random_bases = [b * b % large_N for b in units]
        cases = {
            "random": random_bases,
            "duplicate": [*random_bases[:5], random_bases[0]],
            "power": [*random_bases[:5], pow(random_bases[0], 2, large_N)],
            "multivariate": [
                *random_bases[:5],
                pow(random_bases[0] * random_bases[1] % large_N, -1, large_N),
            ],
            "three_planted": [
                random_bases[0],
                random_bases[0],
                random_bases[1],
                random_bases[1],
                random_bases[2],
                random_bases[2],
            ],
            "power_outside_B2": [*random_bases[:5], pow(random_bases[0], 3, large_N)],
        }
        for name, family in cases.items():
            rel2 = bounded_relations(large_N, family, 2)
            rel3 = bounded_relations(large_N, family, 3) if name == "power_outside_B2" else []
            rows.append(
                {
                    "seed": seed,
                    "case": name,
                    "bounded_product_diversity_B2": bounded_product_diversity(large_N, family, 2),
                    "relation_count_B2": len(rel2),
                    "relation_rank_B2": int(np.linalg.matrix_rank(rel2)) if rel2 else 0,
                    "relation_count_B3": len(rel3),
                }
            )

    # Pairwise independent yet jointly constrained modular samples.
    rng = np.random.default_rng(MASTER_SEED)
    M = 32
    xy = rng.integers(0, M, size=(200_000, 2))
    modular_samples = np.column_stack((xy, (xy[:, 0] + xy[:, 1]) % M))
    modular_metrics = sample_metrics(modular_samples, M)
    return {
        "triple_relation_counterexample": triple_case,
        "planted_structure_runs": rows,
        "pairwise_independent_joint_constraint": {
            "construction": "K3=(K1+K2) mod M with K1,K2 uniform",
            "shots": len(modular_samples),
            **modular_metrics,
        },
    }


def indistinguishability_audit() -> list[dict]:
    rows = []
    for N, M in [(15, 16), (21, 16), (77, 32), (91, 32), (119, 32), (49, 16), (121, 32)]:
        b = 2
        collisions = [
            c
            for c in range(2, N)
            if gcd(c, N) == 1 and c * c % N == b * b % N and c not in (b, N - b)
        ]
        clone_roots = [b, b]
        clone_family = RootedBaseFamily.from_roots(N, clone_roots)
        clone_class = classify_square_relation(clone_family, (1, -1))
        probabilities, _ = exact_uniform_fourier_distribution(N, [b * b % N] * 2, M)
        if collisions:
            c = collisions[0]
            collision_family = RootedBaseFamily.from_roots(N, [b, c])
            collision_class = classify_square_relation(collision_family, (1, -1))
            factor_from_collision = next(
                (g for g in (gcd(c - b, N), gcd(c + b, N)) if 1 < g < N), None
            )
            rows.append(
                {
                    "N": N,
                    "M": M,
                    "bases_both_cases": [b * b % N, b * b % N],
                    "probability_sha256_both_cases": hashlib.sha256(probabilities.tobytes()).hexdigest(),
                    "max_probability_difference": 0.0,
                    "clone_roots": clone_roots,
                    "clone_relation_class": clone_class,
                    "collision_roots": [b, c],
                    "collision_relation_class": collision_class,
                    "collision_search_factor_leak": factor_from_collision,
                }
            )
        else:
            rows.append(
                {
                    "N": N,
                    "M": M,
                    "bases_both_cases": [b * b % N, b * b % N],
                    "probability_sha256_both_cases": hashlib.sha256(probabilities.tobytes()).hexdigest(),
                    "max_probability_difference": 0.0,
                    "clone_roots": clone_roots,
                    "clone_relation_class": clone_class,
                    "collision_roots": None,
                    "collision_relation_class": None,
                    "collision_search_factor_leak": None,
                }
            )
    return rows


def ablation_experiments() -> list[dict]:
    rows = []
    N, d = 299, 3
    pool = CANDIDATE_POOL
    for bound in (1, 2, 3):
        selected = select_dependency_aware_bases(
            N, d, pool, relation_bound=bound, seed=MASTER_SEED
        )["selected_bases"]
        for M in (8, 16, 32):
            probabilities, kernel = exact_uniform_fourier_distribution(N, selected, M)
            metrics = distribution_metrics(probabilities, kernel)
            rows.append(
                {
                    "ablation": "selector_relation_bound_x_fourier_width",
                    "N": N,
                    "selector_bound": bound,
                    "M": M,
                    "bases": selected,
                    "bounded_relation_count_at_selection_bound": len(
                        bounded_relations(N, selected, bound)
                    ),
                    "joint_entropy_bits": metrics["joint_entropy_bits"],
                    "total_correlation_bits": metrics["total_correlation_bits"],
                    "relation_signal_energy": metrics["relation_signal_energy"],
                }
            )
    # Remove provenance while holding N, A, M, and every quantum result fixed.
    for roots in ([2, 3, 73], [2, 3, 326]):
        family = RootedBaseFamily.from_roots(437, roots)
        rows.append(
            {
                "ablation": "root_provenance",
                "N": 437,
                "M": 16,
                "bases": [4, 9, 85],
                "roots": roots,
                "relation": [1, 1, 1],
                **classify_square_relation(family, (1, 1, 1)),
            }
        )
    return rows


def correlation_analysis(exact_rows: list[dict], summaries: list[dict]) -> dict:
    def safe_spearman(x, y):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConstantInputWarning)
            return spearmanr(x, y)

    summary_lookup = {(row["N"], row["method"]): row for row in summaries}
    joined = []
    for row in exact_rows:
        if row["primary"]:
            joined.append({**row, **summary_lookup[(row["N"], row["method"])]})
    target = np.asarray([row["top_is_relation_mean"] for row in joined], dtype=float)
    cluster_labels = np.asarray([row["N"] for row in joined], dtype=int)
    cluster_indices = [
        np.flatnonzero(cluster_labels == N) for N in sorted(set(cluster_labels))
    ]
    predictors = [
        "bounded_product_diversity",
        "joint_entropy_bits",
        "total_correlation_bits",
        "covariance_effective_rank",
        "relation_signal_energy",
        "bounded_relation_count",
    ]
    correlations = {}
    for predictor_index, predictor in enumerate(predictors):
        values = np.asarray([row[predictor] for row in joined], dtype=float)
        result = safe_spearman(values, target)
        observed = float(result.statistic)
        rng = np.random.default_rng(MASTER_SEED + predictor_index)
        permutation_statistics = []
        for _ in range(10_000):
            permuted = target.copy()
            for indices in cluster_indices:
                permuted[indices] = rng.permutation(permuted[indices])
            statistic = float(safe_spearman(values, permuted).statistic)
            if np.isfinite(statistic):
                permutation_statistics.append(statistic)
        cluster_bootstrap = []
        for _ in range(5_000):
            selected = rng.integers(0, len(cluster_indices), len(cluster_indices))
            indices = np.concatenate([cluster_indices[i] for i in selected])
            statistic = float(safe_spearman(values[indices], target[indices]).statistic)
            if np.isfinite(statistic):
                cluster_bootstrap.append(statistic)
        permuted = np.asarray(permutation_statistics)
        bootstrap = np.asarray(cluster_bootstrap)
        correlations[predictor] = {
            "spearman_rho": observed,
            "naive_two_sided_p_not_used_for_claims": float(result.pvalue),
            "within_instance_permutation_p": float(
                (1 + np.count_nonzero(np.abs(permuted) >= abs(observed)))
                / (1 + len(permuted))
            ),
            "instance_cluster_bootstrap_ci_low": float(np.quantile(bootstrap, 0.025)),
            "instance_cluster_bootstrap_ci_high": float(np.quantile(bootstrap, 0.975)),
            "n": len(joined),
            "clusters": len(cluster_indices),
        }
    paired = []
    for N in sorted(set(cluster_labels)):
        proposed = summary_lookup[(N, "dependency_aware")]["top_is_relation_mean"]
        baseline = summary_lookup[(N, "notebook_squared_primes")]["top_is_relation_mean"]
        paired.append(
            {
                "N": int(N),
                "dependency_aware_minus_notebook": float(proposed - baseline),
            }
        )
    return {
        "endpoint": "finite-shot top bounded relation recovery",
        "rows": len(joined),
        "instance_clusters": len(cluster_indices),
        "permutation_resamples": 10_000,
        "cluster_bootstrap_resamples": 5_000,
        "correlations": correlations,
        "paired_dependency_aware_vs_notebook": paired,
        "interpretation_guardrail": (
            "Rows within N are dependent; use the within-instance permutation p and "
            "instance-cluster bootstrap interval, not the naive p-value."
        ),
    }


def resource_experiments() -> list[dict]:
    rows = []
    for N, d, M in [(15, 2, 16), (21, 3, 16)]:
        for method_index, method in enumerate(METHODS):
            family = build_family(N, d, method, MASTER_SEED + N + method_index)
            row = compiled_resources(N, family["bases"], M)
            row["method"] = method
            rows.append(row)
    return rows


def make_plots(output: Path, exact_rows: list[dict], summaries: list[dict]) -> None:
    primary = [row for row in exact_rows if row["primary"]]
    lookup = {(row["N"], row["method"]): row for row in summaries}
    colors = {
        "notebook_squared_primes": "#4c78a8",
        "squared_primes_deduplicated": "#72b7b2",
        "random_coprime_residues": "#f58518",
        "random_coprime_squares": "#b279a2",
        "dependency_aware": "#e45756",
    }
    fig, ax = plt.subplots(figsize=(7, 5))
    for method in METHODS:
        rows = [row for row in primary if row["method"] == method]
        ax.scatter(
            [row["joint_entropy_bits"] for row in rows],
            [lookup[(row["N"], method)]["top_is_relation_mean"] for row in rows],
            label=method.replace("_", " "),
            color=colors[method],
            s=55,
        )
    ax.set_xlabel("Exact joint Fourier entropy (bits)")
    ax.set_ylabel("Bounded relation recovery probability")
    ax.set_title("Higher entropy can mean less recoverable relation signal")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "../figures/entropy_vs_relation_recovery.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    x = np.asarray([row["relation_signal_energy"] for row in exact_rows])
    y = np.asarray([row["chi_square_from_uniform"] for row in exact_rows])
    ax.scatter(x, y, color="#4c78a8")
    limit = max(x.max(), y.max())
    ax.plot([0, limit], [0, limit], linestyle="--", color="black", label="Parseval identity")
    ax.set_xlabel("Relation-signal energy from kernel")
    ax.set_ylabel("Chi-square divergence of Fourier law")
    ax.set_title("Exact finite-window identity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "../figures/parseval_identity.png", dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--skip-compiled-resources", action="store_true")
    args = parser.parse_args()
    output = args.output
    (output / "raw").mkdir(parents=True, exist_ok=True)
    (output / "summary").mkdir(parents=True, exist_ok=True)
    (output.parent / "figures").mkdir(parents=True, exist_ok=True)
    for stale_distribution in (output / "raw").glob("N*_distribution.npz"):
        stale_distribution.unlink()

    exact_rows, batch_rows, artifacts = exact_and_batch_experiments(output)
    summaries = summarize_batches(batch_rows)
    write_csv(output / "summary" / "baseline_exact.csv", exact_rows)
    write_csv(output / "raw" / "batch_metrics.csv", batch_rows)
    write_csv(output / "summary" / "baseline_batches.csv", summaries)
    write_json(output / "summary" / "synthetic_validation.json", synthetic_validation())
    write_json(output / "summary" / "indistinguishability_audit.json", indistinguishability_audit())
    write_json(output / "summary" / "ablations.json", ablation_experiments())
    write_json(output / "summary" / "correlations.json", correlation_analysis(exact_rows, summaries))
    write_json(output / "raw" / "artifact_hashes.json", artifacts)
    if not args.skip_compiled_resources:
        write_json(output / "summary" / "compiled_resources.json", resource_experiments())
    make_plots(output, exact_rows, summaries)
    write_json(
        output / "summary" / "configuration.json",
        {
            "master_seed": MASTER_SEED,
            "shots": SHOTS,
            "batches": BATCHES,
            "relation_bound": RELATION_BOUND,
            "instances": INSTANCES,
            "methods": METHODS,
            "candidate_pool": CANDIDATE_POOL,
        },
    )


if __name__ == "__main__":
    main()

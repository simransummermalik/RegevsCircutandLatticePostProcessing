"""Deterministic descriptive scaling census for bounded Factor-or-Fuse scans."""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from time import perf_counter

import matplotlib.pyplot as plt
import numpy as np
from sympy import nextprime


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from factor_or_fuse_study.freeze import MAX_POWER, method_input_from_modulus  # noqa: E402
from regev_research.orbit_fusion import (  # noqa: E402
    detect_all_pair_power_relations,
    detect_pair_power_relations,
    positive_power_no_wrap_certificate,
)


BIT_LENGTHS = (12, 16, 20, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, 1024, 1536, 2048)
CASES_PER_BIT_LENGTH = 100
RESULTS = Path(__file__).resolve().parent / "results" / "scaling_census"


def _candidate_semiprimes(bit_length: int) -> list[tuple[int, int, int]]:
    lower_product = 1 << (bit_length - 1)
    upper_product = (1 << bit_length) - 1
    center = math.isqrt(lower_product)
    cursor = max(11, center // 4)
    cases: list[tuple[int, int, int]] = []
    seen: set[int] = set()
    while len(cases) < CASES_PER_BIT_LENGTH:
        cursor = int(nextprime(cursor))
        p = cursor
        q_cursor = max(p, (lower_product + p - 1) // p - 1)
        for _ in range(40):
            q = int(nextprime(q_cursor))
            q_cursor = q
            N = p * q
            if N > upper_product:
                break
            if p < q and N.bit_length() == bit_length and N not in seen:
                seen.add(N)
                cases.append((p, q, N))
                if len(cases) == CASES_PER_BIT_LENGTH:
                    return cases
    raise AssertionError("unreachable deterministic case-generation state")


def scan_modulus(N: int) -> dict[str, object]:
    """Factor-free-input worker; its only instance input is the modulus."""

    method_input = method_input_from_modulus(N)
    if method_input.setup_factor is not None or method_input.family is None:
        return {
            "outcome": "setup_factor",
            "factor_pair": method_input.setup_factor,
            "all_witness_factor_pair": method_input.setup_factor,
            "relations": (),
            "all_witness_relations": (),
            "all_witness_outcome": "setup_factor",
            "roots": (),
            "bases": (),
            "dimension": method_input.dimension,
            "no_wrap_certified": False,
        }
    family = method_input.family
    relations = detect_pair_power_relations(family, max_power=MAX_POWER)
    all_witness_relations = detect_all_pair_power_relations(
        family, max_power=MAX_POWER
    )
    factor_pair = next(
        (
            row.classification.factor_pair
            for row in relations
            if row.classification.category == "factor_yielding"
        ),
        None,
    )
    if factor_pair:
        outcome = "classical_factor"
    elif relations:
        outcome = "L0_only"
    else:
        outcome = "no_relation"
    all_witness_factor_pair = next(
        (
            row.classification.factor_pair
            for row in all_witness_relations
            if row.classification.category == "factor_yielding"
        ),
        None,
    )
    all_witness_outcome = (
        "classical_factor"
        if all_witness_factor_pair
        else "L0_only"
        if all_witness_relations
        else "no_relation"
    )
    no_wrap_certificate = positive_power_no_wrap_certificate(
        family, max_power=MAX_POWER
    )
    no_wrap = no_wrap_certificate.certified
    if no_wrap and relations:
        raise ArithmeticError("no-wrap certificate contradicted a detected relation")
    return {
        "outcome": outcome,
        "factor_pair": factor_pair,
        "all_witness_factor_pair": all_witness_factor_pair,
        "relations": relations,
        "all_witness_relations": all_witness_relations,
        "all_witness_outcome": all_witness_outcome,
        "roots": family.roots,
        "bases": family.bases,
        "dimension": len(family.pairs),
        "no_wrap_certified": no_wrap,
    }


def _wilson(successes: int, total: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return center - radius, center + radius


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for bit_length in BIT_LENGTHS:
        for case_index, (p, q, N) in enumerate(_candidate_semiprimes(bit_length)):
            started = perf_counter()
            raw = scan_modulus(N)
            runtime = perf_counter() - started
            relations = raw["relations"]
            all_witness_relations = raw["all_witness_relations"]
            factor_pair = raw["factor_pair"]
            all_witness_factor_pair = raw["all_witness_factor_pair"]
            factor_valid = bool(
                factor_pair
                and factor_pair[0] * factor_pair[1] == N
                and tuple(sorted(factor_pair)) == (p, q)
            )
            rows.append(
                {
                    "bit_length": bit_length,
                    "case_index": case_index,
                    "N": N,
                    "posthoc_p": p,
                    "posthoc_q": q,
                    "dimension": raw["dimension"],
                    "roots": json.dumps(list(raw["roots"])),
                    "bases": json.dumps(list(raw["bases"])),
                    "max_power": MAX_POWER,
                    "outcome": raw["outcome"],
                    "relation_count": len(relations),
                    "factor_relation_count": sum(
                        row.classification.category == "factor_yielding"
                        for row in relations
                    ),
                    "l0_relation_count": sum(
                        row.classification.category == "L0" for row in relations
                    ),
                    "all_witness_outcome": raw["all_witness_outcome"],
                    "all_witness_relation_count": len(all_witness_relations),
                    "all_witness_factor_relation_count": sum(
                        row.classification.category == "factor_yielding"
                        for row in all_witness_relations
                    ),
                    "all_witness_l0_relation_count": sum(
                        row.classification.category == "L0"
                        for row in all_witness_relations
                    ),
                    "factor_missed_by_least_witness_policy": (
                        factor_pair is None and all_witness_factor_pair is not None
                    ),
                    "smallest_power": min(
                        (row.power for row in relations), default=""
                    ),
                    "factor_pair": json.dumps(list(factor_pair)) if factor_pair else "",
                    "all_witness_factor_pair": (
                        json.dumps(list(all_witness_factor_pair))
                        if all_witness_factor_pair
                        else ""
                    ),
                    "posthoc_factor_match": (
                        (factor_pair is None or factor_valid)
                        and (
                            all_witness_factor_pair is None
                            or tuple(sorted(all_witness_factor_pair)) == (p, q)
                        )
                    ),
                    "no_wrap_certified": raw["no_wrap_certified"],
                    "runtime_seconds": runtime,
                    "known_factors_used_by_scan": False,
                    "group_orders_used": False,
                }
            )
    _write_csv(RESULTS / "per_modulus.csv", rows)

    summary: list[dict[str, object]] = []
    for bit_length in BIT_LENGTHS:
        group = [row for row in rows if row["bit_length"] == bit_length]
        activated = sum(row["outcome"] != "no_relation" for row in group)
        low, high = _wilson(activated, len(group))
        summary.append(
            {
                "bit_length": bit_length,
                "N_count": len(group),
                "any_relation_count": activated,
                "any_relation_fraction": activated / len(group),
                "relation_wilson_low": low,
                "relation_wilson_high": high,
                "factor_count": sum(
                    row["outcome"] in ("setup_factor", "classical_factor")
                    for row in group
                ),
                "all_witness_factor_count": sum(
                    row["all_witness_outcome"] == "classical_factor"
                    for row in group
                ),
                "factor_missed_by_least_policy_count": sum(
                    bool(row["factor_missed_by_least_witness_policy"])
                    for row in group
                ),
                "L0_only_count": sum(row["outcome"] == "L0_only" for row in group),
                "no_relation_count": sum(
                    row["outcome"] == "no_relation" for row in group
                ),
                "no_wrap_certified_count": sum(
                    bool(row["no_wrap_certified"]) for row in group
                ),
                "median_runtime_seconds": float(
                    np.median([float(row["runtime_seconds"]) for row in group])
                ),
            }
        )
    _write_csv(RESULTS / "by_bit_length.csv", summary)

    x = np.asarray([int(row["bit_length"]) for row in summary])
    y = np.asarray([100 * float(row["any_relation_fraction"]) for row in summary])
    low = np.asarray([100 * float(row["relation_wilson_low"]) for row in summary])
    high = np.asarray([100 * float(row["relation_wilson_high"]) for row in summary])
    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.plot(x, y, marker="o", color="#0072B2", label="detected within K=64")
    ax.fill_between(
        x,
        low,
        high,
        color="#56B4E9",
        alpha=0.3,
        label="binomial reference band (descriptive only)",
    )
    certified_x = [
        int(row["bit_length"])
        for row in summary
        if int(row["no_wrap_certified_count"]) == int(row["N_count"])
    ]
    if certified_x:
        start = min(certified_x)
        ax.axvspan(start, max(x), color="#009E73", alpha=0.12, label="all cases no-wrap certified")
    ax.set_xscale("log", base=2)
    ax.set_xticks(x, [str(value) for value in x], rotation=45)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Modulus bit length n (log scale)")
    ax.set_ylabel("Cases with a bounded pair-power relation (%)")
    ax.set_title("Factor-or-Fuse activation fades under the standard small-prime rule")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(RESULTS / "scaling_activation.png", dpi=220)
    plt.close(fig)

    payload = {
        "status": "post_holdout_descriptive_census",
        "bit_lengths": list(BIT_LENGTHS),
        "cases_per_bit_length": CASES_PER_BIT_LENGTH,
        "total_moduli": len(rows),
        "max_power": MAX_POWER,
        "all_factor_checks_passed": all(
            bool(row["posthoc_factor_match"]) for row in rows
        ),
        "summary": summary,
    }
    (RESULTS / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

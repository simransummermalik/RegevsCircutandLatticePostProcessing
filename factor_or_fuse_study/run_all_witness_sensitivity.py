"""Post-hoc sensitivity analysis for the factor-first all-witness variant."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from regev_research.core import RootedBaseFamily  # noqa: E402
from regev_research.orbit_fusion import factor_or_fuse_all_witnesses  # noqa: E402


RESULTS = Path(__file__).resolve().parent / "results"


def main() -> None:
    primary_rows = [
        row
        for row in csv.DictReader((RESULTS / "heldout_per_arm.csv").open())
        if row["arm"] == "complete_cost_optimal_factor_or_fuse_K64"
    ]
    rows = []
    for primary in primary_rows:
        N = int(primary["N"])
        family = RootedBaseFamily.from_roots(N, json.loads(primary["roots"]))
        result = factor_or_fuse_all_witnesses(
            family, int(primary["exponent_width"]), max_power=64
        )
        outcome = {
            "classical_factor": "classical_factor",
            "l0_orbit_fusion": "fused",
            "baseline_fallback": "baseline",
        }[result.outcome]
        rows.append(
            {
                "N": N,
                "status": "posthoc_sensitivity_not_new_holdout",
                "primary_least_witness_outcome": primary["outcome"],
                "all_witness_outcome": outcome,
                "outcome_changed": outcome != primary["outcome"],
                "all_witness_relation_count": len(result.relations),
                "all_witness_factor_relation_count": result.factor_relation_count,
                "all_witness_l0_relation_count": result.l0_relation_count,
                "factor_pair": json.dumps(list(result.factor_pair))
                if result.factor_pair
                else "",
                "canonical_cx_saving_fraction": (
                    result.plan.canonical_cx_saving_fraction if result.plan else 1.0
                ),
                "verified": result.verify(),
                "known_factors_used": False,
            }
        )
    path = RESULTS / "all_witness_heldout_sensitivity.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "status": "posthoc_sensitivity_not_new_holdout",
        "N_count": len(rows),
        "outcome_change_count": sum(row["outcome_changed"] for row in rows),
        "factor_count": sum(row["all_witness_outcome"] == "classical_factor" for row in rows),
        "fused_count": sum(row["all_witness_outcome"] == "fused" for row in rows),
        "all_verified": all(row["verified"] for row in rows),
    }
    (RESULTS / "all_witness_heldout_sensitivity.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

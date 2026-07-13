"""Run deterministic development examples for the standard Shor pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from shor_to_regev_study.shor import build_shor_circuit, shor_factor


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "shor_experiments"
EXAMPLES = (
    (15, 2, "factor-yielding order"),
    (15, 14, "trivial square root"),
    (21, 2, "factor-yielding order"),
    (21, 4, "odd order"),
    (21, 5, "trivial square root"),
    (33, 10, "factor-yielding order"),
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for index, (N, base, expected_case) in enumerate(EXAMPLES):
        result = shor_factor(N, base, shots=64, seed=2026071201 + index)
        circuit = build_shor_circuit(N, base, measure=True)
        rows.append({
            "N": N,
            "base": base,
            "expected_case": expected_case,
            "shots": result.shots,
            "phase_qubits": result.phase_qubits,
            "qft_cutoff": result.qft_cutoff,
            "order_recovered": result.order_recovered,
            "recovered_order": result.recovered_order,
            "factor_success": result.success,
            "factor_pair": json.dumps(result.factor_pair),
            "failure_reason": result.failure_reason,
            "circuit_qubits": circuit.num_qubits,
            "circuit_clbits": circuit.num_clbits,
            "circuit_depth_before_decomposition": circuit.depth(),
            "factors_or_order_supplied_to_decoder": False,
        })
    path = OUT / "examples.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "configuration.json").write_text(json.dumps({
        "examples": [list(example) for example in EXAMPLES],
        "shots": 64,
        "seed_base": 2026071201,
        "decoder_received_true_order": False,
        "decoder_received_factors": False,
    }, indent=2, sort_keys=True))
    manifest_files = ("configuration.json", "examples.csv")
    (OUT / "completion.json").write_text(json.dumps({
        "status": "complete",
        "row_counts": {"examples": len(rows)},
        "sha256": {
            name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
            for name in manifest_files
        },
    }, indent=2, sort_keys=True))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()

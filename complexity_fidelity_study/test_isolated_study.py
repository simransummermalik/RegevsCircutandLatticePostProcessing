from collections import Counter
import csv
import json
from pathlib import Path

import pytest
from qiskit import QuantumCircuit, transpile

from complexity_fidelity_study.audit import (
    all_checks_pass,
    dimensional_split_rows,
    source_structure_audit,
)
from regev_research import circuits as _circuits  # noqa: F401
from regev_research.resource_analysis import (
    _controlled_constant_adder_counts,
    controlled_modular_multiplier_counts,
    modular_exponentiation_counts,
)


ROOT = Path(__file__).resolve().parents[1]


def _flat_counts(gate) -> Counter:
    leaves = {"x", "cx", "ccx", "cswap"}
    counts = Counter()

    def visit(operation):
        if operation.name in leaves:
            counts[operation.name] += 1
            return
        assert operation.definition is not None, operation.name
        for instruction in operation.definition.data:
            visit(instruction.operation)

    visit(gate)
    return counts


def test_ast_audit_finds_n_bit_inner_loop_independently():
    rows = source_structure_audit(ROOT)
    assert len(rows) == 8
    assert all_checks_pass(rows)
    inner = [row for row in rows if "addition loop" in str(row["check"])]
    assert {row["observed_iterators"] for row in inner} == {"reversed(range(n))"}


def test_all_exact_dimension_splits_leave_binary_work_invariant():
    rows = dimensional_split_rows((8, 16, 32, 64, 128))
    assert all_checks_pass(rows, "invariant_passed")
    assert all(row["d_times_q"] == 2 * row["n"] for row in rows)
    # The paper-style q substitution agrees with the code only at q=n.
    equal = [row for row in rows if row["code_over_paper"] == 1.0]
    assert len(equal) == 5
    assert all(row["q"] == row["n"] for row in equal)


@pytest.mark.parametrize(
    "constant,N",
    ((2, 5), (2, 9), (4, 15), (5, 21)),
)
def test_both_imported_multiplier_families_match_independent_counter(constant, N):
    from gates.haner.modular_exponentiation import (
        controlled_modular_multiplication_gate as shor_multiplier,
    )
    from gates.r_haner.modular_exponentiation import (
        controlled_modular_multiplication_gate as regev_multiplier,
    )

    n = N.bit_length()
    expected = controlled_modular_multiplier_counts(constant, N, n)
    assert _flat_counts(shor_multiplier(constant, N, n)) == expected
    assert _flat_counts(regev_multiplier(constant, N, n)) == expected


@pytest.mark.parametrize("N,base,q", ((5, 2, 2), (9, 2, 3), (15, 4, 4)))
def test_regev_exponentiation_expands_to_q_full_width_multipliers(N, base, q):
    from gates.r_haner.modular_exponentiation import modular_exponentiation_gate

    n = N.bit_length()
    assert _flat_counts(modular_exponentiation_gate(base, N, n, q)) == (
        modular_exponentiation_counts(base, N, n, q)
    )


def test_shor_exponentiation_expands_to_two_n_full_width_multipliers():
    from gates.haner.modular_exponentiation import modular_exponentiation_gate

    assert _flat_counts(modular_exponentiation_gate(2, 5, 3)) == (
        modular_exponentiation_counts(2, 5, 3, 6)
    )


def test_compiler_optimization_changes_constants_not_hidden_loop_contract():
    from gates.r_haner.modular_exponentiation import controlled_modular_multiplication_gate

    gate = controlled_modular_multiplication_gate(2, 5, 3)
    circuit = QuantumCircuit(gate.num_qubits)
    circuit.append(gate, circuit.qubits)
    compiled = [
        transpile(
            circuit,
            basis_gates=("rz", "sx", "x", "cx"),
            optimization_level=level,
            seed_transpiler=2_026_080_102,
        )
        for level in range(4)
    ]
    assert compiled[0].count_ops()["cx"] == 2192
    assert all(item.count_ops()["cx"] > 2000 for item in compiled)
    assert compiled[-1].count_ops()["cx"] <= compiled[0].count_ops()["cx"]


def test_recursive_adder_normalization_moves_toward_proved_constant_ten():
    ratios = []
    for n in (16, 64, 256, 1024, 4096):
        counts = _controlled_constant_adder_counts((1 << n) - 1, n)
        ratios.append(counts["ccx"] / (n * (n.bit_length() - 1)))
    assert ratios == sorted(ratios)
    assert 8.7 < ratios[-1] < 10.0


def test_paper_code_identity_and_prepublication_provenance_are_frozen():
    results = ROOT / "complexity_fidelity_study/results"
    provenance = json.loads((results / "paper_source_provenance.json").read_text())
    assert provenance["paper"] == "arXiv:2502.09772v2"
    assert provenance["all_files_match_prepublication_revisions"]
    assert len(provenance["files"]) == 6
    assert all(row["matches_prepublication_revision"] for row in provenance["files"])

    with (results / "paper_code_crosswalk.csv").open() as handle:
        crosswalk = list(csv.DictReader(handle))
    assert len(crosswalk) == 4
    assert crosswalk[-1]["consequence"] == (
        "implemented source complexity Theta(n^3 log n)"
    )

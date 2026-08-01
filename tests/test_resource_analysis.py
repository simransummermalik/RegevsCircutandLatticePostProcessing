from collections import Counter

import pytest
from qiskit import QuantumCircuit, transpile

# Importing the portable builder registers the vendored arithmetic package on
# sys.path, matching normal repository use.
from regev_research import circuits as _circuits  # noqa: F401
from regev_research.resource_analysis import (
    _controlled_adder_counts,
    _controlled_constant_adder_counts,
    asymptotic_leading_constants,
    canonical_cx_count,
    controlled_modular_multiplier_counts,
    full_circuit_source_counts,
    notebook_parameters,
    qft_closed_form,
)


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


def test_exact_notebook_parameter_and_qft_constants():
    perfect = notebook_parameters(16, "cover_2n")
    assert (perfect["d"], perfect["q"], perfect["total_qubits"]) == (4, 8, 65)
    assert qft_closed_form(2, 5)["canonical_cx"] == 52
    assert qft_closed_form(2, 5, 3)["saved_canonical_cx"] == 4
    constants = asymptotic_leading_constants()
    assert constants["qubits_over_n"] == 4.0
    assert constants["arithmetic_ccx_over_n_cubed_log2_n"] == 80.0


def test_controlled_adder_formula_matches_imported_gate():
    from gates.haner.adder import controlled_adder

    for n in range(1, 7):
        assert _flat_counts(controlled_adder(n)) == _controlled_adder_counts(n)


def test_recursive_constant_adder_formula_matches_imported_gate():
    from gates.haner.constant_adder import controlled_constant_adder

    for n in range(1, 7):
        for constant in (0, 1, (1 << n) - 1):
            assert _flat_counts(controlled_constant_adder(constant, n)) == (
                _controlled_constant_adder_counts(constant, n)
            )


def test_modular_multiplier_count_and_canonical_basis_validation():
    from gates.r_haner.modular_exponentiation import controlled_modular_multiplication_gate

    gate = controlled_modular_multiplication_gate(2, 5, 3)
    expected = controlled_modular_multiplier_counts(2, 5, 3)
    assert _flat_counts(gate) == expected

    circuit = QuantumCircuit(gate.num_qubits)
    circuit.append(gate, circuit.qubits)
    compiled = transpile(
        circuit,
        basis_gates=("rz", "sx", "x", "cx"),
        optimization_level=0,
    )
    assert compiled.count_ops().get("cx", 0) == canonical_cx_count(expected)


def test_full_counter_rejects_nonunit_bases():
    with pytest.raises(ValueError):
        full_circuit_source_counts(15, (3, 4), 4)

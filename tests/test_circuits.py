import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from regev_research.circuits import build_arbitrary_base_circuit
from regev_research.core import bitstring_to_vector


def _set_register(circuit, register, value):
    for i, qubit in enumerate(register):
        if (value >> i) & 1:
            circuit.x(qubit)


def _get_register(circuit, register, basis_index):
    return sum(
        ((basis_index >> circuit.find_bit(qubit).index) & 1) << i
        for i, qubit in enumerate(register)
    )


def _deterministic_output(circuit):
    state = Statevector.from_instruction(circuit)
    probabilities = np.abs(state.data) ** 2
    index = int(np.argmax(probabilities))
    assert np.isclose(probabilities[index], 1.0)
    return index


def test_controlled_modular_multiplier_contract_and_cleanup():
    from gates.r_haner.modular_exponentiation import (
        controlled_modular_multiplication_gate,
        controlled_modular_multiplication_gate_regs,
    )
    from utils.circuit_creation import create_circuit

    for control in (0, 1):
        for x in range(5):
            circuit = create_circuit(controlled_modular_multiplication_gate_regs(3), "test")
            ctrl, value, aux, flag = circuit.qregs
            _set_register(circuit, ctrl, control)
            _set_register(circuit, value, x)
            circuit.append(controlled_modular_multiplication_gate(2, 5, 3), circuit.qubits)
            output = _deterministic_output(circuit)
            expected = (2 * x) % 5 if control else x
            assert _get_register(circuit, value, output) == expected
            assert _get_register(circuit, aux, output) == 0
            assert _get_register(circuit, flag, output) == 0


def test_multiplier_domain_is_x_less_than_N_not_all_n_bit_strings():
    from gates.r_haner.modular_exponentiation import (
        controlled_modular_multiplication_gate,
        controlled_modular_multiplication_gate_regs,
    )
    from utils.circuit_creation import create_circuit

    circuit = create_circuit(controlled_modular_multiplication_gate_regs(3), "invalid")
    ctrl, value, aux, flag = circuit.qregs
    _set_register(circuit, ctrl, 1)
    _set_register(circuit, value, 6)  # invalid because N=5
    circuit.append(controlled_modular_multiplication_gate(2, 5, 3), circuit.qubits)
    output = _deterministic_output(circuit)
    assert (_get_register(circuit, aux, output), _get_register(circuit, flag, output)) != (0, 0)


def test_modular_exponentiation_contract_and_cleanup():
    from gates.r_haner.modular_exponentiation import modular_exponentiation_gate
    from utils.circuit_creation import create_circuit

    for exponent in range(4):
        circuit = create_circuit({"x": 2, "y": 3, "aux": 4}, "test")
        x, y, aux = circuit.qregs
        _set_register(circuit, x, exponent)
        _set_register(circuit, y, 1)
        circuit.append(modular_exponentiation_gate(2, 5, 3, 2), circuit.qubits)
        output = _deterministic_output(circuit)
        assert _get_register(circuit, x, output) == exponent
        assert _get_register(circuit, y, output) == pow(2, exponent, 5)
        assert _get_register(circuit, aux, output) == 0


def test_qiskit_circuit_matches_exact_N15_distribution_and_decoder():
    circuit = build_arbitrary_base_circuit(15, [4, 4], 16, measure=False)
    state = Statevector.from_instruction(circuit)
    probabilities = state.probabilities_dict(qargs=list(range(8)), decimals=12)
    decoded = {bitstring_to_vector(bits, 2, 4): float(p) for bits, p in probabilities.items()}
    assert decoded == {(0, 0): 0.5, (8, 8): 0.5}


def test_qft_sign_is_not_identifiable_from_this_probability_law():
    forward = Statevector.from_instruction(
        build_arbitrary_base_circuit(15, [4, 4], 16, inverse_qft=False, measure=False)
    ).probabilities(qargs=list(range(8)))
    inverse = Statevector.from_instruction(
        build_arbitrary_base_circuit(15, [4, 4], 16, inverse_qft=True, measure=False)
    ).probabilities(qargs=list(range(8)))
    assert np.allclose(forward, inverse)


def test_arbitrary_builder_rejects_nonunits():
    with pytest.raises(ValueError):
        build_arbitrary_base_circuit(15, [3, 4], 16)

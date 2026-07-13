"""Portable builders for the exact circuit architecture used by the notebook."""

from __future__ import annotations

import sys
from math import gcd, log2, pi
from pathlib import Path
from typing import Sequence

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import QFTGate
from qiskit_aer import AerSimulator


_EXTERNAL = Path(__file__).resolve().parents[1] / "external" / "regev-quantum-algorithm"
if str(_EXTERNAL) not in sys.path:
    sys.path.insert(0, str(_EXTERNAL))

from gates.r_haner.modular_exponentiation import modular_exponentiation_gate  # noqa: E402


def build_arbitrary_base_circuit(
    N: int,
    bases: Sequence[int],
    M: int,
    *,
    inverse_qft: bool = True,
    measure: bool = True,
    qft_cutoff: int | None = None,
) -> QuantumCircuit:
    """Build the notebook circuit with an optional truncated product QFT.

    ``qft_cutoff=None`` retains the notebook's QFTGate.  A nonnegative cutoff
    retains controlled phases whose qubit separation is at most that value;
    the arithmetic oracle and all register conventions are unchanged.
    """
    nd = int(log2(M))
    if 1 << nd != M:
        raise ValueError("M must be a power of two")
    if any(gcd(int(a), N) != 1 for a in bases):
        raise ValueError("every modular base must be coprime to N")
    n = N.bit_length()
    x_registers = [QuantumRegister(nd, name=f"x{i + 1}") for i in range(len(bases))]
    y = QuantumRegister(n, name="y")
    aux = QuantumRegister(n + 1, name="aux")
    classical = ClassicalRegister(len(bases) * nd, name="c") if measure else None
    registers = [*x_registers, y, aux]
    if classical is not None:
        registers.append(classical)
    circuit = QuantumCircuit(*registers, name=f"UniformRegev_N_{N}")
    for x in x_registers:
        circuit.h(x)
    circuit.x(y[0])
    circuit.barrier(label="modexp")
    for x, a in zip(x_registers, bases, strict=True):
        gate = modular_exponentiation_gate(int(a) % N, N, n, nd)
        circuit.append(gate, [*x, *y, *aux])
    circuit.barrier(label="qft")
    for x in x_registers:
        if qft_cutoff is None:
            qft = QFTGate(nd).inverse() if inverse_qft else QFTGate(nd)
            circuit.append(qft, x)
        else:
            if qft_cutoff < 0:
                raise ValueError("qft_cutoff must be nonnegative")
            qft_subcircuit = QuantumCircuit(nd, name=f"ApproxQFT_t{qft_cutoff}")
            for j in reversed(range(nd)):
                qft_subcircuit.h(j)
                for k in reversed(range(j)):
                    separation = j - k
                    if separation <= qft_cutoff:
                        qft_subcircuit.cp(pi / (2**separation), j, k)
            for j in range(nd // 2):
                qft_subcircuit.swap(j, nd - 1 - j)
            if inverse_qft:
                qft_subcircuit = qft_subcircuit.inverse()
            circuit.compose(qft_subcircuit, qubits=x, inplace=True)
    circuit.barrier(label="measure")
    if classical is not None:
        circuit.measure([q for x in x_registers for q in x], classical)
    return circuit


def compiled_resources(
    N: int,
    bases: Sequence[int],
    M: int,
    optimization_level: int = 1,
    seed_transpiler: int = 20260710,
) -> dict:
    circuit = build_arbitrary_base_circuit(N, bases, M, measure=True)
    compiled = transpile(
        circuit,
        AerSimulator(),
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler,
    )
    return {
        "N": N,
        "bases": [int(a) % N for a in bases],
        "M": M,
        "qubits": circuit.num_qubits,
        "logical_depth": circuit.depth(),
        "logical_ops": {str(k): int(v) for k, v in circuit.count_ops().items()},
        "compiled_depth": compiled.depth(),
        "compiled_ops": {str(k): int(v) for k, v in compiled.count_ops().items()},
    }

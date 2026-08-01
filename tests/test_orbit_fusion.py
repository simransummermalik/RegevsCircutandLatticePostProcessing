from collections import Counter
from dataclasses import replace
import inspect

import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from regev_research.circuits import build_arbitrary_base_circuit
from regev_research.core import RootedBaseFamily
from regev_research.orbit_fusion import (
    build_orbit_fused_circuit,
    build_orbit_fused_oracle,
    classify_public_relation,
    detect_all_pair_power_relations,
    factor_or_fuse,
    factor_or_fuse_all_witnesses,
    factor_or_fuse_record,
    orbit_fusion_source_counts,
    plan_power_orbit_fusion,
    positive_power_no_wrap_certificate,
)
from regev_research.resource_analysis import full_circuit_source_counts


def _set_register(circuit, register, value):
    for index, qubit in enumerate(register):
        if (int(value) >> index) & 1:
            circuit.x(qubit)


def _get_register(circuit, register, basis_index):
    return sum(
        ((basis_index >> circuit.find_bit(qubit).index) & 1) << index
        for index, qubit in enumerate(register)
    )


def _deterministic_output(circuit):
    state = Statevector.from_instruction(circuit)
    probabilities = np.abs(state.data) ** 2
    index = int(np.argmax(probabilities))
    assert np.isclose(probabilities[index], 1.0)
    return index


def _flat_counts(circuit):
    counts = Counter()
    source_primitives = {"x", "cx", "ccx", "cswap"}

    def visit(operation):
        if operation.name in source_primitives:
            counts[operation.name] += 1
            return
        definition = getattr(operation, "definition", None)
        if definition is None:
            counts[operation.name] += 1
            return
        for instruction in definition.data:
            visit(instruction.operation)

    for instruction in circuit.data:
        visit(instruction.operation)
    return counts


def test_planner_is_factor_blind_and_certifies_exact_relation():
    parameters = inspect.signature(plan_power_orbit_fusion).parameters
    assert set(parameters) == {
        "N",
        "bases",
        "exponent_width",
        "max_power",
        "exact_partition_limit",
        "allowed_relations",
    }
    plan = plan_power_orbit_fusion(15, [4, 4], 2, max_power=8)
    assert plan.verify()
    assert len(plan.groups) == 1
    group = plan.groups[0]
    assert group.fused
    assert group.weights == (1, 1)
    assert group.accumulator_width == 3
    assert plan.canonical_cx_saving_fraction > 0.2


def test_fused_oracle_is_exact_and_cleans_every_workspace_basis_state():
    plan = plan_power_orbit_fusion(15, [4, 4], 2, max_power=8)
    for first in range(4):
        for second in range(4):
            circuit = build_orbit_fused_oracle(plan)
            x1, x2, y, aux, accumulator, carry = circuit.qregs
            # Move the preparation in front of the already-built oracle.
            prepared = circuit.copy_empty_like()
            _set_register(prepared, x1, first)
            _set_register(prepared, x2, second)
            _set_register(prepared, y, 1)
            prepared.compose(circuit, inplace=True)
            output = _deterministic_output(prepared)
            expected = (pow(4, first, 15) * pow(4, second, 15)) % 15
            assert _get_register(prepared, x1, output) == first
            assert _get_register(prepared, x2, output) == second
            assert _get_register(prepared, y, output) == expected
            assert _get_register(prepared, aux, output) == 0
            assert _get_register(prepared, accumulator, output) == 0
            assert _get_register(prepared, carry, output) == 0


def test_fused_and_direct_sampler_have_identical_exponent_distribution():
    plan = plan_power_orbit_fusion(15, [4, 4], 2, max_power=8)
    direct = Statevector.from_instruction(
        build_arbitrary_base_circuit(15, [4, 4], 4, measure=False)
    ).probabilities(qargs=list(range(4)))
    fused = Statevector.from_instruction(
        build_orbit_fused_circuit(plan, measure=False)
    ).probabilities(qargs=list(range(4)))
    assert np.allclose(direct, fused, atol=1e-12)


def test_exact_resource_counter_matches_recursive_gate_expansion():
    plan = plan_power_orbit_fusion(15, [4, 4], 2, max_power=8)
    observed = _flat_counts(build_orbit_fused_oracle(plan))
    assert observed == plan.selected_arithmetic_counts


def test_no_profitable_relation_falls_back_without_extra_qubits():
    plan = plan_power_orbit_fusion(55, [4, 9, 49], 3, max_power=2)
    assert plan.verify()
    assert not any(group.fused for group in plan.groups)
    assert plan.extra_qubits == 0
    assert orbit_fusion_source_counts(plan) == full_circuit_source_counts(
        55, [4, 9, 49], 3
    )


def test_certificate_rejects_changed_relation_metadata():
    plan = plan_power_orbit_fusion(15, [4, 4], 2, max_power=8)
    bad_group = replace(plan.groups[0], weights=(1, 2))
    assert not replace(plan, groups=(bad_group,)).verify()


def test_planner_rejects_nonunit_base():
    with pytest.raises(ValueError, match="units"):
        plan_power_orbit_fusion(15, [3, 4], 2)


def test_factor_or_fuse_finds_planted_toy_factor_before_building_a_circuit():
    family = RootedBaseFamily.from_roots(15, [2, 7])
    result = factor_or_fuse(family, 2, max_power=8)
    assert result.verify()
    assert result.outcome == "classical_factor"
    assert result.factor_pair == (3, 5)
    assert result.plan is None
    assert any(
        row.power == 1 and row.classification.vector in ((1, -1), (-1, 1))
        for row in result.relations
    )
    record = factor_or_fuse_record(result)
    assert record["quantum_circuit_avoided"] is True
    assert record["factor_information_used"] is False


def test_l0_dependency_is_fused_but_factor_dependency_never_is():
    # 13 == -2 (mod 15), so the stored roots differ only by an allowed sign.
    family = RootedBaseFamily.from_roots(15, [2, 13])
    result = factor_or_fuse(family, 2, max_power=8)
    assert result.verify()
    assert result.outcome == "l0_orbit_fusion"
    assert result.factor_pair is None
    assert result.l0_relation_count == 2
    assert result.factor_relation_count == 0
    assert result.plan is not None
    assert result.plan.canonical_cx_saving_fraction > 0.2


def test_factor_or_fuse_uses_exact_baseline_when_no_dependency_is_found():
    family = RootedBaseFamily.from_roots(55, [2, 3, 7])
    result = factor_or_fuse(family, 3, max_power=2)
    assert result.verify()
    assert result.outcome == "baseline_fallback"
    assert not result.relations
    assert result.plan is not None
    assert result.plan.extra_qubits == 0


def test_public_relation_classification_rejects_nonrelations():
    family = RootedBaseFamily.from_roots(15, [2, 7])
    row = classify_public_relation(family, [1, 0])
    assert row.category == "invalid"
    assert row.root_product is None


def test_l0_fusion_preserves_relation_class_under_exact_integer_map():
    family = RootedBaseFamily.from_roots(15, [2, 13])
    compressed = RootedBaseFamily.from_roots(15, [2])
    for first in range(-3, 4):
        for second in range(-3, 4):
            original = classify_public_relation(family, [first, second])
            image = classify_public_relation(compressed, [first + second])
            assert original.base_product == image.base_product
            assert original.category == image.category
            assert original.factor_pair == image.factor_pair


def test_all_witness_policy_prevents_early_l0_hit_from_hiding_a_factor():
    family = RootedBaseFamily.from_roots(3277, [2, 3, 5, 7])
    least = factor_or_fuse(family, 6, max_power=64)
    complete = factor_or_fuse_all_witnesses(family, 6, max_power=64)
    assert least.verify() and complete.verify()
    assert least.factor_pair is None
    assert complete.outcome == "classical_factor"
    assert complete.factor_pair == (29, 113)
    witnesses = detect_all_pair_power_relations(family, max_power=64)
    pair = [row for row in witnesses if (row.anchor_index, row.target_index) == (1, 3)]
    assert [(row.power, row.classification.category) for row in pair] == [
        (8, "L0"),
        (64, "factor_yielding"),
    ]


def test_no_wrap_certificate_exactly_excludes_bounded_prime_power_relations():
    family = RootedBaseFamily.from_roots((1 << 512) + 1, [2, 3, 5, 7])
    certificate = positive_power_no_wrap_certificate(family, max_power=64)
    assert certificate.verify()
    assert certificate.certified
    assert not detect_all_pair_power_relations(family, max_power=64)
    assert not positive_power_no_wrap_certificate(
        RootedBaseFamily.from_roots(15, [2, 7]), max_power=64
    ).certified

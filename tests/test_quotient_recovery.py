from fractions import Fraction

import pytest

from regev_research.core import RootedBaseFamily
from regev_research.lattice import LLLReduction, build_augmented_lattice
from regev_research.quotient_recovery import (
    RecoveryBudget,
    adaptive_l0_suppression_recovery,
    bkz_or_deterministic_surrogate_baseline,
    enumerate_reduced_basis_combinations,
    exact_augmented_basis_deflation_recovery,
    exact_generated_l0_membership,
    exact_quotient_deduplicated_recovery,
    build_exact_unsaturated_quotient_key,
    matched_cost_recovery_suite,
    random_extra_samples_baseline,
    short_combination_recovery,
    sequential_ldar_recovery,
    standard_lll_enumeration_baseline,
)


def _small_budget(**changes):
    values = {
        "enumeration_rows": 4,
        "coefficient_bound": 1,
        "max_support": 4,
        "max_nodes": 100,
        "max_materialized_nodes": 1_000,
    }
    values.update(changes)
    return RecoveryBudget(**values)


def test_intervention_A_recovers_factor_and_reports_auditable_costs():
    family = RootedBaseFamily.from_roots(15, [2])
    result = short_combination_recovery(
        family,
        [[8]] * 5,
        16,
        scale=16,
        budget=_small_budget(),
    )

    assert result.strategy == "A_short_combination_enumeration"
    assert result.factor_pair == (3, 5)
    assert any(candidate.relation == (2,) for candidate in result.candidates)
    resources = result.resources
    assert resources.nodes_generated >= resources.nodes_visited > 0
    assert resources.modular_relation_checks > 0
    assert resources.verified_relations > 0
    assert resources.root_classifications == resources.verified_relations
    assert resources.reductions == 1
    assert resources.runtime_seconds > 0
    assert resources.peak_memory_estimate_bytes > 0
    assert "not process RSS" in resources.memory_estimate_method


def test_exact_L0_suppression_is_integer_lattice_not_rational_span():
    generators = [(2, 0), (0, 2)]
    assert exact_generated_l0_membership(generators, (4, -2))
    # This vector is in the rational span but not the integer lattice.  A
    # rational-span filter would incorrectly erase its torsion coset.
    assert not exact_generated_l0_membership(generators, (1, 1))


def test_intervention_C_suppresses_seeded_L0_multiples_but_keeps_factor_coset():
    family = RootedBaseFamily.from_roots(15, [2, 2])
    embedding = build_augmented_lattice([[0, 0]] * 6, 8, scale=1)
    dimension = len(embedding.integer_row_basis)
    identity = tuple(
        tuple(1 if i == j else 0 for j in range(dimension))
        for i in range(dimension)
    )
    controlled_reduction = LLLReduction(
        reduced_rows=embedding.integer_row_basis,
        transform_rows=identity,
        delta=Fraction(3, 4),
        backend="controlled-unreduced-basis",
    )
    result = enumerate_reduced_basis_combinations(
        family,
        embedding,
        controlled_reduction,
        budget=RecoveryBudget(
            enumeration_rows=2,
            coefficient_bound=2,
            max_support=2,
            max_nodes=100,
            max_materialized_nodes=100,
        ),
        strategy="C_controlled_test",
        ordering="shell_lexicographic",
        adaptive_l0_suppression=True,
        seed_l0_directions=[(1, -1)],
    )

    assert result.factor_pair == (3, 5)
    assert result.resources.suppressed_l0_nodes >= 1
    assert exact_generated_l0_membership(result.discovered_l0_basis, (2, -2))
    useful = [candidate for candidate in result.candidates if candidate.factor_pair]
    assert useful
    assert useful[0].relation == (1, 1)


def test_C_rejects_an_unverified_seed_and_lifted_relations_are_reverified():
    family = RootedBaseFamily.from_roots(15, [2])
    with pytest.raises(ValueError, match="not a verified L0"):
        adaptive_l0_suppression_recovery(
            family,
            [[8]] * 5,
            16,
            scale=16,
            budget=_small_budget(),
            seed_l0_directions=[(2,)],  # In L minus L0, not L0.
        )

    embedding = build_augmented_lattice([[8]] * 5, 16, scale=16)
    from regev_research.lattice import lll_reduce_augmented_lattice

    reduction = lll_reduce_augmented_lattice(embedding)
    result = enumerate_reduced_basis_combinations(
        family,
        embedding,
        reduction,
        budget=_small_budget(),
        relation_lift=lambda _projected: (1,),  # 1 is not in L for base 4 mod 15.
    )
    assert result.factor_pair is None
    assert result.resources.verified_relations == 0


def test_random_extra_samples_are_genuine_pool_rows_and_seeded_without_replacement():
    family = RootedBaseFamily.from_roots(15, [2])
    extra_pool = [[0], [4], [8], [12]]
    first = random_extra_samples_baseline(
        family,
        [[8]] * 5,
        extra_pool,
        16,
        extra_count=2,
        seed=91,
        scale=16,
        budget=_small_budget(),
    )
    second = random_extra_samples_baseline(
        family,
        [[8]] * 5,
        extra_pool,
        16,
        extra_count=2,
        seed=91,
        scale=16,
        budget=_small_budget(),
    )
    assert first.selected_extra_sample_indices == second.selected_extra_sample_indices
    assert len(set(first.selected_extra_sample_indices)) == 2
    assert first.resources.input_samples == 5
    assert first.resources.extra_samples_used == 2
    with pytest.raises(ValueError, match="extra_count"):
        random_extra_samples_baseline(
            family,
            [[8]] * 5,
            [],
            16,
            extra_count=1,
            seed=0,
            scale=16,
        )


def test_bkz_is_verified_or_fallback_is_unambiguously_not_bkz():
    family = RootedBaseFamily.from_roots(15, [2])
    result = bkz_or_deterministic_surrogate_baseline(
        family,
        [[8]] * 5,
        16,
        block_size=3,
        scale=16,
        budget=_small_budget(enumeration_rows=3, max_support=3),
    )
    if "verified_fpylll_BKZ" in result.strategy:
        assert "transform verified" in result.resources.reduction_backend
    else:
        assert result.strategy.endswith("NOT_BKZ")
        assert "NOT BKZ" in result.resources.reduction_backend
        assert "not reported as BKZ" in result.interpretation


def test_matched_suite_uses_common_node_cap_and_includes_all_required_arms():
    family = RootedBaseFamily.from_roots(15, [2])
    budget = _small_budget(max_nodes=20, enumeration_rows=3, max_support=3)
    comparison = matched_cost_recovery_suite(
        family,
        [[8]] * 5,
        [[0], [8]],
        16,
        extra_count=1,
        seed=7,
        scale=16,
        budget=budget,
        block_size=3,
    )
    names = {result.strategy for result in comparison.results}
    assert "baseline_standard_LLL_enumeration" in names
    assert "A_short_combination_enumeration" in names
    assert "B_exact_unsaturated_quotient_deduplication" in names
    assert "C_adaptive_exact_L0_suppression" in names
    assert "baseline_random_genuine_extra_samples" in names
    assert any("BKZ" in name for name in names)
    assert all(result.resources.node_budget == 20 for result in comparison.results)
    assert all(result.resources.nodes_visited <= 20 for result in comparison.results)
    assert "not assumed equal" in comparison.matching_rule


def test_standard_baseline_uses_same_finite_search_space_as_A():
    family = RootedBaseFamily.from_roots(15, [2])
    budget = _small_budget()
    standard = standard_lll_enumeration_baseline(
        family, [[8]] * 5, 16, scale=16, budget=budget
    )
    intervention = short_combination_recovery(
        family, [[8]] * 5, 16, scale=16, budget=budget
    )
    assert standard.resources.nodes_generated == intervention.resources.nodes_generated
    assert standard.resources.nodes_visited == intervention.resources.nodes_visited
    assert standard.factor_pair == intervention.factor_pair == (3, 5)


def test_exact_quotient_key_preserves_unsaturated_torsion_and_handles_zero_U():
    family = RootedBaseFamily.from_roots(15, [14, 14])
    zero = build_exact_unsaturated_quotient_key(family, [])
    assert zero.invariants.rank == 0
    assert zero((1, 1), ()) != zero((3, 3), ())

    helper = build_exact_unsaturated_quotient_key(
        family, [(2, 0), (0, 2)]
    )
    assert helper.invariants.hnf_basis == ((2, 0), (0, 2))
    assert helper.invariants.smith_diagonal == (2, 2)
    assert helper.invariants.torsion_order == 4
    assert helper.invariants.saturation_index_reported_not_applied == 4
    assert helper((1, 1), ()) == helper((3, 3), ())
    assert helper((1, 1), ()) != helper((0, 0), ())
    assert "unsaturated" in helper.invariants.canonicalization


def test_intervention_B_exactly_deduplicates_modulo_integer_U():
    family = RootedBaseFamily.from_roots(15, [14, 14])
    result = exact_quotient_deduplicated_recovery(
        family,
        [[0, 0]] * 6,
        8,
        verified_l0_directions=[(2, 0), (0, 2)],
        scale=1,
        budget=RecoveryBudget(
            enumeration_rows=2,
            coefficient_bound=2,
            max_support=2,
            max_nodes=100,
            max_materialized_nodes=100,
        ),
    )
    assert result.strategy == "B_exact_unsaturated_quotient_deduplication"
    assert result.resources.duplicate_relation_nodes > 0
    assert result.quotient_invariants is not None
    assert result.quotient_invariants.smith_diagonal == (2, 2)
    assert result.factor_pair is None
    with pytest.raises(ValueError, match="zero U"):
        exact_quotient_deduplicated_recovery(
            family,
            [[0, 0]] * 6,
            8,
            verified_l0_directions=[(2, 0)],
            scale=1,
            root_blind=True,
        )


def test_LDAR_updates_exact_U_repeats_then_consumes_only_fresh_pool_indices():
    family = RootedBaseFamily.from_roots(15, [14, 14])
    budget = RecoveryBudget(
        enumeration_rows=2,
        coefficient_bound=2,
        max_support=2,
        max_nodes=100,
        max_materialized_nodes=100,
    )
    result = sequential_ldar_recovery(
        family,
        [[0, 0]] * 6,
        [[0, 0], [0, 0]],
        8,
        frozen_max_sample_count=8,
        fresh_sample_seed=3,
        samples_per_acquisition=1,
        scale=1,
        budget=budget,
    )
    assert result.factor_pair is None
    assert result.final_sample_count == 8
    assert result.termination_reason == "frozen_max_sample_count_reached"
    assert len(result.selected_fresh_sample_indices) == 2
    assert len(set(result.selected_fresh_sample_indices)) == 2
    assert result.stages[0].sample_count == 6
    assert result.stages[0].u_changed
    assert result.stages[1].sample_count == 6  # rerun after exact U update
    assert not result.stages[1].u_changed
    assert result.final_u == ((1, 0), (0, 1))
    assert result.final_quotient.smith_diagonal == (1, 1)
    assert all(stage.resources.reductions == 1 for stage in result.stages)
    assert result.total_resources.reductions == len(result.stages)


def test_LDAR_root_blind_ablation_only_checks_L_and_cannot_update_U_or_factor():
    family = RootedBaseFamily.from_roots(15, [14, 14])
    result = sequential_ldar_recovery(
        family,
        [[0, 0]] * 6,
        [[0, 0]],
        8,
        frozen_max_sample_count=7,
        fresh_sample_seed=9,
        scale=1,
        budget=RecoveryBudget(
            enumeration_rows=2,
            coefficient_bound=1,
            max_support=2,
            max_nodes=20,
            max_materialized_nodes=20,
        ),
        root_blind=True,
    )
    assert result.root_blind
    assert result.factor_pair is None
    assert result.final_u == ()
    assert result.final_quotient.rank == 0
    assert result.total_resources.root_classifications == 0
    assert result.total_resources.suppressed_l0_nodes == 0
    assert all(
        candidate_class == "L_unclassified_root_blind"
        for stage in result.stages
        for candidate_class in stage.candidate_classes
    )


def test_root_blind_execution_does_not_even_read_root_metadata(monkeypatch):
    family = RootedBaseFamily.from_roots(15, [14, 14])

    def forbidden_roots(_self):
        raise AssertionError("root-blind path accessed roots")

    monkeypatch.setattr(RootedBaseFamily, "roots", property(forbidden_roots))
    result = sequential_ldar_recovery(
        family,
        [[0, 0]] * 6,
        [],
        8,
        frozen_max_sample_count=6,
        fresh_sample_seed=0,
        scale=1,
        budget=RecoveryBudget(
            enumeration_rows=2,
            coefficient_bound=1,
            max_support=2,
            max_nodes=10,
            max_materialized_nodes=10,
        ),
        root_blind=True,
    )
    assert result.total_resources.root_classifications == 0


def test_LDAR_reports_factor_and_stage_resources_at_initial_sample_count():
    family = RootedBaseFamily.from_roots(15, [2])
    result = sequential_ldar_recovery(
        family,
        [[8]] * 5,
        [],
        16,
        frozen_max_sample_count=5,
        fresh_sample_seed=1,
        scale=16,
        budget=_small_budget(),
    )
    assert result.factor_pair == (3, 5)
    assert result.termination_reason == "factor_found_from_stored_roots"
    assert len(result.stages) == 1
    assert result.stages[0].sample_count == 5
    assert result.stages[0].factor_pair == (3, 5)
    assert result.stages[0].resources.root_classifications > 0


def test_exact_augmented_basis_row_deflation_exposes_next_factor_relation():
    # Exact dual-coset samples for L={z: z1+z2 even}.  Initial LLL returns the
    # equal-norm relations (1,-1) then (1,1).  With retained roots (2,2), the
    # first is L0.  Deleting that actual reduced basis row and rectangular
    # re-LLL exposes the second, factor-bearing relation.
    family = RootedBaseFamily.from_roots(15, [2, 2])
    result = exact_augmented_basis_deflation_recovery(
        family,
        [[8, 8]] * 6,
        16,
        scale=4,
        max_deletions=2,
    )
    assert result.factor_pair == (3, 5)
    assert result.factor_relation == (1, 1)
    assert len(result.deleted_rows) == 1
    deleted = result.deleted_rows[0]
    assert deleted.projected_l0_relation == (1, -1)
    assert deleted.root_product == 1
    assert deleted.primitive_in_current_free_row_basis
    assert exact_generated_l0_membership(result.relation_u, (1, -1))
    assert result.resources.reductions == 2  # initial square LLL + rectangular re-LLL
    assert any("rectangular exact row basis" in name for name in result.resources.reduction_backends)
    assert "not orthogonal projection" in result.interpretation

import inspect

from regev_research.quotient_experiments import (
    CIRCUIT_SURROGATE_MODEL,
    DEVELOPMENT_SEMIPRIMES,
    FINITE_GAUSSIAN_MODEL,
    FROZEN_QUOTIENT_EXPERIMENT,
    HELDOUT_SEMIPRIMES,
    QUOTIENT_MODEL_LABELS,
    THEOREM_NOISY_DUAL_MODEL,
    UNIFORM_HARD_BOX_MODEL,
    deterministic_model_seed,
    deterministic_small_prime_family,
    exact_finite_discrete_gaussian_model,
    exact_uniform_hard_box_model,
    frozen_manifest,
    sample_circuit_derived_readout_corruption_surrogate,
    sample_exact_finite_discrete_gaussian,
    sample_exact_uniform_hard_box,
    sample_theorem_consistent_noisy_dual,
)


def test_frozen_semiprime_manifests_are_disjoint_prime_products():
    assert isinstance(DEVELOPMENT_SEMIPRIMES, tuple)
    assert isinstance(HELDOUT_SEMIPRIMES, tuple)
    assert len(DEVELOPMENT_SEMIPRIMES) == 25
    assert len(HELDOUT_SEMIPRIMES) == 20
    assert not ({case.N for case in DEVELOPMENT_SEMIPRIMES} & {case.N for case in HELDOUT_SEMIPRIMES})
    allowed_primes = {79, 83, 89, 97, 101, 103, 107}
    assert all(case.p in allowed_primes and case.q in allowed_primes for case in HELDOUT_SEMIPRIMES)
    assert all(case.N == case.p * case.q for case in (*DEVELOPMENT_SEMIPRIMES, *HELDOUT_SEMIPRIMES))
    assert HELDOUT_SEMIPRIMES[0].N == 6557
    assert HELDOUT_SEMIPRIMES[-1].N == 10807
    assert 103 * 107 not in {case.N for case in HELDOUT_SEMIPRIMES}


def test_freeze_parameters_seeds_and_budgets_are_literal_and_deterministic():
    freeze = FROZEN_QUOTIENT_EXPERIMENT
    assert (freeze.finite_modulus_D, freeze.gaussian_radius_R) == (64, 16)
    assert freeze.finite_reconstruction_scale == 13
    assert freeze.sample_counts == (7, 8, 9, 10, 11)
    assert freeze.recovery_budget.max_nodes == 50
    assert freeze.ldar_stage_budget.max_nodes == 25
    assert freeze.max_ldar_rounds_per_sample_count == 2
    assert freeze.quotient_relation_box_bound == 16
    assert freeze.quotient_gap_log2_threshold == 0
    assert freeze.predictor_diversity_relation_bound == 2
    first = deterministic_model_seed(3, FINITE_GAUSSIAN_MODEL, 9, 4)
    assert first == deterministic_model_seed(3, FINITE_GAUSSIAN_MODEL, 9, 4)
    assert first != deterministic_model_seed(3, UNIFORM_HARD_BOX_MODEL, 9, 4)
    manifest = frozen_manifest()
    assert manifest["heldout_executed"] is False
    assert manifest["heldout_count"] == 20


def test_factor_blind_small_prime_family_is_deterministic_and_has_no_factor_inputs():
    signature = inspect.signature(deterministic_small_prime_family)
    assert tuple(signature.parameters) == ("N", "dimension")
    ordinary = deterministic_small_prime_family(1763)
    assert ordinary.roots == (2, 3, 5)
    # N=15 filters roots 3 and 5 solely by gcd and expands deterministically.
    expanded = deterministic_small_prime_family(15)
    assert expanded.roots == (2, 7, 11)
    assert deterministic_small_prime_family(15) == expanded
    for sampler in (
        sample_exact_uniform_hard_box,
        sample_exact_finite_discrete_gaussian,
        sample_theorem_consistent_noisy_dual,
        sample_circuit_derived_readout_corruption_surrogate,
    ):
        parameters = inspect.signature(sampler).parameters
        assert not ({"p", "q", "factors", "orders"} & set(parameters))


def test_exact_models_are_normalized_labelled_and_sample_deterministically():
    family = deterministic_small_prime_family(1763)
    uniform = exact_uniform_hard_box_model(family)
    gaussian = exact_finite_discrete_gaussian_model(family)
    assert uniform.model_label == UNIFORM_HARD_BOX_MODEL
    assert gaussian.model_label == FINITE_GAUSSIAN_MODEL
    assert uniform.probabilities.shape == gaussian.probabilities.shape == (64, 64, 64)
    assert abs(float(uniform.probabilities.sum()) - 1.0) < 1e-14
    assert abs(float(gaussian.probabilities.sum()) - 1.0) < 1e-14
    assert not uniform.probabilities.flags.writeable
    assert not gaussian.probabilities.flags.writeable

    seed = deterministic_model_seed(0, UNIFORM_HARD_BOX_MODEL, 7, 0)
    first = sample_exact_uniform_hard_box(family, 7, seed)
    second = sample_exact_uniform_hard_box(family, 7, seed)
    assert first == second
    gaussian_batch = sample_exact_finite_discrete_gaussian(family, 7, seed)
    assert gaussian_batch.model_label == FINITE_GAUSSIAN_MODEL


def test_theorem_and_surrogate_models_are_deterministic_and_honestly_labelled():
    family = deterministic_small_prime_family(15)
    theorem_seed = deterministic_model_seed(0, THEOREM_NOISY_DUAL_MODEL, 7, 0)
    theorem = sample_theorem_consistent_noisy_dual(family, 7, theorem_seed)
    assert theorem == sample_theorem_consistent_noisy_dual(family, 7, theorem_seed)
    assert theorem.model_label == THEOREM_NOISY_DUAL_MODEL
    assert theorem.metadata_dict()["theorem_sufficient_inequality"] is True
    assert theorem.metadata_dict()["generator_oracle_withheld_from_recovery"] is True
    assert all(0 <= value < theorem.modulus for row in theorem.samples for value in row)

    surrogate_seed = deterministic_model_seed(0, CIRCUIT_SURROGATE_MODEL, 7, 0)
    surrogate = sample_circuit_derived_readout_corruption_surrogate(
        family, 7, surrogate_seed
    )
    assert surrogate == sample_circuit_derived_readout_corruption_surrogate(
        family, 7, surrogate_seed
    )
    assert surrogate.model_label == CIRCUIT_SURROGATE_MODEL
    assert "surrogate" in surrogate.model_label
    assert surrogate.metadata_dict()["is_gate_level_or_hardware_noise_model"] is False
    assert surrogate.latent_samples is not None
    assert set(QUOTIENT_MODEL_LABELS) == {
        UNIFORM_HARD_BOX_MODEL,
        FINITE_GAUSSIAN_MODEL,
        THEOREM_NOISY_DUAL_MODEL,
        CIRCUIT_SURROGATE_MODEL,
    }

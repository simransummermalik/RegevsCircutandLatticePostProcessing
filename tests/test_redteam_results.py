import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "redteam"


def _csv(name):
    with (RESULTS / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_frozen_result_tables_are_complete_at_the_declared_N_unit():
    configuration = json.loads((RESULTS / "configuration.json").read_text())
    trials = _csv("trials.csv")
    n_level = _csv("n_level.csv")
    families = _csv("families.csv")
    assert configuration["heldout_N_count"] == 24
    assert configuration["primary_generalization_unit"] == "N"
    assert len(families) == 24 * 6
    assert len(n_level) == 24 * 6 * 3
    assert len(trials) == 24 * 6 * 3 * 32
    assert len({row["seed"] for row in trials}) == len(trials)
    assert all(row["selector_setup_factor_leak"] == "False" for row in families)


def test_model_C_always_satisfies_the_declared_theoretical_inequality():
    model_c = [
        row for row in _csv("trials.csv")
        if row["model"] == "C_theoretical_noisy_dual"
    ]
    assert model_c
    assert all(row["theorem_sufficient_inequality"] == "True" for row in model_c)
    assert all(
        float(row["maximum_realized_torus_error"]) < float(row["noise_bound"])
        for row in model_c
    )


def test_negative_association_is_model_specific_not_generalized_to_C():
    statistics = json.loads((RESULTS / "model_statistics.json").read_text())
    models = statistics["models"]
    assert models["A_uniform_hard_box"]["negative_relationship_persists"] is True
    assert models["B_exact_gaussian_state"]["negative_relationship_persists"] is True
    assert models["C_theoretical_noisy_dual"]["negative_relationship_persists"] is False
    assert models["C_theoretical_noisy_dual"]["N_cluster_bootstrap_ci_low"] < 0
    assert models["C_theoretical_noisy_dual"]["N_cluster_bootstrap_ci_high"] > 0


def test_every_exact_A_B_row_satisfies_its_weighted_parseval_check():
    rows = _csv("exact_models.csv")
    assert len(rows) == 24 * 6 * 2
    assert max(float(row["parseval_absolute_error"]) for row in rows) < 3e-9


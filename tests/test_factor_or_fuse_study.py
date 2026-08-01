import csv
import hashlib
import inspect
import json
from pathlib import Path

from factor_or_fuse_study.freeze import (
    ARMS,
    HELDOUT_MODULI,
    MAX_POWER,
    method_input_from_modulus,
    validate_freeze,
)
from factor_or_fuse_study.run_study import run_method_on_modulus


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "factor_or_fuse_study" / "results"


def test_protocol_freeze_and_method_factor_firewall():
    assert validate_freeze()
    assert len(HELDOUT_MODULI) == len(set(HELDOUT_MODULI)) == 24
    assert MAX_POWER == 64
    assert tuple(inspect.signature(run_method_on_modulus).parameters) == ("N", "arm")
    assert "factor_manifest" not in inspect.getsource(run_method_on_modulus)
    for N in HELDOUT_MODULI:
        method_input = method_input_from_modulus(N)
        assert method_input.setup_factor is None
        assert method_input.family is not None
        assert method_input.family.roots == (2, 3, 5, 7)
        assert method_input.family.bases == (4, 9, 25, 49)
        assert (method_input.dimension, method_input.exponent_width) == (4, 8)


def test_sealed_primary_results_and_raw_pre_manifest_hash():
    summary = json.loads((RESULTS / "summary.json").read_text())
    raw = RESULTS / "raw_method_rows.json"
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == summary[
        "raw_method_rows_sha256_before_factor_manifest_load"
    ]
    complete = summary["complete_method_summary"]
    assert complete["N_count"] == 24
    assert complete["factor_count"] == 0
    assert complete["fused_count"] == 1
    assert complete["fallback_count"] == 23
    assert complete["all_certificates_passed"] is True
    assert summary["preregistered_hypothesis_passed"] is False
    assert summary["known_factors_used_by_method"] is False
    rows = list(csv.DictReader((RESULTS / "heldout_per_arm.csv").open()))
    assert len(rows) == len(HELDOUT_MODULI) * len(ARMS)
    assert all(row["posthoc_factor_match"] == "True" for row in rows)


def test_single_heldout_fusion_and_all_witness_sensitivity():
    rows = [
        row
        for row in csv.DictReader((RESULTS / "heldout_per_arm.csv").open())
        if row["arm"] == "complete_cost_optimal_factor_or_fuse_K64"
        and row["outcome"] == "fused"
    ]
    assert len(rows) == 1
    row = rows[0]
    assert int(row["N"]) == 35237
    assert int(row["canonical_cx_saved"]) == 537154
    assert int(row["extra_qubits"]) == 14
    assert int(row["baseline_full_width_multiplier_calls"]) == 32
    assert int(row["selected_full_width_multiplier_calls"]) == 29
    sensitivity = json.loads(
        (RESULTS / "all_witness_heldout_sensitivity.json").read_text()
    )
    assert sensitivity == {
        "N_count": 24,
        "all_verified": True,
        "factor_count": 0,
        "fused_count": 1,
        "outcome_change_count": 0,
        "status": "posthoc_sensitivity_not_new_holdout",
    }


def test_published_toy_audit_and_descriptive_scaling_limitation():
    published = {
        row["label"]: row
        for row in csv.DictReader((RESULTS / "published_benchmark_audit.csv").open())
    }
    assert published["Falco_2026_N15"]["factor_pair"] == "[3, 5]"
    assert published["Falco_2026_N15"]["distinct_base_residues"] == "1"
    assert published["Pawlitko_2026_N21"]["factor_pair"] == "[3, 7]"
    scaling = {
        int(row["bit_length"]): row
        for row in csv.DictReader(
            (RESULTS / "scaling_census" / "by_bit_length.csv").open()
        )
    }
    assert scaling[12]["any_relation_count"] == "50"
    assert scaling[12]["factor_missed_by_least_policy_count"] == "1"
    assert scaling[16]["any_relation_count"] == "4"
    assert scaling[20]["any_relation_count"] == "1"
    assert all(
        scaling[bits]["any_relation_count"] == "0"
        for bits in scaling
        if bits >= 24
    )
    assert all(
        scaling[bits]["no_wrap_certified_count"] == "100"
        for bits in (1024, 1536, 2048)
    )

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_runs import validate

from lifetime_integrity.consolidation import CONSOLIDATORS
from lifetime_integrity.harness import default_budget, run_delayed_credit, run_drift
from lifetime_integrity.lifetime import (
    LifetimeConfig,
    generate_delayed_credit_lifetime,
    generate_drift_lifetime,
)
from lifetime_integrity.mechanisms import DRIFT_MECHANISMS

SEED = 20260902


@pytest.fixture(scope="module")
def drift_runs():
    lt = generate_drift_lifetime(LifetimeConfig(seed=SEED, epochs=12))
    b = default_budget(lt)
    return [run_drift(lt, a, b).manifest for a in DRIFT_MECHANISMS]


@pytest.fixture(scope="module")
def credit_runs():
    lt = generate_delayed_credit_lifetime(
        LifetimeConfig(seed=SEED, epochs=14, delayed_outcomes_per_epoch=1.5)
    )
    b = default_budget(lt)
    return [run_delayed_credit(lt, a, b).manifest for a in CONSOLIDATORS]


def test_matched_pilot_runs_are_valid(drift_runs, credit_runs):
    assert validate(drift_runs)["valid_for_comparison"], validate(drift_runs)["reasons"]
    assert validate(credit_runs)["valid_for_comparison"], validate(credit_runs)["reasons"]


def test_different_corruption_processes_are_rejected(drift_runs):
    runs = copy.deepcopy(drift_runs)
    runs[0]["lifetime_config"]["p_misinformation"] = 0.5
    runs[0]["config_lock_sha256"] = "tampered"
    report = validate(runs)
    assert not report["valid_for_comparison"]
    assert "arms_ran_different_corruption_processes" in report["reasons"]
    assert "arms_disagree_on_config_lock_sha256" in report["reasons"]


def test_audit_field_leak_is_rejected(drift_runs):
    runs = copy.deepcopy(drift_runs)
    runs[0]["audit_leak_count"] = 3
    assert "audit_field_leak" in validate(runs)["reasons"]


def test_read_ceiling_breach_is_rejected(drift_runs):
    runs = copy.deepcopy(drift_runs)
    runs[0]["budget_actual"]["evidence_reads"] = runs[0]["budget_ceiling"]["evidence_reads_ceiling"] + 1
    assert any(r.startswith("read_ceiling_exceeded") for r in validate(runs)["reasons"])


def test_exhausted_read_budget_is_surfaced(drift_runs):
    runs = copy.deepcopy(drift_runs)
    runs[0]["budget_actual"]["exhausted_reads"] = 4
    assert any(r.startswith("read_budget_exhausted") for r in validate(runs)["reasons"])


def test_unequal_budget_ceilings_are_rejected(drift_runs):
    runs = copy.deepcopy(drift_runs)
    runs[0]["budget_ceiling"]["evidence_reads_ceiling"] *= 4
    assert "budget_mismatch:evidence_reads_ceiling" in validate(runs)["reasons"]


def test_ceiling_effect_invalidates_the_configuration(drift_runs):
    runs = copy.deepcopy(drift_runs)
    for r in runs:
        r["metrics"]["canonical_accuracy"] = 0.99
    assert "benchmark_at_ceiling" in validate(runs)["reasons"]


def test_floor_effect_invalidates_the_configuration(drift_runs):
    runs = copy.deepcopy(drift_runs)
    for r in runs:
        r["metrics"]["canonical_accuracy"] = 0.05
    assert "benchmark_at_floor" in validate(runs)["reasons"]


def test_inert_metric_is_reported(drift_runs):
    runs = copy.deepcopy(drift_runs)
    for r in runs:
        r["metrics"]["unsupported_belief_rate"] = 0.0
    assert any(r.startswith("inert_metrics") for r in validate(runs)["reasons"])


def test_unsupported_belief_is_out_of_scope_for_class_b(credit_runs):
    """Every EXP-B001 arm shares an evidence-derived substrate, so this metric
    is structurally zero there and must not be demanded of it."""
    assert all(r["metrics"]["unsupported_belief_rate"] == 0.0 for r in credit_runs)
    assert validate(credit_runs)["valid_for_comparison"]


def test_missing_drift_reference_arm_is_rejected(drift_runs):
    runs = [r for r in copy.deepcopy(drift_runs) if r["arm"] != "unconstrained-accumulator"]
    assert any(r.startswith("missing_required_arms") for r in validate(runs)["reasons"])


def test_regrounding_arm_is_required(drift_runs):
    keep = {"unconstrained-accumulator", "lossy-latent", "last-write-wins"}
    runs = [r for r in copy.deepcopy(drift_runs) if r["arm"] in keep]
    assert "no_regrounding_arm_present" in validate(runs)["reasons"]


def test_nonpilot_claim_is_rejected(drift_runs):
    """A uniform confirmatory claim is rejected outright.

    Narrowed in Phase 2. The original test mutated a single arm and asserted
    this reason, which passed only because the pre-Phase-2 validator collapsed
    "some arm is not PILOT" and "the set claims a disallowed classification"
    into one check. DEVELOPMENT is now an allowed classification, so the two
    conditions are distinguished and each is asserted separately here and in
    `test_mixed_classifications_are_rejected`. Both still fail closed.
    """
    runs = copy.deepcopy(drift_runs)
    for r in runs:
        r["classification"] = "CONFIRMATORY"
    report = validate(runs)
    assert not report["valid_for_comparison"]
    assert "input_run_already_claims_nonpilot_status" in report["reasons"]


def test_mixed_classifications_are_rejected(drift_runs):
    runs = copy.deepcopy(drift_runs)
    runs[0]["classification"] = "CONFIRMATORY"
    report = validate(runs)
    assert not report["valid_for_comparison"]
    assert any(r.startswith("mixed_classifications") for r in report["reasons"])


def test_missing_classification_is_rejected(drift_runs):
    runs = copy.deepcopy(drift_runs)
    del runs[0]["classification"]
    report = validate(runs)
    assert not report["valid_for_comparison"]
    assert "missing_classification" in report["reasons"]


def test_development_runs_require_a_pinned_commit(drift_runs):
    """DEVELOPMENT is allowed, but only with provenance a reader can check."""
    runs = copy.deepcopy(drift_runs)
    for r in runs:
        r["classification"] = "DEVELOPMENT"
    report = validate(runs)
    assert not report["valid_for_comparison"]
    assert "missing_git_commit_for_nonpilot" in report["reasons"]


def test_mixed_experiments_are_rejected(drift_runs, credit_runs):
    report = validate(copy.deepcopy(drift_runs) + copy.deepcopy(credit_runs))
    assert not report["valid_for_comparison"]
    assert any(r.startswith("mixed_experiments") for r in report["reasons"])

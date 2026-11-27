
import pytest

from lifetime_integrity.consolidation import CONSOLIDATORS
from lifetime_integrity.harness import default_budget, run_delayed_credit, run_drift, source_tree_sha256
from lifetime_integrity.lifetime import (
    LifetimeConfig,
    generate_delayed_credit_lifetime,
    generate_drift_lifetime,
)
from lifetime_integrity.mechanisms import DRIFT_MECHANISMS

SEED = 20260902


@pytest.fixture(scope="module")
def drift_lifetime():
    return generate_drift_lifetime(LifetimeConfig(seed=SEED, epochs=10))


@pytest.fixture(scope="module")
def credit_lifetime():
    return generate_delayed_credit_lifetime(
        LifetimeConfig(seed=SEED, epochs=12, delayed_outcomes_per_epoch=1.5)
    )


@pytest.mark.parametrize("arm", sorted(DRIFT_MECHANISMS))
def test_drift_run_is_clean_and_within_budget(drift_lifetime, arm):
    budget = default_budget(drift_lifetime)
    r = run_drift(drift_lifetime, arm, budget)
    m = r.manifest
    assert m["audit_leak_count"] == 0
    assert m["invalidation_reasons"] == []
    assert m["classification"] == "PILOT"
    assert m["experiment"] == "EXP-A001"
    assert m["budget_actual"]["evidence_reads"] <= budget.evidence_reads_ceiling
    assert m["budget_actual"]["maintenance_ops"] <= budget.maintenance_ops_ceiling
    assert len(r.records) == len(drift_lifetime.probes())


def test_drift_runs_are_reproducible(drift_lifetime):
    a = run_drift(drift_lifetime, "lossy-latent", default_budget(drift_lifetime))
    b = run_drift(drift_lifetime, "lossy-latent", default_budget(drift_lifetime))
    assert a.manifest["metrics"] == b.manifest["metrics"]


def test_manifest_carries_full_provenance(drift_lifetime):
    m = run_drift(drift_lifetime, "last-write-wins").manifest
    for field in (
        "config_lock_sha256", "lifetime_spec_sha256", "source_tree_sha256",
        "generator_version", "lifetime_config", "environment", "budget_ceiling",
    ):
        assert m[field], f"missing provenance field {field}"
    assert m["config_lock_sha256"] == drift_lifetime.config_lock
    assert m["git_commit"] is None, "pilot manifests must not claim a commit they do not have"


def test_source_tree_hash_is_stable():
    assert source_tree_sha256() == source_tree_sha256()


def test_every_arm_faces_the_identical_lifetime(drift_lifetime):
    locks = {run_drift(drift_lifetime, a).manifest["lifetime_spec_sha256"] for a in DRIFT_MECHANISMS}
    assert len(locks) == 1


def test_answers_outside_the_option_set_are_scored_as_abstentions(drift_lifetime):
    class Rogue:
        name = "rogue"

        def __init__(self, log, budget):
            pass

        def observe(self, obs):
            pass

        def on_gap(self, ev):
            pass

        def on_context_shift(self, ev):
            pass

        def answer(self, query):
            from lifetime_integrity.mechanisms import Answer

            return Answer("NOT-AN-OPTION", 1.0, ())

        def state_bytes(self):
            return 0

    DRIFT_MECHANISMS["rogue"] = Rogue
    try:
        r = run_drift(drift_lifetime, "rogue")
        assert r.manifest["metrics"]["abstention_rate"] == 1.0
        assert r.manifest["metrics"]["unsupported_belief_rate"] == 0.0
    finally:
        del DRIFT_MECHANISMS["rogue"]


def test_stream_and_runner_must_match(drift_lifetime, credit_lifetime):
    with pytest.raises(ValueError):
        run_delayed_credit(drift_lifetime, "uniform-blame")
    with pytest.raises(ValueError):
        run_drift(credit_lifetime, "last-write-wins")


def test_unknown_arm_is_rejected(drift_lifetime):
    with pytest.raises(KeyError):
        run_drift(drift_lifetime, "no-such-mechanism")


@pytest.mark.parametrize("arm", sorted(CONSOLIDATORS))
def test_delayed_credit_run_is_clean(credit_lifetime, arm):
    r = run_delayed_credit(credit_lifetime, arm)
    m = r.manifest
    assert m["audit_leak_count"] == 0
    assert m["invalidation_reasons"] == []
    assert m["experiment"] == "EXP-B001"
    assert m["delayed_outcomes_seen"] > 0
    c = m["consolidation_metrics"]
    assert 0.0 <= c["attribution_precision"] <= 1.0
    assert 0.0 <= c["attribution_recall"] <= 1.0


def test_all_consolidators_see_the_same_outcomes(credit_lifetime):
    seen = {run_delayed_credit(credit_lifetime, a).manifest["delayed_outcomes_seen"] for a in CONSOLIDATORS}
    assert len(seen) == 1


def test_uniform_blame_damages_slots_it_should_not_have_touched(credit_lifetime):
    """Blaming everything repairs the culprit and wrecks the innocents."""
    c = run_delayed_credit(credit_lifetime, "uniform-blame").manifest["consolidation_metrics"]
    assert c["attribution_recall"] > 0
    assert c["collateral_revision_rate"] > 0
    assert c["decoy_accuracy_delta"] < 0


def test_no_consolidation_never_revises(credit_lifetime):
    c = run_delayed_credit(credit_lifetime, "no-consolidation").manifest["consolidation_metrics"]
    assert c["revisions"] == 0
    assert c["attribution_precision"] == 0.0

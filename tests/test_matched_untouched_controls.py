import copy
import sys
from pathlib import Path

from lifetime_integrity.consolidation import CONSOLIDATORS, ConsolidationReport
from lifetime_integrity.harness import (
    CONFIRMATORY_READ_CEILING_MULTIPLIER,
    default_budget,
    run_delayed_credit,
    run_drift,
)
from lifetime_integrity.lifetime import (
    LifetimeConfig,
    generate_delayed_credit_lifetime,
    generate_drift_lifetime,
)
from lifetime_integrity.mechanisms import DRIFT_MECHANISMS
from lifetime_integrity.metrics import (
    ProbeRecord,
    _matched_untouched_controls,
    excess_net_repair,
    score_consolidation,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_runs import validate

SEED = 20260903


def rec(event_id: int, t: int, slot: tuple[str, str], correct: bool = True) -> ProbeRecord:
    context, key = slot
    return ProbeRecord(
        event_id=event_id,
        t=t,
        epoch=0,
        context=context,
        key=key,
        probe_class="fresh",
        options=("A", "B"),
        canonical="A",
        superseded=(),
        ever_asserted=("A", "B"),
        answer="A" if correct else "B",
        confidence=0.9,
        support=(),
    )


def synthetic_records() -> list[ProbeRecord]:
    slots = [("C", key) for key in ("a", "b", "c", "d", "e", "f", "g")]
    records = []
    eid = 0
    for slot in slots:
        for t in (10, 20, 40, 60, 80, 90):
            eid += 1
            records.append(rec(eid, t, slot))
    return records


def synthetic_outcomes() -> list[dict]:
    return [
        {
            "event_id": 100,
            "t": 50,
            "responsible_slot": ["C", "a"],
            "consulted": [["C", "a"], ["C", "b"]],
        },
        {
            "event_id": 101,
            "t": 70,
            "responsible_slot": ["C", "c"],
            "consulted": [["C", "c"], ["C", "d"]],
        },
    ]


def test_consulted_and_overlapping_outcome_slots_never_enter_control():
    selected, audit = _matched_untouched_controls(
        synthetic_records(),
        synthetic_outcomes(),
        run_seed=SEED,
        window_probes=2,
    )
    first = set(selected[100])
    assert not first.intersection({("C", "a"), ("C", "b")})
    assert not first.intersection({("C", "c"), ("C", "d")})
    assert audit["aggregate_exclusion_counts"]["target_consulted"] > 0
    assert audit["aggregate_exclusion_counts"]["overlapping_outcome_implication"] > 0


def test_control_selection_is_deterministic():
    a = _matched_untouched_controls(
        synthetic_records(),
        synthetic_outcomes(),
        run_seed=SEED,
        window_probes=2,
    )
    b = _matched_untouched_controls(
        synthetic_records(),
        synthetic_outcomes(),
        run_seed=SEED,
        window_probes=2,
    )
    assert a == b


def test_harness_only_control_identity_can_change_without_changing_mechanism_output():
    # First prove the salt can actually change a harness-only control identity.
    single = [synthetic_outcomes()[0]]
    _, audit_a = _matched_untouched_controls(
        synthetic_records(), single, run_seed=SEED, window_probes=2, selection_salt="A"
    )
    _, audit_b = _matched_untouched_controls(
        synthetic_records(), single, run_seed=SEED, window_probes=2, selection_salt="B"
    )
    assert audit_a["selection_sha256"] != audit_b["selection_sha256"]

    # Selection occurs only after the mechanism has consumed the full stream.
    #
    # Exercised across *every* consolidator, not just `no-consolidation`.
    # `no-consolidation` ignores outcomes entirely, so invariance holds there
    # even if control identity leaked into a revising arm; the arms that call
    # `demote` are the ones where such a leak could actually surface.
    lt = generate_delayed_credit_lifetime(
        LifetimeConfig(seed=SEED, epochs=16, delayed_outcomes_per_epoch=1.5)
    )
    budget = default_budget(lt)
    revised_somewhere = 0
    for arm in CONSOLIDATORS:
        a = run_delayed_credit(lt, arm, budget, control_selection_salt="A")
        b = run_delayed_credit(lt, arm, budget, control_selection_salt="B")

        assert a.records == b.records, arm
        assert a.manifest["metrics"] == b.manifest["metrics"], arm

        # Resource spend must also be salt-invariant: a control identity that
        # changed what an arm read or wrote would be a leak. `wall_seconds` is
        # excluded because it is wall-clock noise, not a behavioural property.
        spend_a = {k: v for k, v in a.manifest["budget_actual"].items() if k != "wall_seconds"}
        spend_b = {k: v for k, v in b.manifest["budget_actual"].items() if k != "wall_seconds"}
        assert spend_a == spend_b, arm

        ca = copy.deepcopy(a.manifest["consolidation_metrics"])
        cb = copy.deepcopy(b.manifest["consolidation_metrics"])
        # The untouched delta is *computed from* the controls, so it is the one
        # figure allowed to move with the salt. Everything else must not.
        ca.pop("untouched_accuracy_delta")
        cb.pop("untouched_accuracy_delta")
        assert ca == cb, arm
        revised_somewhere += int(ca["revisions"])

    # Guard against the whole assertion being vacuous: at least one arm must
    # actually have revised state under both salts.
    assert revised_somewhere > 0


def test_default_phase2_configuration_has_measurable_controls():
    lt = generate_delayed_credit_lifetime(
        LifetimeConfig(seed=SEED, epochs=16, delayed_outcomes_per_epoch=1.5)
    )
    result = run_delayed_credit(lt, "no-consolidation")
    audit = result.manifest["matched_untouched_control"]
    assert audit["eligible_total"] > 0
    assert audit["selected_total"] > 0
    assert audit["measured_outcome_deltas"] > 0


def test_validator_fails_closed_without_valid_controls():
    lt = generate_delayed_credit_lifetime(
        LifetimeConfig(seed=SEED, epochs=16, delayed_outcomes_per_epoch=1.5)
    )
    budget = default_budget(lt)
    runs = [run_delayed_credit(lt, arm, budget).manifest for arm in CONSOLIDATORS]
    for run in runs:
        run["matched_untouched_control"]["selected_total"] = 0
        run["matched_untouched_control"]["measured_outcome_deltas"] = 0
    reasons = validate(runs)["reasons"]
    assert "matched_untouched_control_absent" in reasons
    assert "matched_untouched_control_inert" in reasons


def test_development_classification_requires_and_accepts_git_commit():
    lt = generate_drift_lifetime(LifetimeConfig(seed=SEED, epochs=12))
    budget = default_budget(lt)
    missing = [
        run_drift(lt, arm, budget, classification="DEVELOPMENT").manifest
        for arm in DRIFT_MECHANISMS
    ]
    assert "missing_git_commit_for_nonpilot" in validate(missing)["reasons"]

    pinned = [
        run_drift(
            lt,
            arm,
            budget,
            classification="DEVELOPMENT",
            git_commit="0123456789abcdef",
        ).manifest
        for arm in DRIFT_MECHANISMS
    ]
    reasons = validate(pinned)["reasons"]
    assert "missing_git_commit_for_nonpilot" not in reasons
    assert "arms_disagree_on_git_commit" not in reasons


def test_score_aggregates_untouched_control_per_outcome():
    records = synthetic_records()
    outcomes = synthetic_outcomes()
    reports = [
        ConsolidationReport(outcome_event_id=100, revised_slots=(), evidence_reads=0),
        ConsolidationReport(outcome_event_id=101, revised_slots=(), evidence_reads=0),
    ]
    scored = score_consolidation(
        records,
        reports,
        outcomes,
        window_probes=2,
        run_seed=SEED,
    )
    assert scored.matched_untouched_control["measured_outcome_deltas"] > 0
    assert scored.metrics.untouched_accuracy_delta == 0.0


def test_excess_net_repair_is_paired_against_inaction():
    """Amendment 001 (M2): the causal endpoint subtracts the inaction baseline."""
    lt = generate_delayed_credit_lifetime(
        LifetimeConfig(seed=SEED, epochs=16, delayed_outcomes_per_epoch=1.5)
    )
    budget = default_budget(lt)
    runs = [run_delayed_credit(lt, arm, budget).manifest for arm in CONSOLIDATORS]
    excess = excess_net_repair(runs)

    # The baseline arm is exactly zero by construction.
    assert excess["no-consolidation"] == 0.0
    baseline = next(
        r["consolidation_metrics"]["net_repair"] for r in runs if r["arm"] == "no-consolidation"
    )
    for r in runs:
        assert excess[r["arm"]] == r["consolidation_metrics"]["net_repair"] - baseline
    # Raw net_repair is retained, not replaced.
    assert all("net_repair" in r["consolidation_metrics"] for r in runs)


def test_excess_net_repair_is_unanswerable_without_the_baseline():
    lt = generate_delayed_credit_lifetime(
        LifetimeConfig(seed=SEED, epochs=16, delayed_outcomes_per_epoch=1.5)
    )
    budget = default_budget(lt)
    runs = [
        run_delayed_credit(lt, arm, budget).manifest
        for arm in CONSOLIDATORS
        if arm != "no-consolidation"
    ]
    assert set(excess_net_repair(runs).values()) == {None}


def test_read_ceiling_magnitude_is_inert_before_exhaustion():
    """Amendment 001 (M3) safety property.

    Raising the evidence-read ceiling must not change behaviour when the old
    ceiling was never reached, or the confirmatory ceiling change would silently
    become a performance amendment.
    """
    lt = generate_drift_lifetime(LifetimeConfig(seed=SEED, epochs=32))
    base = default_budget(lt)
    raised = default_budget(lt, ceiling_multiplier=CONFIRMATORY_READ_CEILING_MULTIPLIER)
    assert raised.evidence_reads_ceiling > base.evidence_reads_ceiling
    # Only the read ceiling moves: log capacity governs eviction, and therefore
    # behaviour, so it must not.
    assert raised.log_capacity == base.log_capacity
    assert raised.maintenance_ops_ceiling == base.maintenance_ops_ceiling

    for arm in DRIFT_MECHANISMS:
        a = run_drift(lt, arm, base).manifest
        b = run_drift(lt, arm, raised).manifest
        assert a["budget_actual"]["exhausted_reads"] == 0, arm
        assert a["metrics"] == b["metrics"], arm
        assert a["budget_actual"]["evidence_reads"] == b["budget_actual"]["evidence_reads"], arm

import copy
import sys
from pathlib import Path

from lifetime_integrity.consolidation import CONSOLIDATORS, ConsolidationReport
from lifetime_integrity.harness import default_budget, run_delayed_credit, run_drift
from lifetime_integrity.lifetime import (
    LifetimeConfig,
    generate_delayed_credit_lifetime,
    generate_drift_lifetime,
)
from lifetime_integrity.mechanisms import DRIFT_MECHANISMS
from lifetime_integrity.metrics import (
    ProbeRecord,
    _matched_untouched_controls,
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
    lt = generate_delayed_credit_lifetime(
        LifetimeConfig(seed=SEED, epochs=16, delayed_outcomes_per_epoch=1.5)
    )
    budget = default_budget(lt)
    a = run_delayed_credit(lt, "no-consolidation", budget, control_selection_salt="A")
    b = run_delayed_credit(lt, "no-consolidation", budget, control_selection_salt="B")

    assert a.records == b.records
    assert a.manifest["metrics"] == b.manifest["metrics"]

    ca = copy.deepcopy(a.manifest["consolidation_metrics"])
    cb = copy.deepcopy(b.manifest["consolidation_metrics"])
    ca.pop("untouched_accuracy_delta")
    cb.pop("untouched_accuracy_delta")
    assert ca == cb


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
    assert validate(pinned)["valid_for_comparison"], validate(pinned)["reasons"]


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

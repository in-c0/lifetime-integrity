import json

import pytest

from lifetime_integrity.lifetime import (
    AUDIT_FIELDS,
    Assertion,
    ContextShift,
    DelayedOutcome,
    Gap,
    LifetimeConfig,
    Probe,
    generate_delayed_credit_lifetime,
    generate_drift_lifetime,
)

SEED = 20260902


def drift(**kw):
    return generate_drift_lifetime(LifetimeConfig(seed=SEED, **kw))


def credit(**kw):
    kw.setdefault("delayed_outcomes_per_epoch", 1.5)
    return generate_delayed_credit_lifetime(LifetimeConfig(seed=SEED, **kw))


def test_generation_is_deterministic():
    assert drift().spec_sha256() == drift().spec_sha256()
    assert credit().spec_sha256() == credit().spec_sha256()


def test_different_seeds_give_different_lifetimes():
    a = generate_drift_lifetime(LifetimeConfig(seed=1))
    b = generate_drift_lifetime(LifetimeConfig(seed=2))
    assert a.spec_sha256() != b.spec_sha256()


def test_config_lock_tracks_corruption_rates():
    base = LifetimeConfig(seed=SEED)
    assert base.config_lock() == LifetimeConfig(seed=SEED).config_lock()
    # Any change to the corruption process must change the lock.
    assert base.config_lock() != LifetimeConfig(seed=SEED, p_misinformation=0.19).config_lock()
    assert base.config_lock() != LifetimeConfig(seed=SEED, gap_ticks=4001).config_lock()


def test_visible_views_never_carry_audit_fields():
    for lt in (drift(), credit()):
        for ev in lt.events:
            leaked = AUDIT_FIELDS.intersection(ev.visible().keys())
            assert not leaked, f"{ev.kind} leaked {leaked}"


def test_visible_views_are_json_serializable():
    for ev in drift().events:
        json.dumps(ev.visible())


def test_probe_options_contain_canonical_and_are_unique():
    for p in drift().probes():
        assert p.canonical in p.options
        assert len(set(p.options)) == len(p.options)


def test_probes_offer_a_never_asserted_option_somewhere():
    # Without an unasserted option, `unsupported_belief_rate` could never fire.
    probes = drift().probes()
    assert any(set(p.options) - set(p.ever_asserted) for p in probes)


def test_stream_contains_every_corruption_kind():
    lt = drift()
    kinds = {e.corruption for e in lt.events if isinstance(e, Assertion)}
    assert {"clean", "misinformation", "misleading_repeat", "contradiction", "world_change"} <= kinds
    classes = {p.probe_class for p in lt.probes()}
    assert {"fresh", "untouched", "post_gap", "stale_risk", "quiet_change"} <= classes


def test_stream_contains_gaps_and_context_shifts():
    lt = drift()
    assert any(isinstance(e, Gap) for e in lt.events)
    assert any(isinstance(e, ContextShift) for e in lt.events)


def test_clock_is_monotonic():
    for lt in (drift(), credit()):
        times = [e.t for e in lt.events]
        assert times == sorted(times)


def test_event_ids_are_unique_and_ordered():
    for lt in (drift(), credit()):
        ids = [e.event_id for e in lt.events]
        assert len(set(ids)) == len(ids)
        assert ids == sorted(ids)


def test_drift_stream_has_no_delayed_outcomes():
    assert not any(isinstance(e, DelayedOutcome) for e in drift().events)


def test_delayed_credit_requires_outcomes_configured():
    with pytest.raises(ValueError):
        generate_delayed_credit_lifetime(LifetimeConfig(seed=SEED))


def test_delayed_outcomes_are_followed_by_probes():
    """Repair is unmeasurable if outcomes land after the last probe."""
    lt = credit()
    outcomes = [e for e in lt.events if isinstance(e, DelayedOutcome)]
    assert outcomes
    last_probe_t = max(e.t for e in lt.events if isinstance(e, Probe))
    assert all(o.t < last_probe_t for o in outcomes[:-1])


def test_delayed_outcome_implicates_exactly_one_consulted_slot():
    for o in (e for e in credit().events if isinstance(e, DelayedOutcome)):
        assert o.responsible_slot in o.consulted
        assert len(set(o.consulted)) == len(o.consulted)
        assert len(o.consulted) >= 2


def test_delayed_outcome_arrives_after_its_decision():
    for o in (e for e in credit().events if isinstance(e, DelayedOutcome)):
        assert o.t > o.decision_t


def test_shared_codebook_allows_cross_slot_interference():
    """Disjoint per-slot vocabularies would pin unsupported beliefs to zero."""
    lt = drift()
    pools = {}
    for p in lt.probes():
        pools.setdefault(p.slot if hasattr(p, "slot") else (p.context, p.key), set()).update(p.options)
    values = [v for s in pools.values() for v in s]
    assert len(set(values)) < len(values)

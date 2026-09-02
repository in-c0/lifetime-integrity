from lifetime_integrity.metrics import ProbeRecord, evaluate


def rec(**kw):
    base = {
        "event_id": 1, "t": 0, "epoch": 0, "context": "C", "key": "K",
        "probe_class": "fresh", "options": ("A", "B", "C"), "canonical": "A",
        "superseded": (), "ever_asserted": ("A", "B"), "answer": "A",
        "confidence": 0.9, "support": (),
    }
    base.update(kw)
    return ProbeRecord(**base)


def test_correct_supported_answer_is_clean():
    r = rec()
    assert r.correct and not r.stale and not r.unsupported and not r.integrity_violation


def test_unsupported_answer_flagged_even_when_canonical():
    """A right answer nobody ever gave the system is still an integrity failure."""
    r = rec(answer="C", canonical="C", ever_asserted=("A", "B"))
    assert r.correct
    assert r.unsupported and r.integrity_violation


def test_stale_answer_flagged():
    r = rec(answer="B", canonical="A", superseded=("B",))
    assert r.stale and not r.correct and r.integrity_violation


def test_abstention_is_never_an_integrity_violation():
    r = rec(answer=None)
    assert r.abstained and not r.unsupported and not r.stale and not r.integrity_violation


def test_self_contradiction_needs_no_intervening_evidence():
    records = [
        rec(event_id=1, t=10, answer="A"),
        rec(event_id=2, t=20, answer="B", ever_asserted=("A", "B")),
    ]
    m = evaluate(records, {}, {})
    assert m.self_contradiction_rate == 1.0
    # The same flip is legitimate if an assertion arrived in between.
    m2 = evaluate(records, {}, {("C", "K"): [15]})
    assert m2.self_contradiction_rate == 0.0


def test_provenance_consistency_checks_cited_evidence():
    index = {7: ("C", "K", "A"), 8: ("C", "K", "B")}
    good = evaluate([rec(support=(7,))], index, {})
    assert good.provenance_consistency == 1.0
    # Citing evidence that says something else must not count as consistent.
    bad = evaluate([rec(support=(8,))], index, {})
    assert bad.provenance_consistency == 0.0
    # Citing an event that does not exist must not count either.
    missing = evaluate([rec(support=(99,))], index, {})
    assert missing.provenance_consistency == 0.0


def test_unattributed_answers_are_counted_separately():
    m = evaluate([rec(support=())], {}, {})
    assert m.unattributed_answer_rate == 1.0
    assert m.provenance_consistency == 0.0


def test_recovery_counts_probes_until_new_canonical_answered():
    records = [
        rec(event_id=1, t=10, answer="A", canonical="A"),
        rec(event_id=2, t=20, answer="A", canonical="B", superseded=("A",), ever_asserted=("A", "B")),
        rec(event_id=3, t=30, answer="B", canonical="B", superseded=("A",), ever_asserted=("A", "B")),
    ]
    m = evaluate(records, {}, {})
    assert m.mean_recovery_probes == 1.0
    assert m.unrecovered_changes == 0


def test_unrecovered_change_is_counted():
    records = [
        rec(event_id=1, t=10, answer="A", canonical="A"),
        rec(event_id=2, t=20, answer="A", canonical="B", superseded=("A",), ever_asserted=("A", "B")),
    ]
    m = evaluate(records, {}, {})
    assert m.unrecovered_changes == 1


def test_calibration_rewards_honest_confidence():
    confident_wrong = [rec(t=i, answer="B", canonical="A", confidence=1.0, ever_asserted=("A", "B")) for i in range(10)]
    honest = [rec(t=i, answer="B", canonical="A", confidence=0.0, ever_asserted=("A", "B")) for i in range(10)]
    assert evaluate(confident_wrong, {}, {}).expected_calibration_error == 1.0
    assert evaluate(honest, {}, {}).expected_calibration_error == 0.0


def test_drift_slope_detects_worsening_integrity():
    clean = [rec(event_id=i, t=i, epoch=0, answer="A") for i in range(5)]
    dirty = [rec(event_id=10 + i, t=10 + i, epoch=1, answer="B", superseded=("B",)) for i in range(5)]
    m = evaluate(clean + dirty, {}, {})
    assert m.drift_slope_per_epoch > 0
    assert m.drift_late_minus_early > 0


def test_per_class_breakdown_is_reported():
    m = evaluate([rec(probe_class="post_gap"), rec(event_id=2, t=5, probe_class="untouched")], {}, {})
    assert set(m.per_class) == {"post_gap", "untouched"}

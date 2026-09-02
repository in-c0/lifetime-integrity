import os
import subprocess
import sys
from pathlib import Path

import pytest

from lifetime_integrity.consolidation import CONSOLIDATORS, TrackedAccumulator
from lifetime_integrity.mechanisms import DRIFT_MECHANISMS, Budget, EvidenceLog

SRC = str(Path(__file__).resolve().parents[1] / "src")


def obs(eid, t, value, tier="primary", context="C", key="K", source="S1"):
    return {
        "kind": "assert", "event_id": eid, "t": t, "context": context, "key": key,
        "value": value, "source_id": source, "source_tier": tier,
    }


def query(options=("A", "B"), t=100, context="C", key="K"):
    return {"kind": "probe", "event_id": 999, "t": t, "context": context, "key": key, "options": list(options)}


def budget(reads=10_000):
    return Budget(evidence_reads_ceiling=reads, maintenance_ops_ceiling=10_000, log_capacity=1000)


def test_evidence_log_charges_every_scanned_record():
    log = EvidenceLog(capacity=100, read_ceiling=1000)
    for i in range(10):
        log.append(obs(i, i, "A"))
    log.read_slot("C", "K", window=10)
    assert log.reads == 10, "reads must be charged per record scanned, not per record matched"


def test_evidence_log_enforces_read_ceiling():
    log = EvidenceLog(capacity=100, read_ceiling=5)
    for i in range(10):
        log.append(obs(i, i, "A"))
    assert log.read_slot("C", "K", window=10) == []
    assert log.exhausted_reads == 1
    assert log.reads <= 5


def test_evidence_log_evicts_beyond_capacity():
    log = EvidenceLog(capacity=3, read_ceiling=1000)
    for i in range(10):
        log.append(obs(i, i, "A"))
    assert log.stats()["log_size"] == 3
    assert log.stats()["log_evictions"] == 7


@pytest.mark.parametrize("name", sorted(DRIFT_MECHANISMS))
def test_mechanism_answers_within_offered_options(name):
    log = EvidenceLog(capacity=1000, read_ceiling=100_000)
    sut = DRIFT_MECHANISMS[name](log, budget(100_000))
    for i in range(20):
        payload = obs(i, i * 3, "A" if i % 2 else "B")
        log.append(payload)
        sut.observe(payload)
    ans = sut.answer(query(("A", "B")))
    assert ans.value in {"A", "B", None}
    assert 0.0 <= ans.confidence <= 1.0


@pytest.mark.parametrize("name", sorted(DRIFT_MECHANISMS))
def test_mechanism_never_exceeds_read_ceiling(name):
    log = EvidenceLog(capacity=1000, read_ceiling=50)
    sut = DRIFT_MECHANISMS[name](log, budget(50))
    for i in range(60):
        payload = obs(i, i * 3, "A")
        log.append(payload)
        sut.observe(payload)
        sut.answer(query())
    assert log.reads <= 50


@pytest.mark.parametrize("name", sorted(DRIFT_MECHANISMS))
def test_mechanism_abstains_on_unknown_slot(name):
    log = EvidenceLog(capacity=1000, read_ceiling=10_000)
    sut = DRIFT_MECHANISMS[name](log, budget())
    assert sut.answer(query(context="never", key="seen")).value is None


def test_last_write_wins_tracks_the_latest_assertion():
    log = EvidenceLog(capacity=100, read_ceiling=1000)
    sut = DRIFT_MECHANISMS["last-write-wins"](log, budget())
    sut.observe(obs(1, 1, "A"))
    sut.observe(obs(2, 2, "B"))
    assert sut.answer(query()).value == "B"


def test_accumulator_is_captured_by_repetition():
    """The failure this arm exists to demonstrate: volume beats recency."""
    log = EvidenceLog(capacity=100, read_ceiling=1000)
    sut = DRIFT_MECHANISMS["unconstrained-accumulator"](log, budget())
    for i in range(10):
        sut.observe(obs(i, i, "A", tier="unreliable"))
    sut.observe(obs(99, 99, "B", tier="primary"))
    assert sut.answer(query()).value == "A"


def test_confidence_decay_abstains_after_a_long_gap():
    log = EvidenceLog(capacity=100, read_ceiling=1000)
    sut = DRIFT_MECHANISMS["confidence-decay"](log, budget())
    sut.observe(obs(1, 1, "A"))
    assert sut.answer(query(t=2)).value == "A"
    assert sut.answer(query(t=10_000_000)).value is None


def test_lossy_latent_cell_assignment_is_process_stable():
    """Regression: str hashing is salted per process and broke reproducibility."""
    code = (
        f"import sys; sys.path.insert(0, {SRC!r});"
        "from lifetime_integrity.mechanisms import LossyLatent, EvidenceLog, Budget;"
        "m = LossyLatent(EvidenceLog(10, 10), Budget(10, 10, 10));"
        "print([m._cell(('C' + str(i), 'K')) for i in range(8)])"
    )
    outs = set()
    for seed in ("0", "1", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        outs.add(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True).stdout)
    assert len(outs) == 1


def test_lossy_latent_can_produce_an_unsupported_belief():
    """The one reference arm able to move `unsupported_belief_rate` off zero."""
    log = EvidenceLog(capacity=1000, read_ceiling=10_000)
    sut = DRIFT_MECHANISMS["lossy-latent"](log, budget(), cells=1)
    for i in range(20):
        sut.observe(obs(i, i, "Z", context="OTHER", key="OTHER"))
    sut.observe(obs(99, 99, "A"))
    assert sut.answer(query(("A", "Z"))).value == "Z"


@pytest.mark.parametrize("name", sorted(CONSOLIDATORS))
def test_consolidators_share_one_substrate(name):
    log = EvidenceLog(capacity=1000, read_ceiling=10_000)
    sut = CONSOLIDATORS[name](log, budget())
    assert isinstance(sut.base, TrackedAccumulator)


def test_demotion_surfaces_the_next_best_value():
    log = EvidenceLog(capacity=100, read_ceiling=1000)
    acc = TrackedAccumulator(log, budget())
    for i in range(5):
        acc.observe(obs(i, i, "A"))
    acc.observe(obs(9, 9, "B"))
    assert acc.answer(query()).value == "A"
    assert acc.demote(("C", "K"))
    assert acc.answer(query()).value == "B"


def test_uniform_blame_revises_every_consulted_slot():
    log = EvidenceLog(capacity=100, read_ceiling=1000)
    sut = CONSOLIDATORS["uniform-blame"](log, budget())
    for i, key in enumerate(["K1", "K2"]):
        sut.observe(obs(i, i, "A", key=key))
    rep = sut.handle_outcome({"event_id": 1, "t": 10, "consulted": [["C", "K1"], ["C", "K2"]]})
    assert set(rep.revised_slots) == {("C", "K1"), ("C", "K2")}


def test_no_consolidation_revises_nothing():
    log = EvidenceLog(capacity=100, read_ceiling=1000)
    sut = CONSOLIDATORS["no-consolidation"](log, budget())
    sut.observe(obs(1, 1, "A"))
    rep = sut.handle_outcome({"event_id": 1, "t": 10, "consulted": [["C", "K"]]})
    assert rep.revised_slots == ()

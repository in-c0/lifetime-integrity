"""State-integrity metrics for LIS-v0.

These metrics deliberately separate *task accuracy* from *state integrity*. A
system can answer canonically while holding an unsupported belief (a lucky
guess), and it can hold a well-supported belief that is merely obsolete. Both
are distinguishable here.

Nothing in this module knows what a mechanism is made of; it consumes probe
records only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from itertools import pairwise

import numpy as np


@dataclass(frozen=True)
class ProbeRecord:
    """One evaluated probe, joined with harness-only audit fields."""

    event_id: int
    t: int
    epoch: int
    context: str
    key: str
    probe_class: str
    options: tuple[str, ...]
    canonical: str
    superseded: tuple[str, ...]
    ever_asserted: tuple[str, ...]
    answer: str | None
    confidence: float
    support: tuple[int, ...]

    @property
    def slot(self) -> tuple[str, str]:
        return (self.context, self.key)

    @property
    def abstained(self) -> bool:
        return self.answer is None

    @property
    def correct(self) -> bool:
        return self.answer == self.canonical

    @property
    def stale(self) -> bool:
        return self.answer is not None and self.answer in self.superseded

    @property
    def unsupported(self) -> bool:
        """The answered value was never asserted to this system.

        A value can be unsupported and still canonical: the system guessed a
        truth it was never told. That is an integrity failure, not a success.
        """
        return self.answer is not None and self.answer not in self.ever_asserted

    @property
    def integrity_violation(self) -> bool:
        return self.stale or self.unsupported


@dataclass(frozen=True)
class IntegrityMetrics:
    probes: int
    canonical_accuracy: float
    abstention_rate: float
    accuracy_when_answered: float
    unsupported_belief_rate: float
    stale_state_rate: float
    integrity_violation_rate: float
    self_contradiction_rate: float
    provenance_consistency: float
    unattributed_answer_rate: float
    expected_calibration_error: float
    brier_score: float
    mean_recovery_probes: float
    unrecovered_changes: int
    drift_slope_per_epoch: float
    drift_late_minus_early: float
    per_class: dict[str, dict[str, float]]
    per_epoch_integrity: list[float]

    def to_dict(self) -> dict:
        return asdict(self)


def _safe_mean(xs: Sequence[float]) -> float:
    return float(np.mean(xs)) if len(xs) else 0.0


def _self_contradiction_rate(records: Sequence[ProbeRecord], assertion_times: dict[tuple[str, str], list[int]]) -> float:
    """Rate of answer flips unjustified by intervening evidence.

    Consecutive probes on one slot with no assertion about that slot in between
    give the system no new information. A different answer is therefore an
    internal inconsistency rather than a legitimate revision.
    """
    by_slot: dict[tuple[str, str], list[ProbeRecord]] = {}
    for r in records:
        by_slot.setdefault(r.slot, []).append(r)
    pairs = 0
    flips = 0
    for slot, rs in by_slot.items():
        rs = sorted(rs, key=lambda r: r.t)
        times = assertion_times.get(slot, [])
        for a, b in pairwise(rs):
            if a.abstained or b.abstained:
                continue
            if any(a.t < ts < b.t for ts in times):
                continue
            pairs += 1
            if a.answer != b.answer:
                flips += 1
    return flips / pairs if pairs else 0.0


def _recovery(records: Sequence[ProbeRecord]) -> tuple[float, int]:
    """Probes-to-recovery after each canonical change.

    A change is detected as a shift in the audit-only canonical value between
    consecutive probes of the same slot. Recovery is the number of probes until
    the system next answers the new canonical value.
    """
    by_slot: dict[tuple[str, str], list[ProbeRecord]] = {}
    for r in records:
        by_slot.setdefault(r.slot, []).append(r)
    delays: list[int] = []
    unrecovered = 0
    for rs in by_slot.values():
        rs = sorted(rs, key=lambda r: r.t)
        for i in range(1, len(rs)):
            if rs[i].canonical == rs[i - 1].canonical:
                continue
            target = rs[i].canonical
            found = None
            for j in range(i, len(rs)):
                if rs[j].canonical != target:
                    break
                if rs[j].answer == target:
                    found = j - i
                    break
            if found is None:
                unrecovered += 1
            else:
                delays.append(found)
    return (_safe_mean(delays), unrecovered)


def _calibration(records: Sequence[ProbeRecord], bins: int = 10) -> tuple[float, float]:
    answered = [r for r in records if not r.abstained]
    if not answered:
        return (0.0, 0.0)
    conf = np.clip(np.array([r.confidence for r in answered], dtype=float), 0.0, 1.0)
    acc = np.array([1.0 if r.correct else 0.0 for r in answered], dtype=float)
    brier = float(np.mean((conf - acc) ** 2))
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lo, hi in pairwise(edges):
        mask = (conf > lo) & (conf <= hi) if lo > 0 else (conf >= lo) & (conf <= hi)
        if not mask.any():
            continue
        ece += (mask.sum() / len(conf)) * abs(float(acc[mask].mean()) - float(conf[mask].mean()))
    return (float(ece), brier)


def _drift(records: Sequence[ProbeRecord]) -> tuple[float, float, list[float]]:
    """Integrity violation as a function of position in the lifetime."""
    epochs = sorted({r.epoch for r in records})
    series: list[float] = []
    for e in epochs:
        rs = [r for r in records if r.epoch == e]
        series.append(_safe_mean([1.0 if r.integrity_violation else 0.0 for r in rs]))
    if len(series) < 2:
        return (0.0, 0.0, series)
    x = np.array(epochs, dtype=float)
    y = np.array(series, dtype=float)
    slope = float(np.polyfit(x, y, 1)[0])
    third = max(1, len(series) // 3)
    late_minus_early = float(np.mean(y[-third:]) - np.mean(y[:third]))
    return (slope, late_minus_early, series)


def evaluate(
    records: Sequence[ProbeRecord],
    support_index: dict[int, tuple[str, str, str]],
    assertion_times: dict[tuple[str, str], list[int]],
) -> IntegrityMetrics:
    """Score a lifetime run.

    `support_index` maps assertion event_id -> (context, key, value) and is used
    to check that cited provenance actually says what the answer claims.
    """
    n = len(records)
    if n == 0:
        raise ValueError("no probe records to evaluate")

    answered = [r for r in records if not r.abstained]
    correct = [1.0 if r.correct else 0.0 for r in records]
    prov_checked = 0
    prov_ok = 0
    unattributed = 0
    for r in answered:
        if not r.support:
            unattributed += 1
            continue
        prov_checked += 1
        entries = [support_index.get(eid) for eid in r.support]
        if all(e is not None and e == (r.context, r.key, r.answer) for e in entries):
            prov_ok += 1

    ece, brier = _calibration(records)
    mean_recovery, unrecovered = _recovery(records)
    slope, late_early, series = _drift(records)

    per_class: dict[str, dict[str, float]] = {}
    for cls in sorted({r.probe_class for r in records}):
        rs = [r for r in records if r.probe_class == cls]
        per_class[cls] = {
            "n": float(len(rs)),
            "canonical_accuracy": _safe_mean([1.0 if r.correct else 0.0 for r in rs]),
            "stale_state_rate": _safe_mean([1.0 if r.stale else 0.0 for r in rs]),
            "unsupported_belief_rate": _safe_mean([1.0 if r.unsupported else 0.0 for r in rs]),
            "abstention_rate": _safe_mean([1.0 if r.abstained else 0.0 for r in rs]),
        }

    return IntegrityMetrics(
        probes=n,
        canonical_accuracy=_safe_mean(correct),
        abstention_rate=_safe_mean([1.0 if r.abstained else 0.0 for r in records]),
        accuracy_when_answered=_safe_mean([1.0 if r.correct else 0.0 for r in answered]),
        unsupported_belief_rate=_safe_mean([1.0 if r.unsupported else 0.0 for r in records]),
        stale_state_rate=_safe_mean([1.0 if r.stale else 0.0 for r in records]),
        integrity_violation_rate=_safe_mean([1.0 if r.integrity_violation else 0.0 for r in records]),
        self_contradiction_rate=_self_contradiction_rate(records, assertion_times),
        provenance_consistency=(prov_ok / prov_checked) if prov_checked else 0.0,
        unattributed_answer_rate=(unattributed / len(answered)) if answered else 0.0,
        expected_calibration_error=ece,
        brier_score=brier,
        mean_recovery_probes=mean_recovery,
        unrecovered_changes=unrecovered,
        drift_slope_per_epoch=slope,
        drift_late_minus_early=late_early,
        per_class=per_class,
        per_epoch_integrity=series,
    )


@dataclass(frozen=True)
class ConsolidationMetrics:
    """Class B: did delayed credit land on the right belief, and what did it cost?

    Attribution is scored against the audit-only responsible slot. Collateral
    damage is measured on the *decoy* slots the same failed decision consulted —
    those were correct at decision time, so any accuracy they lose is damage the
    consolidator did.
    """

    outcomes: int
    revisions: int
    attribution_precision: float
    attribution_recall: float
    collateral_revision_rate: float
    culprit_accuracy_delta: float
    decoy_accuracy_delta: float
    untouched_accuracy_delta: float
    net_repair: float
    consolidation_reads: int

    def to_dict(self) -> dict:
        return asdict(self)


def _windowed_delta(
    records: Sequence[ProbeRecord],
    slot: tuple[str, str],
    t: int,
    k: int,
) -> float | None:
    """Accuracy on `slot` over the k probes after `t` minus the k probes before."""
    rs = sorted([r for r in records if r.slot == slot], key=lambda r: r.t)
    before = [r for r in rs if r.t < t][-k:]
    after = [r for r in rs if r.t >= t][:k]
    if not before or not after:
        return None
    b = _safe_mean([1.0 if r.correct else 0.0 for r in before])
    a = _safe_mean([1.0 if r.correct else 0.0 for r in after])
    return a - b


def score_consolidation(
    records: Sequence[ProbeRecord],
    reports: Sequence,
    outcomes: Sequence[dict],
    window_probes: int = 3,
) -> ConsolidationMetrics:
    """Score delayed-credit consolidation.

    `outcomes` carries the audit view of each delayed outcome: `event_id`, `t`,
    `responsible_slot`, and `consulted`.
    """
    by_id = {o["event_id"]: o for o in outcomes}
    hits = 0
    revisions = 0
    collateral = 0
    reads = 0
    culprit_deltas: list[float] = []
    decoy_deltas: list[float] = []

    touched: set[tuple[str, str]] = set()
    for o in outcomes:
        touched.update(tuple(s) for s in o["consulted"])

    for rep in reports:
        o = by_id.get(rep.outcome_event_id)
        if o is None:
            continue
        responsible = tuple(o["responsible_slot"])
        revised = set(rep.revised_slots)
        revisions += len(revised)
        reads += rep.evidence_reads
        if responsible in revised:
            hits += 1
        collateral += len(revised - {responsible})

        d = _windowed_delta(records, responsible, o["t"], window_probes)
        if d is not None:
            culprit_deltas.append(d)
        for slot in (tuple(s) for s in o["consulted"]):
            if slot == responsible:
                continue
            d = _windowed_delta(records, slot, o["t"], window_probes)
            if d is not None:
                decoy_deltas.append(d)

    untouched_deltas: list[float] = []
    for o in outcomes:
        for slot in {r.slot for r in records} - touched:
            d = _windowed_delta(records, slot, o["t"], window_probes)
            if d is not None:
                untouched_deltas.append(d)

    culprit = _safe_mean(culprit_deltas)
    decoy = _safe_mean(decoy_deltas)
    return ConsolidationMetrics(
        outcomes=len(reports),
        revisions=revisions,
        attribution_precision=(hits / revisions) if revisions else 0.0,
        attribution_recall=(hits / len(reports)) if reports else 0.0,
        collateral_revision_rate=(collateral / revisions) if revisions else 0.0,
        culprit_accuracy_delta=culprit,
        decoy_accuracy_delta=decoy,
        untouched_accuracy_delta=_safe_mean(untouched_deltas),
        net_repair=culprit + decoy,
        consolidation_reads=reads,
    )

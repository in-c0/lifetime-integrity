"""Class B — delayed credit assignment onto persistent belief state.

Every arm here shares one belief substrate (`TrackedAccumulator`) so that the
only thing varying between arms is the *credit-assignment rule* applied when a
delayed outcome arrives. A delayed outcome names the slots a failed decision
consulted but never names which one carried the bad value.

The interesting question is not whether an arm can fix the culprit — demoting
everything does that — but whether it can fix the culprit *without corrupting
the unrelated beliefs it also touched*.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from .mechanisms import TIER_PRIOR, Answer, Budget, EvidenceLog, _argmax, _Base, _restrict, _slot


@dataclass(frozen=True)
class ConsolidationReport:
    outcome_event_id: int
    revised_slots: tuple[tuple[str, str], ...]
    evidence_reads: int
    responsible_slot: tuple[str, str] | None = None  # audit-only; attached by the harness


class TrackedAccumulator(_Base):
    """Shared substrate: accreting scores plus enough bookkeeping to revise."""

    name = "tracked-accumulator"

    def __init__(self, log: EvidenceLog, budget: Budget) -> None:
        super().__init__(log, budget)
        self.scores: dict[tuple[str, str], dict[str, float]] = {}
        self.tiers: dict[tuple[str, str], dict[str, dict[str, int]]] = {}
        self.events: dict[tuple[str, str], dict[str, list[int]]] = {}
        self.last_write: dict[tuple[str, str], int] = {}
        self.suppressed: dict[tuple[str, str], set[str]] = {}

    def observe(self, obs):
        super().observe(obs)
        slot, val = _slot(obs), obs["value"]
        self.scores.setdefault(slot, {})[val] = self.scores.setdefault(slot, {}).get(val, 0.0) + 1.0
        self.tiers.setdefault(slot, {}).setdefault(val, {})
        tier = obs["source_tier"]
        self.tiers[slot][val][tier] = self.tiers[slot][val].get(tier, 0) + 1
        self.events.setdefault(slot, {}).setdefault(val, []).append(obs["event_id"])
        self.last_write[slot] = obs["t"]

    def _live(self, slot: tuple[str, str]) -> dict[str, float]:
        blocked = self.suppressed.get(slot, set())
        return {v: s for v, s in self.scores.get(slot, {}).items() if v not in blocked}

    def answer(self, query):
        slot = _slot(query)
        s = _restrict(self._live(slot), query["options"])
        value, share = _argmax(s)
        if value is None:
            return Answer(None, 0.0, ())
        support = tuple(self.events.get(slot, {}).get(value, ())[-3:])
        return Answer(value, share, support)

    def top(self, slot: tuple[str, str]) -> str | None:
        return _argmax(self._live(slot))[0]

    def dominant_tier(self, slot: tuple[str, str], value: str) -> str:
        counts = self.tiers.get(slot, {}).get(value, {})
        if not counts:
            return "secondary"
        return max(counts, key=lambda t: (counts[t], t))

    def demote(self, slot: tuple[str, str]) -> bool:
        """Suppress the currently believed value so the next-best can surface."""
        value = self.top(slot)
        if value is None:
            return False
        self.suppressed.setdefault(slot, set()).add(value)
        return True

    def state_bytes(self):
        return sum(
            len(c) + len(k) + sum(len(v) + 24 for v in d) for (c, k), d in self.scores.items()
        )


class _Consolidator:
    """Wraps the shared substrate; differs only in `handle_outcome`."""

    name = "base"

    def __init__(self, log: EvidenceLog, budget: Budget) -> None:
        self.log = log
        self.budget = budget
        self.base = TrackedAccumulator(log, budget)
        self.reports: list[ConsolidationReport] = []

    # substrate passthrough
    def observe(self, obs):
        self.base.observe(obs)

    def on_gap(self, ev):
        self.base.on_gap(ev)

    def on_context_shift(self, ev):
        self.base.on_context_shift(ev)

    def answer(self, query):
        return self.base.answer(query)

    def state_bytes(self):
        return self.base.state_bytes()

    @property
    def maintenance_ops(self) -> int:
        return self.base.maintenance_ops

    def _consulted(self, ev: dict) -> list[tuple[str, str]]:
        return [(c, k) for c, k in ev["consulted"]]

    def handle_outcome(self, ev: dict) -> ConsolidationReport:
        raise NotImplementedError

    def _record(self, ev: dict, revised: list[tuple[str, str]], reads: int) -> ConsolidationReport:
        rep = ConsolidationReport(
            outcome_event_id=ev["event_id"],
            revised_slots=tuple(revised),
            evidence_reads=reads,
        )
        self.reports.append(rep)
        return rep


class NoConsolidation(_Consolidator):
    """C0 — the delayed signal is discarded. Nothing is ever repaired."""

    name = "no-consolidation"

    def handle_outcome(self, ev):
        return self._record(ev, [], 0)


class UniformBlame(_Consolidator):
    """C1 — blame everything the decision touched. Maximal recall, maximal harm."""

    name = "uniform-blame"

    def handle_outcome(self, ev):
        revised = [s for s in self._consulted(ev) if self.base.demote(s)]
        self.base.maintenance_ops += len(revised)
        return self._record(ev, revised, 0)


class EligibilityTrace(_Consolidator):
    """C2 — blame by recency of the last write, top-k only.

    A classical eligibility trace assumes the most recently touched state is the
    most likely cause. That assumption is *false* for this failure mode, which
    is exactly why it belongs here as a control.
    """

    name = "eligibility-trace"

    def __init__(self, log, budget, tau: float = 8000.0, top_k: int = 1):
        super().__init__(log, budget)
        self.tau = tau
        self.top_k = top_k

    def handle_outcome(self, ev):
        consulted = self._consulted(ev)
        now = ev["t"]
        traced = sorted(
            consulted,
            key=lambda s: (-math.exp(-(now - self.base.last_write.get(s, 0)) / self.tau), s),
        )
        revised = [s for s in traced[: self.top_k] if self.base.demote(s)]
        self.base.maintenance_ops += len(revised)
        return self._record(ev, revised, 0)


class ProvenanceRestrictedBlame(_Consolidator):
    """C3 — blame only beliefs resting on low-reliability provenance."""

    name = "provenance-restricted-blame"

    def __init__(self, log, budget, distrusted: tuple[str, ...] = ("unreliable",)):
        super().__init__(log, budget)
        self.distrusted = set(distrusted)

    def handle_outcome(self, ev):
        revised = []
        for slot in self._consulted(ev):
            value = self.base.top(slot)
            if value is None:
                continue
            if self.base.dominant_tier(slot, value) in self.distrusted and self.base.demote(slot):
                revised.append(slot)
        self.base.maintenance_ops += len(revised)
        return self._record(ev, revised, 0)


class CounterfactualRecheck(_Consolidator):
    """C4 — spend evidence reads to re-derive each consulted slot, revise on disagreement.

    The most expensive arm, and the only one that consults the record rather
    than a heuristic about it. Whether that expense buys attribution accuracy is
    the empirical question.
    """

    name = "counterfactual-recheck"

    def __init__(self, log, budget, window: int = 200):
        super().__init__(log, budget)
        self.window = window

    def handle_outcome(self, ev):
        before = self.log.reads
        revised = []
        for slot in self._consulted(ev):
            current = self.base.top(slot)
            if current is None:
                continue
            recs = self.log.read_slot(slot[0], slot[1], self.window)
            if not recs:
                continue
            weights: dict[str, float] = {}
            for r in recs:
                w = TIER_PRIOR.get(r["source_tier"], 0.6)
                recency = math.exp(-(ev["t"] - r["t"]) / 6000.0)
                weights[r["value"]] = weights.get(r["value"], 0.0) + w * (0.35 + 0.65 * recency)
            best, _ = _argmax(weights)
            if best is not None and best != current and self.base.demote(slot):
                revised.append(slot)
        self.base.maintenance_ops += len(revised)
        return self._record(ev, revised, self.log.reads - before)


CONSOLIDATORS: dict[str, Callable[[EvidenceLog, Budget], _Consolidator]] = {
    NoConsolidation.name: NoConsolidation,
    UniformBlame.name: UniformBlame,
    EligibilityTrace.name: EligibilityTrace,
    ProvenanceRestrictedBlame.name: ProvenanceRestrictedBlame,
    CounterfactualRecheck.name: CounterfactualRecheck,
}

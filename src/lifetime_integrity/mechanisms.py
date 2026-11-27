"""Reference integrity mechanisms for LIS-v0.

These are deliberately simple, non-neural, and architecture-agnostic. They exist
so the benchmark can be calibrated and released **independently of any CCS
latent architecture**. None of them is a proposed method; they are the controls
against which a future substrate would have to earn its keep.

Every mechanism reaches historical evidence only through `EvidenceLog`, which
meters reads against a shared ceiling. That is what makes "budget-matched"
enforceable rather than aspirational.
"""

from __future__ import annotations

import math
import zlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol

TIER_PRIOR = {"primary": 0.9, "secondary": 0.7, "unreliable": 0.5}


@dataclass
class Budget:
    """Shared resource ceiling for a comparison."""

    evidence_reads_ceiling: int
    maintenance_ops_ceiling: int
    log_capacity: int


@dataclass(frozen=True)
class Answer:
    value: str | None
    confidence: float
    support: tuple[int, ...] = ()


class EvidenceLog:
    """A bounded, metered record of what the system was actually told.

    Reads are charged per record scanned, not per record returned: scanning is
    the cost a real re-grounding pass pays. Once the ceiling is spent, reads
    return nothing and the exhaustion is recorded rather than silently ignored.
    """

    def __init__(self, capacity: int, read_ceiling: int) -> None:
        self.capacity = capacity
        self.read_ceiling = read_ceiling
        self.reads = 0
        self.exhausted_reads = 0
        self.evictions = 0
        self._records: list[dict] = []

    def append(self, obs: dict) -> None:
        self._records.append(obs)
        if len(self._records) > self.capacity:
            self._records.pop(0)
            self.evictions += 1

    @property
    def remaining(self) -> int:
        return max(0, self.read_ceiling - self.reads)

    def _charge(self, scanned: int) -> bool:
        if self.reads + scanned > self.read_ceiling:
            self.exhausted_reads += 1
            self.reads = self.read_ceiling
            return False
        self.reads += scanned
        return True

    def read_slot(self, context: str, key: str, window: int) -> list[dict]:
        """Scan the most recent `window` records, returning those for one slot."""
        recent = self._records[-window:] if window > 0 else self._records
        if not self._charge(len(recent)):
            return []
        return [r for r in recent if r["context"] == context and r["key"] == key]

    def read_recent(self, window: int) -> list[dict]:
        recent = self._records[-window:] if window > 0 else self._records
        if not self._charge(len(recent)):
            return []
        return list(recent)

    def stats(self) -> dict:
        return {
            "evidence_reads": self.reads,
            "read_ceiling": self.read_ceiling,
            "exhausted_reads": self.exhausted_reads,
            "log_capacity": self.capacity,
            "log_evictions": self.evictions,
            "log_size": len(self._records),
        }


class Mechanism(Protocol):
    """The full contract a system under test must satisfy.

    Anything that can implement this — a symbolic store, a latent vector, an
    LLM agent with a scratchpad — can be scored by the same benchmark.
    """

    name: str

    def observe(self, obs: dict) -> None: ...
    def on_gap(self, ev: dict) -> None: ...
    def on_context_shift(self, ev: dict) -> None: ...
    def answer(self, query: dict) -> Answer: ...
    def state_bytes(self) -> int: ...


class _Base:
    name = "base"

    def __init__(self, log: EvidenceLog, budget: Budget) -> None:
        self.log = log
        self.budget = budget
        self.now = 0
        self.context = ""
        self.maintenance_ops = 0

    def on_gap(self, ev: dict) -> None:
        self.now = ev["t"]

    def on_context_shift(self, ev: dict) -> None:
        self.now = ev["t"]
        self.context = ev["context"]

    def observe(self, obs: dict) -> None:
        self.now = obs["t"]

    def state_bytes(self) -> int:
        return 0

    def _spend(self, n: int = 1) -> bool:
        if self.maintenance_ops + n > self.budget.maintenance_ops_ceiling:
            return False
        self.maintenance_ops += n
        return True


def _slot(x: dict) -> tuple[str, str]:
    return (x["context"], x["key"])


def _restrict(scores: dict[str, float], options: Iterable[str]) -> dict[str, float]:
    opts = set(options)
    return {v: s for v, s in scores.items() if v in opts and s > 0}


def _argmax(scores: dict[str, float]) -> tuple[str | None, float]:
    if not scores:
        return (None, 0.0)
    total = sum(scores.values())
    best = max(scores, key=lambda v: (scores[v], v))
    return (best, scores[best] / total if total > 0 else 0.0)


class LastWriteWins(_Base):
    """M0 — trivially cheap, maximally credulous. Zero evidence reads."""

    name = "last-write-wins"

    def __init__(self, log, budget):
        super().__init__(log, budget)
        self.belief: dict[tuple[str, str], tuple[str, int]] = {}

    def observe(self, obs):
        super().observe(obs)
        self.belief[_slot(obs)] = (obs["value"], obs["event_id"])

    def answer(self, query):
        hit = self.belief.get(_slot(query))
        if hit is None:
            return Answer(None, 0.0, ())
        value, eid = hit
        if value not in query["options"]:
            return Answer(None, 0.0, ())
        return Answer(value, 0.85, (eid,))

    def state_bytes(self):
        return sum(len(c) + len(k) + len(v) + 8 for (c, k), (v, _) in self.belief.items())


class UnconstrainedAccumulator(_Base):
    """M1 — persistent state that only ever accretes.

    Stands in for an unconstrained persistent latent state: every observation
    nudges it, nothing is ever re-grounded, provenance is not kept, and old
    evidence never expires. Misleading repetition is expected to win here.
    """

    name = "unconstrained-accumulator"

    def __init__(self, log, budget, gain: float = 1.0):
        super().__init__(log, budget)
        self.gain = gain
        self.scores: dict[tuple[str, str], dict[str, float]] = {}

    def observe(self, obs):
        super().observe(obs)
        self.scores.setdefault(_slot(obs), {})
        s = self.scores[_slot(obs)]
        s[obs["value"]] = s.get(obs["value"], 0.0) + self.gain

    def answer(self, query):
        s = _restrict(self.scores.get(_slot(query), {}), query["options"])
        value, share = _argmax(s)
        if value is None:
            return Answer(None, 0.0, ())
        return Answer(value, share, ())

    def state_bytes(self):
        return sum(len(c) + len(k) + sum(len(v) + 8 for v in d) for (c, k), d in self.scores.items())


class PeriodicReset(_Base):
    """M2 — wipe persistent state on a fixed cadence and rebuild from the log."""

    name = "periodic-reset"

    def __init__(self, log, budget, period: int = 60, window: int = 120):
        super().__init__(log, budget)
        self.period = period
        self.window = window
        self.seen = 0
        self.inner = UnconstrainedAccumulator(log, budget)
        self.resets = 0

    def observe(self, obs):
        super().observe(obs)
        self.inner.observe(obs)
        self.seen += 1
        if self.seen % self.period == 0 and self._spend():
            self.inner = UnconstrainedAccumulator(self.log, self.budget)
            self.resets += 1
            for rec in self.log.read_recent(self.window):
                self.inner.observe(rec)

    def on_gap(self, ev):
        super().on_gap(ev)

    def answer(self, query):
        return self.inner.answer(query)

    def state_bytes(self):
        return self.inner.state_bytes()


class EvidenceReconstruction(_Base):
    """M3 — hold no belief; re-derive from the evidence log at query time."""

    name = "evidence-reconstruction"

    def __init__(self, log, budget, window: int = 200):
        super().__init__(log, budget)
        self.window = window

    def answer(self, query):
        recs = self.log.read_slot(query["context"], query["key"], self.window)
        recs = [r for r in recs if r["value"] in query["options"]]
        if not recs:
            return Answer(None, 0.0, ())
        latest = max(r["t"] for r in recs)
        winner = next(r for r in recs if r["t"] == latest)
        agree = [r for r in recs if r["value"] == winner["value"]]
        return Answer(winner["value"], len(agree) / len(recs), tuple(r["event_id"] for r in agree))

    def state_bytes(self):
        return 0


class ProvenanceRegrounding(_Base):
    """M4 — weight evidence by an estimated per-source reliability.

    Reliability is estimated without ground truth: a source is credited when it
    agrees with the tier-weighted consensus it was part of. The estimate is
    therefore itself corruptible, which is the point.
    """

    name = "provenance-regrounding"

    def __init__(self, log, budget, window: int = 200, prior: float = 4.0):
        super().__init__(log, budget)
        self.window = window
        self.prior = prior
        self.hits: dict[str, float] = {}
        self.trials: dict[str, float] = {}
        self.tier: dict[str, str] = {}

    def observe(self, obs):
        super().observe(obs)
        self.tier[obs["source_id"]] = obs["source_tier"]

    def _reliability(self, source_id: str) -> float:
        tier = self.tier.get(source_id, "secondary")
        p0 = TIER_PRIOR.get(tier, 0.6)
        h = self.hits.get(source_id, 0.0)
        n = self.trials.get(source_id, 0.0)
        return (h + self.prior * p0) / (n + self.prior)

    def answer(self, query):
        recs = self.log.read_slot(query["context"], query["key"], self.window)
        recs = [r for r in recs if r["value"] in query["options"]]
        if not recs:
            return Answer(None, 0.0, ())
        weights: dict[str, float] = {}
        for r in recs:
            rel = self._reliability(r["source_id"])
            recency = math.exp(-(self.now - r["t"]) / 6000.0)
            weights[r["value"]] = weights.get(r["value"], 0.0) + rel * (0.35 + 0.65 * recency)
        value, share = _argmax(weights)
        # Credit sources that agreed with the resolved consensus.
        for r in recs:
            self.trials[r["source_id"]] = self.trials.get(r["source_id"], 0.0) + 1.0
            if r["value"] == value:
                self.hits[r["source_id"]] = self.hits.get(r["source_id"], 0.0) + 1.0
        support = tuple(r["event_id"] for r in recs if r["value"] == value)
        return Answer(value, share, support)

    def state_bytes(self):
        return sum(len(s) + 24 for s in self.tier)


class ConfidenceDecay(_Base):
    """M5 — beliefs lose confidence with elapsed time and abstain when unsure."""

    name = "confidence-decay"

    def __init__(self, log, budget, half_life: float = 5000.0, abstain_below: float = 0.35):
        super().__init__(log, budget)
        self.half_life = half_life
        self.abstain_below = abstain_below
        self.scores: dict[tuple[str, str], dict[str, float]] = {}
        self.stamp: dict[tuple[str, str], int] = {}

    def _decay(self, slot: tuple[str, str]) -> None:
        last = self.stamp.get(slot)
        if last is None:
            return
        dt = max(0, self.now - last)
        factor = 0.5 ** (dt / self.half_life)
        for v in self.scores.get(slot, {}):
            self.scores[slot][v] *= factor
        self.stamp[slot] = self.now

    def observe(self, obs):
        super().observe(obs)
        slot = _slot(obs)
        self.scores.setdefault(slot, {})
        self._decay(slot)
        self.scores[slot][obs["value"]] = self.scores[slot].get(obs["value"], 0.0) + 1.0
        self.stamp[slot] = self.now

    def answer(self, query):
        slot = _slot(query)
        self.now = query["t"]
        self._decay(slot)
        s = _restrict(self.scores.get(slot, {}), query["options"])
        value, share = _argmax(s)
        if value is None:
            return Answer(None, 0.0, ())
        strength = 1.0 - math.exp(-sum(s.values()))
        conf = share * strength
        if conf < self.abstain_below:
            return Answer(None, conf, ())
        return Answer(value, conf, ())

    def state_bytes(self):
        return sum(len(c) + len(k) + sum(len(v) + 8 for v in d) for (c, k), d in self.scores.items())


class ContradictionTriggeredRegrounding(_Base):
    """M6 — cheap accumulation until a conflict fires a targeted re-grounding."""

    name = "contradiction-regrounding"

    def __init__(self, log, budget, window: int = 200):
        super().__init__(log, budget)
        self.window = window
        self.inner = UnconstrainedAccumulator(log, budget)
        self.support: dict[tuple[str, str], tuple[int, ...]] = {}
        self.triggers = 0

    def observe(self, obs):
        super().observe(obs)
        slot = _slot(obs)
        prior, _ = _argmax(self.inner.scores.get(slot, {}))
        self.inner.observe(obs)
        if prior is not None and obs["value"] != prior and self._spend():
            self.triggers += 1
            recs = self.log.read_slot(obs["context"], obs["key"], self.window)
            if recs:
                fresh: dict[str, float] = {}
                for r in recs:
                    w = TIER_PRIOR.get(r["source_tier"], 0.6)
                    recency = math.exp(-(self.now - r["t"]) / 6000.0)
                    fresh[r["value"]] = fresh.get(r["value"], 0.0) + w * (0.35 + 0.65 * recency)
                self.inner.scores[slot] = fresh
                win, _ = _argmax(fresh)
                self.support[slot] = tuple(r["event_id"] for r in recs if r["value"] == win)

    def answer(self, query):
        ans = self.inner.answer(query)
        if ans.value is None:
            return ans
        sup = self.support.get(_slot(query), ())
        return Answer(ans.value, ans.confidence, sup)

    def state_bytes(self):
        return self.inner.state_bytes()


class HybridSymbolicLatent(_Base):
    """M7 — a canonical symbolic store fronting a latent accumulator.

    A slot is promoted into the symbolic store only on corroborated
    high-reliability evidence; everything else is answered from the accumulator.
    This is the *control* for "would a symbolic spine have been enough", not a
    proposed CCS architecture.
    """

    name = "hybrid-symbolic-latent"

    def __init__(self, log, budget, corroboration: int = 2):
        super().__init__(log, budget)
        self.corroboration = corroboration
        self.symbolic: dict[tuple[str, str], tuple[str, tuple[int, ...], int]] = {}
        self.pending: dict[tuple[str, str], dict[str, list[int]]] = {}
        self.latent = UnconstrainedAccumulator(log, budget)

    def observe(self, obs):
        super().observe(obs)
        self.latent.observe(obs)
        slot = _slot(obs)
        if obs["source_tier"] == "unreliable":
            return
        book = self.pending.setdefault(slot, {})
        book.setdefault(obs["value"], []).append(obs["event_id"])
        if len(book[obs["value"]]) >= self.corroboration:
            self.symbolic[slot] = (obs["value"], tuple(book[obs["value"]][-4:]), obs["t"])
            self.pending[slot] = {obs["value"]: book[obs["value"]]}

    def answer(self, query):
        slot = _slot(query)
        hit = self.symbolic.get(slot)
        if hit is not None and hit[0] in query["options"]:
            return Answer(hit[0], 0.9, hit[1])
        return self.latent.answer(query)

    def state_bytes(self):
        sym = sum(len(c) + len(k) + len(v) + 8 * len(s) for (c, k), (v, s, _) in self.symbolic.items())
        return sym + self.latent.state_bytes()


class LossyLatent(_Base):
    """M8 — a bounded persistent latent state with capacity interference.

    Slots are hashed into a fixed number of cells and share whatever is stored
    there, so writes about one slot bleed into beliefs about another. This is
    the crudest honest stand-in for a fixed-width latent state, and it is the
    only reference arm that can produce a belief *nothing ever asserted about
    that slot* — the failure the unsupported-belief and self-contradiction
    metrics exist to catch.

    It is a control, not a proposal. No CCS architecture is implied by it.
    """

    name = "lossy-latent"

    def __init__(self, log, budget, cells: int = 12, bleed: float = 0.55, decay: float = 0.997):
        super().__init__(log, budget)
        self.cells = cells
        self.bleed = bleed
        self.decay = decay
        self.table: list[dict[str, float]] = [{} for _ in range(cells)]
        self.own: dict[tuple[str, str], dict[str, float]] = {}

    def _cell(self, slot: tuple[str, str]) -> int:
        # zlib.crc32, not hash(): str hashing is salted per process, which would
        # make this arm irreproducible across runs of the same seed.
        return zlib.crc32("\x00".join(slot).encode()) % self.cells

    def observe(self, obs):
        super().observe(obs)
        slot, val = _slot(obs), obs["value"]
        own = self.own.setdefault(slot, {})
        for v in own:
            own[v] *= self.decay
        own[val] = own.get(val, 0.0) + 1.0
        cell = self.table[self._cell(slot)]
        for v in cell:
            cell[v] *= self.decay
        cell[val] = cell.get(val, 0.0) + 1.0

    def answer(self, query):
        slot = _slot(query)
        merged: dict[str, float] = {}
        for v, sc in self.own.get(slot, {}).items():
            merged[v] = merged.get(v, 0.0) + sc
        for v, sc in self.table[self._cell(slot)].items():
            merged[v] = merged.get(v, 0.0) + self.bleed * sc
        s = _restrict(merged, query["options"])
        value, share = _argmax(s)
        if value is None:
            return Answer(None, 0.0, ())
        return Answer(value, share, ())

    def state_bytes(self):
        return sum(sum(len(v) + 8 for v in cell) for cell in self.table)


DRIFT_MECHANISMS: dict[str, Callable[[EvidenceLog, Budget], _Base]] = {
    LastWriteWins.name: LastWriteWins,
    UnconstrainedAccumulator.name: UnconstrainedAccumulator,
    PeriodicReset.name: PeriodicReset,
    EvidenceReconstruction.name: EvidenceReconstruction,
    ProvenanceRegrounding.name: ProvenanceRegrounding,
    ConfidenceDecay.name: ConfidenceDecay,
    ContradictionTriggeredRegrounding.name: ContradictionTriggeredRegrounding,
    HybridSymbolicLatent.name: HybridSymbolicLatent,
    LossyLatent.name: LossyLatent,
}

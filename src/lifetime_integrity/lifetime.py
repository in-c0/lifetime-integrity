"""LIS-v0 — Lifetime Integrity Stream generator.

A *lifetime* is a long, deterministic sequence of events over a hidden canonical
world. The system under test (SUT) sees only the redacted `visible()` view of
each event; canonical values, truthfulness flags, and corruption tags are
harness-only audit metadata.

The corruption process is deliberately independent of any mechanism. Rates live
in `LifetimeConfig`, and `config_lock()` fingerprints them so a run manifest can
prove which corruption process produced its lifetime. Corruption rates must not
be edited after mechanism results are inspected; see
`experiments/EXP-A001-PREREG.md`.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Iterable
from dataclasses import asdict, dataclass

GENERATOR_VERSION = "LIS-v0.1.0"

SYLLABLES_A = ["ka", "vo", "ri", "me", "tu", "sa", "ne", "po", "lu", "di", "fa", "zy"]
SYLLABLES_B = ["rin", "vok", "tal", "mos", "qen", "pax", "dul", "zim", "lor", "fen", "gur", "siv"]

TIERS = ("primary", "secondary", "unreliable")

# Fields that must never reach the SUT. Enforced by tests and by the harness.
AUDIT_FIELDS = frozenset(
    {
        "truthful",
        "corruption",
        "world_version",
        "canonical",
        "superseded",
        "ever_asserted",
        "probe_class",
        "responsible_slot",
        "responsible_event_id",
        "epoch",
    }
)


@dataclass(frozen=True)
class LifetimeConfig:
    """Frozen description of the corruption process.

    Every field here is part of the preregistered benchmark definition. Changing
    any of them produces a different `config_lock()` and therefore a different
    benchmark version.
    """

    seed: int
    epochs: int = 24
    contexts: int = 4
    keys_per_context: int = 6
    global_keys: int = 3
    values_per_slot: int = 5
    vocab_size: int = 24
    asserts_per_epoch: int = 14
    probes_per_epoch: int = 10

    p_world_change: float = 0.08
    world_change_announcements: int = 2
    p_quiet_world_change: float = 0.25

    p_misinformation: float = 0.18
    p_misleading_repeat: float = 0.35
    repeat_burst: int = 3

    p_contradiction: float = 0.12
    p_context_shift: float = 0.35
    p_gap: float = 0.25
    gap_ticks: int = 4000
    tick_per_event: int = 3

    tier_reliability: tuple[float, float, float] = (0.98, 0.85, 0.35)
    tier_weights: tuple[float, float, float] = (0.35, 0.40, 0.25)
    sources_per_tier: int = 3

    delayed_outcomes_per_epoch: float = 0.0
    outcome_lag_epochs: int = 3
    outcome_decoy_slots: int = 4

    def config_lock(self) -> str:
        payload = {"generator": GENERATOR_VERSION, "config": asdict(self)}
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Assertion:
    """An observation offered to the SUT by some source."""

    event_id: int
    t: int
    context: str
    key: str
    value: str
    source_id: str
    source_tier: str
    # audit-only
    truthful: bool
    corruption: str
    world_version: int
    epoch: int
    kind: str = "assert"

    def visible(self) -> dict:
        return {
            "kind": "assert",
            "event_id": self.event_id,
            "t": self.t,
            "context": self.context,
            "key": self.key,
            "value": self.value,
            "source_id": self.source_id,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True)
class Probe:
    """An evaluation query. Never available to the SUT as evidence."""

    event_id: int
    t: int
    context: str
    key: str
    options: tuple[str, ...]
    # audit-only
    canonical: str
    superseded: tuple[str, ...]
    ever_asserted: tuple[str, ...]
    probe_class: str
    epoch: int
    kind: str = "probe"

    def visible(self) -> dict:
        return {
            "kind": "probe",
            "event_id": self.event_id,
            "t": self.t,
            "context": self.context,
            "key": self.key,
            "options": list(self.options),
        }


@dataclass(frozen=True)
class Gap:
    event_id: int
    t: int
    ticks: int
    epoch: int
    kind: str = "gap"

    def visible(self) -> dict:
        return {"kind": "gap", "event_id": self.event_id, "t": self.t, "ticks": self.ticks}


@dataclass(frozen=True)
class ContextShift:
    event_id: int
    t: int
    context: str
    epoch: int
    kind: str = "context_shift"

    def visible(self) -> dict:
        return {
            "kind": "context_shift",
            "event_id": self.event_id,
            "t": self.t,
            "context": self.context,
        }


@dataclass(frozen=True)
class DelayedOutcome:
    """A late signal that an earlier decision was wrong.

    The SUT is told *that* a decision at `decision_t` went wrong and which slots
    that decision consulted. It is not told which of them carried the bad value:
    that is the credit-assignment problem under test.
    """

    event_id: int
    t: int
    outcome: str
    decision_t: int
    decision_event_id: int
    task_id: str
    consulted: tuple[tuple[str, str], ...]
    # audit-only
    responsible_slot: tuple[str, str]
    responsible_event_id: int
    epoch: int
    kind: str = "delayed_outcome"

    def visible(self) -> dict:
        return {
            "kind": "delayed_outcome",
            "event_id": self.event_id,
            "t": self.t,
            "outcome": self.outcome,
            "decision_t": self.decision_t,
            "decision_event_id": self.decision_event_id,
            "task_id": self.task_id,
            "consulted": [list(s) for s in self.consulted],
        }


Event = Assertion | Probe | Gap | ContextShift | DelayedOutcome


@dataclass
class Lifetime:
    config: LifetimeConfig
    events: list[Event]
    slots: list[tuple[str, str]]
    stream: str

    @property
    def config_lock(self) -> str:
        return self.config.config_lock()

    def spec_sha256(self) -> str:
        """Fingerprint of the realized event sequence, audit fields included."""
        h = hashlib.sha256()
        for e in self.events:
            h.update(json.dumps(asdict(e), sort_keys=True, separators=(",", ":")).encode())
        return h.hexdigest()

    def probes(self) -> list[Probe]:
        return [e for e in self.events if isinstance(e, Probe)]

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for e in self.events:
            counts[e.kind] = counts.get(e.kind, 0) + 1
        pclass: dict[str, int] = {}
        for p in self.probes():
            pclass[p.probe_class] = pclass.get(p.probe_class, 0) + 1
        corruption: dict[str, int] = {}
        for e in self.events:
            if isinstance(e, Assertion):
                corruption[e.corruption] = corruption.get(e.corruption, 0) + 1
        return {
            "stream": self.stream,
            "events": len(self.events),
            "event_counts": counts,
            "probe_classes": pclass,
            "assertion_corruption": corruption,
            "slots": len(self.slots),
            "final_t": self.events[-1].t if self.events else 0,
        }


def _nonce(rng: random.Random, used: set[str]) -> str:
    """Draw a fresh pronounceable nonce.

    The two-syllable space is only 144 wide, so a numeric suffix is appended
    once a bare pair is taken. Long lifetimes need thousands of distinct
    symbols and must never block here.
    """
    while True:
        stem = (rng.choice(SYLLABLES_A) + rng.choice(SYLLABLES_B)).upper()
        if stem not in used:
            used.add(stem)
            return stem
        for _ in range(64):
            word = f"{stem}{rng.randrange(10, 1000)}"
            if word not in used:
                used.add(word)
                return word


class _Builder:
    """Shared construction logic for both lifetime streams."""

    def __init__(self, cfg: LifetimeConfig, salt: int) -> None:
        self.cfg = cfg
        self.rng = random.Random(cfg.seed + salt)
        self.used: set[str] = set()
        self.eid = 0
        self.t = 0
        self.events: list[Event] = []

        self.contexts = [_nonce(self.rng, self.used) for _ in range(cfg.contexts)]
        # One codebook shared by every slot. Disjoint per-slot vocabularies would
        # make cross-slot interference unrepresentable: a bounded latent state
        # that bleeds a neighbour's value could never surface it as an answer,
        # and `unsupported_belief_rate` would be structurally pinned to zero.
        self.vocab = [_nonce(self.rng, self.used) for _ in range(cfg.vocab_size)]
        self.global_context = "GLOBAL"
        self.slots: list[tuple[str, str]] = []
        self.pool: dict[tuple[str, str], list[str]] = {}
        self.canonical: dict[tuple[str, str], str] = {}
        self.version: dict[tuple[str, str], int] = {}
        self.superseded: dict[tuple[str, str], list[str]] = {}
        self.asserted: dict[tuple[str, str], set[str]] = {}
        self.last_assert_epoch: dict[tuple[str, str], int] = {}
        self.recent_flags: dict[tuple[str, str], set[str]] = {}
        self.last_true_event: dict[tuple[str, str], int] = {}
        self.last_false_event: dict[tuple[str, str], int] = {}

        for ctx in self.contexts:
            for _ in range(cfg.keys_per_context):
                self._add_slot(ctx)
        for _ in range(cfg.global_keys):
            self._add_slot(self.global_context)

        self.sources: list[tuple[str, str]] = []
        for tier in TIERS:
            for _ in range(cfg.sources_per_tier):
                self.sources.append((_nonce(self.rng, self.used), tier))

        self.active_context = self.contexts[0]

    # -- construction helpers -------------------------------------------------

    def _add_slot(self, ctx: str) -> None:
        key = _nonce(self.rng, self.used)
        slot = (ctx, key)
        values = self.rng.sample(self.vocab, self.cfg.values_per_slot)
        self.slots.append(slot)
        self.pool[slot] = values
        self.canonical[slot] = values[0]
        self.version[slot] = 1
        self.superseded[slot] = []
        self.asserted[slot] = set()
        self.last_assert_epoch[slot] = -99
        self.recent_flags[slot] = set()
        self.last_true_event[slot] = -1
        self.last_false_event[slot] = -1

    def _tick(self) -> int:
        self.t += self.cfg.tick_per_event
        return self.t

    def _next_id(self) -> int:
        self.eid += 1
        return self.eid

    def _pick_source(self, tier: str | None = None) -> tuple[str, str]:
        if tier is None:
            tier = self.rng.choices(TIERS, weights=self.cfg.tier_weights, k=1)[0]
        candidates = [s for s in self.sources if s[1] == tier]
        return self.rng.choice(candidates)

    def _false_value(self, slot: tuple[str, str]) -> str:
        options = [v for v in self.pool[slot] if v != self.canonical[slot]]
        return self.rng.choice(options)

    def _emit_assert(
        self, slot: tuple[str, str], value: str, source: tuple[str, str], corruption: str, epoch: int
    ) -> Assertion:
        ctx, key = slot
        truthful = value == self.canonical[slot]
        ev = Assertion(
            event_id=self._next_id(),
            t=self._tick(),
            context=ctx,
            key=key,
            value=value,
            source_id=source[0],
            source_tier=source[1],
            truthful=truthful,
            corruption=corruption,
            world_version=self.version[slot],
            epoch=epoch,
        )
        self.events.append(ev)
        self.asserted[slot].add(value)
        self.last_assert_epoch[slot] = epoch
        if truthful:
            self.last_true_event[slot] = ev.event_id
        else:
            self.last_false_event[slot] = ev.event_id
            self.recent_flags[slot].add("misinfo")
        return ev

    def _change_world(self, slot: tuple[str, str], epoch: int) -> None:
        old = self.canonical[slot]
        options = [v for v in self.pool[slot] if v != old]
        new = self.rng.choice(options)
        self.superseded[slot].append(old)
        self.canonical[slot] = new
        self.version[slot] += 1
        self.recent_flags[slot].add("world_change")
        # A quiet change is announced by nobody this epoch: the SUT can only find
        # out later. Otherwise a few sources announce the new value.
        if self.rng.random() < self.cfg.p_quiet_world_change:
            self.recent_flags[slot].add("quiet_change")
            return
        for _ in range(self.cfg.world_change_announcements):
            self._emit_assert(slot, new, self._pick_source(), "world_change", epoch)

    def _emit_probe(self, slot: tuple[str, str], probe_class: str, epoch: int) -> Probe:
        ctx, key = slot
        canonical = self.canonical[slot]
        asserted = self.asserted[slot]
        # Options always include the canonical value, every superseded value, any
        # value the SUT was actually told, and one never-asserted foil so that
        # unsupported answers are detectable.
        opts: list[str] = [canonical]
        for v in self.superseded[slot] + sorted(asserted):
            if v not in opts:
                opts.append(v)
        foils = [v for v in self.pool[slot] if v not in opts and v not in asserted]
        if foils:
            opts.append(self.rng.choice(foils))
        opts = opts[:5]
        order = list(opts)
        self.rng.shuffle(order)
        ev = Probe(
            event_id=self._next_id(),
            t=self._tick(),
            context=ctx,
            key=key,
            options=tuple(order),
            canonical=canonical,
            superseded=tuple(self.superseded[slot]),
            ever_asserted=tuple(sorted(asserted)),
            probe_class=probe_class,
            epoch=epoch,
        )
        self.events.append(ev)
        return ev

    def _classify(self, slot: tuple[str, str], epoch: int, post_gap: bool) -> str:
        if post_gap:
            return "post_gap"
        flags = self.recent_flags[slot]
        if "quiet_change" in flags:
            return "quiet_change"
        if "world_change" in flags:
            return "stale_risk"
        if "contradiction" in flags:
            return "contradiction"
        if "misinfo" in flags:
            return "misinfo_target"
        if epoch - self.last_assert_epoch[slot] >= 4:
            return "untouched"
        if self.last_assert_epoch[slot] == epoch:
            return "fresh"
        return "settled"

    def _assert_block(self, epoch: int) -> None:
        cfg = self.cfg
        scoped = [s for s in self.slots if s[0] in (self.active_context, self.global_context)]
        n = 0
        while n < cfg.asserts_per_epoch:
            slot = self.rng.choice(scoped)
            r = self.rng.random()
            if r < cfg.p_misinformation:
                value = self._false_value(slot)
                source = self._pick_source("unreliable" if self.rng.random() < 0.7 else "secondary")
                self._emit_assert(slot, value, source, "misinformation", epoch)
                n += 1
                if self.rng.random() < cfg.p_misleading_repeat:
                    # Misleading repetition: the same false value, restated.
                    for _ in range(cfg.repeat_burst):
                        if n >= cfg.asserts_per_epoch:
                            break
                        self._emit_assert(slot, value, self._pick_source(), "misleading_repeat", epoch)
                        n += 1
            elif r < cfg.p_misinformation + cfg.p_contradiction:
                # Two sources disagree in the same epoch about the same slot.
                self._emit_assert(slot, self.canonical[slot], self._pick_source("primary"), "contradiction", epoch)
                n += 1
                if n < cfg.asserts_per_epoch:
                    self._emit_assert(slot, self._false_value(slot), self._pick_source("unreliable"), "contradiction", epoch)
                    n += 1
                self.recent_flags[slot].add("contradiction")
            else:
                self._emit_assert(slot, self.canonical[slot], self._pick_source(), "clean", epoch)
                n += 1

    def _probe_block(self, epoch: int, post_gap: bool) -> None:
        cfg = self.cfg
        # Probe both currently-scoped slots and slots from other contexts, so
        # that drift on out-of-context state is observable.
        scoped = [s for s in self.slots if s[0] in (self.active_context, self.global_context)]
        others = [s for s in self.slots if s not in scoped]
        picks: list[tuple[str, str]] = []
        for i in range(cfg.probes_per_epoch):
            src = scoped if (i % 3 != 2 or not others) else others
            picks.append(self.rng.choice(src))
        for i, slot in enumerate(picks):
            self._emit_probe(slot, self._classify(slot, epoch, post_gap and i == 0), epoch)

    def _maybe_shift(self, epoch: int) -> None:
        if self.rng.random() >= self.cfg.p_context_shift:
            return
        self.active_context = self.rng.choice(self.contexts)
        self.events.append(
            ContextShift(event_id=self._next_id(), t=self._tick(), context=self.active_context, epoch=epoch)
        )

    def _maybe_gap(self, epoch: int) -> bool:
        if self.rng.random() >= self.cfg.p_gap:
            return False
        self.t += self.cfg.gap_ticks
        self.events.append(
            Gap(event_id=self._next_id(), t=self.t, ticks=self.cfg.gap_ticks, epoch=epoch)
        )
        return True

    def _world_changes(self, epoch: int) -> None:
        for slot in self.slots:
            if self.rng.random() < self.cfg.p_world_change:
                self._change_world(slot, epoch)


def generate_drift_lifetime(config: LifetimeConfig) -> Lifetime:
    """Class A stream: latent drift and re-grounding. No delayed outcomes."""
    b = _Builder(config, salt=0)
    post_gap = False
    for epoch in range(config.epochs):
        for slot in b.slots:
            b.recent_flags[slot].clear()
        b._maybe_shift(epoch)
        b._world_changes(epoch)
        b._assert_block(epoch)
        b._probe_block(epoch, post_gap)
        post_gap = b._maybe_gap(epoch)
    return Lifetime(config=config, events=b.events, slots=b.slots, stream="drift")


def generate_delayed_credit_lifetime(config: LifetimeConfig) -> Lifetime:
    """Class B stream: delayed outcomes that implicate an earlier belief.

    A decision is recorded at epoch `e` consulting several slots; the outcome
    arrives at epoch `e + outcome_lag_epochs`. Exactly one consulted slot carried
    a value the SUT had been told but that was false at decision time. The other
    consulted slots are decoys that were correct.
    """
    if config.delayed_outcomes_per_epoch <= 0:
        raise ValueError("delayed_credit stream requires delayed_outcomes_per_epoch > 0")
    b = _Builder(config, salt=7717)
    pending: dict[int, list[dict]] = {}
    post_gap = False

    for epoch in range(config.epochs):
        for slot in b.slots:
            b.recent_flags[slot].clear()
        b._maybe_shift(epoch)
        b._world_changes(epoch)
        b._assert_block(epoch)

        # Outcomes scheduled for this epoch are emitted here, in stream order and
        # on the live clock, so that probes still follow them. Assigning ids or
        # timestamps in a later pass would push every outcome past the last
        # probe and make post-outcome repair unmeasurable.
        for kwargs in pending.pop(epoch, []):
            b.events.append(
                DelayedOutcome(event_id=b._next_id(), t=b._tick(), epoch=epoch, **kwargs)
            )

        n_out = int(config.delayed_outcomes_per_epoch)
        frac = config.delayed_outcomes_per_epoch - n_out
        if b.rng.random() < frac:
            n_out += 1
        for _ in range(n_out):
            arrival = epoch + config.outcome_lag_epochs
            if arrival >= config.epochs:
                continue
            corrupted = [
                s
                for s in b.slots
                if b.last_false_event[s] >= 0 and b.last_false_event[s] > b.last_true_event[s]
            ]
            if not corrupted:
                continue
            culprit = b.rng.choice(corrupted)
            decoys = [
                s
                for s in b.slots
                if s != culprit and b.last_true_event[s] >= 0 and b.last_true_event[s] > b.last_false_event[s]
            ]
            if len(decoys) < config.outcome_decoy_slots:
                continue
            consulted = [culprit] + b.rng.sample(decoys, config.outcome_decoy_slots)
            b.rng.shuffle(consulted)
            pending.setdefault(arrival, []).append(
                {
                    "outcome": "failure",
                    "decision_t": b.t,
                    "decision_event_id": b.eid,
                    "task_id": f"task-{epoch}-{b.eid}",
                    "consulted": tuple(consulted),
                    "responsible_slot": culprit,
                    "responsible_event_id": b.last_false_event[culprit],
                }
            )

        b._probe_block(epoch, post_gap)
        post_gap = b._maybe_gap(epoch)

    return Lifetime(config=config, events=b.events, slots=b.slots, stream="delayed_credit")


def write_jsonl(path, events: Iterable[Event]) -> None:
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(asdict(ev), sort_keys=True) + "\n")

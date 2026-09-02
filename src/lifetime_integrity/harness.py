"""Run a mechanism over a lifetime and emit a machine-checkable manifest.

The harness is the only component that sees both the visible stream and the
audit fields. It enforces the separation: every dict handed to a mechanism is
checked against `AUDIT_FIELDS`, and any leak is counted in the manifest rather
than raised away silently.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .consolidation import CONSOLIDATORS, ConsolidationReport
from .lifetime import (
    AUDIT_FIELDS,
    GENERATOR_VERSION,
    Assertion,
    ContextShift,
    DelayedOutcome,
    Gap,
    Lifetime,
    Probe,
)
from .mechanisms import DRIFT_MECHANISMS, Budget, EvidenceLog
from .metrics import (
    ProbeRecord,
    evaluate,
    score_consolidation,
    scoring_protocol,
    scoring_protocol_sha256,
)

MANIFEST_VERSION = "1.1"


def source_tree_sha256(root: Path | None = None) -> str:
    """Deterministic fingerprint of the package source.

    A pilot provenance fallback only. Development and confirmatory runs should
    additionally record a real git commit SHA.
    """
    root = root or Path(__file__).resolve().parent
    h = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        h.update(path.relative_to(root).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def default_budget(lifetime: Lifetime, reads_per_probe: int = 200) -> Budget:
    """A ceiling generous enough for the hungriest reference mechanism.

    Sized from the lifetime, not from any mechanism's measured appetite, so the
    ceiling cannot be quietly tuned to favour one arm.
    """
    n_probes = sum(1 for e in lifetime.events if isinstance(e, Probe))
    n_asserts = sum(1 for e in lifetime.events if isinstance(e, Assertion))
    return Budget(
        evidence_reads_ceiling=n_probes * reads_per_probe,
        maintenance_ops_ceiling=n_asserts,
        log_capacity=max(256, n_asserts),
    )


def _audit_leaks(payload: dict) -> int:
    return len(AUDIT_FIELDS.intersection(payload.keys()))


@dataclass
class RunResult:
    manifest: dict
    records: list[ProbeRecord]

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.manifest, indent=2, sort_keys=True))


def _environment() -> dict:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
    }


def _base_manifest(
    lifetime: Lifetime,
    name: str,
    budget: Budget,
    classification: str,
    git_commit: str | None,
) -> dict:
    return {
        "manifest_version": MANIFEST_VERSION,
        "classification": classification,
        "arm": name,
        "stream": lifetime.stream,
        "seed": lifetime.config.seed,
        "generator_version": GENERATOR_VERSION,
        "config_lock_sha256": lifetime.config_lock,
        "lifetime_spec_sha256": lifetime.spec_sha256(),
        "lifetime_config": asdict(lifetime.config),
        "lifetime_summary": lifetime.summary(),
        "source_tree_sha256": source_tree_sha256(),
        "git_commit": git_commit,
        "environment": _environment(),
        "budget_ceiling": asdict(budget),
        "invalidation_reasons": [],
    }


def run_drift(
    lifetime: Lifetime,
    mechanism: str,
    budget: Budget | None = None,
    classification: str = "PILOT",
    git_commit: str | None = None,
) -> RunResult:
    """Class A: score one integrity mechanism over one lifetime."""
    if lifetime.stream != "drift":
        raise ValueError(f"run_drift expects the drift stream, got {lifetime.stream!r}")
    if any(isinstance(e, DelayedOutcome) for e in lifetime.events):
        raise ValueError("drift lifetime unexpectedly contains delayed outcomes")
    if mechanism not in DRIFT_MECHANISMS:
        raise KeyError(f"unknown mechanism {mechanism!r}")
    budget = budget or default_budget(lifetime)
    log = EvidenceLog(capacity=budget.log_capacity, read_ceiling=budget.evidence_reads_ceiling)
    sut = DRIFT_MECHANISMS[mechanism](log, budget)

    records: list[ProbeRecord] = []
    support_index: dict[int, tuple[str, str, str]] = {}
    assertion_times: dict[tuple[str, str], list[int]] = {}
    leaks = 0
    started = time.perf_counter()

    for ev in lifetime.events:
        payload = ev.visible()
        leaks += _audit_leaks(payload)
        if isinstance(ev, Assertion):
            support_index[ev.event_id] = (ev.context, ev.key, ev.value)
            assertion_times.setdefault((ev.context, ev.key), []).append(ev.t)
            log.append(payload)
            sut.observe(payload)
        elif isinstance(ev, Gap):
            sut.on_gap(payload)
        elif isinstance(ev, ContextShift):
            sut.on_context_shift(payload)
        elif isinstance(ev, Probe):
            ans = sut.answer(payload)
            value = ans.value
            if value is not None and value not in ev.options:
                # Answering outside the offered options is a protocol violation,
                # scored as an abstention and reported.
                value = None
            records.append(
                ProbeRecord(
                    event_id=ev.event_id,
                    t=ev.t,
                    epoch=ev.epoch,
                    context=ev.context,
                    key=ev.key,
                    probe_class=ev.probe_class,
                    options=ev.options,
                    canonical=ev.canonical,
                    superseded=ev.superseded,
                    ever_asserted=ev.ever_asserted,
                    answer=value,
                    confidence=float(ans.confidence),
                    support=tuple(ans.support),
                )
            )

    elapsed = time.perf_counter() - started
    metrics = evaluate(records, support_index, assertion_times)

    manifest = _base_manifest(lifetime, mechanism, budget, classification, git_commit)
    manifest.update(
        {
            "experiment": "EXP-A001",
            "metrics": metrics.to_dict(),
            "budget_actual": {
                **log.stats(),
                "maintenance_ops": getattr(sut, "maintenance_ops", 0),
                "maintenance_ops_ceiling": budget.maintenance_ops_ceiling,
                "state_bytes": sut.state_bytes(),
                "wall_seconds": elapsed,
            },
            "audit_leak_count": leaks,
        }
    )
    if leaks:
        manifest["invalidation_reasons"].append(f"audit_field_leak:{leaks}")
    if log.reads > budget.evidence_reads_ceiling:
        manifest["invalidation_reasons"].append("evidence_read_ceiling_exceeded")
    return RunResult(manifest=manifest, records=records)


def run_delayed_credit(
    lifetime: Lifetime,
    consolidator: str,
    budget: Budget | None = None,
    classification: str = "PILOT",
    window_probes: int = 3,
    git_commit: str | None = None,
    control_selection_salt: str = "",
) -> RunResult:
    """Class B: score one delayed-credit rule over one lifetime."""
    if lifetime.stream != "delayed_credit":
        raise ValueError(f"run_delayed_credit expects the delayed_credit stream, got {lifetime.stream!r}")
    if consolidator not in CONSOLIDATORS:
        raise KeyError(f"unknown consolidator {consolidator!r}")
    budget = budget or default_budget(lifetime)
    log = EvidenceLog(capacity=budget.log_capacity, read_ceiling=budget.evidence_reads_ceiling)
    sut = CONSOLIDATORS[consolidator](log, budget)

    records: list[ProbeRecord] = []
    support_index: dict[int, tuple[str, str, str]] = {}
    assertion_times: dict[tuple[str, str], list[int]] = {}
    outcomes: list[dict] = []
    reports: list[ConsolidationReport] = []
    leaks = 0
    started = time.perf_counter()

    for ev in lifetime.events:
        payload = ev.visible()
        leaks += _audit_leaks(payload)
        if isinstance(ev, Assertion):
            support_index[ev.event_id] = (ev.context, ev.key, ev.value)
            assertion_times.setdefault((ev.context, ev.key), []).append(ev.t)
            log.append(payload)
            sut.observe(payload)
        elif isinstance(ev, Gap):
            sut.on_gap(payload)
        elif isinstance(ev, ContextShift):
            sut.on_context_shift(payload)
        elif isinstance(ev, DelayedOutcome):
            reports.append(sut.handle_outcome(payload))
            outcomes.append(
                {
                    "event_id": ev.event_id,
                    "t": ev.t,
                    "responsible_slot": list(ev.responsible_slot),
                    "consulted": [list(s) for s in ev.consulted],
                }
            )
        elif isinstance(ev, Probe):
            ans = sut.answer(payload)
            value = ans.value if (ans.value is None or ans.value in ev.options) else None
            records.append(
                ProbeRecord(
                    event_id=ev.event_id,
                    t=ev.t,
                    epoch=ev.epoch,
                    context=ev.context,
                    key=ev.key,
                    probe_class=ev.probe_class,
                    options=ev.options,
                    canonical=ev.canonical,
                    superseded=ev.superseded,
                    ever_asserted=ev.ever_asserted,
                    answer=value,
                    confidence=float(ans.confidence),
                    support=tuple(ans.support),
                )
            )

    elapsed = time.perf_counter() - started
    integrity = evaluate(records, support_index, assertion_times)
    credit = score_consolidation(
        records,
        reports,
        outcomes,
        window_probes=window_probes,
        run_seed=lifetime.config.seed,
        control_selection_salt=control_selection_salt,
    )

    manifest = _base_manifest(lifetime, consolidator, budget, classification, git_commit)
    manifest.update(
        {
            "experiment": "EXP-B001",
            "metrics": integrity.to_dict(),
            "consolidation_metrics": credit.metrics.to_dict(),
            "scoring_protocol": scoring_protocol(window_probes),
            "scoring_protocol_sha256": scoring_protocol_sha256(window_probes),
            "matched_untouched_control": credit.matched_untouched_control,
            "budget_actual": {
                **log.stats(),
                "maintenance_ops": sut.maintenance_ops,
                "maintenance_ops_ceiling": budget.maintenance_ops_ceiling,
                "state_bytes": sut.state_bytes(),
                "wall_seconds": elapsed,
            },
            "audit_leak_count": leaks,
            "delayed_outcomes_seen": len(outcomes),
        }
    )
    if leaks:
        manifest["invalidation_reasons"].append(f"audit_field_leak:{leaks}")
    if not outcomes:
        manifest["invalidation_reasons"].append("no_delayed_outcomes_in_lifetime")
    return RunResult(manifest=manifest, records=records)

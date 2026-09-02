#!/usr/bin/env python3
"""Validate LIS-v0 run manifests before any comparative claim is made.

The validator answers one question: *is this set of runs a fair comparison at
all?* It never looks at which arm won. Run it before reading any metric.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# An EXP-A001 comparison is meaningless without a drift reference to improve on
# and at least one re-grounding mechanism to test.
A_REQUIRED = {"unconstrained-accumulator", "lossy-latent"}
A_REGROUNDING = {
    "periodic-reset",
    "evidence-reconstruction",
    "provenance-regrounding",
    "confidence-decay",
    "contradiction-regrounding",
    "hybrid-symbolic-latent",
}
B_REQUIRED = {"no-consolidation", "uniform-blame"}

CEILING_ACCURACY = 0.95
FLOOR_ACCURACY = 0.40

# Metrics each experiment claims to measure. Liveness is enforced only on these:
# a metric that is structurally zero for an experiment's substrate is not a
# broken benchmark, but it must not be reported as evidence either. EXP-B001
# shares one evidence-derived substrate across arms, so no arm can hold a belief
# nothing asserted; `unsupported_belief_rate` is therefore out of scope there.
LIVE_METRICS = {
    "EXP-A001": ("unsupported_belief_rate", "self_contradiction_rate", "stale_state_rate"),
    "EXP-B001": ("stale_state_rate",),
}
LIVE_CONSOLIDATION = ("attribution_precision", "attribution_recall", "collateral_revision_rate")


def rel_spread(values: list[float]) -> float:
    if not values:
        return 0.0
    m = max(values)
    return 0.0 if m == 0 else (m - min(values)) / m


def validate(runs: list[dict], tolerance: float = 0.02) -> dict:
    reasons: list[str] = []
    arms = {r.get("arm") for r in runs}
    experiments = {r.get("experiment") for r in runs}

    mixed = len(experiments) > 1
    if mixed:
        reasons.append(f"mixed_experiments:{sorted(experiments)}")
    # A mixed set has no single experiment contract, so experiment-specific
    # checks below are skipped rather than applied to the wrong manifests.
    experiment = None if mixed else next(iter(experiments), None)

    if any(r.get("classification") != "PILOT" for r in runs):
        reasons.append("input_run_already_claims_nonpilot_status")

    for field in ("config_lock_sha256", "lifetime_spec_sha256", "source_tree_sha256", "seed", "stream"):
        values = {r.get(field) for r in runs}
        if None in values or "" in values:
            reasons.append(f"missing_{field}")
        elif len(values) > 1:
            reasons.append(f"arms_disagree_on_{field}")

    # Corruption process must be identical across arms. This is the guard
    # against tuning the benchmark to a preferred winner.
    if len({json.dumps(r.get("lifetime_config"), sort_keys=True) for r in runs}) > 1:
        reasons.append("arms_ran_different_corruption_processes")

    if any(int(r.get("audit_leak_count", 1)) != 0 for r in runs):
        reasons.append("audit_field_leak")

    if any(r.get("invalidation_reasons") for r in runs):
        reasons.append("run_level_invalidation_present")

    ceilings = [float(r["budget_ceiling"]["evidence_reads_ceiling"]) for r in runs]
    if rel_spread(ceilings) > tolerance:
        reasons.append("budget_mismatch:evidence_reads_ceiling")
    caps = [float(r["budget_ceiling"]["log_capacity"]) for r in runs]
    if rel_spread(caps) > tolerance:
        reasons.append("budget_mismatch:log_capacity")

    for r in runs:
        actual = r["budget_actual"]
        if actual["evidence_reads"] > r["budget_ceiling"]["evidence_reads_ceiling"]:
            reasons.append(f"read_ceiling_exceeded:{r['arm']}")
        if actual.get("exhausted_reads", 0):
            reasons.append(f"read_budget_exhausted:{r['arm']}:{actual['exhausted_reads']}")
        if actual["maintenance_ops"] > r["budget_ceiling"]["maintenance_ops_ceiling"]:
            reasons.append(f"maintenance_ceiling_exceeded:{r['arm']}")

    accuracies = [float(r["metrics"]["canonical_accuracy"]) for r in runs]
    if accuracies and min(accuracies) > CEILING_ACCURACY:
        reasons.append("benchmark_at_ceiling")
    if accuracies and max(accuracies) < FLOOR_ACCURACY:
        reasons.append("benchmark_at_floor")

    # A metric that no arm can move is not measuring anything on this
    # configuration and must not be reported as though it were.
    inert: list[str] = []
    for metric in LIVE_METRICS.get(experiment or "", ()):
        if all(float(r["metrics"][metric]) == 0.0 for r in runs):
            inert.append(metric)
    if experiment == "EXP-B001":
        for metric in LIVE_CONSOLIDATION:
            if all(float(r.get("consolidation_metrics", {}).get(metric, 0.0)) == 0.0 for r in runs):
                inert.append(metric)
    if inert:
        reasons.append(f"inert_metrics:{sorted(inert)}")

    if experiment == "EXP-A001":
        missing = A_REQUIRED - arms
        if missing:
            reasons.append(f"missing_required_arms:{sorted(missing)}")
        if not (A_REGROUNDING & arms):
            reasons.append("no_regrounding_arm_present")
    elif experiment == "EXP-B001":
        missing = B_REQUIRED - arms
        if missing:
            reasons.append(f"missing_required_arms:{sorted(missing)}")
        if any(r.get("delayed_outcomes_seen", 0) == 0 for r in runs):
            reasons.append("arm_saw_no_delayed_outcomes")
        seen = {r.get("delayed_outcomes_seen") for r in runs}
        if len(seen) > 1:
            reasons.append("arms_saw_different_outcome_counts")

    return {
        "experiment": experiment,
        "arms": sorted(a for a in arms if a),
        "n_runs": len(runs),
        "valid_for_comparison": not reasons,
        "reasons": reasons,
        "note": "Validity only. This says nothing about which arm performed better.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("runs", nargs="+", type=Path)
    p.add_argument("--tolerance", type=float, default=0.02)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    runs = [json.loads(path.read_text()) for path in args.runs]
    report = validate(runs, tolerance=args.tolerance)
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    raise SystemExit(0 if report["valid_for_comparison"] else 1)


if __name__ == "__main__":
    main()

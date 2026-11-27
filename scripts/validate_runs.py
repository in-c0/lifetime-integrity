#!/usr/bin/env python3
"""Validate LIS-v0 run manifests before any comparative claim is made.

The validator answers one question: *is this set of runs a fair comparison at
all?* It never looks at which arm won. Run it before reading any metric.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lifetime_integrity.seeds import CONFIRMATORY_SEEDS

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
# CONFIRMATORY became admissible at the Phase-3 freeze (2026-09-03). Before the
# freeze it was banned outright to stop premature confirmatory claims. A blanket
# ban after the freeze would be theatre — it is bypassed by relabelling — so it
# is replaced by a stricter, checkable contract: a CONFIRMATORY run must carry a
# pinned commit and must sit on a seed from the frozen 12-seed list, and no
# non-confirmatory run may squat on a confirmatory seed.
ALLOWED_CLASSIFICATIONS = {"PILOT", "DEVELOPMENT", "CONFIRMATORY"}
PROTOCOL_VERSION = "phase3-confirmatory-lock"

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

# --- Phase-2 amendment 001 (M1): claim-scoped metric validity -----------------
#
# A metric may invalidate only the claims that actually depend on it. Structural
# and provenance failures still invalidate the whole cell. This exists because
# an inert `self_contradiction_rate` at 8 epochs suppressed the H2 diagnostic,
# which consumes `integrity_violation_rate` and never touches it.
#
# Where each metric is read from in a manifest.
METRIC_SOURCE = {
    "integrity_violation_rate": "metrics",
    "canonical_accuracy": "metrics",
    "unsupported_belief_rate": "metrics",
    "self_contradiction_rate": "metrics",
    "stale_state_rate": "metrics",
    "net_repair": "consolidation_metrics",
    "decoy_accuracy_delta": "consolidation_metrics",
    "attribution_precision": "consolidation_metrics",
    "attribution_recall": "consolidation_metrics",
    "collateral_revision_rate": "consolidation_metrics",
}

# Metrics that are meaningful at zero and must never be called inert: a zero
# here is a finding, not a dead instrument.
ALWAYS_LIVE = frozenset({"canonical_accuracy", "net_repair", "decoy_accuracy_delta"})

CLAIM_DEPENDENCIES = {
    "EXP-A001": {
        "H1_cost_matched_separation": ("integrity_violation_rate",),
        "H2_horizon_rank_stability": ("integrity_violation_rate",),
        "H3_integrity_not_accuracy": (
            "unsupported_belief_rate",
            "self_contradiction_rate",
            "canonical_accuracy",
        ),
        "unsupported_belief_analysis": ("unsupported_belief_rate",),
        "self_contradiction_analysis": ("self_contradiction_rate",),
        "stale_state_analysis": ("stale_state_rate",),
    },
    "EXP-B001": {
        "causal_excess_repair": ("net_repair",),
        "attribution_analysis": ("attribution_precision", "attribution_recall"),
        "collateral_analysis": ("decoy_accuracy_delta",),
        "stale_state_analysis": ("stale_state_rate",),
    },
}

# Claims with a precondition beyond metric liveness.
CLAIM_REQUIRED_ARMS = {"causal_excess_repair": ("no-consolidation",)}


def _metric_value(run: dict, metric: str) -> float:
    return float(run.get(METRIC_SOURCE[metric], {}).get(metric, 0.0))


def assess_metrics(runs: list[dict], experiment: str | None) -> dict:
    """Per-metric liveness for every metric any declared claim depends on."""
    status: dict[str, dict] = {}
    for metric in sorted({m for deps in CLAIM_DEPENDENCIES.get(experiment or "", {}).values() for m in deps}):
        if metric in ALWAYS_LIVE:
            status[metric] = {"live": True, "reason": "meaningful_at_zero"}
            continue
        inert = all(_metric_value(r, metric) == 0.0 for r in runs)
        status[metric] = {
            "live": not inert,
            "reason": "inert_across_all_arms" if inert else "live",
        }
    return status


def assess_claims(
    runs: list[dict],
    experiment: str | None,
    metric_status: dict,
    structurally_valid: bool,
    structural_reasons: list[str],
) -> dict:
    """Per-claim validity. A structural failure invalidates every claim."""
    arms = {r.get("arm") for r in runs}
    claims: dict[str, dict] = {}
    for claim, deps in CLAIM_DEPENDENCIES.get(experiment or "", {}).items():
        reasons: list[str] = []
        if not structurally_valid:
            reasons.append(f"structurally_invalid:{sorted(structural_reasons)}")
        for metric in deps:
            if not metric_status.get(metric, {}).get("live", False):
                reasons.append(f"inert_dependency:{metric}")
        for required in CLAIM_REQUIRED_ARMS.get(claim, ()):
            if required not in arms:
                reasons.append(f"missing_required_arm:{required}")
        claims[claim] = {"valid": not reasons, "depends_on": list(deps), "reasons": reasons}
    return claims


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

    classifications = {r.get("classification") for r in runs}
    if None in classifications or "" in classifications:
        reasons.append("missing_classification")
        classification = None
    elif len(classifications) > 1:
        reasons.append(f"mixed_classifications:{sorted(classifications)}")
        classification = None
    else:
        classification = next(iter(classifications), None)
        if classification not in ALLOWED_CLASSIFICATIONS:
            reasons.append("input_run_already_claims_nonpilot_status")

    for field in (
        "config_lock_sha256",
        "lifetime_spec_sha256",
        "source_tree_sha256",
        "seed",
        "stream",
    ):
        values = {r.get(field) for r in runs}
        if None in values or "" in values:
            reasons.append(f"missing_{field}")
        elif len(values) > 1:
            reasons.append(f"arms_disagree_on_{field}")

    if classification in {"DEVELOPMENT", "CONFIRMATORY"}:
        commits = {r.get("git_commit") for r in runs}
        if None in commits or "" in commits:
            reasons.append("missing_git_commit_for_nonpilot")
        elif len(commits) > 1:
            reasons.append("arms_disagree_on_git_commit")

    seeds = {r.get("seed") for r in runs}
    if classification == "CONFIRMATORY":
        stray = sorted(x for x in seeds if x not in CONFIRMATORY_SEEDS)
        if stray:
            reasons.append(f"confirmatory_run_on_unfrozen_seed:{stray}")
        if any(r.get("protocol_version") != PROTOCOL_VERSION for r in runs):
            reasons.append("confirmatory_run_missing_frozen_protocol_version")
    elif seeds & set(CONFIRMATORY_SEEDS):
        reasons.append("nonconfirmatory_run_squatting_on_confirmatory_seed")

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
    # Amendment 001 (M1): inert declared metrics no longer invalidate the whole
    # cell. They are reported here and consumed by the per-claim assessment
    # below, so they invalidate exactly the claims that depend on them.

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

        protocol_hashes = {r.get("scoring_protocol_sha256") for r in runs}
        if None in protocol_hashes or "" in protocol_hashes:
            reasons.append("missing_scoring_protocol_sha256")
        elif len(protocol_hashes) > 1:
            reasons.append("arms_disagree_on_scoring_protocol_sha256")

        salts = {r.get("control_selection_salt") for r in runs}
        if None in salts:
            reasons.append("missing_control_selection_salt")
        elif len(salts) > 1:
            reasons.append("arms_disagree_on_control_selection_salt")
        elif classification == "DEVELOPMENT" and next(iter(salts)) != "":
            reasons.append("nondefault_control_selection_salt_in_development")

        controls = [r.get("matched_untouched_control") for r in runs]
        if any(not isinstance(c, dict) for c in controls):
            reasons.append("missing_matched_untouched_control")
        else:
            selected = [int(c.get("selected_total", 0)) for c in controls]
            measured = [int(c.get("measured_outcome_deltas", 0)) for c in controls]
            if any(n <= 0 for n in selected):
                reasons.append("matched_untouched_control_absent")
            if any(n <= 0 for n in measured):
                reasons.append("matched_untouched_control_inert")

            control_shapes = {
                (
                    c.get("selection_sha256"),
                    int(c.get("eligible_total", 0)),
                    int(c.get("selected_total", 0)),
                    int(c.get("outcomes_with_controls", 0)),
                )
                for c in controls
            }
            if len(control_shapes) > 1:
                reasons.append("arms_disagree_on_matched_untouched_controls")
            if any(not c.get("selection_sha256") for c in controls):
                reasons.append("missing_matched_untouched_control_selection_hash")

    structurally_valid = not reasons
    metric_status = assess_metrics(runs, experiment)
    claims = assess_claims(runs, experiment, metric_status, structurally_valid, reasons)

    return {
        "experiment": experiment,
        "classification": classification,
        "arms": sorted(a for a in arms if a),
        "n_runs": len(runs),
        "protocol_version": PROTOCOL_VERSION,
        # Structural/provenance validity. A failure here invalidates every claim.
        "structurally_valid": structurally_valid,
        "structural_reasons": reasons,
        # Retained: since amendment 001 this is defined as structural validity,
        # not as a single boolean standing in for every scientific claim.
        "valid_for_comparison": structurally_valid,
        "reasons": reasons,
        "inert_metrics": sorted(inert),
        "metric_status": metric_status,
        "claims": claims,
        "note": (
            "Validity only. This says nothing about which arm performed better. "
            "Read `claims` for per-claim validity; `valid_for_comparison` is structural only."
        ),
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

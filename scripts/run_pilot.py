#!/usr/bin/env python3
"""Run the full LIS-v0 engineering pilot across every reference arm.

ENGINEERING PILOT ONLY. Nothing this script prints is confirmatory evidence.
It exists to show that the harness runs, the budgets bind, the audit separation
holds, and every metric can actually move.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lifetime_integrity.consolidation import CONSOLIDATORS
from lifetime_integrity.harness import default_budget, run_delayed_credit, run_drift
from lifetime_integrity.lifetime import (
    LifetimeConfig,
    generate_delayed_credit_lifetime,
    generate_drift_lifetime,
)
from lifetime_integrity.mechanisms import DRIFT_MECHANISMS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_runs import validate


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=20260902)
    p.add_argument("--epochs", type=int, default=24)
    p.add_argument("--stream", choices=["drift", "delayed_credit", "both"], default="both")
    p.add_argument("--out", type=Path, default=Path("results"))
    args = p.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    overall_ok = True

    if args.stream in ("drift", "both"):
        lt = generate_drift_lifetime(LifetimeConfig(seed=args.seed, epochs=args.epochs))
        budget = default_budget(lt)
        runs = []
        for arm in DRIFT_MECHANISMS:
            result = run_drift(lt, arm, budget)
            result.write(args.out / f"EXP-A001-{arm}-seed{args.seed}.json")
            runs.append(result.manifest)
        overall_ok &= _report("EXP-A001", runs, args.out, args.seed)

    if args.stream in ("delayed_credit", "both"):
        cfg = LifetimeConfig(seed=args.seed, epochs=args.epochs, delayed_outcomes_per_epoch=1.5)
        lt = generate_delayed_credit_lifetime(cfg)
        budget = default_budget(lt)
        runs = []
        for arm in CONSOLIDATORS:
            result = run_delayed_credit(lt, arm, budget)
            result.write(args.out / f"EXP-B001-{arm}-seed{args.seed}.json")
            runs.append(result.manifest)
        overall_ok &= _report("EXP-B001", runs, args.out, args.seed)

    print("\nPILOT ONLY — not confirmatory evidence. See experiments/*-PREREG.md.")
    raise SystemExit(0 if overall_ok else 1)


def _report(experiment: str, runs: list[dict], out: Path, seed: int) -> bool:
    report = validate(runs)
    (out / f"{experiment}-validation-seed{seed}.json").write_text(json.dumps(report, indent=2))
    print(f"\n=== {experiment} (seed {seed}) ===")
    print(f"validity: {report['valid_for_comparison']}  reasons: {report['reasons'] or 'none'}")
    if not report["valid_for_comparison"]:
        print("Comparison is invalid; metrics below are printed for debugging only.")
    header = f"{'arm':30s} {'acc':>6s} {'unsup':>6s} {'stale':>6s} {'contra':>6s} {'prov':>5s} {'ECE':>6s} {'drift':>7s} {'reads':>7s}"
    print(header)
    print("-" * len(header))
    for r in runs:
        m, b = r["metrics"], r["budget_actual"]
        print(
            f"{r['arm']:30s} {m['canonical_accuracy']:6.3f} {m['unsupported_belief_rate']:6.3f} "
            f"{m['stale_state_rate']:6.3f} {m['self_contradiction_rate']:6.3f} "
            f"{m['provenance_consistency']:5.2f} {m['expected_calibration_error']:6.3f} "
            f"{m['drift_late_minus_early']:+7.3f} {b['evidence_reads']:7d}"
        )
    if experiment == "EXP-B001":
        header = f"{'arm':30s} {'prec':>6s} {'recall':>6s} {'collat':>6s} {'culprit':>8s} {'decoy':>8s} {'net':>8s}"
        print(header)
        print("-" * len(header))
        for r in runs:
            c = r["consolidation_metrics"]
            print(
                f"{r['arm']:30s} {c['attribution_precision']:6.2f} {c['attribution_recall']:6.2f} "
                f"{c['collateral_revision_rate']:6.2f} {c['culprit_accuracy_delta']:+8.3f} "
                f"{c['decoy_accuracy_delta']:+8.3f} {c['net_repair']:+8.3f}"
            )
    return report["valid_for_comparison"]


if __name__ == "__main__":
    main()

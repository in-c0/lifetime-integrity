#!/usr/bin/env python3
"""Reinterpret the existing Phase-2 development matrix under amendment 001.

Reads the already-recorded manifests and writes derived outputs *beside* them
under an `amended-001/` subtree carrying explicit protocol provenance. Original
manifests and validation files are never modified. No mechanism is re-run: this
is a reinterpretation, not an execution.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_development import DEVELOPMENT_SEEDS, HORIZONS, _rank, _spearman
from validate_runs import PROTOCOL_VERSION, validate

from lifetime_integrity.metrics import (
    PREVIOUS_SCORING_PROTOCOL_VERSION,
    SCORING_PROTOCOL_VERSION,
    excess_net_repair,
)

H2_THRESHOLD = 0.6
H2_CLAIM = "H2_horizon_rank_stability"
BASELINE_ARM = "no-consolidation"


def load_cell(root: Path, experiment: str, seed: int, epochs: int) -> list[dict]:
    d = root / experiment / f"seed-{seed}" / f"epochs-{epochs}"
    return [
        json.loads(p.read_text()) for p in sorted(d.glob("*.json")) if p.name != "validation.json"
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("results/development/0c79b2efcbf9"))
    args = ap.parse_args()
    root: Path = args.root
    out = root / "amended-001"
    out.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "protocol_version": PROTOCOL_VERSION,
        "amendment": "PHASE-2-AMENDMENT-001",
        "scoring_protocol_now": SCORING_PROTOCOL_VERSION,
        "scoring_protocol_of_recorded_manifests": PREVIOUS_SCORING_PROTOCOL_VERSION,
        "source_manifests": str(root),
        "note": (
            "Reinterpretation of existing manifests under amendment 001. "
            "No mechanism was re-run. Originals are untouched."
        ),
        "EXP-A001": {"cells": [], "H2_spearman_8_vs_128": []},
        "EXP-B001": {"cells": [], "excess_net_repair": []},
    }

    # --- EXP-A001 -----------------------------------------------------------
    ranks: dict[tuple[int, int], dict[str, float]] = {}
    claim_valid: dict[tuple[int, int], bool] = {}
    for seed in DEVELOPMENT_SEEDS:
        for epochs in HORIZONS:
            runs = load_cell(root, "EXP-A001", seed, epochs)
            v = validate(runs)
            report["EXP-A001"]["cells"].append(
                {
                    "seed": seed,
                    "epochs": epochs,
                    "structurally_valid": v["structurally_valid"],
                    "structural_reasons": v["structural_reasons"],
                    "inert_metrics": v["inert_metrics"],
                    "claims": {k: c["valid"] for k, c in v["claims"].items()},
                }
            )
            claim_valid[(seed, epochs)] = v["claims"][H2_CLAIM]["valid"]
            ranks[(seed, epochs)] = _rank(
                {r["arm"]: r["metrics"]["integrity_violation_rate"] for r in runs},
                lower_is_better=True,
            )

    for seed in DEVELOPMENT_SEEDS:
        ok8, ok128 = claim_valid[(seed, 8)], claim_valid[(seed, 128)]
        if not (ok8 and ok128):
            report["EXP-A001"]["H2_spearman_8_vs_128"].append(
                {"seed": seed, "spearman_8_vs_128": None, "reason": "h2_claim_invalid_at_endpoint"}
            )
            continue
        rho = _spearman(ranks[(seed, 8)], ranks[(seed, 128)])
        report["EXP-A001"]["H2_spearman_8_vs_128"].append(
            {
                "seed": seed,
                "spearman_8_vs_128": rho,
                "below_preregistered_0_6_threshold": (rho is not None and rho < H2_THRESHOLD),
            }
        )

    # --- EXP-B001 -----------------------------------------------------------
    excess: dict[tuple[int, int], dict[str, float | None]] = {}
    for seed in DEVELOPMENT_SEEDS:
        for epochs in HORIZONS:
            runs = load_cell(root, "EXP-B001", seed, epochs)
            v = validate(runs)
            ex = excess_net_repair(runs)
            excess[(seed, epochs)] = ex
            report["EXP-B001"]["cells"].append(
                {
                    "seed": seed,
                    "epochs": epochs,
                    "structurally_valid": v["structurally_valid"],
                    "structural_reasons": v["structural_reasons"],
                    "inert_metrics": v["inert_metrics"],
                    "claims": {k: c["valid"] for k, c in v["claims"].items()},
                    "arms": {
                        r["arm"]: {
                            "net_repair": r["consolidation_metrics"]["net_repair"],
                            "excess_net_repair": ex[r["arm"]],
                            "attribution_precision": r["consolidation_metrics"]["attribution_precision"],
                            "attribution_recall": r["consolidation_metrics"]["attribution_recall"],
                            "collateral_revision_rate": r["consolidation_metrics"]["collateral_revision_rate"],
                            "culprit_accuracy_delta": r["consolidation_metrics"]["culprit_accuracy_delta"],
                            "decoy_accuracy_delta": r["consolidation_metrics"]["decoy_accuracy_delta"],
                            "untouched_accuracy_delta": r["consolidation_metrics"]["untouched_accuracy_delta"],
                            "matched_control_coverage": r["matched_untouched_control"]["outcomes_with_controls"],
                            "delayed_outcomes_seen": r["delayed_outcomes_seen"],
                            "consolidation_reads": r["consolidation_metrics"]["consolidation_reads"],
                            "evidence_reads": r["budget_actual"]["evidence_reads"],
                            "maintenance_ops": r["budget_actual"]["maintenance_ops"],
                            "state_bytes": r["budget_actual"]["state_bytes"],
                        }
                        for r in runs
                    },
                }
            )

    # Development standard (amendment 001, M2): an active policy demonstrates
    # beneficial localization iff at >=1 horizon its excess is positive for
    # EVERY development seed. Cell counts are explicitly not sufficient.
    active = sorted({a for v in excess.values() for a in v if a != BASELINE_ARM})
    verdicts = []
    for arm in active:
        horizons_all_seeds = [
            e for e in HORIZONS if all((excess[(s, e)].get(arm) or 0.0) > 0 for s in DEVELOPMENT_SEEDS)
        ]
        verdicts.append(
            {
                "arm": arm,
                "horizons_positive_in_every_development_seed": horizons_all_seeds,
                "meets_development_standard": bool(horizons_all_seeds),
                "cells_positive": sum(
                    1 for k in excess if (excess[k].get(arm) or 0.0) > 0
                ),
                "cells_total": len(excess),
            }
        )
    report["EXP-B001"]["excess_net_repair"] = verdicts
    report["EXP-B001"]["class_kill_criterion_fires"] = not any(
        v["meets_development_standard"] for v in verdicts
    )

    path = out / "reinterpretation.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report["EXP-A001"]["H2_spearman_8_vs_128"], indent=2))
    print(json.dumps(report["EXP-B001"]["excess_net_repair"], indent=2))
    print(f"class_kill_criterion_fires: {report['EXP-B001']['class_kill_criterion_fires']}")
    print(f"written: {path}")


if __name__ == "__main__":
    main()

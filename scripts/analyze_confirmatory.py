#!/usr/bin/env python3
"""Preregistered confirmatory analysis. Implements the Phase-3 frozen procedure.

Written before any confirmatory value was inspected. Every estimator, interval,
RNG derivation and correction is fixed by `experiments/PHASE-3-CONFIRMATORY-LOCK.md`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_development import _rank, _spearman
from validate_runs import validate

from lifetime_integrity.metrics import excess_net_repair
from lifetime_integrity.seeds import CONFIRMATORY_SEEDS

HORIZONS = (8, 16, 32, 64, 128)
REPLICATES = 10_000
BASELINE_ARM = "no-consolidation"
DRIFT_REFERENCE = "unconstrained-accumulator"

# Erratum E3 (resolved before any confirmatory value was inspected). The lock
# said "best re-grounding arm" for P2 without naming it; choosing it from
# confirmatory data would be a forking path. It is therefore pinned to the arm
# that was best on DEVELOPMENT data at E128 (lowest integrity_violation_rate:
# confidence-decay, 0.516). Development exists to fix exactly this kind of
# choice. All re-grounding arms are reported regardless.
P2_ARM = "confidence-decay"
P3_ARM = "counterfactual-recheck"
P2_HORIZON, P3_HORIZON = 128, 64


def rng_for(experiment: str, claim: str, horizon) -> np.random.Generator:
    key = f"lifetime-integrity/bootstrap/v1/{experiment}/{claim}/{horizon}"
    return np.random.default_rng(int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], "big"))


def bootstrap_mean(values: list[float], rng: np.random.Generator) -> dict:
    """Percentile 95% CI for the mean; seeds are the resampling unit."""
    x = np.asarray(values, dtype=float)
    n = len(x)
    idx = rng.integers(0, n, size=(REPLICATES, n))
    means = x[idx].mean(axis=1)
    return {
        "mean": float(x.mean()),
        "ci_low": float(np.percentile(means, 2.5)),
        "ci_high": float(np.percentile(means, 97.5)),
        "n_seeds": n,
        "replicates": REPLICATES,
        "_draws": means,
    }


def holm(pvals: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    ordered = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(ordered)
    out, prev_reject = {}, True
    for i, (name, p) in enumerate(ordered):
        thresh = alpha / (m - i)
        reject = prev_reject and p <= thresh
        prev_reject = reject
        out[name] = {"p": p, "holm_threshold": thresh, "reject_null": bool(reject)}
    return out


def load(root: Path, experiment: str, seed: int, epochs: int) -> list[dict]:
    d = root / experiment / f"seed-{seed}" / f"epochs-{epochs}"
    return [json.loads(p.read_text()) for p in sorted(d.glob("*.json")) if p.name != "validation.json"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    root = args.root
    report: dict = {"root": str(root), "replicates": REPLICATES,
                    "p2_arm": P2_ARM, "p3_arm": P3_ARM,
                    "erratum_E3": "P2 arm pinned from development, not confirmatory data"}

    # ---- validity ---------------------------------------------------------
    validity, ivr, cost, excess, raw = {}, {}, {}, {}, {}
    for exp in ("EXP-A001", "EXP-B001"):
        for seed in CONFIRMATORY_SEEDS:
            for E in HORIZONS:
                runs = load(root, exp, seed, E)
                v = validate(runs)
                validity[(exp, seed, E)] = v
                if exp == "EXP-A001":
                    ivr[(seed, E)] = {r["arm"]: r["metrics"]["integrity_violation_rate"] for r in runs}
                    cost[(seed, E)] = {r["arm"]: (r["metrics"]["integrity_violation_rate"],
                                                  r["budget_actual"]["evidence_reads"],
                                                  r["metrics"]["canonical_accuracy"],
                                                  r["budget_actual"]["maintenance_ops"],
                                                  r["budget_actual"]["state_bytes"]) for r in runs}
                else:
                    excess[(seed, E)] = excess_net_repair(runs)
                    raw[(seed, E)] = {r["arm"]: r["consolidation_metrics"] for r in runs}

    report["validity"] = {
        "n_cells": len(validity),
        "n_structurally_valid": sum(1 for v in validity.values() if v["structurally_valid"]),
        "invalid": [{"experiment": k[0], "seed": k[1], "epochs": k[2],
                     "reasons": v["structural_reasons"]}
                    for k, v in validity.items() if not v["structurally_valid"]],
        "claim_invalid": [{"experiment": k[0], "seed": k[1], "epochs": k[2],
                           "claims": [c for c, d in v["claims"].items() if not d["valid"]]}
                          for k, v in validity.items()
                          if v["structurally_valid"] and any(not d["valid"] for d in v["claims"].values())],
    }

    def h2_valid(seed):
        return (validity[("EXP-A001", seed, 8)]["claims"]["H2_horizon_rank_stability"]["valid"]
                and validity[("EXP-A001", seed, 128)]["claims"]["H2_horizon_rank_stability"]["valid"])

    # ---- P1: A001 H2 ------------------------------------------------------
    rhos, per_seed = [], []
    for seed in CONFIRMATORY_SEEDS:
        if not h2_valid(seed):
            per_seed.append({"seed": seed, "rho": None, "reason": "h2_claim_invalid_at_endpoint"}); continue
        r = _spearman(_rank(ivr[(seed, 8)], lower_is_better=True),
                      _rank(ivr[(seed, 128)], lower_is_better=True))
        per_seed.append({"seed": seed, "rho": r})
        if r is not None:
            rhos.append(r)
    b = bootstrap_mean(rhos, rng_for("EXP-A001", "H2", "8v128"))
    draws = b.pop("_draws")
    p1_p = float(max((draws >= 1.0).mean(), 1.0 / REPLICATES))
    report["P1_A001_H2"] = {
        **b, "per_seed": per_seed,
        "mean_below_0_6": b["mean"] < 0.6,
        "ci_excludes_1_0": b["ci_high"] < 1.0,
        "preregistered_success": bool(b["mean"] < 0.6 and b["ci_high"] < 1.0),
        "bootstrap_p_vs_null_rho_1": p1_p,
    }

    # ---- P2: A001 H1 ------------------------------------------------------
    diffs = [ivr[(s, P2_HORIZON)][P2_ARM] - ivr[(s, P2_HORIZON)][DRIFT_REFERENCE] for s in CONFIRMATORY_SEEDS]
    b2 = bootstrap_mean(diffs, rng_for("EXP-A001", "H1", P2_HORIZON))
    d2 = b2.pop("_draws")
    p2_p = float(max(2 * min((d2 >= 0).mean(), (d2 <= 0).mean()), 1.0 / REPLICATES))
    report["P2_A001_H1"] = {**b2, "arm": P2_ARM, "reference": DRIFT_REFERENCE,
                            "horizon": P2_HORIZON, "per_seed": diffs,
                            "ci_excludes_zero": bool(b2["ci_high"] < 0 or b2["ci_low"] > 0),
                            "lower_is_better": True, "bootstrap_p": p2_p}

    # ---- P3: B001 H1 ------------------------------------------------------
    p3_seeds = [s for s in CONFIRMATORY_SEEDS
                if validity[("EXP-B001", s, P3_HORIZON)]["structurally_valid"]]
    ex = [excess[(s, P3_HORIZON)][P3_ARM] for s in p3_seeds]
    b3 = bootstrap_mean(ex, rng_for("EXP-B001", "H1", P3_HORIZON))
    d3 = b3.pop("_draws")
    p3_p = float(max(2 * min((d3 >= 0).mean(), (d3 <= 0).mean()), 1.0 / REPLICATES))
    report["P3_B001_H1"] = {**b3, "arm": P3_ARM, "horizon": P3_HORIZON, "per_seed": ex,
                            "seeds_used": p3_seeds,
                            "seeds_excluded_invalid": [s for s in CONFIRMATORY_SEEDS if s not in p3_seeds],
                            "ci_excludes_zero": bool(b3["ci_low"] > 0 or b3["ci_high"] < 0),
                            "bootstrap_p": p3_p}

    report["holm_primary"] = holm({"P1_A001_H2": p1_p, "P2_A001_H1": p2_p, "P3_B001_H1": p3_p})

    # ---- frontier + secondary --------------------------------------------
    frontier = {}
    for E in HORIZONS:
        arms = sorted(ivr[(CONFIRMATORY_SEEDS[0], E)])
        agg = {a: (float(np.mean([ivr[(s, E)][a] for s in CONFIRMATORY_SEEDS])),
                   float(np.mean([cost[(s, E)][a][1] for s in CONFIRMATORY_SEEDS]))) for a in arms}
        front = [a for a in arms if not any(
            (agg[b2_][0] <= agg[a][0] and agg[b2_][1] <= agg[a][1]) and
            (agg[b2_][0] < agg[a][0] or agg[b2_][1] < agg[a][1]) for b2_ in arms if b2_ != a)]
        frontier[E] = {"pareto": sorted(front), "aggregate": agg,
                       "last_write_wins_on_frontier": "last-write-wins" in front,
                       "reading_arms_on_frontier": sorted(a for a in front if agg[a][1] > 0)}
    report["A001_frontier"] = frontier

    # Manuscript-audit correction: a structurally invalid cell cannot contribute
    # to an inferential claim (frozen validity rule). Two EXP-B001 E128 cells
    # failed `benchmark_at_floor`; including them silently contaminated the E128
    # secondary estimates. This applies the existing rule, it does not change it.
    def valid_seeds(exp: str, E: int) -> list[int]:
        return [s for s in CONFIRMATORY_SEEDS if validity[(exp, s, E)]["structurally_valid"]]

    sec = {}
    for a in sorted(excess[(CONFIRMATORY_SEEDS[0], HORIZONS[0])]):
        if a == BASELINE_ARM:
            continue
        per_h = {}
        for E in HORIZONS:
            seeds_E = valid_seeds("EXP-B001", E)
            vals = [excess[(s, E)][a] for s in seeds_E]
            bb = bootstrap_mean(vals, rng_for("EXP-B001", f"excess/{a}", E)); bb.pop("_draws")
            per_h[E] = {**bb, "positive_in_every_seed": all(v > 0 for v in vals),
                        "n_seeds_positive": sum(1 for v in vals if v > 0),
                        "excluded_seeds": [s for s in CONFIRMATORY_SEEDS if s not in seeds_E]}
        sec[a] = per_h
    report["B001_excess_by_horizon"] = sec

    report["B001_descriptive"] = {
        str(E): {a: {k: float(np.mean([raw[(s, E)][a][k] for s in valid_seeds("EXP-B001", E)]))
                     for k in ("net_repair", "attribution_precision", "attribution_recall",
                               "collateral_revision_rate", "culprit_accuracy_delta",
                               "decoy_accuracy_delta", "untouched_accuracy_delta",
                               "consolidation_reads")}
                 for a in sorted(raw[(CONFIRMATORY_SEEDS[0], E)])}
        for E in HORIZONS}
    report["B001_descriptive_n_seeds"] = {str(E): len(valid_seeds("EXP-B001", E)) for E in HORIZONS}

    out = args.out or (root / "analysis.json")
    out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str))
    print(f"written: {out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run the frozen Phase-2 development matrix.

DEVELOPMENT CALIBRATION ONLY. This script refuses a dirty working tree, pins the
exact git commit into every manifest, validates each paired comparison before
summarizing it, and never begins confirmatory work.
"""

from __future__ import annotations

import json
import math
import subprocess
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

DEVELOPMENT_SEEDS = (231368116, 1043567494, 1443029309)
HORIZONS = (8, 16, 32, 64, 128)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def git_commit() -> str:
    return _git("rev-parse", "HEAD")


def require_clean_tree() -> None:
    if _git("status", "--porcelain"):
        raise SystemExit("Refusing DEVELOPMENT run from a dirty working tree.")


def _rank(values: dict[str, float], *, lower_is_better: bool) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda kv: (kv[1], kv[0]), reverse=not lower_is_better)
    ranks: dict[str, float] = {}
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        average_rank = ((i + 1) + j) / 2.0
        for arm, _ in ordered[i:j]:
            ranks[arm] = average_rank
        i = j
    return ranks


def _spearman(a: dict[str, float], b: dict[str, float]) -> float | None:
    arms = sorted(set(a) & set(b))
    if len(arms) < 2:
        return None
    x = [a[arm] for arm in arms]
    y = [b[arm] for arm in arms]
    mx = sum(x) / len(x)
    my = sum(y) / len(y)
    vx = sum((v - mx) ** 2 for v in x)
    vy = sum((v - my) ** 2 for v in y)
    if vx == 0.0 or vy == 0.0:
        return None
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y, strict=True))
    return cov / math.sqrt(vx * vy)


def _dominates(a: dict, b: dict, *, value_key: str, lower_is_better: bool) -> bool:
    if lower_is_better:
        performance_ok = a[value_key] <= b[value_key]
        performance_strict = a[value_key] < b[value_key]
    else:
        performance_ok = a[value_key] >= b[value_key]
        performance_strict = a[value_key] > b[value_key]

    cost_keys = ("evidence_reads", "maintenance_ops", "state_bytes")
    costs_ok = all(a[k] <= b[k] for k in cost_keys)
    costs_strict = any(a[k] < b[k] for k in cost_keys)
    return performance_ok and costs_ok and (performance_strict or costs_strict)


def _frontier(rows: list[dict], *, value_key: str, lower_is_better: bool) -> list[str]:
    frontier = []
    for candidate in rows:
        if not any(
            _dominates(other, candidate, value_key=value_key, lower_is_better=lower_is_better)
            for other in rows
            if other["arm"] != candidate["arm"]
        ):
            frontier.append(candidate["arm"])
    return sorted(frontier)


def _cost_row(run: dict) -> dict:
    actual = run["budget_actual"]
    ceiling = float(run["budget_ceiling"]["evidence_reads_ceiling"])
    reads = float(actual["evidence_reads"])
    return {
        "arm": run["arm"],
        "evidence_reads": int(actual["evidence_reads"]),
        "evidence_reads_ceiling": int(ceiling),
        "read_ceiling_utilization": (reads / ceiling) if ceiling else 0.0,
        "exhausted_reads": int(actual.get("exhausted_reads", 0)),
        "maintenance_ops": int(actual["maintenance_ops"]),
        "state_bytes": int(actual["state_bytes"]),
        "wall_seconds": float(actual["wall_seconds"]),
    }


def _run_a(seed: int, epochs: int, commit: str, root: Path) -> dict:
    lt = generate_drift_lifetime(LifetimeConfig(seed=seed, epochs=epochs))
    budget = default_budget(lt)
    out = root / "EXP-A001" / f"seed-{seed}" / f"epochs-{epochs}"
    out.mkdir(parents=True, exist_ok=True)

    runs = []
    for arm in sorted(DRIFT_MECHANISMS):
        result = run_drift(
            lt,
            arm,
            budget,
            classification="DEVELOPMENT",
            git_commit=commit,
        )
        result.write(out / f"{arm}.json")
        runs.append(result.manifest)

    validity = validate(runs)
    (out / "validation.json").write_text(json.dumps(validity, indent=2, sort_keys=True))
    rows = []
    for run in runs:
        row = _cost_row(run)
        row.update(
            {
                "integrity_violation_rate": float(run["metrics"]["integrity_violation_rate"]),
                "canonical_accuracy": float(run["metrics"]["canonical_accuracy"]),
            }
        )
        rows.append(row)

    return {
        "experiment": "EXP-A001",
        "seed": seed,
        "epochs": epochs,
        "validity": validity,
        "rows": rows,
        "integrity_cost_frontier": (
            _frontier(rows, value_key="integrity_violation_rate", lower_is_better=True)
            if validity["valid_for_comparison"]
            else []
        ),
    }


def _run_b(seed: int, epochs: int, commit: str, root: Path) -> dict:
    cfg = LifetimeConfig(seed=seed, epochs=epochs, delayed_outcomes_per_epoch=1.5)
    lt = generate_delayed_credit_lifetime(cfg)
    budget = default_budget(lt)
    out = root / "EXP-B001" / f"seed-{seed}" / f"epochs-{epochs}"
    out.mkdir(parents=True, exist_ok=True)

    runs = []
    for arm in sorted(CONSOLIDATORS):
        result = run_delayed_credit(
            lt,
            arm,
            budget,
            classification="DEVELOPMENT",
            git_commit=commit,
        )
        result.write(out / f"{arm}.json")
        runs.append(result.manifest)

    validity = validate(runs)
    (out / "validation.json").write_text(json.dumps(validity, indent=2, sort_keys=True))
    rows = []
    for run in runs:
        row = _cost_row(run)
        control = run["matched_untouched_control"]
        row.update(
            {
                "net_repair": float(run["consolidation_metrics"]["net_repair"]),
                "attribution_recall": float(run["consolidation_metrics"]["attribution_recall"]),
                "untouched_accuracy_delta": float(
                    run["consolidation_metrics"]["untouched_accuracy_delta"]
                ),
                "canonical_accuracy": float(run["metrics"]["canonical_accuracy"]),
                "matched_control_selected": int(control["selected_total"]),
                "matched_control_measured_outcomes": int(control["measured_outcome_deltas"]),
            }
        )
        rows.append(row)

    return {
        "experiment": "EXP-B001",
        "seed": seed,
        "epochs": epochs,
        "validity": validity,
        "rows": rows,
        "repair_cost_frontier": (
            _frontier(rows, value_key="net_repair", lower_is_better=False)
            if validity["valid_for_comparison"]
            else []
        ),
    }


def _a_h2(comparisons: list[dict]) -> list[dict]:
    diagnostics = []
    for seed in DEVELOPMENT_SEEDS:
        short = next(
            (c for c in comparisons if c["seed"] == seed and c["epochs"] == 8),
            None,
        )
        long = next(
            (c for c in comparisons if c["seed"] == seed and c["epochs"] == 128),
            None,
        )
        if not short or not long:
            continue
        if not short["validity"]["valid_for_comparison"] or not long["validity"]["valid_for_comparison"]:
            diagnostics.append({"seed": seed, "spearman_8_vs_128": None, "reason": "invalid_endpoint"})
            continue
        short_values = {r["arm"]: r["integrity_violation_rate"] for r in short["rows"]}
        long_values = {r["arm"]: r["integrity_violation_rate"] for r in long["rows"]}
        rho = _spearman(
            _rank(short_values, lower_is_better=True),
            _rank(long_values, lower_is_better=True),
        )
        diagnostics.append(
            {
                "seed": seed,
                "spearman_8_vs_128": rho,
                "below_preregistered_0_6_threshold": (rho is not None and rho < 0.6),
            }
        )
    return diagnostics


def _read_ceiling_summary(comparisons: list[dict]) -> dict:
    rows = [row for c in comparisons for row in c["rows"]]
    if not rows:
        return {"max_utilization": 0.0, "ceiling_bound_arms": []}
    max_utilization = max(r["read_ceiling_utilization"] for r in rows)
    bound = sorted(
        {
            f"{c['experiment']}:{c['seed']}:{c['epochs']}:{r['arm']}"
            for c in comparisons
            for r in c["rows"]
            if r["exhausted_reads"] > 0 or r["read_ceiling_utilization"] >= 0.95
        }
    )
    return {"max_utilization": max_utilization, "ceiling_bound_or_near_bound": bound}


def main() -> None:
    require_clean_tree()
    commit = git_commit()
    root = Path("results") / "development" / commit[:12]
    root.mkdir(parents=True, exist_ok=True)

    a_comparisons = []
    b_comparisons = []
    for seed in DEVELOPMENT_SEEDS:
        for epochs in HORIZONS:
            a_comparisons.append(_run_a(seed, epochs, commit, root))
            b_comparisons.append(_run_b(seed, epochs, commit, root))

    all_comparisons = a_comparisons + b_comparisons
    invalid = [
        {
            "experiment": c["experiment"],
            "seed": c["seed"],
            "epochs": c["epochs"],
            "reasons": c["validity"]["reasons"],
        }
        for c in all_comparisons
        if not c["validity"]["valid_for_comparison"]
    ]

    summary = {
        "classification": "DEVELOPMENT",
        "git_commit": commit,
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "horizons": list(HORIZONS),
        "all_comparisons_valid": not invalid,
        "invalid_comparisons": invalid,
        "read_ceiling": _read_ceiling_summary(all_comparisons),
        "EXP-A001": {
            "comparisons": a_comparisons,
            "H2_spearman_8_vs_128": _a_h2(a_comparisons),
        },
        "EXP-B001": {"comparisons": b_comparisons},
        "note": "Development calibration only; not confirmatory evidence.",
    }
    summary_path = root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    raise SystemExit(0 if not invalid else 2)


if __name__ == "__main__":
    main()

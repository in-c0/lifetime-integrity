#!/usr/bin/env python3
"""Execute the frozen Phase-3 confirmatory matrix. One shot.

Runs the 12 frozen seeds x 5 horizons x all arms for both experiments, under
the Phase-3 lock. Refuses a dirty tree, pins the commit, and enforces the
reveal order: raw manifests -> structural validity -> claim-scoped validity ->
only then performance metrics.

No cherry-picking, no early stopping, no reruns for inconvenient results. A
rerun is permissible only for a documented execution failure, and the failed
artifact must be preserved.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_runs import PROTOCOL_VERSION, validate

from lifetime_integrity.consolidation import CONSOLIDATORS
from lifetime_integrity.harness import (
    CONFIRMATORY_READ_CEILING_MULTIPLIER,
    default_budget,
    run_delayed_credit,
    run_drift,
)
from lifetime_integrity.lifetime import (
    LifetimeConfig,
    generate_delayed_credit_lifetime,
    generate_drift_lifetime,
)
from lifetime_integrity.mechanisms import DRIFT_MECHANISMS
from lifetime_integrity.seeds import CONFIRMATORY_SEEDS

HORIZONS = (8, 16, 32, 64, 128)
OUTCOMES_PER_EPOCH = 1.5


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def require_clean_tree() -> None:
    if _git("status", "--porcelain"):
        raise SystemExit("Refusing CONFIRMATORY run from a dirty working tree.")


def run_cell(experiment: str, seed: int, epochs: int, root: Path, commit: str) -> dict:
    out = root / experiment / f"seed-{seed}" / f"epochs-{epochs}"
    out.mkdir(parents=True, exist_ok=True)
    runs: list[dict] = []

    if experiment == "EXP-A001":
        lt = generate_drift_lifetime(LifetimeConfig(seed=seed, epochs=epochs))
        budget = default_budget(lt, ceiling_multiplier=CONFIRMATORY_READ_CEILING_MULTIPLIER)
        for arm in DRIFT_MECHANISMS:
            r = run_drift(
                lt, arm, budget,
                classification="CONFIRMATORY", git_commit=commit,
                protocol_version=PROTOCOL_VERSION,
            )
            r.write(out / f"{arm}.json")
            runs.append(r.manifest)
    else:
        lt = generate_delayed_credit_lifetime(
            LifetimeConfig(seed=seed, epochs=epochs, delayed_outcomes_per_epoch=OUTCOMES_PER_EPOCH)
        )
        budget = default_budget(lt, ceiling_multiplier=CONFIRMATORY_READ_CEILING_MULTIPLIER)
        for arm in CONSOLIDATORS:
            r = run_delayed_credit(
                lt, arm, budget,
                classification="CONFIRMATORY", git_commit=commit,
                protocol_version=PROTOCOL_VERSION,
            )
            r.write(out / f"{arm}.json")
            runs.append(r.manifest)

    # Reveal order: validity is established and written before any metric is read.
    validity = validate(runs)
    (out / "validation.json").write_text(json.dumps(validity, indent=2, sort_keys=True))
    return {
        "experiment": experiment,
        "seed": seed,
        "epochs": epochs,
        "structurally_valid": validity["structurally_valid"],
        "structural_reasons": validity["structural_reasons"],
        "inert_metrics": validity["inert_metrics"],
        "claims": {k: c["valid"] for k, c in validity["claims"].items()},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--allow-dirty", action="store_true", help="documented execution recovery only")
    args = ap.parse_args()

    if not args.allow_dirty:
        require_clean_tree()
    commit = _git("rev-parse", "HEAD")
    root = args.out or Path("results/confirmatory") / commit[:12]
    root.mkdir(parents=True, exist_ok=True)

    cells = []
    for experiment in ("EXP-A001", "EXP-B001"):
        for seed in CONFIRMATORY_SEEDS:
            for epochs in HORIZONS:
                cells.append(run_cell(experiment, seed, epochs, root, commit))
                print(f"  {experiment} seed={seed} E{epochs} "
                      f"structural={cells[-1]['structurally_valid']}")

    summary = {
        "classification": "CONFIRMATORY",
        "protocol_version": PROTOCOL_VERSION,
        "git_commit": commit,
        "confirmatory_seeds": list(CONFIRMATORY_SEEDS),
        "horizons": list(HORIZONS),
        "read_ceiling_multiplier": CONFIRMATORY_READ_CEILING_MULTIPLIER,
        "cells": cells,
        "n_cells": len(cells),
        "n_structurally_valid": sum(1 for c in cells if c["structurally_valid"]),
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\ncells: {summary['n_structurally_valid']}/{summary['n_cells']} structurally valid")
    print(f"written: {root}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Materialize LIS-v0 lifetimes as JSONL, including audit fields.

Lifetimes are generated deterministically rather than committed as data blobs.
The printed `config_lock` is what a run manifest must carry to prove which
corruption process it faced.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lifetime_integrity.lifetime import (
    LifetimeConfig,
    generate_delayed_credit_lifetime,
    generate_drift_lifetime,
    write_jsonl,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=20260902)
    p.add_argument("--epochs", type=int, default=24)
    p.add_argument("--out", type=Path, default=Path("data"))
    p.add_argument("--outcomes-per-epoch", type=float, default=1.5)
    args = p.parse_args()

    drift_cfg = LifetimeConfig(seed=args.seed, epochs=args.epochs)
    credit_cfg = LifetimeConfig(
        seed=args.seed, epochs=args.epochs, delayed_outcomes_per_epoch=args.outcomes_per_epoch
    )

    for name, lt in (
        ("drift", generate_drift_lifetime(drift_cfg)),
        ("delayed_credit", generate_delayed_credit_lifetime(credit_cfg)),
    ):
        path = args.out / f"lis-v0-{name}-seed{args.seed}.jsonl"
        write_jsonl(path, lt.events)
        print(json.dumps({
            "stream": name,
            "path": str(path),
            "config_lock_sha256": lt.config_lock,
            "lifetime_spec_sha256": lt.spec_sha256(),
            "summary": lt.summary(),
        }, indent=2))


if __name__ == "__main__":
    main()

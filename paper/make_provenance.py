#!/usr/bin/env python3
"""Emit the manuscript provenance table: every denominator and hash, from disk."""
from __future__ import annotations
import glob, hashlib, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lifetime_integrity.lifetime import GENERATOR_VERSION, LifetimeConfig
from lifetime_integrity.metrics import (CAUSAL_ENDPOINT_VERSION, MATCHED_UNTOUCHED_CONTROL_VERSION,
                                        SCORING_PROTOCOL_VERSION, scoring_protocol_sha256)
from lifetime_integrity.seeds import CONFIRMATORY_SEEDS
from dataclasses import asdict

R = Path("results/confirmatory/9954ab69cd4d")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

d = asdict(LifetimeConfig(seed=0)); d.pop("seed")
corruption = hashlib.sha256(json.dumps(
    {"generator": GENERATOR_VERSION, "corruption_process": d}, sort_keys=True, separators=(",", ":")
).encode()).hexdigest()

arm = len([f for f in glob.glob(f"{R}/**/*.json", recursive=True)
           if Path(f).name not in {"validation.json", "summary.json", "analysis.json", "analysis-audited.json"}])
a_arm = len([f for f in glob.glob(f"{R}/EXP-A001/**/*.json", recursive=True) if Path(f).name != "validation.json"])
b_arm = len([f for f in glob.glob(f"{R}/EXP-B001/**/*.json", recursive=True) if Path(f).name != "validation.json"])
cells = len(glob.glob(f"{R}/**/validation.json", recursive=True))
allj = len(glob.glob(f"{R}/**/*.json", recursive=True))
an = json.loads((R / "analysis-audited.json").read_text())

prov = {
  "denominators": {
    "comparison_cells_seed_x_horizon_x_experiment": cells,
    "logical_arm_runs_total": arm,
    "logical_arm_runs_A001": a_arm,
    "logical_arm_runs_B001": b_arm,
    "stored_json_artifacts": allj,
    "secondary_execution_passes": 0,
    "note": "12 seeds x 5 horizons x (9 A001 + 5 B001) = 840. The figure 1680 "
            "reported at freeze was an arithmetic error (120 cells x 14 arms "
            "double-counts, since both factors already span the two experiments)."
  },
  "validity": {
    "structurally_valid_cells": an["validity"]["n_structurally_valid"],
    "structurally_invalid_cells": an["validity"]["invalid"],
    "claim_invalid_cells": len(an["validity"]["claim_invalid"]),
    "claim_invalid_detail": an["validity"]["claim_invalid"],
  },
  "denominators_per_estimate": {
    "P1_A001_H2_seeds": an["P1_A001_H2"]["n_seeds"],
    "P2_A001_H1_seeds": an["P2_A001_H1"]["n_seeds"],
    "P3_B001_H1_seeds": an["P3_B001_H1"]["n_seeds"],
    "B001_E128_secondary_seeds": an["B001_excess_by_horizon"]["counterfactual-recheck"]["128"]["n_seeds"],
  },
  "holm_family": {"members": sorted(an["holm_primary"]), "alpha_family_wise": 0.05,
                  "detail": an["holm_primary"]},
  "identity": {
    "execution_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "freeze_sha": "5b9435afd68ec55c05a3f0f4bcc4ffdd4d0b0e79",
    "merge_sha": "9954ab69cd4d802ccfbffbaff23b6e4f332ad9c0",
    "corruption_process_sha256": corruption,
    "generator_version": GENERATOR_VERSION,
    "scoring_protocol_version": SCORING_PROTOCOL_VERSION,
    "scoring_protocol_sha256_k3": scoring_protocol_sha256(3),
    "matched_control_version": MATCHED_UNTOUCHED_CONTROL_VERSION,
    "causal_endpoint_version": CAUSAL_ENDPOINT_VERSION,
    "window_k": 3,
    "confirmatory_seeds": list(CONFIRMATORY_SEEDS),
    "horizons": [8, 16, 32, 64, 128],
    "read_ceiling_formula": "round(1.25 * n_probes * 200) = 2500 * epochs",
  },
  "document_hashes": {
    p: sha(p) for p in [
      "experiments/EXP-A001-PREREG.md", "experiments/EXP-B001-PREREG.md",
      "experiments/PHASE-2-AMENDMENT-001.md", "experiments/PHASE-3-CONFIRMATORY-LOCK.md",
      "docs/LITERATURE-AUDIT-2026-09-03.md", "scripts/validate_runs.py",
      "src/lifetime_integrity/seeds.py", "src/lifetime_integrity/lifetime.py",
    ]
  },
}
Path("paper/provenance.json").write_text(json.dumps(prov, indent=2, sort_keys=True))
print(json.dumps(prov["denominators"], indent=2))
print("written: paper/provenance.json")

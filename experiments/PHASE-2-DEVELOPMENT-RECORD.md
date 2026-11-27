# Phase-2 development record

**Status: DEVELOPMENT CALIBRATION. NOT CONFIRMATORY EVIDENCE.**

> **Interpretation superseded by `PHASE-2-DEVELOPMENT-RECORD-AMENDED-001.md`.**
> This document is preserved unchanged as the pre-amendment record. Its raw
> measurements remain correct; its validity and endpoint *interpretations* were
> revised by `PHASE-2-AMENDMENT-001.md`. No mechanism was re-run.
Nothing here supports or refutes H1/H2/H3. Development seeds are permanently
reserved and may never become confirmatory seeds.

- Date: 2026-09-03
- Gate commit: `0c79b2efcbf9f98e642e34c52736ee461faead38`
- Corruption lock: `6e890d154d637d826613172a376396cb54f22c420e063125927fd979397b5b40` (unchanged)
- Scoring protocol: `LIS-SCORE-v0.2.0` / `matched-contemporaneous-v1`, hash `3a7bf5eb123ce2904a99c68edcd9e97152fc6e90fc8d2167cdf79b411bbde728`
- Development seeds: `231368116`, `1043567494`, `1443029309`
- Horizons: 8, 16, 32, 64, 128
- Manifests: `results/development/0c79b2efcbf9/` (210 run manifests + 30 per-cell `validation.json` + `summary.json`)
- Reproduce: `python scripts/run_development.py`

Every figure below is drawn from those manifests.

## 1. Validity — 28 / 30 comparison cells valid

| experiment | 8 | 16 | 32 | 64 | 128 |
|---|---|---|---|---|---|
| EXP-A001 seed 231368116 | ok | ok | ok | ok | ok |
| EXP-A001 seed 1043567494 | **INVALID** | ok | ok | ok | ok |
| EXP-A001 seed 1443029309 | **INVALID** | ok | ok | ok | ok |
| EXP-B001 (all three seeds) | ok | ok | ok | ok | ok |

Both invalid cells fail for the same reason: `inert_metrics:['self_contradiction_rate']`
— the metric is exactly 0.0 for all nine arms, so the declared-liveness rule
refuses the cell. This is the validator working as designed.

## 2. Ceiling, floor, and metric liveness

- **No ceiling effect.** No cell has every arm above 0.95 canonical accuracy.
- **No floor effect.** No cell has its best arm below 0.40. Across all 210 runs
  canonical accuracy spans 0.059–0.834.
- **`stale_state_rate`** live in every cell.
- **`unsupported_belief_rate`** live in every cell, but it *shrinks* with
  horizon (max-across-arms mean: 0.113 at E8 → 0.0135 at E128). Only the
  bounded-latent arms move it, and the longer the lifetime the more probes are
  dominated by ordinary staleness.
- **`self_contradiction_rate`** is the problem metric: ~0.03–0.04 at E16–E128
  but structurally near-zero at E8, where each slot receives too few probes to
  form consecutive un-evidenced pairs. It is dead in 2 of 3 seeds at E8.

## 3. Read-budget utilisation

- **No arm exhausted its read budget anywhere** (`exhausted_reads == 0` in all 210 runs).
- Peak utilisation **0.962**, reached at E128 by `evidence-reconstruction` and
  `provenance-regrounding` in all three seeds.

Not currently binding, but with ~96% consumed at the longest horizon, any
extension of the ladder or a modestly denser lifetime would make these two arms
ceiling-bound and silently distort the cost frontier. Flagged for the freeze
decision, not treated as a blocker.

## 4. EXP-A001 — integrity versus lifetime length

Mean `integrity_violation_rate` over valid seeds (E8 is one seed only):

| arm | E8 | E16 | E32 | E64 | E128 |
|---|---|---|---|---|---|
| `confidence-decay` | 0.113 | 0.110 | 0.145 | **0.302** | **0.516** |
| `evidence-reconstruction` | **0.050** | **0.077** | **0.118** | 0.303 | 0.541 |
| `periodic-reset` | 0.113 | 0.123 | 0.167 | 0.324 | 0.541 |
| `provenance-regrounding` | 0.113 | 0.115 | 0.149 | 0.322 | 0.553 |
| `last-write-wins` | **0.050** | 0.079 | 0.122 | 0.316 | 0.582 |
| `hybrid-symbolic-latent` | 0.062 | 0.098 | 0.134 | 0.325 | 0.586 |
| `contradiction-regrounding` | 0.113 | 0.127 | 0.191 | 0.369 | 0.612 |
| `lossy-latent` | 0.225 | 0.181 | 0.299 | 0.545 | 0.752 |
| `unconstrained-accumulator` | 0.113 | 0.152 | 0.276 | 0.536 | 0.753 |

### The cost frontier moves with horizon

Pareto frontier over (integrity violation ↓, evidence reads ↓):

| horizon | frontier | `last-write-wins` | frontier arms that spend reads |
|---|---|---|---|
| E8 | `last-write-wins` | on frontier | none |
| E16 | `evidence-reconstruction`, `last-write-wins` | on frontier | `evidence-reconstruction` |
| E32 | `evidence-reconstruction`, `last-write-wins` | on frontier | `evidence-reconstruction` |
| E64 | `confidence-decay` | **dominated** | none |
| E128 | `confidence-decay` | **dominated** | none |

Two findings, both preserved as-is:

**Paying for re-grounding buys nothing at long horizons.** At E64 and E128 the
sole Pareto-optimal arm is `confidence-decay`, which spends **zero** evidence
reads. `evidence-reconstruction` and `provenance-regrounding` each spend ~245,000
reads at E128 and are dominated by it. This is the negative result that gap G1
was posed to detect, and it is the most important thing in this record.

**`last-write-wins` is finally beaten — but not by anything expensive.** It is
on the frontier through E32 and is dominated at E64/E128 by `confidence-decay`
(0.516 vs 0.582 at E128), which is equally free. The Phase-1 signal therefore
half-survives: trivial recency is hard to beat, and what beats it is another
cheap heuristic, not evidence re-derivation.

**`provenance-regrounding` again shows no clean integrity advantage.** It has the
second-best canonical accuracy at E128 (0.726) and the fourth-worst integrity
violation rate (0.553), while spending 96% of the read ceiling. Consistent with
the Phase-1 pilot and with the published negative result in arXiv:2606.22030.

### H2 — cannot be evaluated as preregistered

Preregistered diagnostic: rank arms by `integrity_violation_rate`, Spearman
between E8 and E128, success below 0.6.

| seed | ρ(E8, E128) | outcome |
|---|---|---|
| `231368116` | **0.330** | below 0.6 — consistent with H2 |
| `1043567494` | — | `invalid_endpoint` (E8 cell invalid) |
| `1443029309` | — | `invalid_endpoint` (E8 cell invalid) |

**Only one of three development seeds yields the statistic**, because the E8
endpoint is invalidated by the inert `self_contradiction_rate`. H2 is neither
supported nor refuted at the required replication. No substitute endpoint was
computed: searching for a horizon pair where H2 works is precisely the failure
mode the preregistration forbids.

The frontier-composition change in the table above is *consistent* with the H2
premise, but it is not the preregistered statistic and is not offered as
evidence for it.

## 5. EXP-B001 — delayed credit

### Matched untouched controls now work

The Phase-2 repair succeeded. `untouched_accuracy_delta` is live, and the
control selection hash is identical across all five arms in all 15 cells.

| seed | horizon | outcomes | with controls | coverage | eligible | selected |
|---|---|---|---|---|---|---|
| 231368116 | 8 / 16 / 32 / 64 / 128 | 7 / 18 / 39 / 86 / 182 | 7 / 18 / 39 / 57 / 117 | 100 / 100 / 100 / 66.3 / **64.3**% | 40 / 81 / 106 / 140 / 193 | 27 / 69 / 98 / 134 / 189 |
| 1043567494 | 8 / 16 / 32 / 64 / 128 | 4 / 19 / 42 / 92 / 189 | 4 / 19 / 42 / 67 / 114 | 100 / 100 / 100 / 72.8 / **60.3**% | 27 / 107 / 100 / 112 / 173 | 15 / 69 / 98 / 110 / 171 |
| 1443029309 | 8 / 16 / 32 / 64 / 128 | 7 / 21 / 46 / 95 / 190 | 7 / 21 / 46 / 73 / 131 | 100 / 100 / 100 / 76.8 / **68.9**% | 38 / 96 / 117 / 152 / 239 | 26 / 74 / 106 / 141 / 228 |

Coverage is complete through E32 and falls to 60–69% at E128, matching the
pre-run stream-only audit. Reported as a limitation under the locked rule; the
benchmark was not changed to raise it.

**Interpretation caveat.** Controls are *contemporaneously* untouched, not
globally untouched: a control slot may have been revised by an earlier outcome
outside its scoring window. Consequently `untouched_accuracy_delta` differs
across arms within a cell (e.g. −0.064 to +0.067 at seed 231368116, E128) even
though the selected control set is byte-identical. It measures contemporaneous
collateral isolation, not arm-independent drift, and must not be read as the
latter.

### Net repair — the absolute endpoint is ill-posed

Mean `net_repair` over three seeds:

| arm | E8 | E16 | E32 | E64 | E128 |
|---|---|---|---|---|---|
| `counterfactual-recheck` | +0.126 | +0.056 | +0.057 | −0.026 | −0.073 |
| `no-consolidation` | **+0.126** | **+0.089** | −0.170 | −0.120 | −0.113 |
| `provenance-restricted-blame` | +0.055 | −0.270 | −0.116 | −0.184 | −0.143 |
| `eligibility-trace` | −0.370 | −0.355 | −0.225 | −0.181 | −0.101 |
| `uniform-blame` | −0.939 | −0.766 | −0.404 | −0.263 | −0.123 |

**`no-consolidation` posts positive mean net repair at E8 (+0.126) and E16
(+0.089).** It performs zero revisions by construction, so this is not repair:
`net_repair` (culprit Δ + decoy Δ) carries a non-zero, horizon-dependent
baseline from ordinary benchmark dynamics. The preregistered B001 primary
endpoint and kill criterion — both phrased as *positive* `net_repair` — are
therefore ill-posed as absolute tests. A do-nothing arm can satisfy them.

### Paired against the do-nothing control

Mean `net_repair` minus `no-consolidation` on the identical lifetime:

| arm | E8 | E16 | E32 | E64 | E128 | cells > 0 |
|---|---|---|---|---|---|---|
| `counterfactual-recheck` | +0.000 | −0.034 | **+0.226** | **+0.094** | **+0.040** | 9/15 |
| `eligibility-trace` | −0.496 | −0.444 | −0.055 | −0.061 | +0.012 | 2/15 |
| `provenance-restricted-blame` | −0.071 | −0.359 | +0.053 | −0.064 | −0.030 | 4/15 |
| `uniform-blame` | −1.065 | −0.855 | −0.235 | −0.143 | −0.010 | 1/15 |

`counterfactual-recheck` is the only rule that beats doing nothing at more than
half the cells, and it does so while spending ~110,000 evidence reads at E128 to
buy +0.040. On a repair/cost frontier that is a poor trade, and no other arm
spends reads at all.

**The Phase-1 signal on recall survives.** At E128 `uniform-blame` has the
highest attribution recall (0.17) tied with `counterfactual-recheck` (0.16) and
the worst overall accuracy by a wide margin (0.061 versus 0.423 for doing
nothing). Recall remains the wrong objective.

## 6. Kill criteria

**Track kill criterion (A001 H2) — DOES NOT FIRE, but is not evaluable.**
It fires if short-horizon rankings reliably predict long-horizon rankings. The
one computable seed gives ρ = 0.330, below the 0.6 threshold, i.e. rankings do
*not* transfer. Two seeds are unevaluable. There is no evidence the premise
fails; there is also not enough evidence to say it holds.

**Class kill criterion (B001 net repair) — DOES NOT FIRE.**
Under the corrected paired reading, `counterfactual-recheck` achieves positive
repair relative to doing nothing at E32/E64/E128 and in 9 of 15 cells. Under the
literal absolute reading it also does not fire, but that reading is invalid
because `no-consolidation` satisfies it too.

## 7. Mechanical amendments required before protocol freeze

Each is score-independent and none is applied in this record.

**M1 — Scope declared-metric liveness to the claim it guards.** Cell validity is
currently all-or-nothing across every declared metric. The H2 diagnostic uses
only `integrity_violation_rate`, which is live at E8 in all three seeds; the
cells are refused solely because `self_contradiction_rate` is dead there.
Proposal: a cell is valid for a given claim if the metrics that claim consumes
are live, and claims about a dead metric remain forbidden in that cell. This
neither revives the dead metric nor changes any magnitude.

**M2 — Define the B001 endpoint against the do-nothing control.** Replace
absolute `net_repair` with paired `Δnet = net_repair − net_repair(no-consolidation)`
on the identical lifetime, and restate the class kill criterion in those terms.
`no-consolidation` is already a preregistered arm serving exactly this role.

**M3 — Re-derive the read ceiling before confirmatory.** At 0.962 peak
utilisation the ceiling is near-binding for two arms at E128. Raise
`reads_per_probe` by a declared rule applied uniformly and derived from the
lifetime, never from any arm's measured appetite.

**M4 — Record the contemporaneous-control caveat in EXP-B001.** State in the
preregistration that `untouched_accuracy_delta` is arm-dependent by
construction and is not a global isolation control.

## 8. What was not done

- No corruption rate, generator behaviour, seed, horizon, or mechanism
  hyperparameter was changed at any point.
- No confirmatory seed was generated or run.
- No cell was re-run or cherry-picked after inspection; the matrix was executed
  once, in full.
- No alternative H2 endpoint pair was computed.

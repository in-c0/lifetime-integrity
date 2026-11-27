# Phase-2 development record — reinterpreted under amendment 001

**Status: DEVELOPMENT CALIBRATION. NOT CONFIRMATORY EVIDENCE.**

Supersedes the interpretation in `PHASE-2-DEVELOPMENT-RECORD.md`, which is
preserved unchanged. **No mechanism was re-run.** Every number here comes from
the same manifests, reinterpreted under `PHASE-2-AMENDMENT-001.md`.

- Amendment commit: `a269f17` (written before any value below was computed)
- Implementation commit: `5d76a2f`
- Matrix executed at: `0c79b2efcbf9f98e642e34c52736ee461faead38`
- Corruption lock: `6e890d154d637d826613172a376396cb54f22c420e063125927fd979397b5b40` **unchanged**
- Scoring protocol of recorded manifests: `LIS-SCORE-v0.2.0` / `3a7bf5eb…`
- Scoring protocol now: `LIS-SCORE-v0.3.0` / `c001a916c4ceb05ec02735c1f2f8066bc81b5d035beab2821657bdb1d9a0a7df`
- Derived outputs: `results/development/0c79b2efcbf9/amended-001/reinterpretation.json`
- Reproduce: `python scripts/reinterpret_development.py`

## 1. M1 — what claim-scoping actually changed

The two previously-refused cells (EXP-A001 @ E8, seeds `1043567494` and
`1443029309`) are **structurally valid**. Under claim-scoped validity:

| seed | E | structural | H1 | H2 | H3 | `self_contradiction_analysis` | inert |
|---|---|---|---|---|---|---|---|
| 231368116 | 8 | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| 1043567494 | 8 | ✅ | ✅ | ✅ | ❌ | ❌ | `self_contradiction_rate` |
| 1443029309 | 8 | ✅ | ✅ | ✅ | ❌ | ❌ | `self_contradiction_rate` |

The dead metric still kills exactly the analyses that depend on it. It no longer
kills H2, which never consumed it. **No metric was revived and no magnitude
changed.**

## 2. EXP-A001 — H2, computed exactly as preregistered

Rank arms by `integrity_violation_rate` at E8 and at E128, existing tie rule,
Spearman, preregistered threshold `< 0.6`. All three development seeds are now
claim-valid for H2.

| seed | ρ(E8, E128) | below 0.6 |
|---|---|---|
| `231368116` | **0.330** | ✅ |
| `1043567494` | **0.395** | ✅ |
| `1443029309` | **0.580** | ✅ |

All three seeds fall below the threshold: short-horizon rankings do **not**
reliably predict long-horizon rankings. **The track kill criterion does not
fire.**

**Caveat, stated plainly.** Seed `1443029309` at ρ = 0.580 clears 0.6 by 0.02.
The result is directionally consistent across three seeds but one of them is
marginal, and no confidence interval exists at n = 3. This is a risk to carry
into confirmatory, not a defect to repair.

## 3. EXP-A001 — the frontier result is unchanged and undiminished

The amendment touched neither `integrity_violation_rate` nor evidence reads, so
the Pareto result stands exactly as first recorded:

| horizon | frontier | `last-write-wins` | frontier arms spending reads |
|---|---|---|---|
| E8 | `last-write-wins` | on frontier | none |
| E16 / E32 | `evidence-reconstruction`, `last-write-wins` | on frontier | `evidence-reconstruction` |
| E64 / E128 | `confidence-decay` | **dominated** | **none** |

**At E64 and E128 no arm that spends evidence reads is Pareto-optimal.**
`confidence-decay` (zero reads) dominates `evidence-reconstruction` and
`provenance-regrounding`, each of which spends ~245,000 reads at E128.
`provenance-regrounding` again buys no clean integrity advantage despite the
second-best accuracy (0.726) and 96% ceiling utilisation.

No evidence-reading method purchases an integrity advantage sufficient to
justify its cost at long horizons. This is a scientific result about mechanisms,
not a measurement defect, and amendment 001 was not permitted to touch it.

## 4. EXP-B001 — paired causal endpoint

`excess_net_repair = net_repair − net_repair(no-consolidation)` on the identical
paired lifetime. Raw `net_repair` is retained in every manifest and reported in
the original record.

| arm | seed | E8 | E16 | E32 | E64 | E128 |
|---|---|---|---|---|---|---|
| `counterfactual-recheck` | 231368116 | +0.000 | −0.109 | **+0.025** | **+0.042** | −0.034 |
| | 1043567494 | +0.000 | −0.147 | **+0.266** | **+0.101** | +0.125 |
| | 1443029309 | +0.000 | +0.156 | **+0.388** | **+0.140** | +0.027 |
| `eligibility-trace` | 231368116 | −0.636 | −0.608 | +0.026 | −0.017 | −0.045 |
| | 1043567494 | −0.424 | −0.395 | −0.080 | −0.091 | +0.089 |
| | 1443029309 | −0.428 | −0.330 | −0.113 | −0.074 | −0.009 |
| `provenance-restricted-blame` | 231368116 | +0.000 | −0.362 | −0.168 | −0.141 | −0.088 |
| | 1043567494 | −0.273 | −0.313 | +0.134 | −0.000 | +0.051 |
| | 1443029309 | +0.061 | −0.403 | +0.193 | −0.050 | −0.054 |
| `uniform-blame` | 231368116 | −1.091 | −1.089 | −0.315 | −0.159 | −0.041 |
| | 1043567494 | −1.737 | −0.762 | −0.186 | −0.148 | +0.026 |
| | 1443029309 | −0.367 | −0.715 | −0.204 | −0.122 | −0.015 |

Applying the preregistered cross-seed standard (positive per-seed mean at a
**common horizon for all three seeds**, not a favourable-cell count):

| arm | horizons positive in every seed | meets standard | cells > 0 |
|---|---|---|---|
| `counterfactual-recheck` | **{32, 64}** | ✅ | 9/15 |
| `provenance-restricted-blame` | {} | ❌ | 4/15 |
| `eligibility-trace` | {} | ❌ | 2/15 |
| `uniform-blame` | {} | ❌ | 1/15 |

**The class kill criterion does not fire.** `counterfactual-recheck` beats
inaction consistently at E32 and E64.

Three caveats that must travel with that sentence:

1. **It fails at the longest horizon.** At E128 it is negative for seed
   `231368116` (−0.034), so E128 does not meet the standard. The one policy that
   works does not work where the track's premise says the problem is hardest.
2. **At E8 its excess is exactly +0.000 in all three seeds** — it performed no
   revisions, so it merely reproduced the baseline. Zero is not positive and E8
   does not count.
3. **It is the only arm that spends evidence reads** (~110,000 at E128). On a
   repair/cost frontier, +0.042 mean excess at E64 for that spend is a poor
   trade, and no cheaper policy achieves it at all.

Had the earlier cell-count reading been used, `counterfactual-recheck`'s 9/15
would have looked like the same conclusion for the wrong reason: 9/15 includes
E128 and E16 cells where it is not consistent across seeds.

## 5. Matched-control coverage (unchanged)

Complete through E32; 64.3 / 60.3 / 68.9% at E128. Reported as a limitation
under the locked rule. Per M4, `untouched_accuracy_delta` differs across arms
within a cell despite byte-identical control identity — that difference is
itself evidence of collateral state modification from earlier out-of-window
outcomes, not a defect.

## 6. Kill criteria

| criterion | fires? | basis |
|---|---|---|
| Track (A001 H2) | **No** | ρ = 0.330 / 0.395 / 0.580, all below 0.6, all three seeds claim-valid |
| Class (B001 causal) | **No** | `counterfactual-recheck` positive in every seed at E32 and E64 |

## 7. Defect versus finding

Amendment 001 repaired three measurement defects — a claim suppressed by a
metric it never used, a causal endpoint satisfiable by inaction, and a
near-binding ceiling. It repaired **nothing** about mechanism performance, and
the central negative result survives untouched: at long horizons a zero-read
heuristic dominates every expensive re-grounding mechanism on this benchmark.

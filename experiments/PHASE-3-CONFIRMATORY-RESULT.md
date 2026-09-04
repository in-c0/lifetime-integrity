# Phase-3 confirmatory result

**Status: CONFIRMATORY. Executed once, as frozen.**

- Execution SHA: `9954ab69cd4d802ccfbffbaff23b6e4f332ad9c0` (post-merge `main`)
- Freeze SHA: `5b9435a`; diff freeze→execution is the merge commit only, no substantive change
- Protocol: `phase3-confirmatory-lock` · scoring `LIS-SCORE-v0.3.0` / `c001a916…`
- Corruption process (seed-independent): `0ebb3e60633de4a4e748c2a474c210927d8026265c86e0786555836bfb4201f4` — unchanged since `eb8547c`
- 12 frozen seeds × 5 horizons × 2 experiments = **120 cells, 1,680 runs**, 961 files
- Manifests: `results/confirmatory/9954ab69cd4d/`; analysis `analysis.json`
- Gate at execution: 143 passed, ruff clean, tree clean

Reveal order was enforced: manifests → structural validity → claim validity →
metrics. No rerun, no cherry-picking, no early stopping.

## 1. Validity

| | |
|---|---|
| structurally valid | **118 / 120** |
| structurally invalid | 2 — EXP-B001 @ E128, seeds `238245273` and `1257774472`, both `benchmark_at_floor` |
| claim-invalid (structurally valid) | 11 — all `H3_integrity_not_accuracy` + `self_contradiction_analysis`, 10 at E8 and 1 at E16, from inert `self_contradiction_rate` |

Canonical accuracy: A001 0.364–0.812 (540 runs); B001 0.042–0.750 (300 runs).
The two floor failures are real: at E128 the B001 substrate degrades far enough
in two lifetimes that the best arm falls below 0.40. Those cells contribute no
inferential claim and are retained as evidence.

## 2. Primary confirmatory tests (Holm, family-wise α = 0.05)

| # | test | estimate | 95% CI | p | Holm thresh | reject null |
|---|---|---|---|---|---|---|
| P1 | A001 H2 — mean Spearman ρ(E8,E128) | **0.3354** | [0.2517, 0.4146] | 0.0001 | 0.0167 | ✅ |
| P2 | A001 H1 — `confidence-decay` − `unconstrained-accumulator` IVR @E128 | **−0.2234** | [−0.2378, −0.2089] | 0.0001 | 0.0250 | ✅ |
| P3 | B001 H1 — `excess_net_repair`, `counterfactual-recheck` @E64 | **+0.0469** | [+0.0032, +0.0943] | 0.0360 | 0.0500 | ✅ |

All three reject their nulls under Holm.

### A001 H2 — **SURVIVES**

Per-seed ρ: 0.243, 0.040, 0.523, 0.411, 0.214, 0.419, 0.167, 0.368, 0.548,
0.242, 0.439, 0.411. **All 12 below 0.6** (max 0.548); mean 0.3354, CI excludes
1.0. Short-horizon mechanism rankings do not predict long-horizon rankings.

The track's central methodological premise **holds**. Development (0.330 / 0.395
/ 0.580) agrees closely with confirmatory (0.335), and the marginal development
seed did not recur as a systematic problem.

### A001 H1 — supported

`confidence-decay` achieves 0.223 lower integrity-violation rate than the
unconstrained accumulator at E128, CI tight and far from zero, **at zero
evidence reads**.

### A001 H3 — supported at E128

Exactly one qualifying pair: `last-write-wins` vs `provenance-regrounding` are
statistically **indistinguishable on canonical accuracy** (diff −0.0027, CI spans
zero) yet **differ on integrity** (IVR diff +0.0160, CI [+0.0051, +0.0270]).
Integrity separates mechanisms that accuracy cannot. One pair is thin support;
reported as such.

### B001 H1 — supported, but see §4

### B001 H2 — supported

At E64 the highest-recall arm is `uniform-blame` (0.29) while the highest-excess
arm is `counterfactual-recheck` (+0.047). Recall and causal repair are
dissociable, as preregistered.

### B001 H3 — evidence beats heuristics, at a large read cost

`counterfactual-recheck` (+0.047 excess, **77,766** consolidation reads at E64)
outperforms `eligibility-trace` (−0.054), `provenance-restricted-blame` (−0.021)
and `uniform-blame` (−0.108), all of which spend **zero** reads.

## 3. A001 integrity/cost frontier — the development result did **not** fully replicate

| horizon | Pareto frontier | `last-write-wins` | reading arms on frontier |
|---|---|---|---|
| E8 | `hybrid-symbolic-latent` | off | none |
| E16 | `evidence-reconstruction`, `last-write-wins` | **on** | `evidence-reconstruction` |
| E32 | `evidence-reconstruction`, `last-write-wins` | **on** | `evidence-reconstruction` |
| E64 | `confidence-decay`, `evidence-reconstruction`, `periodic-reset` | off | `evidence-reconstruction`, `periodic-reset` |
| E128 | `confidence-decay`, `periodic-reset` | off | **`periodic-reset`** |

Arms at E128 (mean over 12 seeds):

| arm | IVR | evidence reads |
|---|---|---|
| `periodic-reset` | **0.5457** | 4,290 |
| `confidence-decay` | 0.5479 | **0** |
| `evidence-reconstruction` | 0.5487 | 245,347 |
| `provenance-regrounding` | 0.5721 | 245,347 |
| `last-write-wins` | 0.5882 | 0 |
| `hybrid-symbolic-latent` | 0.6103 | 0 |
| `contradiction-regrounding` | 0.6204 | 223,261 |
| `lossy-latent` | 0.7694 | 0 |
| `unconstrained-accumulator` | 0.7713 | 0 |

**Correction to the development finding.** Development concluded that at E64 and
E128 *no* evidence-reading arm is Pareto-optimal. Confirmatory refutes that in
its strong form: `periodic-reset` reaches the frontier at both, spending 4,290
reads — **1.7% of the ceiling**. Its advantage over free `confidence-decay` is
0.0022 IVR, which is Pareto-strict but practically negligible.

**What does replicate, and strengthens:** *expensive* re-grounding buys nothing.
`evidence-reconstruction` and `provenance-regrounding` each spend ~245,000 reads
at E128 — 57× `periodic-reset` — and neither beats a zero-read heuristic.
`provenance-regrounding` is *worse* than free `confidence-decay` (0.5721 vs
0.5479) while spending 96% of the ceiling. Provenance re-grounding purchases
nothing on this benchmark.

`last-write-wins` remains competitive at mid horizons and is beaten at long
horizons only by other cheap methods.

## 4. The B001 result is weaker than "positive excess repair" sounds

P3 is statistically positive, but the absolute quantities are not.

At E64, means over 12 seeds:

| arm | culprit Δ | decoy Δ | raw `net_repair` | reads |
|---|---|---|---|---|
| `counterfactual-recheck` | **−0.033** | −0.060 | **−0.093** | 77,766 |
| `no-consolidation` | −0.052 | −0.088 | −0.140 | 0 |

**Every arm's raw net repair is negative, including the winner.** The culprit
slot's accuracy still *declines* under `counterfactual-recheck` (−0.033, CI
[−0.0845, +0.0167] — spans zero). Positive `excess_net_repair` therefore means
*degrades the state less than inaction does*, **not** that anything was
repaired.

This is exactly the distinction the paired endpoint was introduced to expose,
and it cuts against the class rather than for it. Stated plainly: **no tested
policy demonstrably repairs a culprit belief.** The best one merely loses less
ground than doing nothing.

`excess_net_repair` by horizon, `counterfactual-recheck`: +0.140 (E8), +0.116
(E16), +0.141 (E32), +0.047 (E64), **+0.017 (E128, CI [−0.027, +0.063] — spans
zero)**. The advantage decays with horizon and vanishes at the longest one. All
three other policies are negative or indistinguishable from zero at every
horizon except E128, where all four converge near zero as the substrate
approaches the floor.

## 5. Kill criteria

| criterion | fires? | basis |
|---|---|---|
| Track — A001 H2 premise | **No** | mean ρ 0.335, all 12 seeds < 0.6; rankings do not transfer |
| Class — B001 causal repair | **No** (narrowly) | `counterfactual-recheck` positive with CI excluding zero at E8–E64 |

The class criterion does not fire on its literal terms. It would be dishonest to
present that as a healthy class result given §4.

## 6. Development vs confirmatory

| finding | development | confirmatory | agreement |
|---|---|---|---|
| A001 H2 | ρ 0.330 / 0.395 / 0.580 | mean 0.335, all 12 < 0.6 | **agree** |
| No reading arm on frontier @E64/E128 | held | **refuted** — `periodic-reset` (4,290 reads) makes it | **disagree** |
| Expensive re-grounding buys nothing | held | held, strengthened | **agree** |
| `provenance-regrounding` no integrity advantage | held | held; now *worse* than free | **agree** |
| `last-write-wins` on frontier @E8 | held | refuted (`hybrid-symbolic-latent`) | **disagree** |
| `counterfactual-recheck` best B001 policy | E32/E64 all-seed | E8–E64 CI-positive | **agree** |
| B001 policies actually repair | not examined | **no — less damage only** | new |

Two development conclusions did not replicate, both about which cheap arm
occupies the frontier at a given horizon. That instability is itself consistent
with H2.

## 7. What may and may not be claimed

**May be claimed:**

- Mechanism rankings at short horizons do not predict long-horizon rankings
  (12 seeds, mean ρ = 0.335, CI [0.252, 0.415]); short-horizon evaluation is
  unsafe for mechanism selection on this benchmark.
- Integrity and accuracy dissociate: a pair indistinguishable on accuracy
  differs significantly on integrity violation.
- Under an enforced equal read ceiling and a locked corruption process, expensive
  evidence re-grounding does not beat cheap heuristics on integrity; provenance
  re-grounding is worse than free confidence decay.
- Attribution recall and causal repair are dissociable; maximizing recall is
  actively harmful.
- No tested delayed-credit policy repairs a culprit belief; the best reduces
  damage relative to inaction, with the advantage decaying to nothing by E128.

**May not be claimed:**

- That any mechanism "solves" latent drift — every arm's integrity violation
  exceeds 0.54 at E128.
- That evidence-reading is useless: `periodic-reset` reaches the frontier cheaply.
- That `counterfactual-recheck` repairs beliefs (§4).
- Any generalization beyond LIS-v0 and these nine/five reference arms.
- Anything about a CCS latent substrate. That dependency is untouched and
  remains separate.
- The narrowed novelty positions of G1–G3 as originally phrased (see
  `docs/LITERATURE-AUDIT-2026-09-03.md`).

---

## 8. Errata from the manuscript provenance audit (2026-09-04)

Found while reconciling every quantity against the manifests for the paper. No
sealed artifact was altered; no seed was rerun; no threshold changed.

### E4 — run-count miscount (documentation only)

This document and the Phase-3 lock stated "**1,680 runs**". The correct figure is
**840 logical arm-runs**.

`12 seeds × 5 horizons × (9 A001 + 5 B001 arms) = 840`. The erroneous 1,680 came
from computing `120 cells × 14 arms`, which double-counts: the 120-cell figure
already spans both experiments, and so does the 9+5 arm count.

Verified on disk: **840** arm manifests, each of the 14 arm names appearing
exactly 60 times (= 12 × 5). There was no duplicated or secondary execution
pass. Full file accounting: 840 arm manifests + 120 `validation.json` +
`summary.json` + `analysis.json` = **962** files.

Denominators to keep distinct:

| unit | count |
|---|---|
| seed × horizon × experiment comparison cells | **120** |
| logical arm-runs | **840** (A001 540, B001 300) |
| stored JSON artifacts | 962 |
| secondary execution passes | **0** |

### E5 — inferential estimates must exclude structurally invalid cells

The original `analysis.json` computed the B001 **E128** secondary estimates over
all 12 seeds, including the two `benchmark_at_floor` cells. The frozen rule bars
an invalid cell from contributing to an inferential claim. Corrected in
`analysis-audited.json` (originals preserved):

| arm | E128 contaminated (n=12) | E128 corrected (n=10) |
|---|---|---|
| `counterfactual-recheck` | +0.0172 [−0.0267, +0.0631] | +0.0113 [−0.0397, +0.0661] |
| `eligibility-trace` | +0.0029 [−0.0462, +0.0535] | +0.0029 [−0.0561, +0.0613] |
| `provenance-restricted-blame` | +0.0172 [−0.0186, +0.0520] | +0.0088 [−0.0296, +0.0437] |
| `uniform-blame` | −0.0002 [−0.0573, +0.0483] | −0.0087 [−0.0718, +0.0451] |

**All three primary tests are unaffected** (P1/P2 are A001; P3 is at E64, which
has no invalid cell). Every qualitative conclusion at E128 is unchanged: all CIs
still span zero.

### E6 — "no policy demonstrably repairs a culprit belief" was overstated

§4 above, and the verdict derived from it, generalised an **E64** observation to
all horizons. That is wrong. Culprit-specific delta for `counterfactual-recheck`,
by horizon:

| horizon | culprit Δ | 95% CI | reading |
|---|---|---|---|
| E8 | +0.109 | [−0.116, +0.316] | inconclusive |
| E16 | +0.078 | [−0.044, +0.190] | inconclusive |
| **E32** | **+0.066** | **[+0.015, +0.120]** | **absolute culprit repair** |
| E64 | −0.033 | [−0.085, +0.017] | no repair (preregistered endpoint) |
| E128 | −0.038 | [−0.067, −0.004] | significant **deterioration** |

**Corrected statement.** At the preregistered E64 endpoint there is no absolute
culprit repair — only reduced damage relative to inaction. But at E32 there *is*
absolute culprit repair with a CI excluding zero, and at E128 the same policy
significantly *degrades* the culprit. Repair is **horizon-dependent and
reverses**, rather than being uniformly absent.

Status: culprit/decoy deltas are **descriptive/exploratory** under the frozen
claim tiers, so the E32 repair result cannot carry a headline confirmatory
claim. It is reported because suppressing it would misstate the evidence, and
because it is uncorrected across 5 horizons × 4 arms.

This finding strengthens rather than weakens the paper's thesis: whether a
maintenance or repair policy "works" is itself horizon-dependent.

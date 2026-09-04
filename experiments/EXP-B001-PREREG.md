# EXP-B001 preregistration — Delayed credit assignment onto belief state

**Status:** DRAFT LOCK candidate. Must be committed before any confirmatory
EXP-B001 result is inspected.

**Dependency notice.** Architecture-agnostic. No result here may be used to
claim that a CCS latent substrate is validated.

## Question

An observation at time `t` may not reveal its utility until `t+k`, with `k`
large. When the late signal says *"a decision you made three epochs ago failed,
and it consulted these five beliefs"* — without saying which belief was wrong —
**can offline consolidation localize and repair the faulty belief without
corrupting the four that were correct?**

The question is not whether offline consolidation helps (settled: 2606.03979,
2604.20943) or whether hindsight can assign credit to memory writes (settled:
2606.16285). It is whether **ambiguous** delayed blame can be localized at
acceptable collateral cost.

## Primary hypotheses

> **Erratum E1 (pre-confirmatory consistency correction, 2026-09-03).** Amendment
> 001 (M2) changed the causal estimand from absolute `net_repair` to paired
> `excess_net_repair`, but this hypothesis prose still referred to the superseded
> absolute endpoint. The hypotheses below are rewritten onto the causal estimand.
> **No mechanism result motivates this correction and no observed development
> value changes.** Raw `net_repair` remains mandatory descriptive output.

Throughout: `excess_net_repair(policy) = net_repair(policy) − net_repair(no-consolidation)`
on the identical paired lifetime. `no-consolidation` is the inaction baseline and
is exactly zero by construction; only active policies are evaluated on it.

**H1 (causal repair without damage).** At least one active credit-assignment
rule achieves positive `excess_net_repair` — repair of the culprit net of damage
to the decoys, over and above what inaction would have produced.

*Confirmatory success*, for a preregistered horizon and active policy across the
frozen paired confirmatory seeds:

- mean `excess_net_repair` > 0;
- paired bootstrap 95% CI (procedure §Statistics) excludes zero;
- every seed reported, including unfavourable ones;
- **no favourable-cell counting substitutes for the paired estimate.**

Absolute `net_repair` is reported alongside for transparency but is not the
inferential target: `no-consolidation` posted positive absolute net repair at
short horizons in development, so the absolute endpoint cannot identify a causal
effect.

**H2 (recall is not the objective).** Attribution recall and *causal* repair are
dissociable: an arm can achieve high `attribution_recall` and negative
`excess_net_repair`.

*Confirmatory success:* the arm with the highest mean `attribution_recall` is not
the arm with the highest mean `excess_net_repair`, at a preregistered horizon,
across the frozen confirmatory seeds.

`attribution_recall` is a raw descriptive quantity and is deliberately retained
in its raw form here: it measures whether the culprit was revised at all, which
is a property of the policy's targeting, not of the benchmark's baseline drift,
and so needs no inaction subtraction. Repair, by contrast, is always evaluated
causally.

**H3 (evidence versus heuristics, at stated cost).** Spending evidence reads to
re-derive consulted beliefs (`counterfactual-recheck`) yields higher
`excess_net_repair` than the recency- and provenance-heuristic blame rules at
the same maintenance-op ceiling — **or** it does not, and the cheaper heuristic
is preferable.

*Confirmatory evaluation:* paired difference in `excess_net_repair` between
`counterfactual-recheck` and each heuristic arm, with the frozen bootstrap CI,
reported **beside** each arm's `consolidation_reads` and `evidence_reads`. A
causal advantage bought with a large read spend is reported on the repair/cost
frontier, never as a like-for-like win. Either direction is a reportable result.

There is exactly one definition of repair success in this document:
positive `excess_net_repair`.

## Benchmark

The LIS-v0 `delayed_credit` stream, identical to the drift stream plus
`delayed_outcome` events. Each outcome names a failed decision, its decision
time, and the slots it consulted. Exactly one consulted slot carried a value
that was false at decision time; the rest were correct. The identity of the
culprit is harness-only audit metadata.

Outcomes are emitted on the live clock at their arrival epoch so that probes
still follow them. (The pilot found and fixed a defect where post-hoc timestamp
assignment pushed every outcome past the last probe, making repair
structurally unmeasurable. See `EXP-000-PILOT-RECORD.md`.)

## Arms

All arms share one substrate, `TrackedAccumulator`, so the **only** variable is
the credit-assignment rule. Revision means suppressing the currently believed
value so the next-best can surface.

| arm | rule |
|---|---|
| `no-consolidation` | discard the delayed signal |
| `uniform-blame` | revise every consulted slot |
| `eligibility-trace` | revise the top-k consulted slots by recency of last write |
| `provenance-restricted-blame` | revise only beliefs resting on low-tier provenance |
| `counterfactual-recheck` | re-read the log per consulted slot; revise on disagreement |

`eligibility-trace` is included as a control precisely because its recency
assumption is *wrong* for this failure mode; a classical trace should not be
expected to work here, and showing that cleanly is part of the point.

## Metrics

- `attribution_precision` — revised slots that were the culprit;
- `attribution_recall` — outcomes whose culprit was revised;
- `collateral_revision_rate` — revisions that hit a non-culprit;
- `culprit_accuracy_delta` — windowed accuracy change on the culprit slot;
- `decoy_accuracy_delta` — windowed accuracy change on consulted-but-innocent
  slots; **the collateral-damage measure**;
- `untouched_accuracy_delta` — per-outcome change on a deterministic matched set
  of contemporaneously measurable slots outside the implicated decision;
- `net_repair` = culprit delta + decoy delta; descriptive, retained for
  transparency and auditability;
- `excess_net_repair` = `net_repair` − `net_repair(no-consolidation)` on the
  identical paired lifetime; **primary causal endpoint** (amendment 001, M2);
- `consolidation_reads` — evidence reads spent on consolidation;
- all EXP-A001 integrity metrics, since consolidation can itself induce drift.

Windowed deltas compare the k probes before an outcome with the k probes after
it, per slot, averaged over outcomes (default k=3).

### Declared live metrics

`stale_state_rate`, `attribution_precision`, `attribution_recall`,
`collateral_revision_rate`. `unsupported_belief_rate` is **out of scope** for
EXP-B001: every arm shares an evidence-derived substrate that cannot produce a
belief nothing asserted, so the metric is structurally zero and the validator
must not demand it.

### Measurement amendment 001 — matched contemporaneously untouched control

**Pre-development, score-independent amendment.** The engineering pilot showed
that the original global untouched set was structurally degenerate: over a long
lifetime, delayed outcomes collectively consult nearly every slot. This defect
was identified before development seeds and is repaired without changing the
stream or corruption process. The corruption lock therefore remains the lock
established at `eb8547c4c9577d318901ce84e94c62972c9c2f37`.

For each delayed outcome, the harness selects a matched control set that:

1. excludes every slot consulted by the target outcome;
2. has at least one measurable probe before and after the outcome inside the
   same k-probe scoring rule used for culprit/decoy deltas;
3. excludes any slot implicated by another delayed outcome whose consolidation
   time falls inside that candidate slot's pre/post evaluation window;
4. is selected deterministically by a stable SHA-256 rank over run seed,
   outcome event id, and slot identity, after the mechanism has consumed the
   stream and without exposing control identity to the mechanism.

The target control count is one control per consulted decoy, capped by the
number of eligible slots. All current Class-B policies can revise only consulted
slots, so excluding overlapping-outcome implicated slots also excludes every
slot another admissible current policy could revise while preserving the same
control identity across arms.

The manifest records per-outcome eligible/selected counts, exclusion counts,
and a control-selection hash. The validator fails closed if controls are absent
or unmeasurable, if control selection differs across arms, or if the scoring
protocol hash differs. A numerically zero `untouched_accuracy_delta` is **not**
by itself an inert metric: zero collateral change on a live matched control is a
valid result.

## Budget matching

Same rules as EXP-A001: identical read, maintenance-op, and log-capacity
ceilings; reads charged per record scanned; actual spend reported. Because
`counterfactual-recheck` is the only arm that spends reads, its result must be
presented on a cost frontier and never as a like-for-like win.

## Phase separation

Identical to EXP-A001. Pilot (complete, non-evidential) → development
calibration on ≥3 disjoint seeds → confirmatory on **exactly 12 disjoint paired
seeds, frozen before execution** (erratum E2; the earlier "≥5" rule is revoked).
Freeze protocol, commit SHA, environment, generator version, corruption lock,
scoring-protocol hash, and seed rule before the first confirmatory run.

## Statistics (frozen 2026-09-03, erratum E2)

> **Erratum E2 (pre-confirmatory statistical specification).** The original
> statistics sections named the estimators but left the exact procedure
> underspecified. Fixed here **before any confirmatory data exists**. No
> substantive hypothesis is changed; only underspecified operations are made
> reproducible. Development values are calibration observations and must never
> enter a confirmatory estimate.

### Resampling unit and pairing

- **Resampling unit: the lifetime seed.** Seeds are the independent units.
- Arms stay **paired inside** each resampled seed: a bootstrap replicate draws
  seeds with replacement and carries every arm's value for that seed together.
- Horizons are **not** resampled; each horizon is analysed separately.

### Bootstrap procedure

- **Replicates: 10,000**, fixed.
- **Interval: percentile** (not BCa, not basic), two-sided 95%.
- **RNG derivation, deterministic:**
  `seed_int = int.from_bytes(sha256(f"lifetime-integrity/bootstrap/v1/{experiment}/{claim}/{horizon}".encode()).digest()[:4], "big")`
  passed to `numpy.random.default_rng`. The same claim at the same horizon
  therefore always yields the identical interval.
- **Degenerate replicates:** a replicate in which every resampled seed is
  identical is retained, not discarded. If the statistic is undefined for a
  replicate (e.g. zero rank variance in a Spearman computation), that replicate
  is dropped and the number dropped is reported; if more than 5% are dropped the
  interval is reported as unreliable rather than silently narrowed.
- **Ties:** the already-frozen average-rank treatment, unchanged.

### A001 H2 — exact estimator

1. For each confirmatory seed *s*, compute one Spearman `rho_s` between the
   **nine** mechanism rankings by `integrity_violation_rate` at **E8** and at
   **E128**, using the frozen average-rank tie treatment.
2. Primary confirmatory estimate = **arithmetic mean of `rho_s`** over the
   confirmatory seeds.
3. Bootstrap seeds as paired units under the procedure above.
4. Report a percentile 95% CI for the mean.
5. **H2 succeeds iff mean `rho` < 0.6 AND the 95% CI excludes 1.0.**
6. Every per-seed `rho_s` is reported.

No other horizon pair may be substituted, and no additional H2 statistic may be
introduced. The development values 0.330 / 0.395 / 0.580 are calibration
observations only and do not enter this estimate.

### Multiplicity

The arm × horizon matrix must not become a garden of significance tests. Tests
are predeclared into exactly three tiers:

**Primary confirmatory** (the only tests that can support a headline claim):

| # | experiment | claim | test |
|---|---|---|---|
| P1 | A001 | H2 | mean Spearman rho over seeds, CI as above |
| P2 | A001 | H1 | paired `integrity_violation_rate` difference, best re-grounding arm vs `unconstrained-accumulator`, at **E128** |
| P3 | B001 | H1 | paired `excess_net_repair` for `counterfactual-recheck` at **E64** |

Three primary tests. Holm–Bonferroni correction across P1–P3 at family-wise
α = 0.05. P2's arm and P3's arm/horizon are fixed here, before confirmatory
data exists, from the preregistered structure — not chosen post hoc.

**Secondary confirmatory** (reported with CIs, Holm-corrected within the family,
never headline on their own): H3 for both experiments; `excess_net_repair` for
the remaining active B001 policies; H1 at horizons other than E128.

**Descriptive / exploratory** (no inferential claim, no p-values): everything
else — per-class breakdowns, calibration, recovery, provenance consistency,
`untouched_accuracy_delta`, matched-control coverage, raw `net_repair`,
attribution precision/recall, resource counters.

**Integrity/cost and repair/cost frontiers remain the headline outputs.** A
mechanism is never described as "winning" because one uncorrected pairwise test
at one horizon crossed 0.05.

### Confirmatory sample size — frozen, no optional stopping

**12 paired seeds, fixed before the first confirmatory run.** The earlier
"minimum 5, scale to >=12 if inconclusive" rule permitted optional stopping and
is **revoked**. Given a marginal development H2 value (0.580 at one seed), the
sample size is committed up front:

- generated by the committed deterministic seed rule;
- disjoint from all pilot and development seeds;
- an exact list, fixed before execution;
- identical for A001 and B001;
- run across the full {8, 16, 32, 64, 128} ladder;
- **never replaced because a seed produces an inconvenient result.**

## Invalidation / kill criteria

1. Any arm saw a different number of delayed outcomes.
2. Any arm saw no delayed outcomes.
3. `audit_leak_count > 0`.
4. Budget ceilings differ by more than 2%, or an arm exceeded or exhausted its
   ceiling.
5. Arms faced different corruption processes or lifetimes.
6. A declared live metric is inert across all arms.
7. The matched untouched control is absent/unmeasurable or differs across arms.
8. Arms disagree on the scoring-protocol hash.
9. Ceiling or floor effect on `canonical_accuracy`.
10. Results depend on a single seed.
11. `no-consolidation` is not dominated: if no arm beats doing nothing, say so.

## Kill criterion for the class

**Amended by `PHASE-2-AMENDMENT-001.md` (M2), post-development and
pre-confirmatory.** The original wording used absolute `net_repair`, which the
development matrix showed to be satisfiable by `no-consolidation` — an arm that
performs zero revisions. The motivation is that observed non-zero inaction
baseline, not a preference for any active mechanism.

> If no active delayed-credit policy achieves positive `excess_net_repair` with
> adequate consistency across development seeds — that is, no active policy has
> a positive per-seed mean at a common horizon for all three development seeds —
> then the tested policies have failed to demonstrate beneficial localization
> beyond the `no-consolidation` baseline. That is a publishable negative result
> and the correct trigger to redesign the outcome signal or abandon class B, not
> to iterate until a policy wins.

Confirmatory standard: per horizon, across the **12 frozen disjoint paired
seeds** (erratum E2), mean `excess_net_repair` > 0 with a paired bootstrap 95%
CI excluding zero under the frozen procedure, and every seed reported including
unfavourable ones.

A count of favourable cells is explicitly **not** sufficient evidence.

## Novelty boundary

We do **not** claim novelty for: experience replay, offline RL, eligibility
traces, memory consolidation, or complementary learning systems; sleep-style
consolidation for LMs (2606.03979, 2604.20943, 2605.26099); hindsight credit
assignment to memory writes (2606.16285); transactional belief commit with
cascading repair from explicit retraction (2607.23929); or measuring collateral
damage to unrelated knowledge after targeted revision (2307.12976, 2305.14795).

The intended contribution is: **attribution of an ambiguous delayed outcome to
one of several jointly consulted persistent beliefs, scored jointly for repair
and for collateral damage to the innocent beliefs the same decision touched.**

Full audit: `docs/LITERATURE-AUDIT-2026-09-02.md`.

## Publication policy

As EXP-A001. Negative results published.

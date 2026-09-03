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

**H1 (repair without damage).** At least one credit-assignment rule achieves
positive `net_repair` — culprit accuracy recovered minus decoy accuracy lost —
with a bootstrap 95% CI excluding zero.

**H2 (recall is not the objective).** Attribution recall and net repair are
dissociable: an arm can achieve high recall and negative net repair.

*Success:* the arm with the highest `attribution_recall` does not have the
highest `net_repair`, across a majority of confirmatory seeds. The pilot already
shows the expected pattern — `uniform-blame` reaches 0.72 recall and −0.57 net
repair — but the pilot is not evidence.

**H3 (evidence beats heuristics).** Spending evidence reads to re-derive
consulted beliefs (`counterfactual-recheck`) yields higher net repair than
recency- or provenance-heuristic blame at the same maintenance-op ceiling,
**or** it does not and the cheaper heuristic is preferable. Either direction is
a reportable result; the read cost must be reported alongside.

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
calibration on ≥3 disjoint seeds → confirmatory on ≥5 disjoint paired seeds.
Freeze protocol, commit SHA, environment, generator version, corruption lock,
scoring-protocol hash, and seed rule before the first confirmatory run.

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

Confirmatory standard: per horizon, across at least 5 disjoint paired seeds,
mean `excess_net_repair` > 0 with a paired bootstrap 95% CI excluding zero, and
every seed reported including unfavourable ones.

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

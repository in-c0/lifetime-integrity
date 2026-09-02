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
- `untouched_accuracy_delta` — change on slots no outcome consulted;
- `net_repair` = culprit delta + decoy delta; **primary**;
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

### Known calibration item

In the default configuration, outcomes consult nearly every slot, so the
untouched-slot set is empty and `untouched_accuracy_delta` is degenerate at 0.
Development phase must either enlarge the slot set or reduce outcome coverage
so that a genuine untouched control exists. This is recorded before lock as a
mechanical defect, not a result-driven adjustment.

## Budget matching

Same rules as EXP-A001: identical read, maintenance-op, and log-capacity
ceilings; reads charged per record scanned; actual spend reported. Because
`counterfactual-recheck` is the only arm that spends reads, its result must be
presented on a cost frontier and never as a like-for-like win.

## Phase separation

Identical to EXP-A001. Pilot (complete, non-evidential) → development
calibration on ≥3 disjoint seeds → confirmatory on ≥5 disjoint paired seeds.
Freeze protocol, commit SHA, environment, generator version, corruption lock,
and seed rule before the first confirmatory run.

## Invalidation / kill criteria

1. Any arm saw a different number of delayed outcomes.
2. Any arm saw no delayed outcomes.
3. `audit_leak_count > 0`.
4. Budget ceilings differ by more than 2%, or an arm exceeded or exhausted its
   ceiling.
5. Arms faced different corruption processes or lifetimes.
6. A declared live metric is inert across all arms.
7. Ceiling or floor effect on `canonical_accuracy`.
8. Results depend on a single seed.
9. `no-consolidation` is not dominated: if no arm beats doing nothing, say so.

## Kill criterion for the class

**If no rule achieves positive `net_repair` across development seeds**, the
finding is that ambiguous delayed blame cannot be localized safely by any of
these policies on this benchmark — a negative result worth publishing, and the
correct trigger to either redesign the signal (richer outcome information) or
abandon class B rather than iterate until something wins.

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

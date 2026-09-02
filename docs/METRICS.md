# Metric definitions

Every metric is computed from probe records alone, so it applies to any system
satisfying the mechanism contract.

## Why integrity is not accuracy

Two failures are invisible to a correctness score:

- A system answers the canonical value **that nobody ever told it**. It is right
  by luck or by confabulation, and its state is not grounded in its experience.
- A system answers a value it was legitimately told, which has since been
  superseded. Its state is well-supported and obsolete.

`canonical_accuracy` scores the first as a success and cannot distinguish the
second from ordinary error. The integrity metrics separate them.

## Integrity metrics

| metric | definition | fires when |
|---|---|---|
| `unsupported_belief_rate` | answered a value not in `ever_asserted` for that slot | state has drifted off the evidence, even if correct |
| `stale_state_rate` | answered a superseded value | belief is grounded but obsolete |
| `integrity_violation_rate` | either of the above | **primary endpoint for EXP-A001** |
| `self_contradiction_rate` | consecutive probes on one slot, no intervening assertion, different answers | state is unstable without cause |
| `provenance_consistency` | cited evidence exists and asserts the answered value | among answers that cite anything |
| `unattributed_answer_rate` | answered while citing nothing | mechanism cannot explain itself |

Abstention is never an integrity violation. Declining to answer is the correct
behaviour for a system that knows its state is unreliable, and the benchmark
must not punish it — `abstention_rate` is reported separately so that abstaining
into silence is still visible.

Each probe carries a never-asserted option so `unsupported_belief_rate` is
reachable, and the codebook is shared across slots so a bounded state can bleed
a neighbour's value into an offered option.

## Temporal metrics

- `mean_recovery_probes` — probes between a canonical change and the first
  correct answer, per change, averaged.
- `unrecovered_changes` — changes never recovered before the lifetime ended.
  Report alongside the mean: a mechanism that recovers fast *when it recovers*
  can still leave most changes unrecovered.
- `drift_slope_per_epoch` — OLS slope of per-epoch integrity violation.
- `drift_late_minus_early` — final third minus first third; more robust than the
  slope on short lifetimes.

## Calibration

`expected_calibration_error` (10 bins) and `brier_score` over answered probes.
A system asserting stale beliefs with high confidence is worse than one that
knows it is unsure, and only calibration captures that.

## Consolidation metrics (EXP-B001)

| metric | definition |
|---|---|
| `attribution_precision` | revisions that hit the culprit |
| `attribution_recall` | outcomes whose culprit was revised |
| `collateral_revision_rate` | revisions that hit an innocent slot |
| `culprit_accuracy_delta` | windowed accuracy change on the culprit |
| `decoy_accuracy_delta` | windowed accuracy change on consulted-but-correct slots |
| `untouched_accuracy_delta` | change on slots no outcome consulted |
| `net_repair` | culprit delta + decoy delta; **primary endpoint for EXP-B001** |

Windowed deltas compare the k probes before an outcome against the k probes
after it, per slot (default k=3), averaged over outcomes. Recall alone is
worthless here: revising every consulted slot guarantees recall 1.0 and wrecks
the state.

## Liveness

A metric identically zero across every arm is not measuring anything on that
configuration. Each experiment declares its live metrics and the validator
rejects a comparison in which a declared metric is inert. `unsupported_belief_rate`
is declared for EXP-A001 and explicitly **not** for EXP-B001, whose arms share
an evidence-derived substrate that cannot confabulate.

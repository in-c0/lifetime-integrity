# EXP-A001 preregistration — Latent drift and re-grounding under matched cost

**Status:** DRAFT LOCK candidate. Must be committed before any confirmatory
EXP-A001 result is inspected.

**Dependency notice.** This experiment is deliberately **architecture-agnostic**.
It makes no claim about any CCS latent substrate, and no result from it may be
used to assert that a CCS latent architecture is validated. That claim requires
an admissible substrate established by the State Promotion track and subsequent
routing work. Until then, LIS-v0 is a benchmark of *maintenance policies*, and
is intended to stand on its own if the CCS programme goes nowhere.

## Question

When a persistent system is run for a very long time against a stream containing
contradictions, misinformation, misleading repetition, genuine world change,
long inactivity gaps, and unequal source reliability — **how much re-grounding
does it have to buy, and which re-grounding policy buys the most integrity per
unit of cost?**

The question is deliberately not "do agents drift" (settled: 2605.26302) or "can
agents detect stale memories" (settled: 2605.06527).

## Primary hypotheses

**H1 (cost-matched separation).** At an equal ceiling on evidence reads,
maintenance operations, and log capacity, at least one re-grounding mechanism
achieves a lower `integrity_violation_rate` than the unconstrained persistent
accumulator, and the advantage is not explained by simply spending more.

*Success:* paired-seed mean `integrity_violation_rate` strictly lower than
`unconstrained-accumulator` with a bootstrap 95% CI excluding zero, at equal
`evidence_reads_ceiling`, with the winner's actual `evidence_reads` reported.

**H2 (horizon dependence).** The ranking of mechanisms by
`integrity_violation_rate` at short lifetimes does not predict the ranking at
long lifetimes.

*Success:* Spearman correlation between short-horizon (8 epochs) and
long-horizon (128 epochs) mechanism rankings is below 0.6, with the CI over
seeds excluding 1.0. This is the methodological claim the track most wants to
support, and it is falsifiable: if rankings are stable across horizons, then
short-horizon evaluation is adequate and this track loses its main premise.

**H3 (integrity is not accuracy).** `unsupported_belief_rate` and
`self_contradiction_rate` separate mechanisms that `canonical_accuracy` does
not.

*Success:* at least one pair of mechanisms is statistically indistinguishable on
`canonical_accuracy` while differing on an integrity metric with a CI excluding
zero.

## Benchmark: LIS-v0

A lifetime is a deterministic event sequence over a hidden canonical world of
context/key slots drawn from a **shared codebook**, so that a bounded state can
bleed a neighbouring slot's value.

Event types: `assert`, `probe`, `gap`, `context_shift`. Assertions are tagged
(audit-only) as `clean`, `misinformation`, `misleading_repeat`, `contradiction`,
or `world_change`. Sources belong to `primary` / `secondary` / `unreliable`
tiers with different hidden reliabilities. World changes are sometimes **quiet**
— canonical value changes with no announcement that epoch.

Probes are classified (audit-only) as `fresh`, `settled`, `untouched`,
`post_gap`, `stale_risk`, `quiet_change`, `misinfo_target`, `contradiction`.

### Corruption-process lock

`LifetimeConfig.config_lock()` is the SHA-256 of the generator version plus
every corruption rate. Every run manifest carries it, and `validate_runs.py`
rejects a comparison whose arms ran different corruption processes.

**Locking rule.** Corruption rates were fixed during pilot construction and are
frozen at the commit that lands this document. After that commit they may be
changed only by a numbered amendment stating a reason that is **independent of
which mechanism won**. Permitted reasons: ceiling effect, floor effect, an
inert metric, or a mechanical defect. Forbidden: any adjustment made because a
preferred arm underperformed.

### Audit separation

Canonical values, truthfulness flags, corruption tags, probe classes, and
superseded-value lists are harness-only. Mechanisms receive `visible()` views.
The harness counts any leak in `audit_leak_count`, and the validator rejects a
comparison with a nonzero count. This is enforced by test, not by convention.

## Arms

All arms implement the same interface and share one metered `EvidenceLog`.

| arm | role |
|---|---|
| `last-write-wins` | trivial baseline; zero evidence reads. **Must be reported prominently** — 2606.22030 found it hard to beat, and so did our pilot |
| `unconstrained-accumulator` | the drift reference: persistent state that only accretes, no provenance, no expiry |
| `lossy-latent` | bounded-capacity state with cross-slot interference; the only arm that can hold a belief nothing asserted |
| `periodic-reset` | wipe and rebuild from a recent window on a fixed cadence |
| `evidence-reconstruction` | hold no belief; re-derive at query time |
| `provenance-regrounding` | estimated per-source reliability weighting. **Baseline, not a proposed method** (2606.22030) |
| `confidence-decay` | time-decayed confidence with abstention |
| `contradiction-regrounding` | cheap accumulation until a conflict fires a targeted re-read |
| `hybrid-symbolic-latent` | corroboration-gated symbolic store fronting a latent accumulator |

`lossy-latent` and `hybrid-symbolic-latent` are **controls**, not proposals. In
particular `hybrid-symbolic-latent` exists to answer "would a symbolic spine
have been enough", which is the question a CCS claim would have to survive.

## Budget matching

Before a run counts as confirmatory:

- identical `evidence_reads_ceiling`, `maintenance_ops_ceiling`, and
  `log_capacity` across arms, within 2%;
- confirmatory runs use `evidence_reads_ceiling = round(1.25 × derived ceiling)`
  per amendment 001 (M3), applied uniformly to every arm; `log_capacity` and
  `maintenance_ops_ceiling` are unchanged;
- ceilings derived from the lifetime (probe and assertion counts), never from a
  mechanism's measured appetite;
- reads charged per record **scanned**, not per record returned;
- an arm may spend **less** than the ceiling — that is part of the mechanism,
  not a reason to pad it;
- actual reads, maintenance ops, state bytes, and wall time reported for every
  arm;
- any arm hitting `exhausted_reads > 0` marks the comparison ceiling-bound, and
  the whole set must be re-run at a higher ceiling.

Because arms differ enormously in cost (pilot: 0 to ~38k reads), the headline
result must be an **integrity/cost frontier**, not a single winner. An arm that
wins only by spending 40× more has not won.

## Metrics

Integrity, independent of task accuracy:

- `unsupported_belief_rate` — answered a value never asserted for that slot,
  *even if canonical*;
- `stale_state_rate` — answered a superseded value;
- `integrity_violation_rate` — either of the above; **primary**;
- `self_contradiction_rate` — answer flipped with no intervening evidence;
- `provenance_consistency` — cited support exists and entails the answer;
- `unattributed_answer_rate` — answered while citing nothing;
- `expected_calibration_error`, `brier_score`;
- `mean_recovery_probes`, `unrecovered_changes`;
- `drift_slope_per_epoch`, `drift_late_minus_early`;
- per-probe-class breakdown.

Accuracy (`canonical_accuracy`, `abstention_rate`) is reported but is **not** the
primary endpoint.

### Metric-liveness rule (amended)

**Amended by `PHASE-2-AMENDMENT-001.md` (M1).** Liveness is now claim-scoped: a
metric may invalidate only the claims that actually depend on it, while
structural and provenance failures still invalidate the entire cell. H2 depends
on `integrity_violation_rate` and is unaffected by an inert
`self_contradiction_rate`; `H3_integrity_not_accuracy` and
`self_contradiction_analysis` remain invalid wherever that metric is inert.

### Metric-liveness rule (original)

Each experiment declares which metrics it claims to measure. The validator
rejects a comparison in which a declared metric is identically zero across all
arms. EXP-A001 declares `unsupported_belief_rate`, `self_contradiction_rate`,
and `stale_state_rate`. A metric no arm can move is not evidence.

## Phase separation

**Phase 1 — engineering pilot (complete).** Mechanics only. See
`experiments/EXP-000-PILOT-RECORD.md`. Explicitly not evidence.

**Phase 2 — development calibration.** At least 3 development seeds, disjoint
from confirmatory seeds. May be used only to: confirm the benchmark is neither
at ceiling nor at floor; confirm declared metrics are live; fix the horizon
ladder; fix the read ceiling; and repair mechanical defects. May **not** be used
to tune corruption rates toward a preferred ranking. Freeze at the end.

**Phase 3 — confirmatory.** Minimum 5 paired seeds, disjoint from development,
across the full horizon ladder {8, 16, 32, 64, 128} epochs. Before the first
confirmatory run, freeze: protocol version, code commit SHA, environment lock,
generator version, corruption lock, seed list or committed selection rule.

## Statistics

Paired seeds across arms. Bootstrap 95% CIs on paired differences. Report effect
sizes, not only p-values. Report every seed, including valid runs that failed to
show an effect. Scale to ≥12 seeds if intervals are inconclusive.

## Invalidation / kill criteria

The configuration is invalid for the primary claim if:

1. all arms exceed 0.95 `canonical_accuracy` (ceiling);
2. no arm reaches 0.40 `canonical_accuracy` (floor);
3. any declared metric is inert across all arms;
4. `audit_leak_count > 0` for any arm;
5. budget ceilings differ by more than 2%, or any arm exceeds its ceiling;
6. arms faced different corruption processes or different lifetimes;
7. any arm exhausted its read budget;
8. results depend on a single lifetime seed;
9. the apparent advantage of any re-grounding arm disappears once cost is
   plotted rather than held nominally equal.

## Kill criteria for the track

State these now so they cannot be quietly dropped later:

- **If H2 fails** — if short-horizon rankings do predict long-horizon rankings —
  then the central premise ("these failures only appear over long lifetimes") is
  wrong, and this should be published as a negative methodological result.
- **If no mechanism beats `last-write-wins`** on the integrity/cost frontier
  across development seeds, the honest output is a negative result reporting
  that sophisticated maintenance does not pay on this benchmark, echoing
  2606.22030. That is a publishable finding and must not be buried.

## Novelty boundary

We do **not** claim novelty for: agent aging or drift over deployment
(2605.26302); stale-belief detection (2605.06527); belief drift across sessions
(2603.23848); contradiction resolution or bitemporal provenance (2606.06240,
2607.23929); provenance-capped reliability-conditional updating (2606.22030);
closed-world symbolic belief benchmarks (2605.30219); representational drift in
continual learning (2511.22615, 2512.22045, 2602.19655); or the term *epistemic
integrity* (2606.04017).

The intended contribution is narrower: a **cost-matched comparison of integrity
maintenance policies under a fixed, locked corruption process, with lifetime
length as the independent variable, and integrity metrics that fire
independently of task accuracy.**

Full audit: `docs/LITERATURE-AUDIT-2026-09-02.md`.

## Publication policy

- Code, configs, and manifests public before submission.
- Every table traceable to a machine-readable manifest.
- No cherry-picked seeds.
- Negative results published.
- Claims restricted to LIS-v0 and the reference arms actually run.

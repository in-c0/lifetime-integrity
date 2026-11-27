# Phase-2 protocol amendment 001 — post-development, pre-confirmatory

**Status:** APPROVED by owner 2026-09-03. Written and committed **before**
recomputing any affected development interpretation, so that every decision rule
below is fixed in advance of the values it will judge.

- Amends: `EXP-A001-PREREG.md`, `EXP-B001-PREREG.md`, `scripts/validate_runs.py`
- Motivated by: `experiments/PHASE-2-DEVELOPMENT-RECORD.md` (matrix at gate commit `0c79b2ef`)
- Development matrix is **not** re-run. All four amendments are applied to the
  existing manifests under explicit protocol-version provenance.

## What remains frozen

Untouched by this amendment, and unchanged from `eb8547c`:

- the lifetime generator (`src/lifetime_integrity/lifetime.py`);
- the corruption process and every corruption rate;
- the corruption lock `6e890d154d637d826613172a376396cb54f22c420e063125927fd979397b5b40`;
- all nine EXP-A001 mechanisms and all five EXP-B001 credit rules;
- the development seeds `231368116`, `1043567494`, `1443029309`;
- the horizon ladder {8, 16, 32, 64, 128};
- the matched-control matching algorithm and control identities;
- `log_capacity` and `maintenance_ops_ceiling`.

## Classification of each amendment

| # | changes | interpretation only | execution configuration |
|---|---|---|---|
| M1 | validity semantics | ✅ | — |
| M2 | derived endpoint | ✅ | — |
| M3 | evidence-read ceiling | — | ✅ (confirmatory only) |
| M4 | documentation | ✅ | — |

Only **M3** alters execution configuration, and only for confirmatory runs.
M1, M2 and M4 change how existing numbers are interpreted and reported; none
alters any mechanism's behaviour or any recorded raw value.

---

## M1 — Claim-scoped metric validity

### Observation that motivated it

Two development cells (EXP-A001 at 8 epochs, seeds `1043567494` and
`1443029309`) were refused wholesale for `inert_metrics:['self_contradiction_rate']`.
The preregistered H2 diagnostic does not consume `self_contradiction_rate`. It
consumes `integrity_violation_rate`, which was live in all three seeds at both
endpoints. A metric H2 never touches therefore suppressed H2 in two of three
seeds.

This is a dependency-structure defect in the reporting model. It is not
motivated by any mechanism's performance, and it does not revive the dead
metric.

### The principle

> A metric can invalidate only claims or analyses that actually depend on that
> metric. Structural and provenance failures still invalidate the entire cell.

### The change

`validate()` no longer returns one boolean standing in for every scientific
claim. It returns:

- `structurally_valid` — provenance, corruption-lock agreement, budget parity,
  audit leaks, ceiling/floor, required arms, control presence. A structural
  failure invalidates **everything** in the cell.
- `metric_status` — per declared metric: `live` or `inert`, with the reason.
- `claims` — per preregistered claim: `valid`, the metrics it `depends_on`, and
  the reasons for any invalidity.

`valid_for_comparison` is retained and is now defined as `structurally_valid`.
`inert_metrics` remains reported at top level for audit continuity.

### Declared claim dependencies

**EXP-A001**

| claim | depends on |
|---|---|
| `H1_cost_matched_separation` | `integrity_violation_rate` |
| `H2_horizon_rank_stability` | `integrity_violation_rate` |
| `H3_integrity_not_accuracy` | `unsupported_belief_rate`, `self_contradiction_rate`, `canonical_accuracy` |
| `unsupported_belief_analysis` | `unsupported_belief_rate` |
| `self_contradiction_analysis` | `self_contradiction_rate` |
| `stale_state_analysis` | `stale_state_rate` |

**EXP-B001**

| claim | depends on |
|---|---|
| `causal_excess_repair` | `net_repair`, presence of the `no-consolidation` arm |
| `attribution_analysis` | `attribution_precision`, `attribution_recall` |
| `collateral_analysis` | `decoy_accuracy_delta`, matched untouched control |
| `stale_state_analysis` | `stale_state_rate` |

Consequence for the affected cells: `H2_horizon_rank_stability` becomes valid,
while `self_contradiction_analysis` and `H3_integrity_not_accuracy` remain
**invalid** at E8 for those two seeds. Claims about a dead metric stay
forbidden.

---

## M2 — Paired causal endpoint for EXP-B001

### Observation that motivated it

`no-consolidation` performs zero revisions by construction, yet posted positive
mean absolute `net_repair` at E8 (+0.126) and E16 (+0.089). `net_repair`
(culprit Δ + decoy Δ) therefore carries a non-zero, horizon-dependent baseline
produced by ordinary benchmark dynamics rather than by any repair.

The motivation is this observed inaction baseline. It is **not** a preference
for any active mechanism, and the amendment was written before any aggregated
excess value was computed.

### The change

`net_repair` is **not** wrong and is **not** removed. It remains in every
manifest as a descriptive measure of pre/post state change around an outcome.
What changes is that it may no longer serve as the causal endpoint on its own.

Added derived endpoint, computed against the identical paired lifetime:

```
excess_net_repair(policy, seed, horizon)
    = net_repair(policy, seed, horizon)
    - net_repair(no-consolidation, seed, horizon)
```

`no-consolidation` is by definition the inaction baseline and has
`excess_net_repair == 0`. Only active policies are evaluated on it.

**An active policy succeeds on the causal question only when its paired
`excess_net_repair` is positive.**

### Cross-seed standard

Taken from the existing preregistration language rather than invented here. The
governing constraints already on record are invalidation item 10, *"Results
depend on a single seed"*, and the EXP-A001 statistics section, *"Paired seeds
across arms. Bootstrap 95% CIs on paired differences… Report every seed."*

Minimal adaptation to the paired endpoint:

- **Development standard.** An active policy demonstrates beneficial
  localization iff, at **at least one horizon**, its mean `excess_net_repair` is
  positive for **every one of the three development seeds**. Per-seed sign
  consistency is required so the result cannot rest on a single seed. A count of
  favourable cells is explicitly **not** sufficient.
- **Confirmatory standard.** *(Sample size superseded by erratum E2, 2026-09-03:
  exactly 12 frozen seeds, no optional stopping.)* Per horizon, across the
  confirmatory seeds: mean
  `excess_net_repair` > 0 with a paired bootstrap 95% CI excluding zero, and
  per-seed values reported in full including unfavourable seeds.

### Amended class kill criterion

Replaces the absolute-`net_repair` wording in `EXP-B001-PREREG.md`:

> If no active delayed-credit policy achieves positive `excess_net_repair` with
> adequate consistency across development seeds — that is, no active policy has
> a positive per-seed mean at a common horizon for all three development seeds —
> then the tested policies have failed to demonstrate beneficial localization
> beyond the `no-consolidation` baseline. That is a publishable negative result
> and the correct trigger to redesign the outcome signal or abandon class B,
> not to iterate until a policy wins.

### Scoring-protocol version

Derived endpoint semantics change, so the scoring protocol is versioned:

- old: `LIS-SCORE-v0.2.0`, hash `3a7bf5eb123ce2904a99c68edcd9e97152fc6e90fc8d2167cdf79b411bbde728`
  (the version under which the development matrix was executed);
- new: `LIS-SCORE-v0.3.0`, hash recorded in `scripts/validate_runs.py` and pinned
  in `tests/test_scoring_protocol_lock.py`.

The **corruption lock is not touched**. Existing development manifests keep the
v0.2.0 hash; revalidated and derived outputs are written beside them carrying
v0.3.0 provenance. Originals are never overwritten.

---

## M3 — Evidence-read ceiling calibration

### Observation that motivated it

Peak development read-ceiling utilisation was **0.962**
(`evidence-reconstruction` and `provenance-regrounding` at E128, all three
seeds), with **zero** exhausted reads anywhere in 210 runs.

### The change

Frozen, mechanism-independent rule applied to confirmatory runs:

```
confirmatory evidence_reads_ceiling = round(1.25 × existing derived ceiling)
```

The existing ceiling remains derived from the lifetime
(`n_probes × reads_per_probe`), never from any arm's measured appetite. The
1.25 factor is triggered solely by aggregate utilisation, is identical across
all arms, and prevents confirmatory truncation at longer or denser lifetimes.

`log_capacity` and `maintenance_ops_ceiling` are unchanged — `log_capacity`
affects eviction and therefore behaviour.

### Required safety property, verified

Raising the ceiling must not change behaviour when the old ceiling was never
reached. Verified across all 210 development arm-cells (9 A001 arms + 5 B001
arms × 3 seeds × 5 horizons) at 1.0× and 1.25×: **zero** differences in metrics,
consolidation metrics, or actual evidence reads. Pinned by regression test.

Development resource counts are **not** retroactively rewritten, and the
development matrix is **not** re-run.

---

## M4 — Matched-control semantics

### Observation that motivated it

`untouched_accuracy_delta` differs across arms within a cell (−0.064 to +0.067
at seed `231368116`, E128) even though the control selection hash is
byte-identical across all five arms in all 15 cells.

This is correct behaviour, not a defect. Controls are excluded when another
outcome implicates them **inside the scoring window**; a control slot may still
have been revised by an earlier outcome outside that window.

### The change

Documentation only. No control identity and no matching rule is altered.

> **Matched-control identity is arm-invariant; matched-control response is not.**
> A matched control is causally and contemporaneously untouched with respect to
> the target outcome's assignment. It is not guaranteed to remain numerically
> unchanged under every arm: broad or collateral revisions from earlier outcomes
> can alter those slots. Arm-dependent change in matched controls is therefore
> itself evidence of collateral state modification, and must not be read as a
> global, arm-independent drift baseline.

The name `untouched_accuracy_delta` is **retained**. Renaming would create
provenance noise across 210 existing manifests for no mechanical gain; the
definition above is carried in the metric docs, the preregistration, and the
manifest schema notes instead.

---

## Scientific-result boundary

M1–M4 repair measurement and reporting. None of them repairs, and none is
permitted to repair, the following development observation, which is a
scientific result rather than a defect:

> At E64 and E128 no arm that spends evidence reads is on the Pareto frontier.
> A zero-read heuristic (`confidence-decay`) dominates `evidence-reconstruction`
> and `provenance-regrounding`, which each spend ~245,000 reads at E128.

A benchmark failing to measure its intended construct is a defect to fix. A
sophisticated mechanism genuinely failing to beat a cheap heuristic is a
finding to report. This amendment addresses only the former.

# EXP-000 — engineering pilot record

**Status: NOT EVIDENCE.** Single seed, no replication, no confidence intervals,
and the generator was still being constructed while these numbers were
produced. Nothing here supports or refutes any hypothesis. This document exists
so that the construction history is auditable and so that the pilot orderings
cannot later be mistaken for findings.

- Date: 2026-09-02
- Seed: `20260902`, 24 epochs, 27 slots
- Corruption lock: `6e890d154d637d826613172a376396cb54f22c420e063125927fd979397b5b40`
- Lifetime spec: `d221464d072c67a8253327391be6568c1860e19fd03bdbd21ecafb2b37bb0af2`
- Budget ceiling: 48000 evidence reads, 422 maintenance ops, 422 log capacity
- Reproduce: `make pilot`

## Purpose

Establish only that: the harness runs; budgets bind; the audit separation holds;
every declared metric can move; and the benchmark sits between floor and
ceiling. All four were confirmed.

## EXP-A001 — drift stream (single seed, not evidence)

| arm | acc | integrity viol. | stale | unsupported | self-contra | provenance | ECE | reads |
|---|---|---|---|---|---|---|---|---|
| `last-write-wins` | 0.633 | 0.133 | 0.133 | 0.000 | 0.000 | 1.00 | 0.162 | 0 |
| `unconstrained-accumulator` | 0.613 | 0.263 | 0.263 | 0.000 | 0.000 | 0.00 | 0.080 | 0 |
| `periodic-reset` | 0.654 | 0.163 | 0.163 | 0.000 | 0.027 | 0.00 | 0.127 | 780 |
| `evidence-reconstruction` | 0.613 | 0.117 | 0.117 | 0.000 | 0.000 | 1.00 | 0.126 | 38080 |
| `provenance-regrounding` | 0.700 | 0.192 | 0.192 | 0.000 | 0.036 | 1.00 | 0.116 | 38080 |
| `confidence-decay` | 0.683 | 0.192 | 0.192 | 0.000 | 0.000 | 0.00 | 0.158 | 0 |
| `contradiction-regrounding` | 0.708 | 0.208 | 0.208 | 0.000 | 0.000 | 1.00 | 0.086 | 32387 |
| `hybrid-symbolic-latent` | 0.729 | 0.158 | 0.158 | 0.000 | 0.000 | 1.00 | 0.126 | 0 |
| `lossy-latent` | 0.600 | 0.279 | 0.246 | 0.058 | 0.021 | 0.00 | 0.050 | 0 |

Observations, all provisional:

- **`last-write-wins` is hard to beat**, echoing the published negative result
  in 2606.22030. Only `evidence-reconstruction` shows a lower integrity
  violation rate, and it spends 38,080 reads to do it against zero.
- **`provenance-regrounding` does not dominate.** The pilot does not reproduce a
  clean provenance advantage on integrity, despite winning on accuracy. This is
  recorded deliberately: it is the outcome least favourable to the track's
  original framing, and it is preserved rather than tuned away.
- Only `lossy-latent` moves `unsupported_belief_rate` off zero. Every other
  reference arm is evidence-derived and cannot confabulate, so the metric is
  structurally zero for them. This is a property of the arms, not a defect.
- Accuracy spans 0.600–0.729 against roughly 0.25 chance: neither ceiling nor
  floor.

## Horizon sweep — integrity violation rate vs lifetime length

| arm | 8 | 16 | 32 | 64 | 128 epochs |
|---|---|---|---|---|---|
| `last-write-wins` | 0.013 | 0.081 | 0.175 | 0.342 | 0.552 |
| `unconstrained-accumulator` | 0.025 | 0.181 | 0.372 | 0.577 | 0.770 |
| `periodic-reset` | 0.025 | 0.156 | 0.200 | 0.333 | 0.499 |
| `evidence-reconstruction` | 0.013 | 0.081 | 0.141 | 0.300 | 0.495 |
| `provenance-regrounding` | 0.025 | 0.156 | 0.228 | 0.381 | 0.547 |
| `confidence-decay` | 0.025 | 0.138 | 0.225 | 0.333 | 0.487 |
| `contradiction-regrounding` | 0.025 | 0.144 | 0.281 | 0.428 | 0.613 |
| `hybrid-symbolic-latent` | 0.013 | 0.075 | 0.206 | 0.394 | 0.602 |
| `lossy-latent` | 0.125 | 0.225 | 0.362 | 0.552 | 0.759 |

At 8 epochs the arms span 0.013–0.125 and are practically indistinguishable. At
128 epochs they span 0.487–0.770, and the ordering has changed: `hybrid-symbolic-latent`
is among the best at 8 epochs and among the worst at 128. This is the pattern
EXP-A001 H2 predicts, on one seed, and it is the single most important thing to
attempt to replicate.

## EXP-B001 — delayed credit stream (single seed, not evidence)

32 delayed outcomes, 5 consulted slots each, lag 3 epochs.

| arm | acc | precision | recall | collateral | culprit Δ | decoy Δ | net repair | reads |
|---|---|---|---|---|---|---|---|---|
| `no-consolidation` | 0.625 | 0.00 | 0.00 | 0.00 | -0.051 | -0.176 | -0.227 | 0 |
| `uniform-blame` | 0.221 | 0.28 | 0.72 | 0.72 | -0.268 | -0.300 | -0.568 | 0 |
| `eligibility-trace` | 0.558 | 0.33 | 0.31 | 0.67 | +0.065 | -0.126 | -0.061 | 0 |
| `provenance-restricted-blame` | 0.517 | 0.18 | 0.09 | 0.82 | +0.036 | -0.220 | -0.184 | 0 |
| `counterfactual-recheck` | 0.708 | 0.14 | 0.06 | 0.86 | +0.051 | +0.030 | +0.081 | 28470 |

Observations, all provisional:

- `uniform-blame` is the clearest demonstration that recall is the wrong
  objective: highest recall (0.72), worst net repair (−0.568), and overall
  accuracy collapsing from 0.625 to 0.221.
- `counterfactual-recheck` is the only arm with positive net repair, and it is
  the only arm that spends reads. It must be presented on a cost frontier.
- `untouched_accuracy_delta` is degenerate at 0 because outcomes consult nearly
  every slot. Logged as a calibration item in the EXP-B001 prereg.

## Defects found and fixed during construction

Recorded because each one silently produced plausible-looking numbers:

1. **Nonce exhaustion.** The two-syllable symbol space held 144 names against
   ~175 required; generation hung in an infinite loop.
2. **Disjoint per-slot vocabularies.** Cross-slot interference was
   unrepresentable, pinning `unsupported_belief_rate` to zero for every arm
   including the bounded-latent one. Fixed by a shared codebook. **This changed
   the arm ordering**, and the change was made because a metric was structurally
   dead, not because of who was winning.
3. **Post-hoc outcome timestamps.** Delayed outcomes were assigned ids and times
   in a final pass using the end-of-lifetime clock, placing every outcome after
   the last probe. All repair and damage deltas were therefore exactly zero
   while looking like a legitimate null result.
4. **Salted string hashing.** `LossyLatent` bucketed slots with `hash()`, which
   Python salts per process, so the same seed gave different results across
   runs. Replaced with `zlib.crc32`; regression test added.
5. **Validator crash on mixed manifests.** Experiment-specific checks ran
   against the wrong manifest schema instead of reporting the mismatch.

Defects 2, 3, and 4 each produced output that looked like a finding. That is the
argument for the validator and for the metric-liveness rule.

## Status of the corruption lock

The corruption process was still being constructed while these numbers were
produced, so this pilot is explicitly *pre-lock*. The lock takes effect at the
commit landing the preregistrations. From that commit, changes require a
numbered amendment with a reason independent of which arm won.

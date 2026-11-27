# Lifetime Integrity

**Working research project:** coherence across interrupted lifetimes — how a
persistent cognitive system stays internally consistent when observations
conflict, beliefs go obsolete, state drifts, and consequences arrive long after
the experience that caused them.

> Status: **pre-results / experiment scaffold.** No empirical claim is made yet.
> The single-seed pilot in [`experiments/EXP-000-PILOT-RECORD.md`](experiments/EXP-000-PILOT-RECORD.md)
> is explicitly not evidence.

## Research question

How can a persistent cognitive system remain coherent over very long lifetimes
when observations conflict, beliefs become obsolete, latent state drifts, and
consequences arrive long after the originating experience?

The ambition is a class of papers about coherence across interrupted lifetimes,
not another memory benchmark. The literature audit is blunt about why: the
memory-benchmark framing is already occupied several times over.

## Two candidate experiment classes

### A — Latent drift and re-grounding

Does persistent state gradually depart from the evidence that is supposed to
support it, and **what does it cost to pull it back?** Long synthetic lifetimes
contain repeated observations, contradictions, misinformation, changing world
state, stale beliefs, long inactivity gaps, context shifts, misleading
repetition, and unequal source reliability.

Nine mechanisms are compared at a matched cost ceiling: last-write-wins, an
unconstrained accumulator, a bounded lossy latent state, periodic reset,
evidence reconstruction, provenance re-grounding, confidence decay,
contradiction-triggered re-grounding, and a hybrid symbolic/latent store.

See [`experiments/EXP-A001-PREREG.md`](experiments/EXP-A001-PREREG.md).

### B — Delayed and offline consolidation

An action at time `t` may not reveal its utility until `t+k`. When a late
failure says *"one of these five beliefs was wrong"* without saying which, can
offline consolidation repair the culprit **without corrupting the four that were
right?** Five credit-assignment rules share one belief substrate so the rule is
the only variable.

See [`experiments/EXP-B001-PREREG.md`](experiments/EXP-B001-PREREG.md).

## What makes this different from a memory benchmark

1. **Integrity is scored separately from accuracy.** Answering the right value
   that nobody ever told you is an integrity failure, not a success. So is
   holding a well-supported belief that is obsolete.
2. **Re-grounding costs are metered and capped.** Every historical evidence
   access goes through a bounded log that charges per record scanned and refuses
   reads past a shared ceiling. Headline results are integrity/cost frontiers,
   not single winners.
3. **Lifetime length is the independent variable.** In the pilot, mechanisms are
   practically indistinguishable at 8 epochs and separate by more than 0.25
   absolute integrity-violation rate at 128. If that replicates, short-horizon
   evaluation is actively misleading about mechanism choice.
4. **The corruption process is locked.** A SHA-256 over every corruption rate is
   carried in each manifest, and the validator rejects comparisons whose arms
   faced different corruption. Rates may not be retuned after seeing who won.

## Architecture-agnostic by design

Nothing here assumes a particular substrate. Any system implementing
`observe / on_gap / on_context_shift / answer / state_bytes` can be scored —
symbolic store, latent vector, or LLM agent.

**This is a hard dependency, not a stylistic choice.** No result from this
repository may be used to claim that a CCS latent architecture is validated.
That requires an admissible substrate established by
[`in-c0/state-promotion`](https://github.com/in-c0/state-promotion) and
subsequent routing work. The benchmark is built to remain useful if that
programme goes nowhere.

## Novelty boundary

The field is crowded and the audit says so plainly. We do **not** claim novelty
for: agent aging or drift over deployment; stale-belief detection; belief drift
across sessions; contradiction resolution or bitemporal provenance; provenance-capped
reliability-conditional updating; offline/sleep consolidation, replay, or
eligibility traces; hindsight credit assignment to memory writes; measuring
collateral damage after targeted revision; or the term *epistemic integrity*.

Four gaps survive the audit, and they are narrow. Read
[`docs/LITERATURE-AUDIT-2026-09-02.md`](docs/LITERATURE-AUDIT-2026-09-02.md)
before writing anything for circulation.

## Reproducibility policy

- Preregister hypotheses, invalidation criteria, and kill criteria before result
  runs.
- Keep pilot, development, and confirmatory phases strictly separate, with
  disjoint seeds.
- **Do not tune benchmark corruption patterns after seeing which method wins.**
- Publish negative results. `last-write-wins` being hard to beat is a finding.
- Treat ceiling effects, floor effects, inert metrics, audit leaks, and unequal
  budgets as invalidating confounds, enforced by the validator.
- Validate before interpreting: `validate_runs.py` never looks at which arm won.
- Record seeds, corruption locks, and complete configs for every result.

## Local gates

```bash
make test
make pilot
make lifetimes
```

`make pilot` runs every reference arm on both streams, writes manifests to
`results/`, and validates them. It exits nonzero if the comparison is invalid.

## Repository layout

```text
src/lifetime_integrity/   generator, mechanisms, consolidation, metrics, harness
experiments/              preregistrations and the non-evidential pilot record
docs/                     literature audit, architecture, metric definitions
scripts/                  generation, pilot orchestration, run validation
tests/                    110 tests covering audit separation and budget enforcement
```

## Status and dependencies

Literature, simulator, hypotheses, and preregistration may proceed now. Claims
about a specific CCS latent substrate may not. Source of truth for execution
order is issue #1.

## License

Apache-2.0.

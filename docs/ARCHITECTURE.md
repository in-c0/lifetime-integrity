# Architecture

## Why the benchmark is architecture-agnostic

This track may not assert that a CCS latent architecture is validated until
State Promotion and later routing work establish an admissible substrate. That
constraint is treated as a design opportunity rather than a delay: LIS-v0 scores
*any* system that can implement a five-method interface, so it is useful whether
or not the CCS programme succeeds.

```text
                 harness (sees everything)
                          |
        +-----------------+------------------+
        |                                    |
   audit view                          visible view
  canonical value                    context / key / value
  truthfulness                       source id + tier
  corruption tag                     options (probes only)
  probe class                        elapsed time, gaps
  responsible slot                          |
        |                                   v
        |                          +--------------------+
        |                          | system under test  |
        |                          +--------------------+
        |                                   |
        |                          Answer(value, confidence, support)
        |                                   |
        +--------------> metrics <----------+
```

The harness counts any audit field appearing in a visible view. A nonzero
`audit_leak_count` invalidates the comparison. This is the same discipline as
State Promotion's held-out-evidence rule, applied to benchmark metadata.

## The contract

```python
class Mechanism(Protocol):
    name: str
    def observe(self, obs: dict) -> None: ...
    def on_gap(self, ev: dict) -> None: ...
    def on_context_shift(self, ev: dict) -> None: ...
    def answer(self, query: dict) -> Answer: ...
    def state_bytes(self) -> int: ...
```

`Answer` carries a value, a confidence, and a tuple of cited evidence ids. The
citation is what makes `provenance_consistency` checkable: a system that answers
correctly while citing evidence saying something else is caught.

A symbolic store, a vector of floats, or an LLM agent with a scratchpad can all
satisfy this. Class B adds `handle_outcome(ev) -> ConsolidationReport`.

## Why evidence access is metered

Re-grounding is not free. A mechanism that stays coherent by re-reading its
entire history has not solved anything a large enough context window would not
also solve. `EvidenceLog` therefore:

- holds a **bounded** record (old evidence is evicted, as in a real lifetime);
- charges every read **per record scanned**, not per record matched;
- refuses reads past the ceiling and records the exhaustion.

This turns "budget-matched" from a claim in a paper into a property the
validator can check. It is the main reason to prefer this harness over scoring
mechanisms informally.

## Modules

| module | role |
|---|---|
| `lifetime.py` | LIS-v0 generator; event types; corruption lock |
| `mechanisms.py` | metered evidence log; nine reference class-A arms |
| `consolidation.py` | shared belief substrate; five class-B credit rules |
| `metrics.py` | integrity metrics; consolidation metrics |
| `harness.py` | run loop, audit enforcement, manifest emission |
| `scripts/validate_runs.py` | comparison validity — never looks at who won |

## Separation of validity from result

`validate_runs.py` answers one question: *is this a fair comparison?* It checks
provenance, corruption-lock agreement, budget parity, audit leaks, ceiling and
floor effects, and metric liveness. It never reads which arm performed better.
Run it first; if it fails, the metrics are debugging output, not results.

## Reproducibility notes

- All randomness flows from one seeded `random.Random`.
- No use of `hash()` on strings anywhere in scoring paths: Python salts it per
  process, and it silently broke reproducibility once already.
- `config_lock_sha256` fingerprints the corruption process; `lifetime_spec_sha256`
  fingerprints the realized event sequence; `source_tree_sha256` fingerprints the
  code. Pilot manifests set `git_commit` to `null` rather than guessing.

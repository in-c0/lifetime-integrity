# Literature audit refresh — 2026-09-03 (Gate F1)

Diff against [`LITERATURE-AUDIT-2026-09-02.md`](LITERATURE-AUDIT-2026-09-02.md),
performed before the Phase-3 preregistration freeze as required by issue #1.

**Verdict: NO NOVELTY BLOCKER.** No new work materially occupies G1–G4.
**But three of the four gaps required narrowing**, and the previous audit
under-sampled the field: 14 directly relevant records it never cited are added
below. G4 is unchanged and intact.

Same evidentiary standard as the original: every record verified against its
arXiv entry (API or `arxiv.org/abs` page), never from search-result summaries.

## 1. Re-verification of the 2026-09-02 citations

All 20 rechecked records still exist with the recorded identifiers and titles.

| finding | detail |
|---|---|
| version changes | **1**: HiMPO `2606.16285` v1 → **v2**, revised 2026-09-01 |
| withdrawals / retitles | none |
| transient API failures | `2605.26099`, `2605.05965` initially failed to return; both re-fetched and confirmed unchanged (v3 / v1). Recorded because a failed fetch must not be silently read as a withdrawal. |

**HiMPO v2 reviewed specifically.** Still a policy-optimization method, not a
benchmark. It does not attribute an ambiguous delayed outcome across several
jointly consulted beliefs, does not measure collateral damage to innocent
beliefs, and uses no inaction baseline. **G4 unaffected.**

## 2. Records the previous audit missed

Verified today; none was cited on 2026-09-02.

| id | date | work | bears on |
|---|---|---|---|
| [2511.14937](https://arxiv.org/abs/2511.14937) | 2025-11-18 | Mireshghallah et al., *CIMemories: Compositional Benchmark for Contextual Integrity of Persistent Memory* | integrity (privacy sense) |
| [2602.01146](https://arxiv.org/abs/2602.01146) | 2026-02-01 | Pulipaka et al., *PersistBench: When Should Long-Term Memories Be Forgotten?* | staleness |
| [2602.19320](https://arxiv.org/abs/2602.19320) | 2026-02-22 | Jiang et al., *Anatomy of Agentic Memory* | G1, G3 |
| [2602.22769](https://arxiv.org/abs/2602.22769) | 2026-02-26 | Zhao et al., *AMA-Bench: Long-Horizon Memory for Agentic Applications* | **G2** |
| [2603.07670](https://arxiv.org/abs/2603.07670) | 2026-03-08 | Du et al., *Memory for Autonomous LLM Agents* | survey |
| [2603.19532](https://arxiv.org/abs/2603.19532) | 2026-03-20 | Tamo et al., *EvidenceRL: Reinforcing Evidence Consistency* | **G3** |
| [2603.25001](https://arxiv.org/abs/2603.25001) | 2026-03-26 | In et al., *Rethinking Failure Attribution in Multi-Agent Systems* | G4-adjacent |
| [2604.08401](https://arxiv.org/abs/2604.08401) | 2026-04-09 | Yuan et al., *Verify Before You Commit* (SAVeR) | **G3**, G4-adjacent |
| [2605.20061](https://arxiv.org/abs/2605.20061) | 2026-05-19 | Tang et al., *Rewarding Beliefs, Not Actions* (ReBel) | **G4-adjacent** |
| [2605.30771](https://arxiv.org/abs/2605.30771) | 2026-05-29 | Joshi, *Eywa: Provenance-Grounded Long-Term Memory* | G1, G3 |
| [2606.04990](https://arxiv.org/abs/2606.04990) | 2026-06-03 | Wang et al., *From Agent Traces to Trust* (survey) | G3 |
| [2606.06448](https://arxiv.org/abs/2606.06448) | 2026-06-04 | Omri et al., *Agent Memory: Characterization and System Implications* | cost profiling |
| [2606.24775](https://arxiv.org/abs/2606.24775) | 2026-06-23 | Zhou et al., *Are We Ready For An Agent-Native Memory System?* | **G1** |
| [2606.30850](https://arxiv.org/abs/2606.30850) | 2026-06-29 | Samanta et al., *BayesBench: LLM Belief Trajectories* | belief updating |

That the first audit missed fourteen relevant records is itself a finding: the
one-per-month estimate of competing output was too low, and the re-audit cadence
should be tightened.

## 3. Gap-by-gap re-evaluation

### G1 — fixed corruption + enforced matched-cost maintenance comparison → **NARROWED, survives**

The threat is **2606.24775**, which evaluates 12 memory systems over 5 workloads
and 11 datasets, explicitly decomposes a **maintenance** module, reports
**cost-performance trade-offs**, and concludes that "localized maintenance is
more cost-efficient". **2606.06448** independently profiles agent-memory cost
across construction/retrieval/generation phases.

So "nobody examines maintenance cost" is **no longer true and must not be
claimed.** What neither does: enforce an *equal, metered* cost ceiling across
the compared mechanisms, hold a *locked* corruption process constant, or compare
maintenance *policies* at parity rather than whole *systems* on natural
workloads.

**Narrowed G1:** an enforced, metered, equal evidence-read ceiling across
maintenance policies under a locked corruption process, yielding an
integrity/cost frontier rather than a system leaderboard.

### G2 — lifetime length as an independent variable → **NARROWED, survives**

**AMA-Bench (2602.22769)** provides synthetic trajectories that "scale to
arbitrary horizons"; **AgingBench (2605.26302)** spans 8–200 sessions; **The
Horizon Gap (2608.06663)** catalogues horizon-linked failure classes.

So "longer horizons are harder, and nobody varies horizon" is **not claimable.**
What is absent everywhere: horizon used to test whether the *ranking of
mechanisms* is stable — a falsifiable rank-correlation diagnostic whose failure
would invalidate short-horizon evaluation as a mechanism-selection method.

**Narrowed G2:** mechanism-ranking *instability* across horizon as a
preregistered, falsifiable diagnostic (H2), not "long horizons degrade agents".

### G3 — integrity metrics independent of correctness → **NARROWED, survives**

**EvidenceRL (2603.19532)** scores grounding (entailment with retrieved
evidence) separately from correctness. **SAVeR (2604.08401)** motivates itself
on "unsupported beliefs repeatedly stored and propagated". **Eywa (2605.30771)**
separates immutable source evidence from derived beliefs for audit and repair.
**2606.04990** catalogues provenance-accuracy and temporal-consistency metrics
as *proposed*.

So "separating grounding from correctness is new" is **false and must not be
claimed.** But EvidenceRL is single-turn RAG grounding against *retrieved
documents at answer time*; SAVeR audits within a trajectory before commitment;
Eywa is a proposed system without correctness-independent scoring.

**Narrowed G3:** correctness-independent integrity of *persistent state across a
lifetime* — an answer that is canonical yet supported by nothing the system was
ever told counts as a failure — combining unsupported-belief rate,
self-contradiction without intervening evidence, and provenance consistency.

### G4 — ambiguous delayed blame onto persistent belief state with collateral scoring → **INTACT**

Closest new work, both examined in full:

- **ReBel (2605.20061)** — RL for long-horizon agents, explicitly framing that
  "delayed rewards obscure the causal impact of intermediate decisions" for
  belief states. But it is a policy-optimization algorithm using
  belief-consistency supervision; no ambiguous multi-belief attribution, no
  collateral-damage measurement, no inaction baseline.
- **SAVeR (2604.08401)** — repairs beliefs via "constraint-guided minimal
  interventions", but triggered by within-trajectory self-audit *before* action
  commitment, localizing violations directly rather than from an ambiguous
  delayed signal, and without quantifying collateral damage.
- **2603.25001** — failure attribution to *agents and steps* in multi-agent
  trajectories, not to persistent beliefs.

None asks: when a late failure says "one of these five beliefs you consulted was
wrong" without saying which, can consolidation repair the culprit without
corrupting the four that were right? **G4 stands unchanged**, and is now the
strongest of the four.

## 4. Additions to the locked non-novelty list

Appended to the nine items of 2026-09-02:

11. **Not novel:** examining the cost of memory maintenance, or reporting
    cost-performance trade-offs across memory systems (2606.24775, 2606.06448).
12. **Not novel:** benchmarks that scale to arbitrary or very long horizons
    (2602.22769, 2605.26302).
13. **Not novel:** scoring evidence-grounding separately from answer correctness
    (2603.19532), or provenance-grounded memory with audit and repair
    (2605.30771, 2606.04990).
14. **Not novel:** repairing a belief via localized minimal intervention to avoid
    disturbing unrelated reasoning (2604.08401).
15. **Not novel:** framing delayed reward as obscuring which intermediate belief
    was at fault (2605.20061).

## 5. Effect on the benchmark

**None.** Per the gate instruction, benchmark results and novelty are separate
questions. No corruption rate, mechanism, metric, seed, horizon, or threshold is
changed by this audit. The only changes are to what may be *claimed*.

## 6. Re-audit cadence

Raised from "before each lock" to **before each lock and before each submission,
with a keyword sweep at least monthly** — justified by having missed fourteen
records in a single prior pass.

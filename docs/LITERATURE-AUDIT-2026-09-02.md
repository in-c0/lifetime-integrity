# Literature audit — 2026-09-02

Performed before locking any novelty claim, as required by the track charter.

**Headline finding: the space is crowded, and the obvious framing is already taken.**
"A benchmark for stale beliefs / contradiction / belief revision in long-lived
agents" has been published at least five times in the last six months. This
track cannot be another memory benchmark. What is *not* taken is narrower than
the original brief assumed, and Section 4 states it precisely.

## 1. Method

Search over arXiv, ACL Anthology, and vendor research blogs for: long-term agent
memory benchmarks; stale/obsolete belief detection; knowledge conflict and
source reliability; provenance-governed memory writes; longitudinal agent
degradation; representation drift in continual learning; sleep/offline
consolidation; delayed credit assignment; knowledge-editing locality.

Every arXiv entry below was verified through the arXiv API — identifier, exact
title, first author, and submission date — rather than taken from search-result
summaries, several of which misreported titles. Two of the papers surfaced under
wrong titles by third-party aggregators; the verified titles are used here.

## 2. What is already established

### 2.1 Long-horizon memory benchmarks

| id | date | work |
|---|---|---|
| [2402.17753](https://arxiv.org/abs/2402.17753) | 2024-02-27 | Maharana et al., *Evaluating Very Long-Term Conversational Memory of LLM Agents* (LoCoMo) |
| [2410.10813](https://arxiv.org/abs/2410.10813) | 2024-10-14 | Wu et al., *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory* |
| [2512.13564](https://arxiv.org/abs/2512.13564) | 2025-12-15 | Hu et al., *Memory in the Age of AI Agents* |
| [2602.06052](https://arxiv.org/abs/2602.06052) | 2026-01-14 | Huang et al., *A Survey of Agent Memory in the Second Half* |
| — | 2026-05-19 | Microsoft, [STATE-Bench](https://opensource.microsoft.com/blog/2026/05/19/introducing-state-bench-a-benchmark-for-ai-agent-memory/) |

LongMemEval already includes a *knowledge updates* and an *abstention* track.
Recall-style long-term memory evaluation is saturated.

### 2.2 Stale beliefs, contradiction, and belief revision

| id | date | work |
|---|---|---|
| [2603.23848](https://arxiv.org/abs/2603.23848) | 2026-03-25 | Myakala et al., *BeliefShift: Benchmarking Temporal Belief Consistency and Opinion Drift in LLM Agents* |
| [2604.04202](https://arxiv.org/abs/2604.04202) | 2026-04-05 | Ji et al., *ClawArena: Benchmarking AI Agents in Evolving Information Environments* |
| [2605.06527](https://arxiv.org/abs/2605.06527) | 2026-05-07 | Chao et al., *STALE: Can LLM Agents Know When Their Memories Are No Longer Valid?* |
| [2605.30219](https://arxiv.org/abs/2605.30219) | 2026-05-28 | Xu et al., *When Should Models Change Their Minds? Contextual Belief Management* (BeliefTrack) |
| [2606.06240](https://arxiv.org/abs/2606.06240) | 2026-06-04 | Wang, *TOKI: A Bitemporal Operator Algebra for Contradiction Resolution in LLM-Agent Persistent Memory* |
| [2408.12076](https://arxiv.org/abs/2408.12076) | 2024-08-22 | Su et al., *ConflictBank* |

This is the densest cluster. **STALE** covers detecting that a belief is
outdated, including implicit invalidation. **BeliefShift** covers drift and
evidence-driven revision across sessions. **BeliefTrack** is a closed-world
symbolic benchmark with exact turn-level belief scoring — architecturally the
nearest neighbour to what this track proposed to build. **ClawArena** covers
multi-source conflict plus dynamic revision in an evolving environment. **TOKI**
formalizes contradiction resolution as write-time concurrency control with
provenance-preserving audit rows.

### 2.3 Provenance, source reliability, and write-time governance

| id | date | work |
|---|---|---|
| [2603.11768](https://arxiv.org/abs/2603.11768) | 2026-03-12 | Lam et al., *Governing Evolving Memory in LLM Agents* (SSGM) |
| [2605.11325](https://arxiv.org/abs/2605.11325) | 2026-05-11 | Flynt, *Structured Belief State and the First Precision-Aware Benchmark for LLM Memory Retrieval* |
| [2605.01847](https://arxiv.org/abs/2605.01847) | 2026-05-03 | Jia, *NeuroState-Bench: Commitment Integrity in LLM Agent Profiles* |
| [2606.22030](https://arxiv.org/abs/2606.22030) | 2026-06-20 | Singh, *When Does Belief-Based Agent Memory Help? Reliability-Conditional Updating and Provenance-Capped Poisoning Defense* |
| [2607.10526](https://arxiv.org/abs/2607.10526) | 2026-07-12 | Mao et al., *Agents Don't Just Agree, They Remember* (PASB) |
| [2607.23929](https://arxiv.org/abs/2607.23929) | 2026-07-27 | Li et al., *MemTX: Transactional Belief Commit for Stateful Agent Memory* |

**2606.22030 is the single closest paper to candidate class A** and must be
treated as the primary novelty threat. It already: estimates per-observation
reliability, shows Bayesian belief updating is worth little against
last-write-wins on benchmarks lacking conflicting evidence, introduces a
controlled contradiction benchmark where it does pay, and proposes
provenance-capped trust. "Provenance-based re-grounding beats naive
accumulation under source-reliability differences" is therefore **already a
published result**, not an open question.

Its negative result is also a direct warning about our own pilot: on
conversational recall, principled belief machinery ≈ last-write-wins. Our pilot
reproduced the same pattern (see `experiments/EXP-000-PILOT-RECORD.md`).

### 2.4 Longitudinal degradation over deployed lifetimes

| id | date | work |
|---|---|---|
| [2605.26302](https://arxiv.org/abs/2605.26302) | 2026-05-25 | Zhu et al., *Your Agents Are Aging Too: Agent Lifespan Engineering* (AgingBench) |
| [2605.28108](https://arxiv.org/abs/2605.28108) | 2026-05-27 | Wu et al., *Ask Now, Use Later: Benchmarking the Proactivity Gap in Long-Lived LLM Agents* |
| [2606.04017](https://arxiv.org/abs/2606.04017) | 2026-06-01 | Shen, *Neither Layer Alone: Epistemic Integrity Requires Hierarchical Joint Design for Long-Running AI Agents* |
| [2606.30306](https://arxiv.org/abs/2606.30306) | 2026-06-29 | Ding et al., *Always-On Agents: A Survey of Persistent Memory, State, and Governance* |
| [2608.06663](https://arxiv.org/abs/2608.06663) | 2026-08-07 | Chen et al., *The Horizon Gap* |

**AgingBench is the second primary novelty threat.** It runs 8–200 sessions
across 14 models and ~400 runs, and organizes degradation into compression,
interference, revision, and maintenance aging. "Agents degrade over long
deployment, and the degradation has distinguishable forms" is published. Note
also that 2606.04017 already uses the exact phrase *epistemic integrity* for
long-running agents.

### 2.5 Representation and latent drift in continual learning

| id | date | work |
|---|---|---|
| [2511.22615](https://arxiv.org/abs/2511.22615) | 2025-11-27 | Theofilou et al., *Stable-Drift: Patient-Aware Latent Drift Replay* |
| [2512.22045](https://arxiv.org/abs/2512.22045) | 2025-12-26 | van der Veldt et al., *Learning continually with representational drift* |
| [2602.19655](https://arxiv.org/abs/2602.19655) | 2026-02-23 | Subramanian, *Representation Stability in a Minimal Continual Learning Agent* |

2602.19655 already studies a persistent state vector across executions,
measures drift by cosine similarity, perturbs it, and observes recovery — a
minimal version of candidate class A's core loop.

### 2.6 Offline consolidation and complementary learning systems

| id | date | work |
|---|---|---|
| [2501.00663](https://arxiv.org/abs/2501.00663) | 2024-12-31 | Behrouz et al., *Titans: Learning to Memorize at Test Time* |
| [2604.20943](https://arxiv.org/abs/2604.20943) | 2026-04-22 | Shinde, *SCM: Sleep-Consolidated Memory with Algorithmic Forgetting* |
| [2605.05097](https://arxiv.org/abs/2605.05097) | 2026-05-06 | Pattichis & Dovrolis, *Continual Knowledge Updating Through Multi-Timescale Memory Dynamics* |
| [2605.26099](https://arxiv.org/abs/2605.26099) | 2026-05-25 | Lee et al., *Do Language Models Need Sleep? Offline Recurrence for Improved Online Inference* |
| [2606.03979](https://arxiv.org/abs/2606.03979) | 2026-06-02 | Behrouz et al., *Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories* |
| [2604.20300](https://arxiv.org/abs/2604.20300) | 2026-04-22 | Gu et al., *FSFM: Selective Forgetting of Agent Memory* |

Offline consolidation as a mechanism is established and actively developed by
strong groups. We claim nothing about consolidation *per se*.

### 2.7 Delayed credit assignment

| id | date | work |
|---|---|---|
| [2512.12818](https://arxiv.org/abs/2512.12818) | 2025-12-14 | Latimer et al., *Hindsight is 20/20: Agent Memory that Retains, Recalls, and Reflects* |
| [2605.05965](https://arxiv.org/abs/2605.05965) | 2026-05-07 | Mou et al., *Beyond Uniform Credit Assignment: Selective Eligibility Traces for RLVR* |
| [2606.16285](https://arxiv.org/abs/2606.16285) | 2026-06-15 | Yan et al., *HiMPO: Hindsight-Informed Memory Policy Optimization* |
| [2601.15086](https://arxiv.org/abs/2601.15086) | 2026-01-21 | Shchendrigin et al., *Memory Retention Is Not Enough to Master Memory Tasks in RL* |

**HiMPO is the primary novelty threat to candidate class B.** It already
assigns less-entangled credit to memory-writing actions, uses hindsight
relevance as a retrospective filter, and reports improved *attribution fidelity*
plus reduced blame leakage from tool-induced errors.

### 2.8 Collateral damage from targeted revision

| id | date | work |
|---|---|---|
| [2307.12976](https://arxiv.org/abs/2307.12976) | 2023-07-24 | Cohen et al., *Evaluating the Ripple Effects of Knowledge Editing* (RippleEdits) |
| [2305.14795](https://arxiv.org/abs/2305.14795) | 2023-05-24 | Zhong et al., *MQuAKE* |

Locality/specificity — "did the edit damage unrelated knowledge" — is a solved
*measurement* problem in knowledge editing. We inherit it; we do not invent it.

## 3. Claims this track may not make

Locked, and binding on every paper from this repository:

1. **Not novel:** that persistent agents drift, age, or degrade over long deployment (2605.26302).
2. **Not novel:** that stored beliefs go stale and that agents fail to notice (2605.06527, 2603.23848).
3. **Not novel:** contradiction resolution, bitemporal versioning, or provenance-preserving audit of belief writes (2606.06240, 2607.23929).
4. **Not novel:** that source reliability and provenance-capped trust improve belief updating under conflicting evidence (2606.22030).
5. **Not novel:** offline/sleep consolidation, replay, complementary learning systems, or eligibility traces (2606.03979, 2604.20943, 2605.05965).
6. **Not novel:** hindsight credit assignment to memory-writing actions (2606.16285).
7. **Not novel:** measuring collateral damage to unrelated knowledge after targeted revision (2307.12976, 2305.14795).
8. **Not novel:** the term *epistemic integrity* for long-running agents (2606.04017).
9. **Not novel:** closed-world symbolic belief benchmarks with exact turn-level scoring (2605.30219).

Any draft asserting one of these as a contribution is defective and must be
rewritten before circulation.

## 4. The residual gap

Four gaps survive the audit. They are narrow, and that is the honest position.

**G1 — Nobody holds the corruption process fixed and compares maintenance
mechanisms at a matched cost ceiling.** Every work in §2.2–§2.4 proposes one
mechanism and compares it to generic baselines, usually without normalizing what
the mechanism is allowed to *spend* on staying coherent. Re-grounding is not
free: it costs evidence reads, maintenance operations, and state. An integrity
result at unbounded re-grounding cost is not a result. LIS-v0 meters every
historical evidence access through a shared, enforced ceiling, which makes an
integrity/cost frontier measurable rather than asserted.

**G2 — Lifetime length is not treated as the independent variable.** AgingBench
spans 8–200 sessions but reports diagnostic profiles and repair targets, not
per-mechanism integrity-versus-horizon scaling at matched cost. Our pilot sweep
(8→128 epochs) shows the mechanisms are nearly indistinguishable at short
horizons and separate by >0.25 absolute integrity-violation rate at long ones.
If that survives replication, *short-horizon evaluation is actively misleading
about mechanism choice*, which is a claim about methodology, not about a method.

**G3 — Integrity is measured as accuracy almost everywhere.** A system that
answers correctly with a belief nothing ever told it has failed, and no
benchmark in §2 scores that as a failure. `unsupported_belief_rate`,
`provenance_consistency`, and `self_contradiction_rate` fire independently of
correctness. In our pilot only the bounded-latent arm moves them off zero, which
is the intended discrimination: these metrics exist to catch latent
confabulation that accuracy hides.

**G4 — Delayed credit onto belief state, scored for collateral damage.** HiMPO
assigns credit to memory-*writing actions* to optimize a policy; MemTX repairs
derived state from an *explicit* retraction. Neither asks: when a late failure
says "one of the five things you believed was wrong" without saying which, can
offline consolidation localize the error without corrupting the four that were
right? Our pilot separates arms sharply on exactly this — uniform blame achieves
0.72 attribution recall while destroying overall accuracy (0.63→0.22), and
counterfactual recheck is the only arm with positive net repair.

## 5. Consequences for the experiment designs

1. Both preregistrations carry an explicit non-novelty section reproducing §3.
2. Class A is positioned as a **cost-matched mechanism comparison and scaling
   study**, not as a stale-belief benchmark. Framing it as the latter is
   pre-empted by STALE and BeliefShift.
3. Class B is positioned around **collateral damage under ambiguous delayed
   blame**, not around consolidation or hindsight credit as mechanisms.
4. `provenance-regrounding` is a **baseline**, not a proposed method: 2606.22030
   already published that result. Our pilot in fact does not reproduce a clean
   provenance advantage, which is worth reporting either way.
5. The last-write-wins baseline must be reported prominently. 2606.22030 found
   it hard to beat; so did we. Suppressing it would be the most likely way for
   this track to produce a misleading result.
6. Comparison against AgingBench and BeliefTrack is mandatory in any write-up.

## 6. Re-audit schedule

This field is moving at roughly one directly competing paper per month. Re-run
this audit before each preregistration lock and before any submission. Record
the date and the diff.

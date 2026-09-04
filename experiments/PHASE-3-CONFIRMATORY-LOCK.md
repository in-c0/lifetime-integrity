# Phase-3 confirmatory lock

**STATUS: FROZEN BEFORE CONFIRMATORY.**

**No confirmatory result had been generated or inspected at freeze time.** No
confirmatory lifetime had been materialized, and no property of any confirmatory
seed's lifetime had been examined. The 12 seeds below are integers produced by a
committed rule; nothing derived from them was looked at before this lock.

Date: 2026-09-03.

## 1. Gates closed

| gate | outcome |
|---|---|
| **F1** literature refresh | **NO NOVELTY BLOCKER.** G4 intact; G1/G2/G3 narrowed. 14 previously-missed records added. `docs/LITERATURE-AUDIT-2026-09-03.md` |
| **F2** B001 endpoint contradiction | Resolved. H1/H2/H3 rewritten onto `excess_net_repair` (erratum E1). One definition of repair success. |
| **F3** statistical ambiguity | Resolved. Estimator, bootstrap, multiplicity tiers and sample size frozen (erratum E2). |

## 2. Document hashes (SHA-256)

| artifact | hash |
|---|---|
| `experiments/EXP-A001-PREREG.md` | `424f47d7bfa8b283cfe5871606c5c68cad02e99a32fed7d5944e1ea65c93ea31` |
| `experiments/EXP-B001-PREREG.md` | `d37b8361004a1e238f7d949b0f579b32b5b26d5484e158999009af1127fba919` |
| `experiments/PHASE-2-AMENDMENT-001.md` | `649a9cb01331ae27bf1a3ed79bb2c4e88453949e34a9bed0d27f139a57541089` |
| `docs/LITERATURE-AUDIT-2026-09-03.md` | `e05b2f14d00010181327f4eec640f429ca6ad7f0c039864ac0c595f0a3ec35ed` |
| `docs/LITERATURE-AUDIT-2026-09-02.md` | `2d4b997339a576d9c7bb3c79afafa37b9cd1da6b7dd88938c7e7248e2bb08b50` |
| `scripts/validate_runs.py` (validator) | `88987c40ee6a604bb1f8e01b8a9655b87ddbaf2131b2b756230a272692a2fc68` |
| `src/lifetime_integrity/seeds.py` | `03f6a19da1484f100a714813e1ff26d63efb59bde50df6774ca4c8f19aeb9368` |

Errata E1 (B001 endpoint consistency) and E2 (statistical specification) are
carried inside the two preregistration documents and are covered by their hashes.

## 3. Benchmark and scoring identity

| item | value |
|---|---|
| generator version | `LIS-v0.1.0` |
| **corruption process** (seed-independent) | `0ebb3e60633de4a4e748c2a474c210927d8026265c86e0786555836bfb4201f4` |
| scoring protocol version | `LIS-SCORE-v0.3.0` |
| scoring protocol SHA-256 (k=3) | `c001a916c4ceb05ec02735c1f2f8066bc81b5d035beab2821657bdb1d9a0a7df` |
| matched-control version | `matched-contemporaneous-v1` |
| causal endpoint version | `excess-net-repair-v1` |
| window `k` | **3** |
| control-selection salt | `""` (default; non-default rejected) |
| validator protocol version | `phase3-confirmatory-lock` |
| source-tree SHA-256 at freeze | `283cb026b7a4554abce71978e1f42a29c99e71d5996f2391e473cffe4f96b46c` |

**Note on the corruption lock.** `LifetimeConfig.config_lock()` includes the seed
field, so it is a *per-seed* fingerprint; the historical value `6e890d15…` is the
lock for seed `20260902`. The seed-independent corruption-process hash above is
the invariant that must not change, and it is identical across all pilot,
development and confirmatory seeds. The corruption process is **unchanged since
`eb8547c`**; `src/lifetime_integrity/lifetime.py` is byte-identical to that commit.

## 4. Resource rules

| item | rule |
|---|---|
| evidence-read ceiling | `round(1.25 × n_probes × 200)` = **2500 × epochs** — 20,000 / 40,000 / 80,000 / 160,000 / 320,000 |
| ceiling multiplier | `CONFIRMATORY_READ_CEILING_MULTIPLIER = 1.25` |
| maintenance-op ceiling | `n_asserts` (unchanged) |
| log capacity | `max(256, n_asserts)` (**unchanged** — governs eviction, hence behaviour) |
| horizon ladder | **{8, 16, 32, 64, 128}** |

Verified across all 210 development arm-cells that ceiling magnitude is inert
before exhaustion, so the 1.25× is a safety margin and not a performance change.

## 5. The 12 confirmatory seeds

Rule (committed in `src/lifetime_integrity/seeds.py`):
`seed_i = int.from_bytes(sha256(f"lifetime-integrity/confirmatory/v1/{i}").digest()[:4],"big") & 0x7FFFFFFF`,
taking the first 12 admissible values, excluding pilot `{20260902, 20260903}` and
development `{231368116, 1043567494, 1443029309}`.

| # | seed | per-seed `config_lock_sha256` |
|---|---|---|
| 0 | `1792867178` | `e899147c59b6b7fb827a0bfa1f2c8b8e2b642b1837910d8ce4c063caac101916` |
| 1 | `2140240615` | `1f4d108d7ce5ad2305e67a049849623390a3ecaeced9c7f62c0875027ef6c088` |
| 2 | `238245273` | `804f434bdafdc0f31caa9159235a859510f803edc88d3f0151cf48580072608b` |
| 3 | `47376287` | `ba9205735d89efc97ac781a398de69047194df65e99ec9f2ae583ff19886b03a` |
| 4 | `1175348042` | `b26d6a16c3eb7500afcecc1850dba936baf0e3c49a20f973c607ff6bd4fa31a8` |
| 5 | `1276344165` | `ca56832743123722b779fec62a58fcec2de7e26a85a0e6c27748fc3502e62d1a` |
| 6 | `141418605` | `d8137cbe2af8f334b8b150463b3f3d3c37cf49e3cb6b8ca90bee76827716fc6c` |
| 7 | `225668972` | `3bbb8c893dc17d76c63c0ebf23fbaed815f4e16ae56405f632d809e85e8aae33` |
| 8 | `1257774472` | `b3fe23bd7319b1d8f6904f13f7f717dea6b2e110b46f6c1d5f477ff440b7cc8d` |
| 9 | `1717315326` | `206ac59982e41568190fded63fc5b8baec2aa8168bf0963a689dda01018f9af3` |
| 10 | `812421351` | `eb4a911b40e347b522e1ee73f0c4ae661d7679a94babffe756ffc6ff99c7144d` |
| 11 | `58640242` | `749c61aad65dbbef56dcabd1303560f58ad31eb1646b988212b5c45887339400` |

Pinned in `tests/test_seeds.py`. The validator rejects a confirmatory run on any
other seed, and rejects a pilot/development run squatting on one of these.

## 6. Bootstrap procedure (frozen)

- resampling unit: **lifetime seed**; arms stay paired within a resampled seed;
- horizons analysed separately, never resampled;
- **10,000** replicates; **percentile** two-sided 95% interval;
- RNG: `numpy.random.default_rng(int.from_bytes(sha256(f"lifetime-integrity/bootstrap/v1/{experiment}/{claim}/{horizon}").digest()[:4],"big"))`;
- ties: frozen average-rank treatment;
- undefined replicates dropped and counted; >5% dropped ⇒ interval reported unreliable.

## 7. Claim tiers

**Primary confirmatory** — Holm–Bonferroni across P1–P3, family-wise α = 0.05:

| # | experiment | claim | test |
|---|---|---|---|
| P1 | A001 | H2 | mean Spearman ρ(E8, E128) over 12 seeds; success iff mean ρ < 0.6 **and** 95% CI excludes 1.0 |
| P2 | A001 | H1 | paired `integrity_violation_rate`, best re-grounding arm vs `unconstrained-accumulator`, at **E128** |
| P3 | B001 | H1 | paired `excess_net_repair`, `counterfactual-recheck`, at **E64** |

**Secondary confirmatory** (Holm within family, never headline alone): A001 H3;
B001 H2 and H3; `excess_net_repair` for other active policies; H1 at other horizons.

**Descriptive / exploratory** (no inferential claim): canonical accuracy,
abstention, raw `net_repair`, `untouched_accuracy_delta`, matched-control
coverage, attribution precision/recall, collateral revision rate, culprit/decoy
deltas, provenance consistency, unattributed answers, calibration (ECE, Brier),
recovery, drift slope, per-probe-class breakdowns, all resource counters.

**Integrity/cost and repair/cost frontiers are the headline outputs.**

## 8. Environment

| item | value |
|---|---|
| Python | `3.14.6` |
| platform | `macOS-15.6-arm64-arm-64bit-Mach-O` (`arm64`) |
| numpy | `2.5.2` |
| pytest | `9.1.1` |
| ruff | `0.16.5` |

Full frozen environment (`pip freeze`, gate-relevant packages):

```text
iniconfig==2.3.0
numpy==2.5.2
packaging==26.3
pluggy==1.6.0
pytest==9.1.1
ruff==0.16.5
```

Runtime dependency is numpy only; pytest and ruff are the engineering gate.

## 9. Execution SHA

The confirmatory matrix executes from the **post-merge `main`** tree. The exact
execution commit is recorded in §10 and stamped into every manifest as
`git_commit`. **No substantive change is permitted between this freeze and the
execution SHA** — only the merge itself and this document's completion.

Runner: `scripts/run_confirmatory.py`, one shot, 12 seeds × 5 horizons ×
(9 A001 arms + 5 B001 arms) = **120 cells / 1,680 runs**.

Reveal order enforced by the runner: raw manifests → structural validity →
claim-scoped validity → only then performance metrics.

## 10. Execution record

- freeze commit: recorded on merge (see issue #1 / PR #2)
- execution commit: `git_commit` in every confirmatory manifest
- gate at freeze: **143 passed**, `ruff check .` clean, working tree clean

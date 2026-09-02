# Phase 2 development lock

**Status:** frozen before the first Phase-2 development run.

This file fixes the development-only seed set and execution order. Development
results may be used only for the calibration actions allowed by issue #1:
ceiling/floor checks, metric liveness, horizon-ladder calibration, read-ceiling
calibration, and repair of mechanical defects. They are not confirmatory.

## Development seeds

The three seeds are:

- `231368116`
- `1043567494`
- `1443029309`

They were derived before any development result was inspected by taking the
first eight bytes of SHA-256(`lifetime-integrity-development-v1:<i>`), for
`i = 0,1,2`, interpreting as an unsigned big-endian integer, then reducing
modulo 2,000,000,000.

These seeds are permanently reserved for development and must not be reused in
confirmatory work.

## Horizon ladder

Both EXP-A001 and EXP-B001 run the locked ladder:

`{8, 16, 32, 64, 128}` epochs.

The runner validates each seed × horizon comparison across all arms before
adding it to any summary. A failed comparison remains debugging output and may
only trigger a Phase-2 calibration action permitted by issue #1.

## Locks carried into development

- LIS corruption-process lock remains the lock established at
  `eb8547c4c9577d318901ce84e94c62972c9c2f37`; no corruption rate changes are
  authorized by the matched-control repair.
- EXP-B001 scoring uses `LIS-SCORE-v0.2.0` and
  `matched-contemporaneous-v1`.
- Development manifests must record the exact git commit and are rejected by
  the validator if it is absent or differs across arms.
- No confirmatory seed selection is made here.

## Interpretation discipline

Development outcomes can falsify feasibility or expose calibration defects, but
must not be described as confirmatory evidence. In particular, preserve
`last-write-wins` and `provenance-regrounding` negative outcomes if they persist,
and apply the existing class kill criteria without tuning toward a preferred
winner.

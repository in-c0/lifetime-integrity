# Generated lifetimes

LIS-v0 lifetimes are generated deterministically rather than committed as opaque
data blobs.

```bash
python scripts/generate_lifetimes.py --seed 20260902
```

The command prints a `config_lock_sha256` (the corruption process) and a
`lifetime_spec_sha256` (the realized event sequence). Every run manifest must
carry both, and `scripts/validate_runs.py` rejects a comparison whose arms
disagree on either.

Written JSONL **includes harness-only audit fields** (canonical values,
truthfulness flags, corruption tags, responsible slots). These files are for
inspection and scoring. Never feed them to a system under test directly — use
the harness, which passes only `visible()` views and counts any leak.

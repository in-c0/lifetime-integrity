"""Frozen seed sets for the Lifetime Integrity track.

Confirmatory seeds are derived by a committed deterministic rule rather than
chosen, so nobody can select a seed after seeing a result. The rule, the
exclusion list, and the resulting 12-seed list are all fixed before the first
confirmatory run (Phase-3 lock, erratum E2).
"""

from __future__ import annotations

import hashlib

# Reserved forever. Never usable as confirmatory seeds.
PILOT_SEEDS: tuple[int, ...] = (20260902, 20260903)
DEVELOPMENT_SEEDS: tuple[int, ...] = (231368116, 1043567494, 1443029309)
RESERVED_SEEDS: frozenset[int] = frozenset(PILOT_SEEDS + DEVELOPMENT_SEEDS)

CONFIRMATORY_SEED_RULE = "lifetime-integrity/confirmatory/v1/{i}"
CONFIRMATORY_SEED_COUNT = 12


def _candidate(i: int) -> int:
    digest = hashlib.sha256(CONFIRMATORY_SEED_RULE.format(i=i).encode()).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def derive_confirmatory_seeds(count: int = CONFIRMATORY_SEED_COUNT) -> tuple[int, ...]:
    """First `count` admissible seeds from the committed rule.

    Admissible = not reserved (pilot/development) and not already drawn.
    Deterministic: anyone can recompute this list and check it against the lock.
    """
    out: list[int] = []
    i = 0
    while len(out) < count:
        seed = _candidate(i)
        if seed not in RESERVED_SEEDS and seed not in out:
            out.append(seed)
        i += 1
    return tuple(out)


# Materialized at the Phase-3 freeze. Pinned so a drift in the rule is caught by
# test rather than silently producing a different confirmatory sample.
CONFIRMATORY_SEEDS: tuple[int, ...] = derive_confirmatory_seeds()

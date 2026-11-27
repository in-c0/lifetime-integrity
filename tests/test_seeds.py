from lifetime_integrity.seeds import (
    CONFIRMATORY_SEED_COUNT,
    CONFIRMATORY_SEEDS,
    DEVELOPMENT_SEEDS,
    PILOT_SEEDS,
    RESERVED_SEEDS,
    derive_confirmatory_seeds,
)

# Materialized at the Phase-3 freeze, 2026-09-03. Pinned so that any drift in the
# derivation rule is caught here rather than silently changing which lifetimes
# the confirmatory claim rests on.
FROZEN_CONFIRMATORY_SEEDS = (
    1792867178, 2140240615, 238245273, 47376287, 1175348042, 1276344165,
    141418605, 225668972, 1257774472, 1717315326, 812421351, 58640242,
)


def test_confirmatory_seed_list_is_frozen():
    assert CONFIRMATORY_SEEDS == FROZEN_CONFIRMATORY_SEEDS
    assert len(CONFIRMATORY_SEEDS) == CONFIRMATORY_SEED_COUNT == 12


def test_seed_derivation_is_deterministic():
    assert derive_confirmatory_seeds() == derive_confirmatory_seeds()


def test_confirmatory_seeds_are_unique():
    assert len(set(CONFIRMATORY_SEEDS)) == len(CONFIRMATORY_SEEDS)


def test_confirmatory_seeds_never_collide_with_reserved_seeds():
    assert not set(CONFIRMATORY_SEEDS) & RESERVED_SEEDS
    assert not set(CONFIRMATORY_SEEDS) & set(DEVELOPMENT_SEEDS)
    assert not set(CONFIRMATORY_SEEDS) & set(PILOT_SEEDS)

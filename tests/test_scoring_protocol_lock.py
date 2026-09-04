from lifetime_integrity.metrics import (
    PREVIOUS_SCORING_PROTOCOL_VERSION,
    SCORING_PROTOCOL_VERSION,
    scoring_protocol,
    scoring_protocol_sha256,
)

# Phase-2 amendment 001 (M2) added the paired causal endpoint, which changes
# derived endpoint semantics and therefore this hash. Recorded for audit:
#   LIS-SCORE-v0.2.0 -> 3a7bf5eb123ce2904a99c68edcd9e97152fc6e90fc8d2167cdf79b411bbde728
# That is the version the Phase-2 development matrix was executed under; its
# manifests legitimately still carry it.
HISTORICAL_V020_SCORING_SHA256 = "3a7bf5eb123ce2904a99c68edcd9e97152fc6e90fc8d2167cdf79b411bbde728"
DEFAULT_SCORING_SHA256 = "c001a916c4ceb05ec02735c1f2f8066bc81b5d035beab2821657bdb1d9a0a7df"


def test_default_scoring_protocol_hash_is_locked():
    assert scoring_protocol_sha256(3) == DEFAULT_SCORING_SHA256


def test_amendment_001_changed_the_scoring_protocol():
    assert SCORING_PROTOCOL_VERSION == "LIS-SCORE-v0.3.0"
    assert PREVIOUS_SCORING_PROTOCOL_VERSION == "LIS-SCORE-v0.2.0"
    assert scoring_protocol_sha256(3) != HISTORICAL_V020_SCORING_SHA256


def test_scoring_protocol_declares_the_causal_endpoint():
    protocol = scoring_protocol(3)
    assert protocol["causal_endpoint"] == "excess-net-repair-v1"
    assert protocol["inaction_baseline_arm"] == "no-consolidation"


def test_scoring_protocol_hash_changes_with_window():
    assert scoring_protocol_sha256(2) != scoring_protocol_sha256(3)

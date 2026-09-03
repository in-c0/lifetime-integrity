from lifetime_integrity.metrics import scoring_protocol_sha256

DEFAULT_PHASE2_SCORING_SHA256 = "3a7bf5eb123ce2904a99c68edcd9e97152fc6e90fc8d2167cdf79b411bbde728"


def test_default_phase2_scoring_protocol_hash_is_locked():
    assert scoring_protocol_sha256(3) == DEFAULT_PHASE2_SCORING_SHA256


def test_scoring_protocol_hash_changes_with_window():
    assert scoring_protocol_sha256(2) != scoring_protocol_sha256(3)

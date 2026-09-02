import pytest

from lifetime_integrity.harness import run_delayed_credit
from lifetime_integrity.lifetime import LifetimeConfig, generate_delayed_credit_lifetime


def test_development_rejects_nondefault_matched_control_salt():
    lt = generate_delayed_credit_lifetime(
        LifetimeConfig(seed=20260903, epochs=16, delayed_outcomes_per_epoch=1.5)
    )
    with pytest.raises(ValueError, match="default matched-control selection salt"):
        run_delayed_credit(
            lt,
            "no-consolidation",
            classification="DEVELOPMENT",
            git_commit="0123456789abcdef",
            control_selection_salt="hidden-knob",
        )


def test_manifest_records_pilot_matched_control_salt():
    lt = generate_delayed_credit_lifetime(
        LifetimeConfig(seed=20260903, epochs=16, delayed_outcomes_per_epoch=1.5)
    )
    result = run_delayed_credit(
        lt,
        "no-consolidation",
        control_selection_salt="invariance-test",
    )
    assert result.manifest["control_selection_salt"] == "invariance-test"

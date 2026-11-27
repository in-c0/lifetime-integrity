import sys
from pathlib import Path

from lifetime_integrity.consolidation import CONSOLIDATORS
from lifetime_integrity.harness import default_budget, run_delayed_credit
from lifetime_integrity.lifetime import LifetimeConfig, generate_delayed_credit_lifetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_runs import validate


def _credit_runs() -> list[dict]:
    lt = generate_delayed_credit_lifetime(
        LifetimeConfig(seed=20260902, epochs=14, delayed_outcomes_per_epoch=1.5)
    )
    budget = default_budget(lt)
    return [run_delayed_credit(lt, arm, budget).manifest for arm in CONSOLIDATORS]


def test_validator_rejects_nondefault_development_control_salt():
    runs = _credit_runs()
    for run in runs:
        run["classification"] = "DEVELOPMENT"
        run["git_commit"] = "0123456789abcdef"
        run["control_selection_salt"] = "hidden-knob"
    reasons = validate(runs)["reasons"]
    assert "nondefault_control_selection_salt_in_development" in reasons


def test_validator_rejects_cross_arm_control_salt_mismatch():
    runs = _credit_runs()
    runs[0]["control_selection_salt"] = "different"
    reasons = validate(runs)["reasons"]
    assert "arms_disagree_on_control_selection_salt" in reasons

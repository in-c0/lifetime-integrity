import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_development as dev


class PoisonMetrics(dict):
    def __getitem__(self, key):
        raise AssertionError(f"performance metric was read before validity passed: {key}")


class FakeResult:
    def __init__(self, manifest: dict):
        self.manifest = manifest

    def write(self, path: Path) -> None:
        return None


def fake_manifest(arm: str) -> dict:
    return {
        "arm": arm,
        "budget_actual": {
            "evidence_reads": 10,
            "exhausted_reads": 0,
            "maintenance_ops": 2,
            "state_bytes": 128,
            "wall_seconds": 0.01,
        },
        "budget_ceiling": {"evidence_reads_ceiling": 100},
        "metrics": PoisonMetrics(),
        "consolidation_metrics": PoisonMetrics(),
        "matched_untouched_control": PoisonMetrics(),
    }


def invalid_report() -> dict:
    return {
        "valid_for_comparison": False,
        "reasons": ["synthetic_invalidity"],
    }


def test_invalid_a_cell_does_not_read_performance(monkeypatch, tmp_path):
    monkeypatch.setattr(dev, "DRIFT_MECHANISMS", {"arm-a": object()})
    monkeypatch.setattr(dev, "generate_drift_lifetime", lambda config: object())
    monkeypatch.setattr(dev, "default_budget", lambda lifetime: object())
    monkeypatch.setattr(dev, "run_drift", lambda *args, **kwargs: FakeResult(fake_manifest("arm-a")))
    monkeypatch.setattr(dev, "validate", lambda runs: invalid_report())

    result = dev._run_a(1, 8, "deadbeef", tmp_path)
    assert result["rows"] == []
    assert result["integrity_cost_frontier"] == []
    assert result["cost_diagnostics"][0]["evidence_reads"] == 10


def test_invalid_b_cell_does_not_read_performance(monkeypatch, tmp_path):
    monkeypatch.setattr(dev, "CONSOLIDATORS", {"arm-b": object()})
    monkeypatch.setattr(dev, "generate_delayed_credit_lifetime", lambda config: object())
    monkeypatch.setattr(dev, "default_budget", lambda lifetime: object())
    monkeypatch.setattr(
        dev,
        "run_delayed_credit",
        lambda *args, **kwargs: FakeResult(fake_manifest("arm-b")),
    )
    monkeypatch.setattr(dev, "validate", lambda runs: invalid_report())

    result = dev._run_b(1, 8, "deadbeef", tmp_path)
    assert result["rows"] == []
    assert result["repair_cost_frontier"] == []
    assert result["cost_diagnostics"][0]["maintenance_ops"] == 2

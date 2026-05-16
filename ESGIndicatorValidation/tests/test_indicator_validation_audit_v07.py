from .helpers import make_orchestrator_output, read_json, run_validation


def test_audit_outputs_and_checks(tmp_path):
    out = tmp_path / "out"
    assert run_validation(make_orchestrator_output(tmp_path), out, "--overwrite").returncode == 0
    assert (out / "indicator_validation_audit_samples.csv").exists()
    summary = read_json(out / "indicator_validation_audit_summary.json")
    assert summary["checks"]["validated_indicators_count"] == 0
    assert summary["checks"]["score_produced_count"] == 0
    assert "possible_indicator_without_unit_count" in summary["checks"]

from .helpers import make_manual_review_output, read_json, run_build


def test_audit_empty_database_warning(tmp_path):
    out = tmp_path / "out"
    assert run_build(make_manual_review_output(tmp_path, accepted=False), out, "--overwrite").returncode == 0
    audit = read_json(out / "indicator_database_audit_summary.json")
    assert audit["checks"]["empty_database_warning"] == 1
    assert audit["errors_count"] == 0
    assert (out / "indicator_database_audit_findings.jsonl").exists()
    assert (out / "indicator_database_audit_samples.csv").exists()

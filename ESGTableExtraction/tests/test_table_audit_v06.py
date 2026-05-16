from pathlib import Path
from .helpers import make_input, read_json, read_jsonl, run


def test_table_audit_outputs(tmp_path: Path):
    out = tmp_path / "out"
    result = run(make_input(tmp_path), out)
    assert result.returncode == 0, result.stdout
    assert (out / "table_audit_summary.json").exists()
    assert (out / "table_audit_findings.jsonl").exists()
    assert (out / "table_audit_samples.csv").exists()
    summary = read_json(out / "table_audit_summary.json")
    findings = read_jsonl(out / "table_audit_findings.jsonl")
    assert summary["findings_count"] == len(findings)
    assert "candidates_without_unit" in summary["checks"]

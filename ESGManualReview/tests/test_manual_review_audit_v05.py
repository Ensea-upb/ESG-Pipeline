from .helpers import make_indicator_output, read_csv, read_json, run_apply, run_build
from .test_apply_review_decisions_v04 import write_decisions


def test_audit_detects_missing_reason(tmp_path):
    workspace = tmp_path / "workspace"
    assert run_build(make_indicator_output(tmp_path), workspace, "--overwrite").returncode == 0
    decisions = read_csv(workspace / "review_decisions_template.csv")
    decisions[0].update({"proposed_decision": "accept_candidate", "reviewer": "qa"})
    dfile = tmp_path / "decisions.csv"
    write_decisions(dfile, decisions)
    out = tmp_path / "applied"
    assert run_apply(workspace, dfile, out, "--overwrite").returncode == 0
    audit = read_json(out / "manual_review_audit_summary.json")
    assert audit["checks"]["accepted_without_reason_count"] == 1
    assert (out / "manual_review_audit_findings.jsonl").exists()
    assert (out / "manual_review_audit_samples.csv").exists()

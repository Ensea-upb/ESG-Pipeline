import csv
import json

from .helpers import make_indicator_output, read_csv, run_apply, run_build


def write_decisions(path, rows):
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_apply_decisions_outputs(tmp_path):
    workspace = tmp_path / "workspace"
    assert run_build(make_indicator_output(tmp_path), workspace, "--overwrite").returncode == 0
    decisions = read_csv(workspace / "review_decisions_template.csv")
    decisions[0].update({"proposed_decision": "accept_candidate", "reviewer": "qa", "decision_reason": "source verified", "corrected_value": "1200"})
    decisions[1].update({"proposed_decision": "reject_candidate", "reviewer": "qa", "decision_reason": "context only"})
    decisions[2].update({"proposed_decision": "needs_more_evidence", "reviewer": "qa", "needs_more_evidence_reason": "weak visual"})
    dfile = tmp_path / "decisions.csv"
    write_decisions(dfile, decisions)
    out = tmp_path / "applied"
    result = run_apply(workspace, dfile, out, "--overwrite")
    assert result.returncode == 0, result.stdout
    assert len(read_csv(out / "accepted_candidate_inputs.csv")) == 1
    assert len(read_csv(out / "rejected_review_candidates.csv")) == 1
    assert len(read_csv(out / "needs_more_evidence_candidates.csv")) == 1
    accepted = read_csv(out / "accepted_candidate_inputs.csv")[0]
    assert accepted["original_raw_value"] == "1200"
    assert accepted["corrected_value"] == "1200"
    assert accepted["validated_indicator"] == "False"
    assert accepted["score_produced"] == "False"


def test_invalid_decision_is_reported(tmp_path):
    workspace = tmp_path / "workspace"
    assert run_build(make_indicator_output(tmp_path), workspace, "--overwrite").returncode == 0
    decisions = read_csv(workspace / "review_decisions_template.csv")
    decisions[0]["proposed_decision"] = "bad"
    dfile = tmp_path / "decisions.csv"
    write_decisions(dfile, decisions)
    out = tmp_path / "applied"
    assert run_apply(workspace, dfile, out, "--overwrite").returncode == 0
    summary = json.loads((out / "review_decision_summary.json").read_text(encoding="utf-8"))
    assert summary["invalid_decision_count"] == 1

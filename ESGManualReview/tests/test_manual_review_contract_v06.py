import csv
import json

from .helpers import CONTRACT, make_indicator_output, read_csv, run_apply, run_build, run_validate
from .test_apply_review_decisions_v04 import write_decisions


def make_applied(tmp_path):
    workspace = tmp_path / "workspace"
    assert run_build(make_indicator_output(tmp_path), workspace, "--overwrite").returncode == 0
    decisions = read_csv(workspace / "review_decisions_template.csv")
    decisions[0].update({"proposed_decision": "accept_candidate", "reviewer": "qa", "decision_reason": "ok"})
    dfile = tmp_path / "decisions.csv"
    write_decisions(dfile, decisions)
    out = tmp_path / "applied"
    assert run_apply(workspace, dfile, out, "--overwrite").returncode == 0
    return out


def test_contract_accepts_valid_output(tmp_path):
    out = make_applied(tmp_path)
    result = run_validate(out)
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["status"] == "success"
    assert CONTRACT.exists()


def test_contract_rejects_validated_indicator_and_score(tmp_path):
    out = make_applied(tmp_path)
    path = out / "reviewed_candidates.csv"
    rows = read_csv(path)
    rows[0]["validated_indicator"] = "True"
    rows[0]["score_produced"] = "True"
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    result = run_validate(out)
    assert result.returncode != 0
    assert json.loads(result.stdout)["errors_count"] >= 2

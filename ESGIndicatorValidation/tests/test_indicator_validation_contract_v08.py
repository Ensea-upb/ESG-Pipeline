import csv
import json

from .helpers import CONTRACT, make_orchestrator_output, read_csv, run_validation, validate_output


def test_contract_accepts_valid_output(tmp_path):
    out = tmp_path / "out"
    assert run_validation(make_orchestrator_output(tmp_path), out, "--overwrite").returncode == 0
    result = validate_output(out)
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["status"] == "success"
    assert CONTRACT.exists()


def test_contract_rejects_forbidden_values(tmp_path):
    out = tmp_path / "out"
    assert run_validation(make_orchestrator_output(tmp_path), out, "--overwrite").returncode == 0
    path = out / "indicator_candidate_validations.csv"
    rows = read_csv(path)
    rows[0]["review_required"] = "False"
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    result = validate_output(out)
    assert result.returncode != 0
    assert json.loads(result.stdout)["errors_count"] > 0


def test_contract_rejects_score_and_validated_indicator(tmp_path):
    out = tmp_path / "out"
    assert run_validation(make_orchestrator_output(tmp_path), out, "--overwrite").returncode == 0
    path = out / "indicator_candidate_validations.csv"
    rows = read_csv(path)
    rows[0]["score_produced"] = "True"
    rows[0]["is_validated_indicator"] = "True"
    rows[0]["validation_status"] = "validated"
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    result = validate_output(out)
    payload = json.loads(result.stdout)
    assert result.returncode != 0
    assert payload["errors_count"] >= 3

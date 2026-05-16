import csv
import json

from .helpers import CONTRACT, make_manual_review_output, read_csv, run_build, run_validate


def test_contract_valid_and_empty_valid(tmp_path):
    out = tmp_path / "out"
    assert run_build(make_manual_review_output(tmp_path), out, "--overwrite").returncode == 0
    assert run_validate(out).returncode == 0
    empty = tmp_path / "empty_out"
    assert run_build(make_manual_review_output(tmp_path / "empty", accepted=False), empty, "--overwrite").returncode == 0
    assert run_validate(empty).returncode == 0
    assert CONTRACT.exists()


def test_contract_rejects_final_indicator_and_score(tmp_path):
    out = tmp_path / "out"
    assert run_build(make_manual_review_output(tmp_path), out, "--overwrite").returncode == 0
    path = out / "indicator_preparation_database.csv"
    rows = read_csv(path)
    rows[0]["is_final_indicator"] = "True"
    rows[0]["score_produced"] = "True"
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    result = run_validate(out)
    assert result.returncode != 0
    assert json.loads(result.stdout)["errors_count"] >= 2

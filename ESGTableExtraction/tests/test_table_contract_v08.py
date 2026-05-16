import csv
import json
from pathlib import Path
from .helpers import make_input, run, validate


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, headers: list[str], rows: list[dict]):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})


def test_contract_validates_and_fails_cleanly(tmp_path: Path):
    out = tmp_path / "out"
    result = run(make_input(tmp_path), out)
    assert result.returncode == 0, result.stdout
    ok = validate(out)
    assert ok.returncode == 0, ok.stdout
    payload = json.loads(ok.stdout)
    assert payload["status"] == "success"

    headers, rows = read_csv(out / "table_metric_candidates.csv")
    rows[0]["review_required"] = "False"
    write_csv(out / "table_metric_candidates.csv", headers, rows)
    bad = validate(out)
    assert bad.returncode != 0
    assert "review_required" in bad.stdout


def test_contract_detects_confidence_score_and_missing_column(tmp_path: Path):
    out = tmp_path / "out"
    result = run(make_input(tmp_path), out)
    assert result.returncode == 0, result.stdout
    headers, rows = read_csv(out / "table_metric_candidates.csv")
    rows[0]["confidence"] = "0.9"
    headers.append("table_score")
    write_csv(out / "table_metric_candidates.csv", headers, rows)
    bad = validate(out)
    assert bad.returncode != 0
    assert "confidence" in bad.stdout
    assert "forbidden" in bad.stdout

    headers.remove("cell_id")
    write_csv(out / "table_metric_candidates.csv", headers, rows)
    bad2 = validate(out)
    assert bad2.returncode != 0
    assert "cell_id" in bad2.stdout

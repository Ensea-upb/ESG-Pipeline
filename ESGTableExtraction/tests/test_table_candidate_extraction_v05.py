import csv
from pathlib import Path
from .helpers import make_input, run


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_candidate_extraction_rules(tmp_path: Path):
    out = tmp_path / "out"
    result = run(make_input(tmp_path), out)
    assert result.returncode == 0, result.stdout
    rows = read_csv(out / "table_metric_candidates.csv")
    assert rows
    assert all(row["raw_value"] for row in rows)
    assert all(float(row["confidence"]) <= 0.6 for row in rows)
    assert {row["review_required"] for row in rows} == {"True"}
    assert {row["extraction_status"] for row in rows} == {"candidate_only"}
    assert all("score" not in key.lower() for key in rows[0])

import csv
from pathlib import Path
from .helpers import make_input, run


def count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as file:
        return len(list(csv.DictReader(file)))


def test_typed_csvs_exist_and_sum(tmp_path: Path):
    out = tmp_path / "out"
    result = run(make_input(tmp_path), out)
    assert result.returncode == 0, result.stdout
    files = ["table_observed_metrics.csv", "table_targets.csv", "table_contexts.csv", "table_rejected_candidates.csv"]
    assert all((out / f).exists() for f in files)
    assert sum(count(out / f) for f in files) == count(out / "table_metric_candidates.csv")

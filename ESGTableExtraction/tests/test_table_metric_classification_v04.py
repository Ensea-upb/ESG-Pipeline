from pathlib import Path
from .helpers import make_input, read_jsonl, run


def test_row_classification_detects_categories(tmp_path: Path):
    out = tmp_path / "out"
    result = run(make_input(tmp_path), out)
    assert result.returncode == 0, result.stdout
    rows = read_jsonl(out / "table_row_classification.jsonl")
    cats = {row["row_category"] for row in rows}
    assert "climate" in cats
    assert "workforce" in cats
    assert all(float(row["classification_confidence"]) <= 0.6 for row in rows)

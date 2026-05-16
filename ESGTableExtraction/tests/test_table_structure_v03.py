from pathlib import Path
from .helpers import make_input, read_json, read_jsonl, run


def test_structure_detects_years_units_headers(tmp_path: Path):
    out = tmp_path / "out"
    result = run(make_input(tmp_path), out)
    assert result.returncode == 0, result.stdout
    structures = read_jsonl(out / "table_structure_index.jsonl")
    st = next(row for row in structures if row["table_id"] == "tbl1")
    assert st["header_row_indices"]
    assert {item["year"] for item in st["candidate_year_columns"]} >= {"2023", "2024"}
    assert st["candidate_unit_cells"]
    summary = read_json(out / "table_structure_summary.json")
    assert summary["tables_structured_count"] >= 1

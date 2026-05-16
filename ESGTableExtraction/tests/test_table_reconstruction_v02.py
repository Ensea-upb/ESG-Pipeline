from pathlib import Path
from .helpers import make_input, read_json, read_jsonl, run


def test_reconstructs_matrix_and_empty_table(tmp_path: Path):
    out = tmp_path / "out"
    result = run(make_input(tmp_path), out)
    assert result.returncode == 0, result.stdout
    tables = read_jsonl(out / "reconstructed_tables.jsonl")
    first = next(row for row in tables if row["table_id"] == "tbl1")
    assert first["matrix"][1][0] == "Scope 1 emissions tCO2e"
    assert first["row_count"] == 3
    assert first["column_count"] == 3
    empty = next(row for row in tables if row["table_id"] == "tbl_empty")
    assert empty["reconstruction_status"] == "empty_table"
    summary = read_json(out / "table_reconstruction_summary.json")
    assert summary["empty_tables_count"] == 1

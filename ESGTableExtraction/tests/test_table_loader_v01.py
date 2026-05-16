from pathlib import Path
from .helpers import hash_tree, make_input, read_jsonl, run


def test_loader_outputs_and_non_destructive(tmp_path: Path):
    input_dir = make_input(tmp_path)
    before = hash_tree(input_dir)
    out = tmp_path / "out"
    result = run(input_dir, out)
    assert result.returncode == 0, result.stdout
    assert (out / "table_input_inventory.json").exists()
    tables = read_jsonl(out / "table_items.jsonl")
    cells = read_jsonl(out / "table_cells_loaded.jsonl")
    assert tables and cells
    assert all(row["table_id"] for row in tables)
    assert all(row["cell_id"] for row in cells)
    assert before == hash_tree(input_dir)


def test_loader_refuses_missing_inputs(tmp_path: Path):
    assert run(make_input(tmp_path / "a", missing="table_index"), tmp_path / "out1").returncode != 0
    assert run(make_input(tmp_path / "b", missing="table_cells"), tmp_path / "out2").returncode != 0

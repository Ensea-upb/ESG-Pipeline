from __future__ import annotations

import json
from pathlib import Path

from .helpers import hash_tree, make_visual_input, read_jsonl, run_visual


def test_loader_refuses_missing_figure_index(tmp_path: Path):
    input_dir = make_visual_input(tmp_path, with_figure_index=False)
    result = run_visual(input_dir, tmp_path / "out")
    assert result.returncode != 0
    assert "figure_index.jsonl" in result.stdout


def test_loader_produces_visual_items_and_summary(tmp_path: Path):
    input_dir = make_visual_input(tmp_path)
    before = hash_tree(input_dir)
    output_dir = tmp_path / "out"
    result = run_visual(input_dir, output_dir)
    assert result.returncode == 0, result.stdout
    assert (output_dir / "visual_input_inventory.json").exists()
    assert (output_dir / "visual_items.jsonl").exists()
    assert (output_dir / "visual_extraction_summary.json").exists()
    rows = read_jsonl(output_dir / "visual_items.jsonl")
    assert rows
    assert all(row["review_required"] is True for row in rows)
    assert before == hash_tree(input_dir)

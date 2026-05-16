from __future__ import annotations

from pathlib import Path

from .helpers import make_visual_input, read_jsonl, run_visual
from esg_visual_extraction.classifier import ALLOWED_VISUAL_TYPES


def test_visual_classifier_uses_allowed_types(tmp_path: Path):
    input_dir = make_visual_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_visual(input_dir, output_dir)
    assert result.returncode == 0, result.stdout
    rows = read_jsonl(output_dir / "visual_classification.jsonl")
    assert rows
    assert all(row["visual_type"] in ALLOWED_VISUAL_TYPES for row in rows)
    assert all(row["review_required"] is True for row in rows)
    chart_rows = [row for row in rows if row["visual_type"] in {"chart", "scanned_table"}]
    assert chart_rows
    assert all(row["is_potentially_esg_relevant"] is True for row in chart_rows)

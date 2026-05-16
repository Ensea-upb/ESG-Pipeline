from __future__ import annotations

from pathlib import Path

from .helpers import make_visual_input, read_json, read_jsonl, run_visual


def test_ocr_outputs_are_documented_without_real_tesseract(tmp_path: Path):
    input_dir = make_visual_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_visual(input_dir, output_dir)
    assert result.returncode == 0, result.stdout
    rows = read_jsonl(output_dir / "visual_ocr_outputs.jsonl")
    assert rows
    assert all(row["review_required"] is True for row in rows)
    assert all(row["ocr_status"] in {"ocr_unavailable", "ocr_failed", "empty_text", "success"} for row in rows)
    summary = read_json(output_dir / "visual_ocr_summary.json")
    assert "ocr_status_distribution" in summary

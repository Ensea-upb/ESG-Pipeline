from __future__ import annotations

from pathlib import Path

from .helpers import hash_tree, make_visual_input, read_jsonl, run_visual


def test_cropper_creates_crops_and_index(tmp_path: Path):
    input_dir = make_visual_input(tmp_path)
    pdf_hash_before = hash_tree(input_dir)
    output_dir = tmp_path / "out"
    result = run_visual(input_dir, output_dir)
    assert result.returncode == 0, result.stdout
    crops = read_jsonl(output_dir / "visual_crops_index.jsonl")
    assert crops
    assert (output_dir / "crops").exists()
    assert all(row["review_required"] is True for row in crops)
    assert any(row["crop_image_path"] for row in crops)
    assert pdf_hash_before == hash_tree(input_dir)


def test_cropper_handles_missing_source_pdf(tmp_path: Path):
    input_dir = make_visual_input(tmp_path, pdf_exists=False)
    output_dir = tmp_path / "out"
    result = run_visual(input_dir, output_dir)
    assert result.returncode == 0, result.stdout
    crops = read_jsonl(output_dir / "visual_crops_index.jsonl")
    assert {row["crop_status"] for row in crops} == {"missing_source_pdf"}

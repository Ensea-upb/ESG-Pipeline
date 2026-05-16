"""
test_visual_crop_robustness_v03.py
===================================
Tests for best-effort visual crop robustness.

- Crop directory is always created.
- Missing / un-renderable crops produce warnings, never exceptions.
- Crop filenames are short enough to avoid Windows MAX_PATH (260 chars).
- Existing visual outputs still pass the contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from .helpers import make_visual_input, run_validator, run_visual, read_jsonl

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from esg_visual_extraction.cropper import crop_visual_items


# ---------------------------------------------------------------------------
# 1. test_visual_crop_directory_created
# ---------------------------------------------------------------------------

def test_visual_crop_directory_created(tmp_path: Path):
    """crops/ must be created even when visual_items is empty."""
    output_dir = tmp_path / "visual"
    output_dir.mkdir()
    rows = crop_visual_items([], pdf_path="", output_dir=output_dir)
    assert (output_dir / "crops").is_dir(), "crops/ directory must be created by crop_visual_items"
    assert rows == []


def test_visual_crop_directory_created_with_items(tmp_path: Path):
    """crops/ must be created when items are present (missing PDF path)."""
    output_dir = tmp_path / "visual"
    output_dir.mkdir()
    item = {
        "figure_id": "fig_test_001",
        "document_id": "doc_test",
        "page_number": 1,
        "figure_bbox": None,
    }
    rows = crop_visual_items([item], pdf_path="", output_dir=output_dir)
    assert (output_dir / "crops").is_dir()
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# 2. test_missing_crop_does_not_crash_visual_extraction
# ---------------------------------------------------------------------------

def test_missing_crop_does_not_crash_when_pdf_absent(tmp_path: Path):
    """
    When the source PDF is missing, crop_visual_items must:
    - not raise any exception
    - return crop_status='missing_source_pdf'
    - return crop_file_exists=False
    - return empty crop_image_path
    """
    output_dir = tmp_path / "visual"
    output_dir.mkdir()
    item = {
        "figure_id": "fig_canonical_abcdef_p0001_0000",
        "document_id": "canonical_abcdef",
        "page_number": 1,
        "figure_bbox": [0, 0, 100, 100],
    }
    rows = crop_visual_items([item], pdf_path="/nonexistent/document.pdf", output_dir=output_dir)

    assert len(rows) == 1
    row = rows[0]
    assert row["crop_status"] == "missing_source_pdf"
    assert row["crop_file_exists"] is False
    assert row["crop_image_path"] == ""
    assert row["visual_warning"] == ""
    assert row["review_required"] is True


def test_missing_crop_does_not_crash_when_pdf_empty_string(tmp_path: Path):
    """Empty pdf_path string → missing_source_pdf, no exception."""
    output_dir = tmp_path / "visual"
    output_dir.mkdir()
    item = {"figure_id": "fig_001", "document_id": "doc_001", "page_number": 1, "figure_bbox": None}
    rows = crop_visual_items([item], pdf_path="", output_dir=output_dir)
    assert len(rows) == 1
    assert rows[0]["crop_file_exists"] is False
    assert rows[0]["crop_status"] == "missing_source_pdf"


def test_missing_crop_does_not_crash_visual_extraction_via_cli(tmp_path: Path):
    """
    CLI pipeline: even if crops cannot be rendered (minimal fake PDF),
    - returncode must be 0 (not a fatal crash)
    - visual_extraction_summary.json is produced
    - visual_candidates.csv is produced
    - crops_with_warnings_count and/or status are exposed
    """
    input_dir = make_visual_input(tmp_path, pdf_exists=True)
    output_dir = tmp_path / "out"
    result = run_visual(input_dir, output_dir)

    assert result.returncode == 0, (
        f"Visual extraction must not crash even on render failures.\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert (output_dir / "visual_extraction_summary.json").exists()
    assert (output_dir / "visual_candidates.csv").exists()
    assert (output_dir / "visual_crops_index.jsonl").exists()

    summary = json.loads((output_dir / "visual_extraction_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] in {"success", "warning"}, f"Unexpected status: {summary['status']}"
    assert "crops_with_warnings_count" in summary


# ---------------------------------------------------------------------------
# 3. test_crop_filename_short_avoids_max_path
# ---------------------------------------------------------------------------

def test_crop_filename_does_not_include_figure_id(tmp_path: Path):
    """
    Crop filenames must be short (crop_NNNN.png) and must NOT include the figure_id.
    This avoids Windows MAX_PATH (260 chars) on long document paths.
    """
    output_dir = tmp_path / "visual"
    output_dir.mkdir()
    long_figure_id = "fig_canonical_40d8e0d89b7401018cec99da_p0001_0000"  # 49 chars
    item = {
        "figure_id": long_figure_id,
        "document_id": "canonical_40d8e0d89b7401018cec99da",
        "page_number": 1,
        "figure_bbox": None,
    }
    rows = crop_visual_items([item], pdf_path="", output_dir=output_dir)
    assert len(rows) == 1
    assert rows[0]["crop_id"] == "crop_0001"
    # figure_id is preserved in metadata, not in filename
    assert rows[0]["figure_id"] == long_figure_id
    # No crop file was created (missing PDF), but if it had been created,
    # its filename would be crop_0001.png not crop_0001_fig_canonical_...png
    crops_dir = output_dir / "crops"
    if crops_dir.exists():
        png_files = list(crops_dir.glob("*.png"))
        for f in png_files:
            assert long_figure_id not in f.name, (
                f"Crop filename must not include figure_id to avoid MAX_PATH: {f.name}"
            )


# ---------------------------------------------------------------------------
# 4. test_existing_visual_outputs_still_pass_contract
# ---------------------------------------------------------------------------

def test_existing_visual_outputs_still_pass_contract(tmp_path: Path):
    """Existing outputs must still pass the visual output contract after the fix."""
    input_dir = make_visual_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_visual(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    validation = run_validator(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode == 0, (
        f"Contract validation failed after crop robustness fix.\n"
        f"stdout={validation.stdout}\nstderr={validation.stderr}"
    )
    assert payload["status"] == "success"

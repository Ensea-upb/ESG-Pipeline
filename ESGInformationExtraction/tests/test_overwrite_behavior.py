from __future__ import annotations

from pathlib import Path

from .conftest import read_json, run_cli


def test_second_run_without_overwrite_fails_cleanly(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    first = run_cli(small_pdf, output_dir)
    assert first.returncode == 0, first.stderr

    second = run_cli(small_pdf, output_dir)

    assert second.returncode != 0
    assert (output_dir / "extraction_summary.json").exists()
    summary = read_json(output_dir / "extraction_summary.json")
    assert summary["status"] in {"success", "failed"}


def test_second_run_with_overwrite_succeeds(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    first = run_cli(small_pdf, output_dir, document_id="doc_overwrite")
    assert first.returncode == 0, first.stderr

    second = run_cli(small_pdf, output_dir, document_id="doc_overwrite", overwrite=True)

    assert second.returncode == 0, second.stderr
    summary = read_json(output_dir / "extraction_summary.json")
    assert summary["status"] == "success"
    assert summary["document_id"] == "doc_overwrite"

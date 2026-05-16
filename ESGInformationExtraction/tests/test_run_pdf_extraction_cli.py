from __future__ import annotations

from pathlib import Path

from .conftest import read_json, run_cli


def test_cli_runs_on_small_pdf(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"

    result = run_cli(small_pdf, output_dir)

    assert result.returncode == 0, result.stderr
    summary = read_json(output_dir / "extraction_summary.json")
    assert summary["status"] == "success"
    assert summary["document_id"] == "doc_test"
    assert summary["pages_processed"] == 1

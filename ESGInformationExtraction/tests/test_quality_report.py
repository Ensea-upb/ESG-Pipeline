from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli


def test_quality_report_contains_minimal_checks(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir)
    assert result.returncode == 0, result.stderr

    checks = read_jsonl(output_dir / "quality_report.jsonl")
    check_names = {check["check_name"] for check in checks}

    assert "pdf_readable" in check_names
    assert "page_count_valid" in check_names
    assert "page_has_text" in check_names
    assert "output_file_not_empty" in check_names
    assert "extraction_summary_exists" in check_names


def test_summary_is_coherent_with_outputs(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir)
    assert result.returncode == 0, result.stderr

    summary = read_json(output_dir / "extraction_summary.json")
    pages = read_jsonl(output_dir / "page_index.jsonl")
    blocks = read_jsonl(output_dir / "text_blocks.jsonl")
    evidence = read_jsonl(output_dir / "evidence_store.jsonl")
    checks = read_jsonl(output_dir / "quality_report.jsonl")

    table_records = read_jsonl(output_dir / "table_index.jsonl")
    cell_records = read_jsonl(output_dir / "table_cells.jsonl")

    assert summary["pages_processed"] == len(pages)
    assert summary["text_blocks_count"] == len(blocks)
    assert summary["quality_checks_count"] == len(checks)
    assert summary["tables_count"] == len(table_records)
    assert summary["table_cells_count"] == len(cell_records)
    assert summary["figures_count"] == 0
    assert summary["sections_count"] >= 0
    assert summary["evidence_count"] == len(evidence)

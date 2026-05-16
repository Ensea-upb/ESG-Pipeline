from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .conftest import PROJECT_ROOT, read_json, read_jsonl, run_cli


def test_low_text_and_visual_page_warnings(require_pdfplumber, low_text_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(low_text_pdf, output_dir, document_id="doc_low_text")
    assert result.returncode == 0, result.stderr

    checks = read_jsonl(output_dir / "quality_report.jsonl")
    check_names = {check["check_name"] for check in checks}
    assert "page_low_text_warning" in check_names
    assert "possible_visual_page" in check_names

    summary = read_json(output_dir / "extraction_summary.json")
    assert summary["pages_low_text_count"] == 1
    assert summary["possible_visual_pages_count"] == 1


def test_possible_table_of_contents_warning(require_pdfplumber, toc_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(toc_pdf, output_dir, document_id="doc_toc")
    assert result.returncode == 0, result.stderr

    checks = read_jsonl(output_dir / "quality_report.jsonl")
    check_names = {check["check_name"] for check in checks}
    assert "possible_table_of_contents_page" in check_names
    assert "high_title_density_warning" in check_names

    summary = read_json(output_dir / "extraction_summary.json")
    assert summary["possible_toc_pages_count"] == 1
    assert summary["high_title_density_pages_count"] == 1


def test_text_block_statistics_is_produced(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="doc_stats")
    assert result.returncode == 0, result.stderr

    stats = read_json(output_dir / "text_block_statistics.json")
    assert stats["document_id"] == "doc_stats"
    assert stats["total_blocks"] > 0
    assert "block_type_counts" in stats
    assert "blocks_by_page" in stats
    assert len(stats["sample_titles"]) <= 20
    assert len(stats["sample_paragraphs"]) <= 20


def test_summary_contains_v01_counters(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="doc_summary_v01")
    assert result.returncode == 0, result.stderr

    summary = read_json(output_dir / "extraction_summary.json")
    for key in {
        "pages_low_text_count",
        "possible_visual_pages_count",
        "possible_toc_pages_count",
        "high_title_density_pages_count",
        "blocks_with_bbox_count",
        "blocks_without_bbox_count",
        "title_blocks_count",
        "paragraph_blocks_count",
        "unknown_blocks_count",
    }:
        assert key in summary


def test_audit_text_blocks_tool(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    audit_output = tmp_path / "audit" / "text_block_statistics.json"
    result = run_cli(small_pdf, output_dir, document_id="doc_audit_tool")
    assert result.returncode == 0, result.stderr

    command = [
        sys.executable,
        str(PROJECT_ROOT / "ESGInformationExtraction" / "tools" / "audit_text_blocks.py"),
        "--text-blocks-path",
        str(output_dir / "text_blocks.jsonl"),
        "--page-index-path",
        str(output_dir / "page_index.jsonl"),
        "--output-path",
        str(audit_output),
    ]
    audit = subprocess.run(command, text=True, capture_output=True, cwd=PROJECT_ROOT)

    assert audit.returncode == 0, audit.stderr
    stats = read_json(audit_output)
    assert stats["document_id"] == "doc_audit_tool"
    assert stats["total_blocks"] > 0

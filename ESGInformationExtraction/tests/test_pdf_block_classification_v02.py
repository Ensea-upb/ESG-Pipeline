from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli


def test_toc_entries_are_detected(require_pdfplumber, toc_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(toc_pdf, output_dir, document_id="doc_toc_v02")
    assert result.returncode == 0, result.stderr

    blocks = read_jsonl(output_dir / "text_blocks.jsonl")
    toc_entries = [block for block in blocks if block["block_type"] == "toc_entry"]
    assert len(toc_entries) >= 5
    assert all(block["is_toc_entry"] is True for block in toc_entries)
    assert all(block["classification_reason"] == "toc_page_title_ending_with_number" for block in toc_entries)


def test_list_items_are_detected(require_pdfplumber, list_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(list_pdf, output_dir, document_id="doc_list_v02")
    assert result.returncode == 0, result.stderr

    blocks = read_jsonl(output_dir / "text_blocks.jsonl")
    list_items = [block for block in blocks if block["block_type"] == "list_item"]
    assert len(list_items) >= 4
    assert all(block["classification_reason"] == "list_item_marker_or_numbering" for block in list_items)


def test_captions_are_detected(require_pdfplumber, caption_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(caption_pdf, output_dir, document_id="doc_caption_v02")
    assert result.returncode == 0, result.stderr

    blocks = read_jsonl(output_dir / "text_blocks.jsonl")
    captions = [block for block in blocks if block["block_type"] == "caption"]
    assert len(captions) >= 3
    assert all(block["classification_reason"] == "caption_prefix" for block in captions)


def test_new_text_block_fields_exist(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="doc_fields_v02")
    assert result.returncode == 0, result.stderr

    block = read_jsonl(output_dir / "text_blocks.jsonl")[0]
    for field in {
        "is_header",
        "is_footer",
        "is_toc_entry",
        "block_type_confidence",
        "classification_reason",
    }:
        assert field in block


def test_summary_contains_v02_counters(require_pdfplumber, caption_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(caption_pdf, output_dir, document_id="doc_summary_v02")
    assert result.returncode == 0, result.stderr

    summary = read_json(output_dir / "extraction_summary.json")
    for key in {
        "header_blocks_count",
        "footer_blocks_count",
        "toc_entry_blocks_count",
        "caption_blocks_count",
        "list_item_blocks_count",
        "unknown_blocks_ratio",
    }:
        assert key in summary
    assert summary["caption_blocks_count"] >= 3


def test_statistics_contains_v02_counters_and_samples(require_pdfplumber, list_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(list_pdf, output_dir, document_id="doc_stats_v02")
    assert result.returncode == 0, result.stderr

    stats = read_json(output_dir / "text_block_statistics.json")
    for key in {
        "header_blocks_count",
        "footer_blocks_count",
        "toc_entry_blocks_count",
        "caption_blocks_count",
        "list_item_blocks_count",
        "unknown_blocks_ratio",
        "sample_headers",
        "sample_footers",
        "sample_toc_entries",
        "sample_captions",
        "sample_list_items",
    }:
        assert key in stats
    assert stats["list_item_blocks_count"] >= 4
    assert len(stats["sample_list_items"]) >= 4


def test_quality_report_contains_v02_checks(require_pdfplumber, toc_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(toc_pdf, output_dir, document_id="doc_quality_v02")
    assert result.returncode == 0, result.stderr

    checks = read_jsonl(output_dir / "quality_report.jsonl")
    check_names = {check["check_name"] for check in checks}
    assert "header_footer_detected" in check_names
    assert "toc_entries_detected" in check_names
    assert "excessive_unknown_blocks_warning" in check_names
    assert "repeated_header_footer_warning" in check_names

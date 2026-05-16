from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli


def test_recurrent_document_footer_is_detected(require_pdfplumber, footer_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(footer_pdf, output_dir, document_id="doc_footer_v021")
    assert result.returncode == 0, result.stderr

    blocks = read_jsonl(output_dir / "text_blocks.jsonl")
    footers = [block for block in blocks if block["block_type"] == "footer"]
    assert len(footers) >= 2
    assert all(block["is_footer"] is True for block in footers)
    assert all(
        block["classification_reason"]
        == "strict_footer_pattern_or_repeated_document_label_in_bottom_page_zone"
        for block in footers
    )


def test_bottom_reference_note_is_detected_as_footnote(require_pdfplumber, footnote_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(footnote_pdf, output_dir, document_id="doc_footnote_v021")
    assert result.returncode == 0, result.stderr

    blocks = read_jsonl(output_dir / "text_blocks.jsonl")
    footnotes = [block for block in blocks if block["block_type"] == "footnote"]
    assert len(footnotes) == 1
    assert footnotes[0]["is_footnote"] is True
    assert footnotes[0]["footnote_confidence"] > 0


def test_historical_bottom_line_is_not_footer(require_pdfplumber, historical_bottom_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(historical_bottom_pdf, output_dir, document_id="doc_history_v021")
    assert result.returncode == 0, result.stderr

    blocks = read_jsonl(output_dir / "text_blocks.jsonl")
    assert blocks
    assert all(block["block_type"] != "footer" for block in blocks)


def test_v021_text_block_fields_exist(require_pdfplumber, footnote_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(footnote_pdf, output_dir, document_id="doc_fields_v021")
    assert result.returncode == 0, result.stderr

    block = read_jsonl(output_dir / "text_blocks.jsonl")[0]
    for field in {
        "is_footnote",
        "is_footer",
        "is_header",
        "is_toc_entry",
        "block_type_confidence",
        "classification_reason",
    }:
        assert field in block


def test_v021_summary_contains_footer_footnote_counters(require_pdfplumber, footnote_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(footnote_pdf, output_dir, document_id="doc_summary_v021")
    assert result.returncode == 0, result.stderr

    summary = read_json(output_dir / "extraction_summary.json")
    assert "footnote_blocks_count" in summary
    assert "refined_footer_blocks_count" in summary
    assert summary["footnote_blocks_count"] == 1


def test_v021_statistics_contains_footer_footnote_samples(require_pdfplumber, footer_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(footer_pdf, output_dir, document_id="doc_stats_v021")
    assert result.returncode == 0, result.stderr

    stats = read_json(output_dir / "text_block_statistics.json")
    assert "footnote_blocks_count" in stats
    assert "sample_footnotes" in stats
    assert "sample_refined_footers" in stats
    assert stats["refined_footer_blocks_count"] >= 2
    assert len(stats["sample_refined_footers"]) >= 2


def test_v021_quality_report_contains_refinement_checks(require_pdfplumber, footnote_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(footnote_pdf, output_dir, document_id="doc_quality_v021")
    assert result.returncode == 0, result.stderr

    checks = read_jsonl(output_dir / "quality_report.jsonl")
    check_names = {check["check_name"] for check in checks}
    assert "footer_detection_refined" in check_names
    assert "footnotes_detected" in check_names

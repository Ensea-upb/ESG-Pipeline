from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli, write_test_pdf


def test_evidence_outputs_still_exist(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_evidence_v041")
    assert result.returncode == 0, result.stderr

    assert (output_dir / "evidence_store.jsonl").exists()


def test_new_evidence_merge_fields_exist(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_fields_evidence_v041")
    assert result.returncode == 0, result.stderr

    evidence = read_jsonl(output_dir / "evidence_store.jsonl")
    assert evidence
    for item in evidence:
        assert "source_text_block_ids" in item
        assert "merged_blocks_count" in item
        assert "was_merged_evidence" in item
        assert "merge_method" in item


def test_consecutive_blocks_same_section_can_be_merged(require_pdfplumber, tmp_path: Path):
    pdf_path = write_test_pdf(
        tmp_path / "merge.pdf",
        [[
            "ENVIRONMENT",
            "This document is a free translation",
            "to help readers understand the original report",
            "and should be read with the French version.",
        ]],
    )
    output_dir = tmp_path / "out"
    result = run_cli(pdf_path, output_dir, document_id="doc_merge_evidence_v041")
    assert result.returncode == 0, result.stderr

    paragraph_evidence = [
        item for item in read_jsonl(output_dir / "evidence_store.jsonl")
        if item["evidence_type"] == "paragraph"
    ]
    assert any(item["was_merged_evidence"] for item in paragraph_evidence)
    merged = next(item for item in paragraph_evidence if item["was_merged_evidence"])
    assert merged["merged_blocks_count"] >= 2
    assert len(merged["source_text_block_ids"]) == merged["merged_blocks_count"]


def test_blocks_from_different_sections_are_not_merged(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_no_cross_merge_v041")
    assert result.returncode == 0, result.stderr

    sections = {section["section_id"] for section in read_jsonl(output_dir / "section_index.jsonl")}
    paragraph_evidence = [
        item for item in read_jsonl(output_dir / "evidence_store.jsonl")
        if item["evidence_type"] == "paragraph"
    ]
    assert paragraph_evidence
    assert all(item["section_id"] in sections for item in paragraph_evidence)


def test_structural_blocks_are_not_merged_into_paragraph_evidence(
    require_pdfplumber,
    toc_pdf: Path,
    footer_pdf: Path,
    caption_pdf: Path,
    tmp_path: Path,
):
    for pdf_path, document_id in [
        (toc_pdf, "doc_toc_no_merge_v041"),
        (footer_pdf, "doc_footer_no_merge_v041"),
        (caption_pdf, "doc_caption_no_merge_v041"),
    ]:
        output_dir = tmp_path / document_id
        result = run_cli(pdf_path, output_dir, document_id=document_id)
        assert result.returncode == 0, result.stderr
        blocks = {
            block["text_block_id"]: block
            for block in read_jsonl(output_dir / "text_blocks.jsonl")
        }
        for evidence in read_jsonl(output_dir / "evidence_store.jsonl"):
            if evidence["evidence_type"] != "paragraph":
                continue
            for block_id in evidence["source_text_block_ids"]:
                assert blocks[block_id]["block_type"] not in {"toc_entry", "header", "footer", "footnote", "caption"}


def test_short_evidence_is_filtered_or_reviewed(require_pdfplumber, tmp_path: Path):
    pdf_path = write_test_pdf(
        tmp_path / "short.pdf",
        [["ENVIRONMENT", "Short evidence paragraph for review."]],
    )
    output_dir = tmp_path / "out"
    result = run_cli(pdf_path, output_dir, document_id="doc_short_evidence_v041")
    assert result.returncode == 0, result.stderr

    paragraph_evidence = [
        item for item in read_jsonl(output_dir / "evidence_store.jsonl")
        if item["evidence_type"] == "paragraph"
    ]
    assert paragraph_evidence
    assert all(len(item["quote"]) >= 30 for item in paragraph_evidence)
    assert any(item["review_required"] for item in paragraph_evidence if len(item["quote"]) < 60)


def test_evidence_statistics_contains_v041_counters(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_stats_evidence_v041")
    assert result.returncode == 0, result.stderr

    stats = read_json(output_dir / "evidence_statistics.json")
    for key in {
        "median_quote_length",
        "short_evidence_count",
        "merged_evidence_count",
        "unmerged_evidence_count",
        "average_merged_blocks_count",
        "evidence_share_by_section",
        "sections_with_high_evidence_density",
        "sections_with_front_matter_warning",
        "sample_short_evidence",
        "sample_merged_evidence",
        "sample_section_mismatch_warnings",
    }:
        assert key in stats


def test_summary_contains_v041_counters(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_summary_evidence_v041")
    assert result.returncode == 0, result.stderr

    summary = read_json(output_dir / "extraction_summary.json")
    for key in {
        "merged_evidence_count",
        "unmerged_evidence_count",
        "short_evidence_skipped_count",
        "short_evidence_review_required_count",
        "sections_with_high_evidence_density_count",
        "sections_with_front_matter_warning_count",
        "section_title_content_mismatch_warning_count",
        "median_evidence_quote_length",
    }:
        assert key in summary


def test_quality_report_contains_v041_checks(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_quality_evidence_v041")
    assert result.returncode == 0, result.stderr

    check_names = {check["check_name"] for check in read_jsonl(output_dir / "quality_report.jsonl")}
    for check_name in {
        "evidence_paragraph_merge_applied",
        "short_evidence_filtered",
        "short_evidence_review_required",
        "section_front_matter_evidence_warning",
        "section_evidence_density_warning",
        "section_title_content_mismatch_warning",
        "evidence_fragmentation_warning",
    }:
        assert check_name in check_names

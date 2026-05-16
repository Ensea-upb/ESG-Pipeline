from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli


def test_evidence_outputs_are_produced(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_evidence_v04")
    assert result.returncode == 0, result.stderr

    assert (output_dir / "evidence_store.jsonl").exists()
    assert (output_dir / "evidence_statistics.json").exists()


def test_sections_create_section_heading_evidence(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_heading_evidence_v04")
    assert result.returncode == 0, result.stderr

    sections = read_jsonl(output_dir / "section_index.jsonl")
    evidence = read_jsonl(output_dir / "evidence_store.jsonl")
    heading_evidence = [item for item in evidence if item["evidence_type"] == "section_heading"]

    assert sections
    assert len(heading_evidence) == len(sections)
    assert {item["section_id"] for item in heading_evidence} == {section["section_id"] for section in sections}


def test_paragraphs_attached_to_sections_create_evidence(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_paragraph_evidence_v04")
    assert result.returncode == 0, result.stderr

    evidence = read_jsonl(output_dir / "evidence_store.jsonl")
    paragraph_evidence = [item for item in evidence if item["evidence_type"] == "paragraph"]

    assert paragraph_evidence
    assert all(item["section_id"] for item in paragraph_evidence)
    assert any("environment" in item["quote"].lower() for item in paragraph_evidence)


def test_structural_blocks_do_not_create_evidence(
    require_pdfplumber,
    toc_pdf: Path,
    footer_pdf: Path,
    tmp_path: Path,
):
    toc_output = tmp_path / "toc_out"
    footer_output = tmp_path / "footer_out"
    toc_result = run_cli(toc_pdf, toc_output, document_id="doc_toc_evidence_v04")
    footer_result = run_cli(footer_pdf, footer_output, document_id="doc_footer_evidence_v04")
    assert toc_result.returncode == 0, toc_result.stderr
    assert footer_result.returncode == 0, footer_result.stderr

    for output_dir in [toc_output, footer_output]:
        evidence = read_jsonl(output_dir / "evidence_store.jsonl")
        blocks = {
            block["text_block_id"]: block
            for block in read_jsonl(output_dir / "text_blocks.jsonl")
        }
        for item in evidence:
            block = blocks.get(item["text_block_id"])
            if not block:
                continue
            assert block["block_type"] not in {"toc_entry", "header", "footer"}


def test_evidence_ids_are_unique_and_quotes_non_empty(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_unique_evidence_v04")
    assert result.returncode == 0, result.stderr

    evidence = read_jsonl(output_dir / "evidence_store.jsonl")
    evidence_ids = [item["evidence_id"] for item in evidence]

    assert evidence_ids
    assert len(evidence_ids) == len(set(evidence_ids))
    assert all(item["quote"].strip() for item in evidence)


def test_evidence_links_are_valid(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_links_evidence_v04")
    assert result.returncode == 0, result.stderr

    evidence = read_jsonl(output_dir / "evidence_store.jsonl")
    block_ids = {block["text_block_id"] for block in read_jsonl(output_dir / "text_blocks.jsonl")}
    section_ids = {section["section_id"] for section in read_jsonl(output_dir / "section_index.jsonl")}

    assert evidence
    for item in evidence:
        if item["source_element_type"] == "text_block":
            assert item["text_block_id"] in block_ids
            assert item["source_element_id"] in block_ids
        if item["section_id"] is not None:
            assert item["section_id"] in section_ids


def test_summary_contains_evidence_counters(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_summary_evidence_v04")
    assert result.returncode == 0, result.stderr

    summary = read_json(output_dir / "extraction_summary.json")
    evidence = read_jsonl(output_dir / "evidence_store.jsonl")

    for key in {
        "evidence_count",
        "section_heading_evidence_count",
        "paragraph_evidence_count",
        "evidence_without_section_count",
        "evidence_review_required_count",
    }:
        assert key in summary
    assert summary["evidence_count"] == len(evidence)
    assert summary["section_heading_evidence_count"] > 0
    assert summary["paragraph_evidence_count"] > 0


def test_quality_report_contains_evidence_checks(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_quality_evidence_v04")
    assert result.returncode == 0, result.stderr

    checks = read_jsonl(output_dir / "quality_report.jsonl")
    check_names = {check["check_name"] for check in checks}

    for check_name in {
        "evidence_store_created",
        "evidence_source_exists",
        "evidence_section_link_valid",
        "evidence_bbox_available",
        "evidence_quote_not_empty",
        "evidence_without_section_warning",
        "no_evidence_created_warning",
    }:
        assert check_name in check_names


def test_evidence_statistics_contains_expected_fields(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_stats_evidence_v04")
    assert result.returncode == 0, result.stderr

    stats = read_json(output_dir / "evidence_statistics.json")
    assert stats["evidence_count"] > 0
    assert "evidence_type_distribution" in stats
    assert "evidence_by_section" in stats
    assert "sample_section_heading_evidence" in stats
    assert "sample_paragraph_evidence" in stats

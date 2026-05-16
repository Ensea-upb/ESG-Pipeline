from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli


def _candidate_by_text(candidates, text):
    for candidate in candidates:
        if candidate["text"] == text:
            return candidate
    raise AssertionError(f"Candidate not found: {text}")


def test_contents_is_rejected_as_toc_heading(require_pdfplumber, section_stabilization_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_stabilization_pdf, output_dir, document_id="doc_v031")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(read_jsonl(output_dir / "section_candidates.jsonl"), "CONTENTS")
    assert candidate["candidate_status"] == "rejected_toc_heading"


def test_universal_registration_document_is_rejected(require_pdfplumber, section_stabilization_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_stabilization_pdf, output_dir, document_id="doc_v031_doc_title")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(read_jsonl(output_dir / "section_candidates.jsonl"), "UNIVERSAL REGISTRATION DOCUMENT")
    assert candidate["candidate_status"] in {"rejected_document_title", "rejected_front_matter"}


def test_fiscal_year_ended_is_rejected_front_matter(require_pdfplumber, section_stabilization_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_stabilization_pdf, output_dir, document_id="doc_v031_front")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(read_jsonl(output_dir / "section_candidates.jsonl"), "FISCAL YEAR ENDED DECEMBER 31, 2024")
    assert candidate["candidate_status"] == "rejected_front_matter"


def test_brand_timeline_year_is_rejected(require_pdfplumber, section_stabilization_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_stabilization_pdf, output_dir, document_id="doc_v031_timeline")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(read_jsonl(output_dir / "section_candidates.jsonl"), "1952 Givenchy")
    assert candidate["candidate_status"] == "rejected_timeline_like"
    assert candidate["is_timeline_like"] is True


def test_chateau_timeline_is_rejected_and_not_water(require_pdfplumber, section_stabilization_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_stabilization_pdf, output_dir, document_id="doc_v031_chateau")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(read_jsonl(output_dir / "section_candidates.jsonl"), "1916 Acqua di Parma Chateau d Esclans")
    assert candidate["candidate_status"] == "rejected_timeline_like"
    sections = read_jsonl(output_dir / "section_index.jsonl")
    assert all(section["section_title"] != "1916 Acqua di Parma Chateau d Esclans" for section in sections)
    assert all(section["section_type"] != "water" for section in sections)


def test_numeric_value_is_rejected(require_pdfplumber, section_stabilization_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_stabilization_pdf, output_dir, document_id="doc_v031_numeric")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(read_jsonl(output_dir / "section_candidates.jsonl"), "19,571 ( EUR millions)")
    assert candidate["candidate_status"] == "rejected_numeric_value"
    assert candidate["is_numeric_value_like"] is True


def test_true_financial_highlights_can_be_accepted(require_pdfplumber, section_stabilization_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_stabilization_pdf, output_dir, document_id="doc_v031_highlights")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(read_jsonl(output_dir / "section_candidates.jsonl"), "FINANCIAL HIGHLIGHTS")
    assert candidate["candidate_status"] == "accepted"


def test_true_risk_factors_can_be_accepted(require_pdfplumber, section_stabilization_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_stabilization_pdf, output_dir, document_id="doc_v031_risk")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(read_jsonl(output_dir / "section_candidates.jsonl"), "RISK FACTORS AND MANAGEMENT")
    assert candidate["candidate_status"] == "accepted"
    sections = read_jsonl(output_dir / "section_index.jsonl")
    risk_sections = [section for section in sections if section["section_title"] == "RISK FACTORS AND MANAGEMENT"]
    assert risk_sections
    assert risk_sections[0]["section_type"] == "risk_management"


def test_v031_section_ranges_are_valid(require_pdfplumber, section_stabilization_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_stabilization_pdf, output_dir, document_id="doc_v031_ranges")
    assert result.returncode == 0, result.stderr

    sections = read_jsonl(output_dir / "section_index.jsonl")
    assert sections
    assert all(section["page_start"] <= section["page_end"] for section in sections)


def test_v031_summary_and_statistics_have_new_counts(require_pdfplumber, section_stabilization_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_stabilization_pdf, output_dir, document_id="doc_v031_counts")
    assert result.returncode == 0, result.stderr

    summary = read_json(output_dir / "extraction_summary.json")
    stats = read_json(output_dir / "section_statistics.json")
    for key in {
        "rejected_cover_page_count",
        "rejected_toc_heading_count",
        "rejected_numeric_value_count",
        "rejected_front_matter_count",
        "rejected_document_title_count",
        "section_type_unknown_ratio",
    }:
        assert key in summary
    for key in {
        "sample_rejected_numeric_values",
        "sample_rejected_front_matter",
        "sample_rejected_timeline_like",
    }:
        assert key in stats

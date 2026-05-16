from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli


def test_section_outputs_are_produced(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_sections_v03")
    assert result.returncode == 0, result.stderr

    assert (output_dir / "section_index.jsonl").exists()
    assert (output_dir / "section_candidates.jsonl").exists()


def test_toc_entries_do_not_become_sections(require_pdfplumber, toc_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(toc_pdf, output_dir, document_id="doc_toc_sections_v03")
    assert result.returncode == 0, result.stderr

    candidates = read_jsonl(output_dir / "section_candidates.jsonl")
    sections = read_jsonl(output_dir / "section_index.jsonl")
    assert any(candidate["candidate_status"] == "rejected_toc_entry" for candidate in candidates)
    section_titles = {section["section_title"] for section in sections}
    rejected_toc_texts = {
        candidate["text"]
        for candidate in candidates
        if candidate["candidate_status"] == "rejected_toc_entry"
    }
    assert section_titles.isdisjoint(rejected_toc_texts)


def test_footer_header_footnote_do_not_become_sections(require_pdfplumber, footnote_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(footnote_pdf, output_dir, document_id="doc_footnote_sections_v03")
    assert result.returncode == 0, result.stderr

    candidates = read_jsonl(output_dir / "section_candidates.jsonl")
    sections = read_jsonl(output_dir / "section_index.jsonl")
    assert any(candidate["candidate_status"] == "rejected_footnote" for candidate in candidates)
    assert sections == []


def test_timeline_like_title_is_rejected(require_pdfplumber, timeline_title_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(timeline_title_pdf, output_dir, document_id="doc_timeline_v03")
    assert result.returncode == 0, result.stderr

    candidates = read_jsonl(output_dir / "section_candidates.jsonl")
    assert any(
        candidate["candidate_status"] == "rejected_timeline_like"
        and "1365" in candidate["text"]
        for candidate in candidates
    )


def test_all_sections_have_valid_ranges(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_ranges_v03")
    assert result.returncode == 0, result.stderr

    sections = read_jsonl(output_dir / "section_index.jsonl")
    assert sections
    assert all(section["page_start"] <= section["page_end"] for section in sections)


def test_two_headings_same_page_do_not_create_negative_range(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_same_page_v03")
    assert result.returncode == 0, result.stderr

    sections = read_jsonl(output_dir / "section_index.jsonl")
    assert len(sections) >= 2
    assert all(section["page_start"] == 1 and section["page_end"] == 1 for section in sections)


def test_summary_contains_section_counters(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_summary_sections_v03")
    assert result.returncode == 0, result.stderr

    summary = read_json(output_dir / "extraction_summary.json")
    for key in {
        "section_candidates_count",
        "section_candidates_accepted_count",
        "section_candidates_rejected_count",
        "sections_count",
        "sections_review_required_count",
        "section_types_distribution",
    }:
        assert key in summary
    assert summary["sections_count"] >= 3


def test_section_statistics_is_produced(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_stats_sections_v03")
    assert result.returncode == 0, result.stderr

    stats = read_json(output_dir / "section_statistics.json")
    assert stats["sections_count"] >= 3
    assert "rejection_reasons_distribution" in stats
    assert "sample_sections" in stats

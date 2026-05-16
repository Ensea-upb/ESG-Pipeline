from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli


def _candidate_by_text(candidates, text):
    for candidate in candidates:
        if candidate["text"] == text:
            return candidate
    raise AssertionError(f"Candidate not found: {text}")


def test_parenthetical_fragment_is_rejected_or_merged(require_pdfplumber, section_false_positive_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_false_positive_pdf, output_dir, document_id="doc_v032_frag")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(read_jsonl(output_dir / "section_candidates.jsonl"), "(FROM FEBRUARY 1, 2025)")
    assert candidate["candidate_status"] == "rejected_heading_fragment"


def test_of_the_group_fragment_is_rejected(require_pdfplumber, section_false_positive_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_false_positive_pdf, output_dir, document_id="doc_v032_of_group")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(read_jsonl(output_dir / "section_candidates.jsonl"), "OF THE GROUP AS OF DECEMBER 31, 2024")
    assert candidate["candidate_status"] == "rejected_heading_fragment"


def test_business_overview_heading_is_merged(require_pdfplumber, section_false_positive_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_false_positive_pdf, output_dir, document_id="doc_v032_merge")
    assert result.returncode == 0, result.stderr

    candidates = read_jsonl(output_dir / "section_candidates.jsonl")
    first = _candidate_by_text(candidates, "BUSINESS OVERVIEW,")
    second = _candidate_by_text(candidates, "HIGHLIGHTS AND OUTLOOK")
    assert first["was_merged_heading"] is True
    assert first["normalized_heading_text"] == "BUSINESS OVERVIEW, HIGHLIGHTS AND OUTLOOK"
    assert len(first["source_heading_block_ids"]) == 2
    assert second["candidate_status"] == "rejected_heading_fragment"


def test_org_chart_labels_do_not_open_sections(require_pdfplumber, section_false_positive_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_false_positive_pdf, output_dir, document_id="doc_v032_org")
    assert result.returncode == 0, result.stderr

    candidates = read_jsonl(output_dir / "section_candidates.jsonl")
    for text in {"LVMH", "OTHER HOLDING", "COMPANIES"}:
        candidate = _candidate_by_text(candidates, text)
        assert candidate["candidate_status"] in {"rejected_org_chart_like", "rejected_heading_fragment"}


def test_percentage_diagram_line_is_rejected(require_pdfplumber, section_false_positive_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_false_positive_pdf, output_dir, document_id="doc_v032_pct")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(
        read_jsonl(output_dir / "section_candidates.jsonl"),
        "100% 50% Citadelles 100% 100% Pelham Media",
    )
    assert candidate["candidate_status"] in {
        "rejected_org_chart_like",
        "rejected_diagram_like",
        "rejected_numeric_value",
    }


def test_sentence_like_heading_is_rejected(require_pdfplumber, section_false_positive_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_false_positive_pdf, output_dir, document_id="doc_v032_sentence")
    assert result.returncode == 0, result.stderr

    candidate = _candidate_by_text(
        read_jsonl(output_dir / "section_candidates.jsonl"),
        "34,000 hectares that can be legally used for production. There",
    )
    assert candidate["candidate_status"] in {
        "rejected_sentence_like_heading",
        "rejected_numeric_value",
    }


def test_accepted_candidates_meet_threshold(require_pdfplumber, section_false_positive_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_false_positive_pdf, output_dir, document_id="doc_v032_score")
    assert result.returncode == 0, result.stderr

    summary = read_json(output_dir / "extraction_summary.json")
    threshold = summary["candidate_score_threshold"]
    candidates = read_jsonl(output_dir / "section_candidates.jsonl")
    accepted = [candidate for candidate in candidates if candidate["candidate_status"] == "accepted"]
    assert accepted
    assert all(candidate["candidate_score"] >= threshold for candidate in accepted)


def test_v032_section_ranges_are_valid(require_pdfplumber, section_false_positive_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_false_positive_pdf, output_dir, document_id="doc_v032_ranges")
    assert result.returncode == 0, result.stderr

    sections = read_jsonl(output_dir / "section_index.jsonl")
    assert all(section["page_start"] <= section["page_end"] for section in sections)


def test_v032_statistics_contains_new_counters(require_pdfplumber, section_false_positive_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_false_positive_pdf, output_dir, document_id="doc_v032_stats")
    assert result.returncode == 0, result.stderr

    stats = read_json(output_dir / "section_statistics.json")
    for key in {
        "rejected_heading_fragment_count",
        "rejected_org_chart_like_count",
        "rejected_diagram_like_count",
        "rejected_sentence_like_count",
        "merged_headings_count",
        "low_confidence_rejected_count",
        "sample_rejected_heading_fragments",
        "sample_rejected_org_chart_like",
        "sample_rejected_sentence_like",
        "sample_merged_headings",
    }:
        assert key in stats

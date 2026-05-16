from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli, write_test_pdf


def suspicious_mismatch_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "suspicious_mismatch.pdf",
        [[
            "REPORT ON THE CERTIFICATION OF SUSTAINABILITY REPORTING",
            "This document is a free translation for readers.",
            "The history of the group includes brands and maisons.",
            "Chronology and brand names are presented in this part.",
            "LVMH brands and historical background continue here.",
        ]],
    )


def test_suspicious_sections_output_is_produced(require_pdfplumber, section_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(section_pdf, output_dir, document_id="doc_suspicious_output_v042")
    assert result.returncode == 0, result.stderr

    assert (output_dir / "suspicious_sections.jsonl").exists()


def test_title_content_mismatch_marks_section_suspicious(require_pdfplumber, tmp_path: Path):
    pdf_path = suspicious_mismatch_pdf(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(pdf_path, output_dir, document_id="doc_mismatch_v042")
    assert result.returncode == 0, result.stderr

    sections = read_jsonl(output_dir / "section_index.jsonl")
    suspicious = read_jsonl(output_dir / "suspicious_sections.jsonl")
    target = next(
        section for section in sections
        if "CERTIFICATION" in section["section_title"]
    )

    assert target["is_suspicious_section"] is True
    assert "title_content_mismatch" in target["suspicion_reasons"]
    assert target["section_quality_score"] < 0.75
    assert suspicious
    assert suspicious[0]["section_id"] == target["section_id"]


def test_evidence_policy_is_propagated_to_evidence(require_pdfplumber, tmp_path: Path):
    pdf_path = suspicious_mismatch_pdf(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(pdf_path, output_dir, document_id="doc_policy_v042")
    assert result.returncode == 0, result.stderr

    sections = read_jsonl(output_dir / "section_index.jsonl")
    evidence = read_jsonl(output_dir / "evidence_store.jsonl")
    target = next(section for section in sections if section["evidence_policy"] in {"quarantine", "review_required"})
    linked = [item for item in evidence if item["section_id"] == target["section_id"]]

    assert linked
    assert all(item["evidence_policy"] == target["evidence_policy"] for item in linked)
    assert all(item["section_quality_score"] == target["section_quality_score"] for item in linked)
    assert all(item["section_is_suspicious"] is True for item in linked)


def test_quarantined_evidence_is_marked_and_retained(require_pdfplumber, tmp_path: Path):
    pdf_path = suspicious_mismatch_pdf(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(pdf_path, output_dir, document_id="doc_quarantine_v042")
    assert result.returncode == 0, result.stderr

    evidence = read_jsonl(output_dir / "evidence_store.jsonl")
    quarantined = [item for item in evidence if item["evidence_policy"] == "quarantine"]

    assert quarantined
    assert all(item["is_quarantined_evidence"] is True for item in quarantined)
    assert all(item["review_required"] is True for item in quarantined)
    assert len(evidence) >= len(quarantined)


def test_evidence_statistics_contains_policy_counters(require_pdfplumber, tmp_path: Path):
    pdf_path = suspicious_mismatch_pdf(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(pdf_path, output_dir, document_id="doc_stats_policy_v042")
    assert result.returncode == 0, result.stderr

    stats = read_json(output_dir / "evidence_statistics.json")
    assert stats["suspicious_sections_count"] >= 1
    assert stats["quarantined_evidence_count"] >= 1
    assert "evidence_policy_distribution" in stats
    assert "quarantine" in stats["evidence_policy_distribution"]


def test_section_statistics_contains_policy_counters(require_pdfplumber, tmp_path: Path):
    pdf_path = suspicious_mismatch_pdf(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(pdf_path, output_dir, document_id="doc_section_stats_policy_v042")
    assert result.returncode == 0, result.stderr

    stats = read_json(output_dir / "section_statistics.json")
    assert stats["suspicious_sections_count"] >= 1
    assert "section_quality_score_distribution" in stats
    assert "evidence_policy_distribution" in stats
    assert "quarantine" in stats["evidence_policy_distribution"]


def test_summary_contains_policy_counters(require_pdfplumber, tmp_path: Path):
    pdf_path = suspicious_mismatch_pdf(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(pdf_path, output_dir, document_id="doc_summary_policy_v042")
    assert result.returncode == 0, result.stderr

    summary = read_json(output_dir / "extraction_summary.json")
    assert summary["suspicious_sections_count"] >= 1
    assert summary["quarantined_evidence_count"] >= 1
    assert "evidence_policy_distribution" in summary
    assert summary["min_section_quality_score"] < 0.75


def test_quality_report_contains_v042_checks(require_pdfplumber, tmp_path: Path):
    pdf_path = suspicious_mismatch_pdf(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(pdf_path, output_dir, document_id="doc_quality_policy_v042")
    assert result.returncode == 0, result.stderr

    check_names = {check["check_name"] for check in read_jsonl(output_dir / "quality_report.jsonl")}
    for check_name in {
        "suspicious_sections_detected",
        "section_quality_score_computed",
        "evidence_policy_assigned",
        "quarantined_evidence_detected",
        "evidence_policy_consistency_check",
        "suspicious_section_evidence_retained",
    }:
        assert check_name in check_names

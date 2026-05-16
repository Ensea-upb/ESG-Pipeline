from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli, write_test_pdf


def _partially_ready_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "partial_audit.pdf",
        [[
            "REPORT ON THE CERTIFICATION OF SUSTAINABILITY REPORTING",
            "This document is a free translation for readers.",
            "The history of the group includes brands and maisons.",
            "Figure 1 Greenhouse gas emissions trend",
            "total emissions scope 1 tco2 headcount revenue eur million",
            "breakdown by region consumption gwh mwh ratio",
        ]],
    )


def test_audit_outputs_are_produced(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v08_outputs")
    assert result.returncode == 0, result.stderr

    assert (out / "consistency_report.json").exists()
    assert (out / "audit_findings.jsonl").exists()
    assert (out / "document_audit_report.md").exists()


def test_consistency_report_contains_overall_status(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v08_consistency")
    assert result.returncode == 0, result.stderr

    report = read_json(out / "consistency_report.json")
    assert report["overall_status"] in {"pass", "warning", "fail"}


def test_findings_include_warning_for_partially_ready_document(require_pdfplumber, tmp_path: Path):
    pdf = _partially_ready_pdf(tmp_path)
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="v08_partial")
    assert result.returncode == 0, result.stderr

    inventory = read_json(out / "document_inventory.json")
    findings = read_jsonl(out / "audit_findings.jsonl")
    if inventory["extraction_readiness_status"] == "partially_ready":
        assert any(f["status"] in {"warning", "pass"} for f in findings)


def test_markdown_report_contains_required_sections(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v08_markdown")
    assert result.returncode == 0, result.stderr

    text = (out / "document_audit_report.md").read_text(encoding="utf-8")
    for expected in {
        "Document Audit Report",
        "Extraction status",
        "Evidence overview",
        "Tables audit",
        "Figures audit",
        "Readiness decision",
        "Limitations",
    }:
        assert expected in text


def test_fragile_evidence_is_not_eligible(require_pdfplumber, tmp_path: Path):
    pdf = _partially_ready_pdf(tmp_path)
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="v08_policy")
    assert result.returncode == 0, result.stderr

    multimodal = read_jsonl(out / "multimodal_evidence_index.jsonl")
    for item in multimodal:
        if item["is_quarantined_evidence"]:
            assert item["downstream_use_policy"] == "exclude_from_automatic_extraction"
        if item["review_required"]:
            assert item["downstream_use_policy"] != "eligible_for_future_extraction"


def test_multimodal_ids_and_counts_are_consistent(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v08_counts")
    assert result.returncode == 0, result.stderr

    evidence = read_jsonl(out / "evidence_store.jsonl")
    multimodal = read_jsonl(out / "multimodal_evidence_index.jsonl")
    stats = read_json(out / "multimodal_statistics.json")
    assert {e["evidence_id"] for e in evidence} == {m["evidence_id"] for m in multimodal}
    assert stats["total_multimodal_evidences"] == len(evidence)


def test_summary_contains_audit_counters(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v08_summary")
    assert result.returncode == 0, result.stderr

    summary = read_json(out / "extraction_summary.json")
    for key in {
        "consistency_report_created",
        "audit_findings_count",
        "critical_audit_findings_count",
        "major_audit_findings_count",
        "document_audit_report_created",
        "audit_overall_status",
    }:
        assert key in summary


def test_quality_report_contains_audit_checks(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v08_quality")
    assert result.returncode == 0, result.stderr

    check_names = {check["check_name"] for check in read_jsonl(out / "quality_report.jsonl")}
    for check_name in {
        "consistency_report_created",
        "audit_findings_created",
        "document_audit_report_created",
        "cross_file_counts_consistent",
        "evidence_references_valid",
        "multimodal_policy_consistent",
        "readiness_status_explained",
        "no_esg_extraction_performed",
    }:
        assert check_name in check_names

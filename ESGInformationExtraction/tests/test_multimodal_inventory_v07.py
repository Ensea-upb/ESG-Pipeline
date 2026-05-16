from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli, write_test_pdf


def _mixed_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "mixed_multimodal.pdf",
        [[
            "REPORT ON THE CERTIFICATION OF SUSTAINABILITY REPORTING",
            "This document is a free translation for readers.",
            "The history of the group includes brands and maisons.",
            "Figure 1 Greenhouse gas emissions trend",
            "total emissions scope 1 tco2 headcount revenue eur million",
            "breakdown by region consumption gwh mwh ratio",
        ]],
    )


def test_inventory_outputs_are_produced(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v07_outputs")
    assert result.returncode == 0, result.stderr

    assert (out / "document_inventory.json").exists()
    assert (out / "multimodal_evidence_index.jsonl").exists()
    assert (out / "multimodal_statistics.json").exists()


def test_each_evidence_appears_in_multimodal_index(require_pdfplumber, tmp_path: Path):
    pdf = _mixed_pdf(tmp_path)
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="v07_all_evidence")
    assert result.returncode == 0, result.stderr

    evidence = read_jsonl(out / "evidence_store.jsonl")
    multimodal = read_jsonl(out / "multimodal_evidence_index.jsonl")
    assert {item["evidence_id"] for item in evidence} == {item["evidence_id"] for item in multimodal}


def test_source_modality_assignments(require_pdfplumber, table_pdf: Path, figure_pdf: Path, section_pdf: Path, tmp_path: Path):
    for pdf, document_id in [
        (table_pdf, "v07_table_modality"),
        (figure_pdf, "v07_figure_modality"),
        (section_pdf, "v07_text_modality"),
    ]:
        out = tmp_path / document_id
        result = run_cli(pdf, out, document_id=document_id)
        assert result.returncode == 0, result.stderr
        multimodal = read_jsonl(out / "multimodal_evidence_index.jsonl")
        assert all(item["source_modality"] in {"text", "table", "figure"} for item in multimodal)
        for item in multimodal:
            if item["evidence_type"] == "table":
                assert item["source_modality"] == "table"
            if item["evidence_type"] == "figure":
                assert item["source_modality"] == "figure"
            if item["evidence_type"] in {"section_heading", "paragraph"}:
                assert item["source_modality"] == "text"


def test_quarantine_and_review_are_not_eligible(require_pdfplumber, tmp_path: Path):
    pdf = _mixed_pdf(tmp_path)
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="v07_policy")
    assert result.returncode == 0, result.stderr

    multimodal = read_jsonl(out / "multimodal_evidence_index.jsonl")
    assert multimodal
    for item in multimodal:
        if item["evidence_policy"] == "quarantine":
            assert item["downstream_use_policy"] == "exclude_from_automatic_extraction"
        if item["review_required"]:
            assert item["downstream_use_policy"] != "eligible_for_future_extraction"


def test_multimodal_statistics_counts_are_coherent(require_pdfplumber, table_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(table_pdf, out, document_id="v07_stats")
    assert result.returncode == 0, result.stderr

    evidence = read_jsonl(out / "evidence_store.jsonl")
    multimodal = read_jsonl(out / "multimodal_evidence_index.jsonl")
    stats = read_json(out / "multimodal_statistics.json")

    assert stats["total_multimodal_evidences"] == len(multimodal) == len(evidence)
    assert sum(stats["evidence_by_modality"].values()) == len(multimodal)
    assert sum(stats["downstream_use_policy_distribution"].values()) == len(multimodal)


def test_summary_contains_multimodal_counters(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v07_summary")
    assert result.returncode == 0, result.stderr

    summary = read_json(out / "extraction_summary.json")
    for key in {
        "multimodal_evidence_count",
        "text_modality_evidence_count",
        "table_modality_evidence_count",
        "figure_modality_evidence_count",
        "eligible_for_future_extraction_count",
        "review_before_extraction_count",
        "excluded_from_automatic_extraction_count",
        "extraction_readiness_status",
    }:
        assert key in summary


def test_quality_report_contains_multimodal_checks(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v07_quality")
    assert result.returncode == 0, result.stderr

    checks = {check["check_name"] for check in read_jsonl(out / "quality_report.jsonl")}
    for check_name in {
        "document_inventory_created",
        "multimodal_evidence_index_created",
        "multimodal_statistics_created",
        "multimodal_evidence_policy_valid",
        "downstream_use_policy_assigned",
        "modality_assignment_valid",
        "quarantined_evidence_excluded_from_automatic_extraction",
        "review_required_evidence_not_marked_eligible",
        "multimodal_counts_consistent",
    }:
        assert check_name in checks


def test_document_inventory_contains_readiness_status(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v07_inventory")
    assert result.returncode == 0, result.stderr

    inventory = read_json(out / "document_inventory.json")
    assert inventory["extraction_readiness_status"] in {
        "ready_for_experimental_extraction",
        "partially_ready",
        "not_ready",
    }
    assert "extraction_readiness_reasons" in inventory

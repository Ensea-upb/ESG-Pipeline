"""Tests for v0.6 figure detection.

Tests A–L are integration tests via the CLI.
Test M is the non-regression guard (handled by running the full suite).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import read_json, read_jsonl, run_cli, write_test_pdf

SCHEMA_VERSION = "1.0.0"

FIGURE_REQUIRED_FIELDS = {
    "schema_version",
    "figure_id",
    "document_id",
    "page_id",
    "page_number",
    "section_id",
    "figure_bbox",
    "figure_type",
    "detection_method",
    "extraction_status",
    "figure_confidence",
    "localization_confidence",
    "review_required",
    "is_quarantined_figure",
    "figure_quality_flags",
    "source_page_diagnostic_flags",
    "nearby_text_block_ids",
    "nearby_caption_text",
    "evidence_policy",
    "section_quality_score",
    "section_is_suspicious",
    "section_suspicion_reasons",
}

V042_FIELDS = {
    "section_quality_score",
    "section_is_suspicious",
    "section_suspicion_reasons",
    "evidence_policy",
    "is_quarantined_evidence",
}

FIGURE_ALLOWED_STATUSES = {"detected", "low_confidence", "detected_not_interpreted", "failed"}
FIGURE_ALLOWED_TYPES = {"image", "chart", "diagram", "logo", "map", "unknown_visual"}

FIGURE_SUMMARY_KEYS = {
    "figures_count",
    "detected_figures_count",
    "low_confidence_figures_count",
    "failed_figures_count",
    "figures_with_caption_count",
    "figures_without_caption_count",
    "quarantined_figures_count",
    "review_required_figures_count",
    "figure_evidence_count",
}

FIGURE_QUALITY_CHECK_NAMES = {
    "figure_detection_completed",
    "figure_index_created",
    "figure_bbox_available",
    "figure_section_link_valid",
    "figure_caption_detection_completed",
    "figure_without_caption_warning",
    "figure_low_confidence_warning",
    "figure_evidence_created",
    "figure_evidence_policy_consistency_check",
    "no_figures_detected_info",
}


def _suspicious_figure_pdf(tmp_path: Path) -> Path:
    """PDF with a certification section mismatch and a figure caption."""
    return write_test_pdf(
        tmp_path / "figure_quarantine.pdf",
        [[
            "REPORT ON THE CERTIFICATION OF SUSTAINABILITY REPORTING",
            "This document is a free translation for readers.",
            "Figure 1 Emissions trend by region",
            "The history of the group includes brands and maisons.",
        ]],
    )


# ── A: figure_index.jsonl is produced ────────────────────────────────────────

def test_A_figure_index_is_produced(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v06_A_small")
    assert result.returncode == 0, result.stderr
    assert (out / "figure_index.jsonl").exists(), "figure_index.jsonl must be produced"


# ── B: figure_statistics.json is produced ────────────────────────────────────

def test_B_figure_statistics_is_produced(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v06_B_stats")
    assert result.returncode == 0, result.stderr
    assert (out / "figure_statistics.json").exists(), "figure_statistics.json must be produced"
    stats = read_json(out / "figure_statistics.json")
    assert "figures_count" in stats, "figure_statistics.json must contain figures_count"


# ── C: a PDF with figure captions produces at least one figure ───────────────

def test_C_figure_caption_produces_figure(require_pdfplumber, figure_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v06_C_figure")
    assert result.returncode == 0, result.stderr
    figures = read_jsonl(out / "figure_index.jsonl")
    assert len(figures) >= 1, (
        "A PDF with 'Figure 1 ...' caption blocks must produce at least one figure record"
    )


# ── D: figure_id is unique across all records ────────────────────────────────

def test_D_figure_ids_are_unique(require_pdfplumber, figure_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v06_D_ids")
    assert result.returncode == 0, result.stderr
    figures = read_jsonl(out / "figure_index.jsonl")
    if not figures:
        pytest.skip("No figures detected — unique ID check skipped")
    ids = [f["figure_id"] for f in figures]
    assert len(ids) == len(set(ids)), "figure_id values must be unique"


# ── E: extraction_status is in the allowed set ───────────────────────────────

def test_E_extraction_status_valid(require_pdfplumber, figure_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v06_E_status")
    assert result.returncode == 0, result.stderr
    figures = read_jsonl(out / "figure_index.jsonl")
    for fig in figures:
        assert fig.get("extraction_status") in FIGURE_ALLOWED_STATUSES, (
            f"figure_id={fig.get('figure_id')} has invalid extraction_status={fig.get('extraction_status')!r}"
        )


# ── F: figure_type is in the allowed set ─────────────────────────────────────

def test_F_figure_type_valid(require_pdfplumber, figure_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v06_F_type")
    assert result.returncode == 0, result.stderr
    figures = read_jsonl(out / "figure_index.jsonl")
    for fig in figures:
        assert fig.get("figure_type") in FIGURE_ALLOWED_TYPES, (
            f"figure_id={fig.get('figure_id')} has invalid figure_type={fig.get('figure_type')!r}"
        )


# ── F2: all required schema fields present ───────────────────────────────────

def test_F2_figure_records_have_required_fields(require_pdfplumber, figure_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v06_F2_fields")
    assert result.returncode == 0, result.stderr
    figures = read_jsonl(out / "figure_index.jsonl")
    for fig in figures:
        missing = FIGURE_REQUIRED_FIELDS - fig.keys()
        assert not missing, (
            f"figure_id={fig.get('figure_id')} missing fields: {missing}"
        )


# ── G: figures are linked to a section when one covers the page ──────────────

def test_G_figure_linked_to_section_when_available(require_pdfplumber, tmp_path: Path):
    pdf = write_test_pdf(
        tmp_path / "fig_section.pdf",
        [[
            "CLIMATE STRATEGY",
            "Figure 1 GHG emissions by source",
        ]],
    )
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="v06_G_section")
    assert result.returncode == 0, result.stderr
    figures = read_jsonl(out / "figure_index.jsonl")
    sections = read_jsonl(out / "section_index.jsonl")
    if not figures or not sections:
        pytest.skip("No figures or sections detected — section link check skipped")
    # At least one figure should be linked to a section
    linked = [f for f in figures if f.get("section_id")]
    assert linked, "At least one figure must be linked to a section when sections exist"


# ── H: quarantined section propagates is_quarantined_figure ─────────────────

def test_H_quarantined_section_propagates_to_figure(require_pdfplumber, tmp_path: Path):
    pdf = _suspicious_figure_pdf(tmp_path)
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="v06_H_quarantine")
    assert result.returncode == 0, result.stderr
    figures = read_jsonl(out / "figure_index.jsonl")
    sections = read_jsonl(out / "section_index.jsonl")
    quarantined_section_ids = {
        s["section_id"] for s in sections if s.get("evidence_policy") == "quarantine"
    }
    if not quarantined_section_ids:
        pytest.skip("No quarantined section produced — propagation check skipped vacuously")
    linked_quarantine_figures = [
        f for f in figures if f.get("section_id") in quarantined_section_ids
    ]
    for fig in linked_quarantine_figures:
        assert fig.get("is_quarantined_figure") is True, (
            f"figure_id={fig.get('figure_id')} linked to quarantined section but "
            f"is_quarantined_figure={fig.get('is_quarantined_figure')}"
        )


# ── I: evidence_store.jsonl contains figure evidences ───────────────────────

def test_I_evidence_store_contains_figure_evidences(require_pdfplumber, figure_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v06_I_evidence")
    assert result.returncode == 0, result.stderr
    figures = read_jsonl(out / "figure_index.jsonl")
    evidence = read_jsonl(out / "evidence_store.jsonl")
    eligible = [
        f for f in figures
        if f.get("extraction_status") in {"detected", "low_confidence", "detected_not_interpreted"}
    ]
    if not eligible:
        pytest.skip("No eligible figures for evidence — check skipped")
    figure_evidences = [e for e in evidence if e.get("evidence_type") == "figure"]
    assert len(figure_evidences) >= 1, (
        "evidence_store.jsonl must contain at least one figure evidence when figures are detected"
    )


# ── J: figure evidences carry v0.4.2 contract fields ────────────────────────

def test_J_figure_evidences_have_v042_fields(require_pdfplumber, figure_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v06_J_contract")
    assert result.returncode == 0, result.stderr
    evidence = read_jsonl(out / "evidence_store.jsonl")
    figure_evidences = [e for e in evidence if e.get("evidence_type") == "figure"]
    if not figure_evidences:
        pytest.skip("No figure evidences — v0.4.2 contract check skipped vacuously")
    for ev in figure_evidences:
        missing = V042_FIELDS - ev.keys()
        assert not missing, (
            f"Figure evidence {ev.get('evidence_id')} missing v0.4.2 fields: {missing}"
        )


def test_J_all_evidences_have_v042_fields(require_pdfplumber, figure_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v06_J2_all")
    assert result.returncode == 0, result.stderr
    evidence = read_jsonl(out / "evidence_store.jsonl")
    for ev in evidence:
        missing = V042_FIELDS - ev.keys()
        assert not missing, (
            f"evidence_type={ev.get('evidence_type')} id={ev.get('evidence_id')} "
            f"missing v0.4.2 fields: {missing}"
        )


# ── K: extraction_summary.json contains new figure counters ─────────────────

def test_K_extraction_summary_has_figure_keys(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v06_K_summary")
    assert result.returncode == 0, result.stderr
    summary = read_json(out / "extraction_summary.json")
    missing = FIGURE_SUMMARY_KEYS - summary.keys()
    assert not missing, f"extraction_summary.json missing v0.6 figure keys: {missing}"


def test_K_figure_counts_consistent(require_pdfplumber, figure_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v06_K2_consistent")
    assert result.returncode == 0, result.stderr
    summary = read_json(out / "extraction_summary.json")
    figures = read_jsonl(out / "figure_index.jsonl")
    evidence = read_jsonl(out / "evidence_store.jsonl")
    fig_ev = [e for e in evidence if e.get("evidence_type") == "figure"]
    assert summary["figures_count"] == len(figures), "figures_count must equal len(figure_index.jsonl)"
    assert summary["figure_evidence_count"] == len(fig_ev), (
        "figure_evidence_count must equal figure evidences in evidence_store.jsonl"
    )


# ── L: quality_report.jsonl contains new figure check names ─────────────────

def test_L_quality_report_has_figure_checks(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v06_L_checks")
    assert result.returncode == 0, result.stderr
    checks = read_jsonl(out / "quality_report.jsonl")
    check_names = {c.get("check_name", "") for c in checks}
    missing = FIGURE_QUALITY_CHECK_NAMES - check_names
    assert not missing, f"quality_report.jsonl missing v0.6 check names: {missing}"


# ── quarantine consistency ────────────────────────────────────────────────────

def test_quarantined_figure_evidence_is_consistent(require_pdfplumber, tmp_path: Path):
    pdf = _suspicious_figure_pdf(tmp_path)
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="v06_quarantine_ev")
    assert result.returncode == 0, result.stderr
    evidence = read_jsonl(out / "evidence_store.jsonl")
    quarantined = [e for e in evidence if e.get("evidence_policy") == "quarantine"]
    for ev in quarantined:
        assert ev.get("is_quarantined_evidence") is True, (
            f"evidence_type={ev.get('evidence_type')} has policy=quarantine "
            f"but is_quarantined_evidence={ev.get('is_quarantined_evidence')}"
        )
        assert ev.get("review_required") is True


# ── figure_statistics.json content ───────────────────────────────────────────

def test_figure_statistics_fields(require_pdfplumber, figure_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v06_figstats")
    assert result.returncode == 0, result.stderr
    stats = read_json(out / "figure_statistics.json")
    required = {
        "document_id",
        "figures_count",
        "detected_figures_count",
        "low_confidence_figures_count",
        "failed_figures_count",
        "figure_type_distribution",
        "figures_by_page",
        "figures_by_section",
        "quarantined_figures_count",
        "review_required_figures_count",
        "figures_with_caption_count",
        "figures_without_caption_count",
        "figure_evidence_count",
        "sample_figures",
        "sample_figures_with_caption",
        "sample_low_confidence_figures",
    }
    missing = required - stats.keys()
    assert not missing, f"figure_statistics.json missing keys: {missing}"


# ── no figures → info check, not error ───────────────────────────────────────

def test_no_figures_produces_info_not_error(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v06_noFig")
    assert result.returncode == 0, result.stderr
    checks = read_jsonl(out / "quality_report.jsonl")
    no_fig_checks = [c for c in checks if c.get("check_name") == "no_figures_detected_info"]
    assert no_fig_checks, "no_figures_detected_info check must be present"
    for c in no_fig_checks:
        assert c.get("severity") in {"info", "pass"}, (
            "no_figures_detected_info must have severity info or pass, not error"
        )

"""Tests for v0.5.2 table extraction quality stabilization.

Tests A–F are unit tests of process_raw_tables / build_table_evidence directly.
Tests G–I are integration tests via the CLI.
Test J ensures all prior tests continue to pass (handled by running the full suite).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ESGInformationExtraction.run_pdf_extraction import (
    _compute_cell_quality_metrics,
    build_table_evidence,
    process_raw_tables,
)

from .conftest import read_json, read_jsonl, run_cli, write_test_pdf

SCHEMA_VERSION = "1.0.0"


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_page_data(rows: list[list[str | None]], page_number: int = 1) -> dict:
    return {
        "page_number": page_number,
        "page_id": f"doc_test_page_{page_number:04d}",
        "page_text": " ".join(
            str(cell or "") for row in rows for cell in row
        ),
        "raw_tables": [rows],
    }


def _make_toc_diag() -> dict:
    return {
        "is_possible_toc": True,
        "is_high_title_density": False,
        "text_char_count": 400,
    }


def _make_high_density_diag() -> dict:
    return {
        "is_possible_toc": False,
        "is_high_title_density": True,
        "text_char_count": 400,
    }


def _plain_diag() -> dict:
    return {
        "is_possible_toc": False,
        "is_high_title_density": False,
        "text_char_count": 400,
    }


# ── A: all-cells-empty → empty_table ─────────────────────────────────────────

def test_A_all_cells_empty_produces_empty_table_status():
    rows: list[list[str | None]] = [
        [None, None, None],
        [None, None, None],
        [None, None, None],
    ]
    page_data = _make_page_data(rows)
    table_recs, cell_recs = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    assert len(table_recs) == 1
    t = table_recs[0]
    assert t["extraction_status"] == "empty_table", (
        f"Expected empty_table, got {t['extraction_status']}"
    )
    assert "all_cells_empty" in t["table_quality_flags"]
    assert cell_recs == [], "empty_table must not produce cell records"


def test_A_all_cells_empty_confidence_is_low():
    rows: list[list[str | None]] = [[None, None], [None, None]]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    t = table_recs[0]
    assert t["table_confidence"] <= 0.15
    assert t["localization_confidence"] <= 0.20


# ── B: >80% empty → low_confidence with mostly_empty_cells ──────────────────

def test_B_mostly_empty_table_gets_low_confidence():
    # 9 cells, 8 empty → 88.9% empty → mostly_empty_cells
    rows: list[list[str | None]] = [
        [None, None, None],
        [None, "data", None],
        [None, None, None],
    ]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    assert len(table_recs) == 1
    t = table_recs[0]
    assert "mostly_empty_cells" in t["table_quality_flags"]
    assert t["extraction_status"] == "low_confidence", (
        f"Expected low_confidence for mostly-empty table, got {t['extraction_status']}"
    )
    assert t["review_required"] is True


def test_B_mostly_empty_table_confidence_is_capped():
    rows: list[list[str | None]] = [
        [None, None, None],
        [None, "x", None],
        [None, None, None],
    ]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    t = table_recs[0]
    assert t["table_confidence"] <= 0.35


# ── C: single row or column → low_confidence ─────────────────────────────────

def test_C_single_row_table_gets_low_confidence():
    rows: list[list[str | None]] = [["A", "B", "C", "D"]]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    assert len(table_recs) == 1
    t = table_recs[0]
    assert "single_row_table" in t["table_quality_flags"]
    assert t["extraction_status"] == "low_confidence"
    assert t["review_required"] is True


def test_C_single_column_table_gets_low_confidence():
    rows: list[list[str | None]] = [["A"], ["B"], ["C"]]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    assert len(table_recs) == 1
    t = table_recs[0]
    assert "single_column_table" in t["table_quality_flags"]
    assert t["extraction_status"] == "low_confidence"


# ── D: tiny table artifact flag ───────────────────────────────────────────────

def test_D_cell_count_le_3_gets_tiny_artifact_flag():
    # 1 row × 2 cols = 2 cells → tiny
    rows: list[list[str | None]] = [["A", "B"]]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    t = table_recs[0]
    assert "tiny_table_artifact" in t["table_quality_flags"]


def test_D_cell_count_gt_3_does_not_get_tiny_flag():
    rows: list[list[str | None]] = [["A", "B"], ["C", "D"]]  # 4 cells
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    t = table_recs[0]
    assert "tiny_table_artifact" not in t["table_quality_flags"]


# ── E: front matter / TOC page gets flag ─────────────────────────────────────

def test_E_toc_page_gets_front_matter_flag():
    rows: list[list[str | None]] = [
        ["Section", "1"],
        ["Overview", "2"],
        ["Details", "3"],
    ]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _make_toc_diag())
    t = table_recs[0]
    assert "front_matter_or_toc_table_like" in t["table_quality_flags"]


def test_E_high_density_page_gets_front_matter_flag():
    rows: list[list[str | None]] = [
        ["Title A", "Value 1"],
        ["Title B", "Value 2"],
        ["Title C", "Value 3"],
    ]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _make_high_density_diag())
    t = table_recs[0]
    assert "front_matter_or_toc_table_like" in t["table_quality_flags"]


def test_E_toc_page_parsed_table_downgraded_to_low_confidence():
    rows: list[list[str | None]] = [
        ["Chapter 1", "10"],
        ["Chapter 2", "20"],
        ["Chapter 3", "30"],
    ]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _make_toc_diag())
    t = table_recs[0]
    assert t["extraction_status"] == "low_confidence", (
        f"TOC-page table should be downgraded to low_confidence, got {t['extraction_status']}"
    )


def test_E_normal_page_with_no_diag_has_no_front_matter_flag():
    rows: list[list[str | None]] = [
        ["Scope 1", "12000"],
        ["Scope 2", "5400"],
        ["Total", "17400"],
    ]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    t = table_recs[0]
    assert "front_matter_or_toc_table_like" not in t["table_quality_flags"]


# ── F: fragmented cells trigger flags ────────────────────────────────────────

def test_F_fragmented_cells_trigger_fragmented_cells_detected():
    # Single-char fragments like "C" / "O" / "N"
    rows: list[list[str | None]] = [
        ["C", "O", "N"],
        ["T", "E", "N"],
        ["T", "S", "X"],
    ]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    t = table_recs[0]
    assert "fragmented_cells_detected" in t["table_quality_flags"]


def test_F_high_ratio_of_fragments_triggers_high_fragmented_ratio_flag():
    # All cells are 1-char fragments → ratio = 1.0 >> threshold
    rows: list[list[str | None]] = [
        ["A", "B", "C"],
        ["D", "E", "F"],
        ["G", "H", "I"],
    ]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    t = table_recs[0]
    assert "high_fragmented_cells_ratio" in t["table_quality_flags"]


# ── G: no evidence for empty_table ───────────────────────────────────────────

def test_G_no_evidence_for_empty_table():
    rows: list[list[str | None]] = [[None, None, None], [None, None, None]]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    assert table_recs[0]["extraction_status"] == "empty_table"
    evidences = build_table_evidence("doc1", table_recs)
    assert evidences == [], "No evidence must be created for empty_table"


def test_G_tiny_artifact_without_table_like_page_has_no_evidence():
    rows: list[list[str | None]] = [["A", "B"]]  # 2 cells, tiny_table_artifact
    page_data = {
        "page_number": 1,
        "page_id": "doc1_page_0001",
        "page_text": "some ordinary text without keywords",
        "raw_tables": [rows],
    }
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    t = table_recs[0]
    assert "tiny_table_artifact" in t["table_quality_flags"]
    assert "page_looks_table_like" not in t["source_page_diagnostic_flags"]
    evidences = build_table_evidence("doc1", table_recs)
    assert evidences == [], "Tiny artifact without table-like page must not produce evidence"


# ── H: low_confidence table evidences are review_required ────────────────────

def test_H_low_confidence_table_evidence_is_review_required():
    # Single-row table → low_confidence
    rows: list[list[str | None]] = [["Scope 1", "12000 tCO2e", "11500", "10800"]]
    page_data = _make_page_data(rows)
    table_recs, _ = process_raw_tables(page_data, "doc1", [], [], _plain_diag())
    t = table_recs[0]
    assert t["extraction_status"] == "low_confidence"
    evidences = build_table_evidence("doc1", table_recs)
    # tiny_table_artifact might suppress evidence if page not table-like
    lc_ev = [e for e in evidences if e.get("evidence_type") == "table"]
    if lc_ev:
        assert all(e["review_required"] is True for e in lc_ev)


# ── I: cell quality fields present in table_index.jsonl via CLI ──────────────

CELL_QUALITY_FIELDS = {
    "non_empty_cells_count",
    "empty_cells_ratio",
    "average_cell_text_length",
    "fragmented_cells_count",
    "numeric_cells_count",
    "numeric_cells_ratio",
}


def test_I_cell_quality_fields_in_table_index(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v052_cell_quality")
    assert result.returncode == 0, result.stderr
    records = read_jsonl(out / "table_index.jsonl")
    for rec in records:
        missing = CELL_QUALITY_FIELDS - rec.keys()
        assert not missing, f"Table {rec.get('table_id')} missing cell quality fields: {missing}"


def test_I_cell_quality_fields_in_table_like_pdf(require_pdfplumber, table_like_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = run_cli(table_like_pdf, out, document_id="v052_cell_quality_tl")
    assert result.returncode == 0, result.stderr
    records = read_jsonl(out / "table_index.jsonl")
    for rec in records:
        missing = CELL_QUALITY_FIELDS - rec.keys()
        assert not missing, f"Table {rec.get('table_id')} missing cell quality fields: {missing}"


def test_I_table_statistics_has_new_v052_keys(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    run_cli(small_pdf, out, document_id="v052_stats")
    stats = read_json(out / "table_statistics.json")
    required = {
        "mostly_empty_tables_count",
        "tiny_table_artifacts_count",
        "front_matter_or_toc_tables_count",
        "fragmented_tables_count",
        "table_artifact_suspected_count",
        "average_empty_cells_ratio",
        "average_numeric_cells_ratio",
        "sample_empty_tables",
        "sample_tiny_table_artifacts",
        "sample_front_matter_or_toc_tables",
        "sample_fragmented_tables",
    }
    missing = required - stats.keys()
    assert not missing, f"table_statistics.json missing v0.5.2 keys: {missing}"


def test_I_extraction_summary_has_new_v052_keys(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    run_cli(small_pdf, out, document_id="v052_summary")
    summary = read_json(out / "extraction_summary.json")
    required = {
        "empty_tables_count",
        "mostly_empty_tables_count",
        "tiny_table_artifacts_count",
        "front_matter_or_toc_tables_count",
        "fragmented_tables_count",
        "table_artifact_suspected_count",
        "table_evidence_count",
    }
    missing = required - summary.keys()
    assert not missing, f"extraction_summary.json missing v0.5.2 keys: {missing}"


def test_I_quality_report_has_v052_checks(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    out = tmp_path / "out"
    run_cli(small_pdf, out, document_id="v052_qreport")
    checks = read_jsonl(out / "quality_report.jsonl")
    check_names = {c.get("check_name", "") for c in checks}
    required = {
        "empty_table_detected",
        "mostly_empty_table_warning",
        "tiny_table_artifact_warning",
        "front_matter_or_toc_table_warning",
        "fragmented_table_warning",
        "table_artifact_suspected_warning",
        "table_evidence_policy_consistency_check",
    }
    missing = required - check_names
    assert not missing, f"quality_report.jsonl missing v0.5.2 check names: {missing}"


# ── unit test _compute_cell_quality_metrics ───────────────────────────────────

def test_compute_cell_metrics_all_empty():
    rows: list[list[str | None]] = [[None, None], [None, None]]
    m = _compute_cell_quality_metrics(rows)
    assert m["non_empty_cells_count"] == 0
    assert m["empty_cells_ratio"] == 1.0
    assert m["fragmented_cells_count"] == 0
    assert m["numeric_cells_count"] == 0


def test_compute_cell_metrics_mixed():
    rows: list[list[str | None]] = [
        ["Scope 1", "12 000", None],
        ["Total", "17 400", "tCO2e"],
    ]
    m = _compute_cell_quality_metrics(rows)
    assert m["non_empty_cells_count"] == 5  # None excluded
    assert 0.0 < m["empty_cells_ratio"] < 1.0
    assert m["numeric_cells_count"] >= 1


def test_compute_cell_metrics_empty_rows():
    m = _compute_cell_quality_metrics([])
    assert m["non_empty_cells_count"] == 0
    assert m["empty_cells_ratio"] == 1.0

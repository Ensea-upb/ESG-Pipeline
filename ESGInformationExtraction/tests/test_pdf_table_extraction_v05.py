"""Tests for v0.5 table extraction engine."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from .conftest import run_cli, read_json, read_jsonl


# ── A: output files exist ────────────────────────────────────────────────────

def test_A_table_index_file_created(small_pdf, tmp_path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out)
    assert result.returncode == 0
    assert (out / "table_index.jsonl").exists(), "table_index.jsonl must be created"


def test_A_table_cells_file_created(small_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(small_pdf, out)
    assert (out / "table_cells.jsonl").exists(), "table_cells.jsonl must be created"


def test_A_table_statistics_file_created(small_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(small_pdf, out)
    assert (out / "table_statistics.json").exists(), "table_statistics.json must be created"


# ── B: table_index schema ───────────────────────────────────────────────────

def test_B_table_index_records_have_required_fields(table_pdf, tmp_path):
    out = tmp_path / "out"
    result = run_cli(table_pdf, out)
    assert result.returncode == 0
    records = read_jsonl(out / "table_index.jsonl")
    required = {
        "table_id", "document_id", "page_id", "page_number",
        "extraction_status", "row_count", "column_count", "cell_count",
        "table_confidence", "review_required",
    }
    for rec in records:
        missing = required - rec.keys()
        assert not missing, f"Missing fields in table record: {missing}"


# ── C: table_cells schema ───────────────────────────────────────────────────

def test_C_cell_records_have_required_fields(table_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(table_pdf, out)
    cells = read_jsonl(out / "table_cells.jsonl")
    required = {"cell_id", "table_id", "document_id", "row_index", "column_index", "text"}
    for cell in cells:
        missing = required - cell.keys()
        assert not missing, f"Missing fields in cell record: {missing}"


# ── D: table_statistics schema ──────────────────────────────────────────────

def test_D_table_statistics_has_expected_keys(table_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(table_pdf, out)
    stats = read_json(out / "table_statistics.json")
    required = {"document_id", "tables_count", "table_cells_count"}
    missing = required - stats.keys()
    assert not missing, f"Missing keys in table_statistics: {missing}"


# ── E: table_statistics counts match index/cells ────────────────────────────

def test_E_table_statistics_counts_consistent(table_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(table_pdf, out)
    stats = read_json(out / "table_statistics.json")
    records = read_jsonl(out / "table_index.jsonl")
    cells = read_jsonl(out / "table_cells.jsonl")
    assert stats["tables_count"] == len(records)
    assert stats["table_cells_count"] == len(cells)


# ── F: extraction_summary counters updated ──────────────────────────────────

def test_F_extraction_summary_tables_count(table_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(table_pdf, out)
    summary = read_json(out / "extraction_summary.json")
    assert "tables_count" in summary
    assert "table_cells_count" in summary
    assert isinstance(summary["tables_count"], int)
    assert isinstance(summary["table_cells_count"], int)


# ── G: parsed table has cells ───────────────────────────────────────────────

def test_G_parsed_table_produces_cells(table_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(table_pdf, out)
    records = read_jsonl(out / "table_index.jsonl")
    cells = read_jsonl(out / "table_cells.jsonl")
    parsed = [r for r in records if r.get("extraction_status") == "parsed"]
    if parsed:
        # Each parsed table should have at least one cell
        parsed_ids = {r["table_id"] for r in parsed}
        cells_for_parsed = [c for c in cells if c.get("table_id") in parsed_ids]
        assert cells_for_parsed, "Parsed tables must produce cell records"


# ── H: detected_not_parsed has no cells ─────────────────────────────────────

def test_H_detected_not_parsed_has_no_cells(table_like_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(table_like_pdf, out)
    records = read_jsonl(out / "table_index.jsonl")
    cells = read_jsonl(out / "table_cells.jsonl")
    not_parsed = [r for r in records if r.get("extraction_status") == "detected_not_parsed"]
    if not_parsed:
        np_ids = {r["table_id"] for r in not_parsed}
        cells_for_np = [c for c in cells if c.get("table_id") in np_ids]
        assert not cells_for_np, "detected_not_parsed tables must not produce cells"


# ── I: non-table PDF produces empty table files ─────────────────────────────

def test_I_small_pdf_may_have_no_tables(small_pdf, tmp_path):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out)
    assert result.returncode == 0
    records = read_jsonl(out / "table_index.jsonl")
    # May be empty or detected_not_parsed — never fails just because no tables
    assert isinstance(records, list)


# ── J: table evidence added to evidence_store ───────────────────────────────

def test_J_table_evidence_in_evidence_store(table_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(table_pdf, out)
    records = read_jsonl(out / "table_index.jsonl")
    parsed_or_detected = [
        r for r in records
        if r.get("extraction_status") in ("parsed", "detected_not_parsed", "low_confidence")
    ]
    if parsed_or_detected:
        evidence = read_jsonl(out / "evidence_store.jsonl")
        table_ev = [e for e in evidence if e.get("evidence_type") == "table"]
        assert table_ev, "Table evidence records must appear in evidence_store.jsonl"


# ── K: quality_report contains table checks ─────────────────────────────────

def test_K_quality_report_has_table_check(table_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(table_pdf, out)
    checks = read_jsonl(out / "quality_report.jsonl")
    check_names = {c.get("check_name") or c.get("check_type") or c.get("name", "") for c in checks}
    # At minimum the table_detection check should be present
    table_checks = [
        name for name in check_names
        if "table" in name.lower()
    ]
    assert table_checks, f"No table-related quality checks found. Checks: {sorted(check_names)}"


# ── L: table_id uniqueness ──────────────────────────────────────────────────

def test_L_table_ids_are_unique(table_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(table_pdf, out)
    records = read_jsonl(out / "table_index.jsonl")
    ids = [r.get("table_id") for r in records]
    assert len(ids) == len(set(ids)), "All table_id values must be unique"


# ── M: cell_id uniqueness ───────────────────────────────────────────────────

def test_M_cell_ids_are_unique(table_pdf, tmp_path):
    out = tmp_path / "out"
    run_cli(table_pdf, out)
    cells = read_jsonl(out / "table_cells.jsonl")
    ids = [c.get("cell_id") for c in cells]
    assert len(ids) == len(set(ids)), "All cell_id values must be unique"

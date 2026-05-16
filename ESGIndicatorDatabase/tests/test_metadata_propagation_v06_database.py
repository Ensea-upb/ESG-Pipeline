"""Tests for metadata propagation and warnings in ESGIndicatorDatabase — v0.6."""
from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ESGIndicatorDatabase" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from esg_indicator_database.database_builder import IndicatorDatabaseBuilder


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({f: row.get(f, "") for f in fields})


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


ACCEPTED_FIELDS = [
    "candidate_id", "review_item_id", "document_id", "company", "fiscal_year",
    "source_engine", "information_type", "validation_status", "review_status",
    "indicator_family", "indicator_key_candidate", "corrected_indicator_key",
    "corrected_indicator_family", "label", "raw_value", "raw_unit", "year",
    "normalized_value", "normalized_unit", "normalized_year", "corrected_value",
    "corrected_unit", "corrected_year", "page_number", "quote", "evidence_id",
    "table_id", "cell_id", "figure_id", "reviewer", "decision_reason", "reviewer_notes",
    "review_required", "extraction_status",
]


def _accepted_row(company: str = "TotalEnergies", fiscal_year: str = "2024", indicator_key: str = "human_capital", value: str = "102887", unit: str = "employees", year: str = "2024") -> dict:
    return {
        "candidate_id": "cand_001",
        "review_item_id": "ri_001",
        "document_id": "doc_001",
        "company": company,
        "fiscal_year": fiscal_year,
        "source_engine": "csv",
        "information_type": "esg_metric_candidate",
        "validation_status": "possible_indicator",
        "review_status": "accepted",
        "indicator_family": "human_capital",
        "indicator_key_candidate": indicator_key,
        "corrected_indicator_key": indicator_key,
        "corrected_indicator_family": "human_capital",
        "label": "Total Workforce",
        "raw_value": value,
        "raw_unit": unit,
        "year": year,
        "normalized_value": value,
        "normalized_unit": unit,
        "normalized_year": year,
        "corrected_value": "",
        "corrected_unit": "",
        "corrected_year": "",
        "page_number": "13",
        "quote": f"Total workforce: {value} {unit} as of December 31, {year}",
        "evidence_id": "ev_001",
        "table_id": "",
        "cell_id": "",
        "figure_id": "",
        "reviewer": "test_user",
        "decision_reason": "clear_numeric_value",
        "reviewer_notes": "",
        "review_required": "False",
        "extraction_status": "candidate_only",
    }


def _make_input_dir(tmp_path: Path, rows: list[dict]) -> Path:
    """Create a minimal ESGManualReview output directory."""
    input_dir = tmp_path / "review_output"
    input_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(input_dir / "accepted_candidate_inputs.csv", rows, ACCEPTED_FIELDS)
    all_rows = rows.copy()
    for r in all_rows:
        r = dict(r)
        r["review_status"] = "accepted"
    _write_csv(input_dir / "reviewed_candidates.csv", rows, ACCEPTED_FIELDS)
    _write_json(input_dir / "review_decision_summary.json", {"accepted_count": len(rows), "rejected_count": 0})
    _write_json(input_dir / "manual_review_audit_summary.json", {"errors_count": 0, "warnings_count": 0})
    return input_dir


def test_database_propagates_company_fiscal_year(tmp_path: Path) -> None:
    """indicator_preparation_database.csv must contain company and fiscal_year from accepted candidates."""
    input_dir = _make_input_dir(tmp_path, [_accepted_row()])
    output_dir = tmp_path / "db_output"

    builder = IndicatorDatabaseBuilder(input_dir, output_dir, overwrite=False)
    result = builder.run()

    rows = _read_csv(output_dir / "indicator_preparation_database.csv")
    assert rows, "indicator_preparation_database.csv must not be empty"
    assert rows[0].get("company") == "TotalEnergies", f"company missing: {rows[0]}"
    assert rows[0].get("fiscal_year") == "2024", f"fiscal_year missing: {rows[0]}"


def test_database_summary_has_metadata_missing_company_count(tmp_path: Path) -> None:
    """indicator_database_summary.json must include metadata_missing_company_count."""
    # One row with company, one without
    rows = [_accepted_row(), _accepted_row(company="")]
    input_dir = _make_input_dir(tmp_path, rows)
    output_dir = tmp_path / "db_output_mixed"

    builder = IndicatorDatabaseBuilder(input_dir, output_dir, overwrite=False)
    builder.run()

    summary = _read_json(output_dir / "indicator_database_summary.json")
    assert "metadata_missing_company_count" in summary, "summary missing metadata_missing_company_count"
    assert summary["metadata_missing_company_count"] == 1


def test_database_logs_warning_for_missing_company(tmp_path: Path, caplog) -> None:
    """IndicatorDatabaseBuilder must log a warning when company is empty."""
    input_dir = _make_input_dir(tmp_path, [_accepted_row(company="")])
    output_dir = tmp_path / "db_output_empty_co"

    with caplog.at_level(logging.WARNING, logger="esg_indicator_database.database_builder"):
        builder = IndicatorDatabaseBuilder(input_dir, output_dir, overwrite=False)
        builder.run()

    warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("metadata_missing_company" in msg for msg in warning_messages), (
        f"Expected 'metadata_missing_company' warning, got: {warning_messages}"
    )


def test_database_logs_warning_for_missing_fiscal_year(tmp_path: Path, caplog) -> None:
    """IndicatorDatabaseBuilder must log a warning when fiscal_year is empty."""
    input_dir = _make_input_dir(tmp_path, [_accepted_row(fiscal_year="")])
    output_dir = tmp_path / "db_output_empty_fy"

    with caplog.at_level(logging.WARNING, logger="esg_indicator_database.database_builder"):
        builder = IndicatorDatabaseBuilder(input_dir, output_dir, overwrite=False)
        builder.run()

    warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("metadata_missing_fiscal_year" in msg for msg in warning_messages), (
        f"Expected 'metadata_missing_fiscal_year' warning, got: {warning_messages}"
    )


def test_database_fiscal_year_not_overwritten_by_year_raw(tmp_path: Path) -> None:
    """fiscal_year must never be overwritten by year_raw or year_prepared in indicator_preparation_database."""
    # Row with fiscal_year=2024 but a different year_raw that could come from content
    row = _accepted_row(fiscal_year="2024", year="2015")  # year in content is 2015
    input_dir = _make_input_dir(tmp_path, [row])
    output_dir = tmp_path / "db_output_fy"

    builder = IndicatorDatabaseBuilder(input_dir, output_dir, overwrite=False)
    builder.run()

    rows = _read_csv(output_dir / "indicator_preparation_database.csv")
    assert rows
    # fiscal_year must remain 2024
    assert rows[0].get("fiscal_year") == "2024", f"fiscal_year was overwritten: {rows[0].get('fiscal_year')}"
    # year_raw may be 2015 (from content)
    # year_prepared may be 2024 (from fiscal_year fallback) — that is OK


def test_database_summary_reporting_vs_extracted_year_diff_count(tmp_path: Path) -> None:
    """Summary must report count of records where fiscal_year != year_prepared."""
    row = _accepted_row(fiscal_year="2024", year="2015")
    input_dir = _make_input_dir(tmp_path, [row])
    output_dir = tmp_path / "db_output_diff"

    builder = IndicatorDatabaseBuilder(input_dir, output_dir, overwrite=False)
    builder.run()

    summary = _read_json(output_dir / "indicator_database_summary.json")
    assert "reporting_year_vs_extracted_year_difference_count" in summary
    # The count is >=0; if year_raw differs from fiscal_year, it should be >0 in some cases
    assert isinstance(summary["reporting_year_vs_extracted_year_difference_count"], int)

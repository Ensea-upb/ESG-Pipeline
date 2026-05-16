"""Tests for company/fiscal_year propagation in ESGExtractionOrchestrator — v0.4."""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

import pytest

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from esg_extraction_orchestrator.candidate_consolidator import (
    CONSOLIDATED_FIELDS,
    consolidate_candidates,
)


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _make_collected(
    csv_rows: list[dict] | None = None,
    visual_rows: list[dict] | None = None,
    table_rows: list[dict] | None = None,
) -> dict[str, Any]:
    return {
        "csv": {"rows": csv_rows or []},
        "visual": {"rows": visual_rows or []},
        "table": {"rows": table_rows or []},
    }


def test_consolidated_fields_include_company_and_fiscal_year() -> None:
    """CONSOLIDATED_FIELDS must include company and fiscal_year."""
    assert "company" in CONSOLIDATED_FIELDS
    assert "fiscal_year" in CONSOLIDATED_FIELDS


def test_csv_candidates_preserve_company_fiscal_year(tmp_path: Path) -> None:
    """company/fiscal_year from CSV candidates must be preserved in consolidated output."""
    collected = _make_collected(csv_rows=[{
        "document_id": "doc_001",
        "company": "TotalEnergies",
        "fiscal_year": "2024",
        "information_type": "esg_metric_candidate",
        "esg_category": "emissions",
        "label": "GHG Emissions",
        "raw_value": "102887",
        "raw_unit": "employees",
        "year": "2024",
        "source_modality": "text",
        "page_number": "13",
        "section_id": "sec_1",
        "evidence_id": "ev_001",
        "quote": "Total workforce: 102,887 employees",
        "confidence": "0.85",
        "review_required": "True",
        "extraction_status": "candidate_only",
    }])
    rows = consolidate_candidates(collected, tmp_path)
    assert rows
    assert rows[0]["company"] == "TotalEnergies"
    assert rows[0]["fiscal_year"] == "2024"


def test_visual_candidates_get_company_backfilled_from_csv(tmp_path: Path) -> None:
    """Visual candidates without company/fiscal_year must be backfilled from CSV candidates sharing same document_id."""
    collected = _make_collected(
        csv_rows=[{
            "document_id": "doc_001",
            "company": "TotalEnergies",
            "fiscal_year": "2024",
            "information_type": "esg_metric_candidate",
            "esg_category": "emissions",
            "label": "test",
            "raw_value": "100",
            "raw_unit": "t",
            "year": "2024",
            "source_modality": "text",
            "page_number": "1",
            "section_id": "",
            "evidence_id": "ev_001",
            "quote": "emissions 100 t",
            "confidence": "0.8",
            "review_required": "True",
            "extraction_status": "candidate_only",
        }],
        visual_rows=[{
            "document_id": "doc_001",
            "company": "",   # empty — should be backfilled
            "fiscal_year": "",  # empty — should be backfilled
            "information_type": "visual_metric_candidate",
            "esg_category": "emissions",
            "label": "visual ESG candidate",
            "raw_value": "50",
            "raw_unit": "t",
            "year": "2024",
            "figure_id": "fig_001",
            "page_number": "2",
            "section_id": "",
            "caption": "Chart",
            "ocr_text": "50 t CO2",
            "confidence": "0.3",
            "review_required": "True",
            "extraction_status": "candidate_only",
        }],
    )
    rows = consolidate_candidates(collected, tmp_path)
    visual_row = next((r for r in rows if r["source_engine"] == "visual"), None)
    assert visual_row is not None
    assert visual_row["company"] == "TotalEnergies", f"Expected backfilled company, got: {visual_row['company']}"
    assert visual_row["fiscal_year"] == "2024", f"Expected backfilled fiscal_year, got: {visual_row['fiscal_year']}"


def test_visual_candidates_with_own_company_not_overwritten(tmp_path: Path) -> None:
    """Visual candidates that already have company/fiscal_year must not be overwritten."""
    collected = _make_collected(
        csv_rows=[{
            "document_id": "doc_001",
            "company": "TotalEnergies",
            "fiscal_year": "2024",
            "information_type": "esg_metric_candidate",
            "esg_category": "emissions",
            "label": "test",
            "raw_value": "100",
            "raw_unit": "t",
            "year": "2024",
            "source_modality": "text",
            "page_number": "1",
            "section_id": "",
            "evidence_id": "ev_001",
            "quote": "test",
            "confidence": "0.8",
            "review_required": "True",
            "extraction_status": "candidate_only",
        }],
        visual_rows=[{
            "document_id": "doc_001",
            "company": "TotalEnergies",   # already present
            "fiscal_year": "2024",         # already present
            "information_type": "visual_metric_candidate",
            "esg_category": "emissions",
            "label": "visual ESG candidate",
            "raw_value": "50",
            "raw_unit": "t",
            "year": "2024",
            "figure_id": "fig_001",
            "page_number": "2",
            "section_id": "",
            "caption": "Chart",
            "ocr_text": "50 t CO2",
            "confidence": "0.3",
            "review_required": "True",
            "extraction_status": "candidate_only",
        }],
    )
    rows = consolidate_candidates(collected, tmp_path)
    visual_row = next((r for r in rows if r["source_engine"] == "visual"), None)
    assert visual_row is not None
    assert visual_row["company"] == "TotalEnergies"
    assert visual_row["fiscal_year"] == "2024"


def test_table_candidates_preserve_company_fiscal_year(tmp_path: Path) -> None:
    """company/fiscal_year from Table candidates must be preserved in consolidated output."""
    collected = _make_collected(table_rows=[{
        "document_id": "doc_001",
        "company": "TotalEnergies",
        "fiscal_year": "2024",
        "esg_category": "water",
        "metric_label": "Water withdrawal",
        "raw_value": "92",
        "raw_unit": "Mm3",
        "reported_year": "2024",
        "page_number": "13",
        "section_id": "",
        "table_id": "tbl_001",
        "cell_id": "cell_001",
        "source_row_text": "Fresh water withdrawal 92 Mm3",
        "confidence": "0.75",
        "review_required": "True",
        "extraction_status": "candidate_only",
        "information_type": "table_metric_candidate",
    }])
    rows = consolidate_candidates(collected, tmp_path)
    assert rows
    table_row = next((r for r in rows if r["source_engine"] == "table"), None)
    assert table_row is not None
    assert table_row["company"] == "TotalEnergies"
    assert table_row["fiscal_year"] == "2024"


def test_consolidated_csv_written_with_company_fiscal_year(tmp_path: Path) -> None:
    """consolidated_candidates.csv must contain company and fiscal_year columns."""
    collected = _make_collected(csv_rows=[{
        "document_id": "doc_001",
        "company": "TotalEnergies",
        "fiscal_year": "2024",
        "information_type": "esg_metric_candidate",
        "esg_category": "emissions",
        "label": "GHG",
        "raw_value": "100",
        "raw_unit": "t",
        "year": "2024",
        "source_modality": "text",
        "page_number": "1",
        "section_id": "",
        "evidence_id": "ev_001",
        "quote": "100t",
        "confidence": "0.8",
        "review_required": "True",
        "extraction_status": "candidate_only",
    }])
    consolidate_candidates(collected, tmp_path)
    csv_rows = _read_csv(tmp_path / "consolidated_candidates.csv")
    assert csv_rows
    assert "company" in csv_rows[0], "company column missing from consolidated_candidates.csv"
    assert "fiscal_year" in csv_rows[0], "fiscal_year column missing from consolidated_candidates.csv"
    assert csv_rows[0]["company"] == "TotalEnergies"
    assert csv_rows[0]["fiscal_year"] == "2024"

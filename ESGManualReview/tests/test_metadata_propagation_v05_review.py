"""Tests for company/fiscal_year propagation in ESGManualReview — v0.5."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ESGManualReview" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from esg_manual_review.review_workspace import WORKSPACE_FIELDS, ManualReviewWorkspaceBuilder


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


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


VALIDATION_INPUT_FIELDS = [
    "candidate_id", "candidate_validation_id", "document_id", "company", "fiscal_year",
    "source_engine", "information_type", "original_information_type", "esg_category", "label",
    "raw_value", "raw_unit", "year", "normalized_value", "normalized_unit",
    "normalized_year", "year_inferred", "normalization_status", "normalization_notes",
    "unit_detection_source", "year_detection_source", "page_number", "section_id",
    "evidence_id", "table_id", "cell_id", "figure_id", "quote", "confidence",
    "validation_status", "validation_reason", "is_validated_indicator", "score_produced",
    "indicator_family", "indicator_key_candidate", "indicator_label_candidate",
    "indicator_mapping_confidence", "indicator_mapping_reason", "review_priority",
    "review_reason", "review_action_suggested", "reviewer_decision", "reviewer_notes",
    "ready_for_manual_review", "duplicate_group_id", "duplicate_status",
    "canonical_validation_candidate_id", "duplicate_reason", "review_required",
    "extraction_status",
]


def _validation_row(company: str = "TotalEnergies", fiscal_year: str = "2024") -> dict:
    return {
        "candidate_id": "cand_001",
        "candidate_validation_id": "val_001",
        "document_id": "doc_001",
        "company": company,
        "fiscal_year": fiscal_year,
        "source_engine": "csv",
        "information_type": "esg_metric_candidate",
        "original_information_type": "esg_metric_candidate",
        "esg_category": "emissions",
        "label": "GHG Emissions",
        "raw_value": "102887",
        "raw_unit": "employees",
        "year": "2024",
        "normalized_value": "102887",
        "normalized_unit": "employees",
        "normalized_year": "2024",
        "year_inferred": "False",
        "normalization_status": "complete",
        "normalization_notes": "",
        "unit_detection_source": "raw_unit",
        "year_detection_source": "year",
        "page_number": "13",
        "section_id": "sec_1",
        "evidence_id": "ev_001",
        "table_id": "",
        "cell_id": "",
        "figure_id": "",
        "quote": "Total workforce: 102,887 employees",
        "confidence": "0.85",
        "validation_status": "possible_indicator",
        "validation_reason": "numeric value present",
        "is_validated_indicator": "False",
        "score_produced": "False",
        "indicator_family": "human_capital",
        "indicator_key_candidate": "human_capital",
        "indicator_label_candidate": "Total Workforce",
        "indicator_mapping_confidence": "0.9",
        "indicator_mapping_reason": "indicator_key",
        "review_priority": "high",
        "review_reason": "possible_indicator",
        "review_action_suggested": "accept",
        "reviewer_decision": "",
        "reviewer_notes": "",
        "ready_for_manual_review": "True",
        "duplicate_group_id": "",
        "duplicate_status": "unique",
        "canonical_validation_candidate_id": "",
        "duplicate_reason": "",
        "review_required": "True",
        "extraction_status": "candidate_only",
    }


def _make_validation_input_dir(tmp_path: Path, company: str = "TotalEnergies", fiscal_year: str = "2024") -> Path:
    """Create a minimal ESGIndicatorValidation output directory."""
    input_dir = tmp_path / "validation_output"
    input_dir.mkdir(parents=True, exist_ok=True)
    rows = [_validation_row(company, fiscal_year)]
    _write_csv(input_dir / "indicator_candidate_validations.csv", rows, VALIDATION_INPUT_FIELDS)
    _write_csv(input_dir / "possible_indicators.csv", rows, VALIDATION_INPUT_FIELDS)
    _write_csv(input_dir / "rejected_candidates.csv", [], VALIDATION_INPUT_FIELDS)
    _write_csv(input_dir / "validation_review_queue.csv", rows, VALIDATION_INPUT_FIELDS)
    _write_json(input_dir / "indicator_validation_audit_summary.json", {"errors_count": 0, "warnings_count": 0})
    _write_json(input_dir / "indicator_validation_summary.json", {
        "schema_version": "1.0.0",
        "validations_count": 1,
        "possible_indicators_count": 1,
    })
    return input_dir


def test_workspace_fields_include_company_and_fiscal_year() -> None:
    """WORKSPACE_FIELDS must include company and fiscal_year."""
    assert "company" in WORKSPACE_FIELDS
    assert "fiscal_year" in WORKSPACE_FIELDS


def test_manual_review_workspace_propagates_company_fiscal_year(tmp_path: Path) -> None:
    """ManualReviewWorkspaceBuilder must pass company/fiscal_year to manual_review_workspace.csv."""
    input_dir = _make_validation_input_dir(tmp_path)
    output_dir = tmp_path / "review_output"

    builder = ManualReviewWorkspaceBuilder(input_dir, output_dir, overwrite=False)
    builder.run()

    workspace_csv = output_dir / "manual_review_workspace.csv"
    assert workspace_csv.exists()
    rows = _read_csv(workspace_csv)
    assert rows, "manual_review_workspace.csv must not be empty"
    assert rows[0].get("company") == "TotalEnergies", f"company missing: {rows[0]}"
    assert rows[0].get("fiscal_year") == "2024", f"fiscal_year missing: {rows[0]}"


def test_manual_review_preserves_empty_company_without_inventing(tmp_path: Path) -> None:
    """ManualReview must NOT invent company when it's empty."""
    input_dir = _make_validation_input_dir(tmp_path, company="", fiscal_year="")
    output_dir = tmp_path / "review_output_empty"

    builder = ManualReviewWorkspaceBuilder(input_dir, output_dir, overwrite=False)
    builder.run()

    workspace_csv = output_dir / "manual_review_workspace.csv"
    rows = _read_csv(workspace_csv)
    assert rows
    assert rows[0].get("company") == "", f"ManualReview invented company: '{rows[0].get('company')}'"

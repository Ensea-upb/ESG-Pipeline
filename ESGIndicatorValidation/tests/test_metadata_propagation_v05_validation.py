"""Tests for company/fiscal_year propagation in ESGIndicatorValidation — v0.5."""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ESGIndicatorValidation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from esg_indicator_validation.validator import VALIDATION_FIELDS, IndicatorValidator
from esg_indicator_validation.normalizer import normalize_candidate


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({f: row.get(f, "") for f in fields})


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


INPUT_FIELDS = [
    "document_id", "company", "fiscal_year", "source_engine", "information_type",
    "esg_category", "label", "raw_value", "raw_unit", "year", "source_modality",
    "page_number", "section_id", "evidence_id", "table_id", "cell_id", "figure_id",
    "quote", "confidence", "review_required", "extraction_status",
    "normalized_candidate_key", "deduplication_group_id", "deduplication_status",
    "canonical_candidate_id", "duplicate_reason",
]


def _candidate_row(company: str = "TotalEnergies", fiscal_year: str = "2024") -> dict:
    return {
        "document_id": "doc_001",
        "company": company,
        "fiscal_year": fiscal_year,
        "source_engine": "csv",
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
        "table_id": "",
        "cell_id": "",
        "figure_id": "",
        "quote": "Total workforce: 102,887 employees as of December 31, 2024",
        "confidence": "0.85",
        "review_required": "True",
        "extraction_status": "candidate_only",
        "normalized_candidate_key": "",
        "deduplication_group_id": "",
        "deduplication_status": "unique_candidate",
        "canonical_candidate_id": "",
        "duplicate_reason": "",
    }


def test_validation_fields_include_company_and_fiscal_year() -> None:
    """VALIDATION_FIELDS must include company and fiscal_year."""
    assert "company" in VALIDATION_FIELDS
    assert "fiscal_year" in VALIDATION_FIELDS


def test_validator_propagates_company_fiscal_year_to_output(tmp_path: Path) -> None:
    """ESGIndicatorValidation must pass company/fiscal_year from input to output."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    _write_csv(input_dir / "consolidated_unique_candidates.csv", [_candidate_row()], INPUT_FIELDS)
    output_dir = tmp_path / "output"

    validator = IndicatorValidator(input_dir, output_dir, overwrite=False)
    result = validator.run()

    rows = _read_csv(output_dir / "indicator_candidate_validations.csv")
    assert rows, "indicator_candidate_validations.csv must not be empty"
    assert rows[0].get("company") == "TotalEnergies", f"company missing in output: {rows[0]}"
    assert rows[0].get("fiscal_year") == "2024", f"fiscal_year missing in output: {rows[0]}"


def test_validator_preserves_empty_company_without_inventing_value(tmp_path: Path) -> None:
    """Validator must NOT invent company when it's empty — pass through empty string."""
    input_dir = tmp_path / "input_empty"
    input_dir.mkdir()
    _write_csv(input_dir / "consolidated_unique_candidates.csv", [_candidate_row(company="", fiscal_year="")], INPUT_FIELDS)
    output_dir = tmp_path / "output_empty"

    validator = IndicatorValidator(input_dir, output_dir, overwrite=False)
    result = validator.run()

    rows = _read_csv(output_dir / "indicator_candidate_validations.csv")
    assert rows
    # company must stay empty — never guessed
    assert rows[0].get("company") == "", f"Validator invented company: '{rows[0].get('company')}'"


def test_normalizer_does_not_overwrite_fiscal_year_with_content_year() -> None:
    """normalize_candidate must NOT overwrite fiscal_year with year_raw from content."""
    row = {
        "raw_value": "92",
        "raw_unit": "Mm3",
        "label": "Water withdrawal",
        "quote": "Fresh water withdrawal: 92 Mm3 in 2024 (compared to 85 Mm3 in 2015)",
        "year": "",
        "fiscal_year": "2024",
    }
    result = normalize_candidate(row)
    # normalized_year may be "2024" or "2015" from the quote — that's OK
    # but fiscal_year in the input dict must NOT be modified
    assert row["fiscal_year"] == "2024", "normalizer must not modify fiscal_year in original row"


def test_possible_indicators_csv_has_company_fiscal_year(tmp_path: Path) -> None:
    """possible_indicators.csv must contain company and fiscal_year columns."""
    input_dir = tmp_path / "input_poss"
    input_dir.mkdir()
    _write_csv(input_dir / "consolidated_unique_candidates.csv", [_candidate_row()], INPUT_FIELDS)
    output_dir = tmp_path / "output_poss"

    validator = IndicatorValidator(input_dir, output_dir, overwrite=False)
    validator.run()

    poss_csv = output_dir / "possible_indicators.csv"
    assert poss_csv.exists()
    rows = _read_csv(poss_csv)
    if rows:
        assert "company" in rows[0], "possible_indicators.csv missing company column"
        assert "fiscal_year" in rows[0], "possible_indicators.csv missing fiscal_year column"

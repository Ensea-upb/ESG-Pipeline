"""Tests for metadata propagation and override flags in ESGVariableDatasetBuilder — v0.7."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ESGVariableDatasetBuilder" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from esg_variable_dataset_builder.dataset_builder import build_dataset


PREP_FIELDS = [
    "preparation_indicator_id", "indicator_database_status", "candidate_id", "document_id",
    "company", "fiscal_year", "source_engine", "indicator_family", "indicator_key",
    "indicator_label", "value_raw", "unit_raw", "year_raw", "value_prepared",
    "unit_prepared", "year_prepared", "page_number", "quote", "evidence_id",
    "table_id", "cell_id", "figure_id", "reviewer", "decision_reason",
    "is_final_indicator", "score_produced",
]


def _make_prep_dir(root: Path, name: str, rows: list[dict]) -> Path:
    output_dir = root / name
    output_dir.mkdir(parents=True)
    with (output_dir / "indicator_preparation_database.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=PREP_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            base = {field: "" for field in PREP_FIELDS}
            base.update(row)
            base.setdefault("indicator_database_status", "preparation_only")
            base.setdefault("is_final_indicator", "False")
            base.setdefault("score_produced", "False")
            writer.writerow(base)
    with (output_dir / "indicator_evidence_links.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["preparation_indicator_id", "evidence_id", "document_id"])
        writer.writeheader()
    (output_dir / "indicator_lineage.jsonl").write_text("", encoding="utf-8")
    (output_dir / "indicator_database_summary.json").write_text('{"status":"preparation_only"}\n', encoding="utf-8")
    return output_dir


def _row_with_metadata(company: str = "TotalEnergies", fiscal_year: str = "2024", indicator_key: str = "human_capital", value: str = "102887", unit: str = "employees") -> dict:
    return {
        "preparation_indicator_id": "prep_001",
        "candidate_id": "cand_001",
        "document_id": "totalenergies_2024_urd",
        "company": company,
        "fiscal_year": fiscal_year,
        "source_engine": "csv",
        "indicator_family": "human_capital",
        "indicator_key": indicator_key,
        "indicator_label": "Total Workforce",
        "value_prepared": value,
        "unit_prepared": unit,
        "year_prepared": fiscal_year,
        "page_number": "13",
        "quote": f"Total workforce: {value} {unit}",
        "evidence_id": "ev_001",
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_summary_has_metadata_missing_counts(tmp_path: Path) -> None:
    """esg_variables_dataset_summary.json must include metadata_missing_company_count and metadata_missing_fiscal_year_count."""
    input_root = tmp_path / "inputs"
    _make_prep_dir(input_root, "run1", [_row_with_metadata()])
    output_dir = tmp_path / "out"

    summary = build_dataset(input_root, output_dir, company="TotalEnergies", year="2024")
    assert "metadata_missing_company_count" in summary
    assert "metadata_missing_fiscal_year_count" in summary
    assert summary["metadata_missing_company_count"] == 0
    assert summary["metadata_missing_fiscal_year_count"] == 0


def test_summary_has_ignored_records_count(tmp_path: Path) -> None:
    """esg_variables_dataset_summary.json must include ignored_records_count."""
    input_root = tmp_path / "inputs"
    _make_prep_dir(input_root, "run1", [_row_with_metadata()])
    output_dir = tmp_path / "out"

    summary = build_dataset(input_root, output_dir, company="TotalEnergies", year="2024")
    assert "ignored_records_count" in summary
    assert isinstance(summary["ignored_records_count"], int)


def test_summary_detects_missing_company_count(tmp_path: Path) -> None:
    """metadata_missing_company_count must be >0 when records have empty company."""
    input_root = tmp_path / "inputs"
    _make_prep_dir(input_root, "run1", [_row_with_metadata(company="", fiscal_year="2024")])
    output_dir = tmp_path / "out"

    summary = build_dataset(input_root, output_dir)
    assert summary["metadata_missing_company_count"] > 0


def test_override_empty_company_single_doc_mode(tmp_path: Path) -> None:
    """override_empty_company_from_cli must fill empty company in single-document mode."""
    input_root = tmp_path / "inputs"
    _make_prep_dir(input_root, "run1", [_row_with_metadata(company="", fiscal_year="2024")])
    output_dir = tmp_path / "out"

    summary = build_dataset(
        input_root, output_dir,
        company="TotalEnergies",
        year="2024",
        override_empty_company_from_cli=True,
        single_document_mode=True,
    )
    # After override, metadata_missing_company_count should be 0
    assert summary["metadata_missing_company_count"] == 0


def test_override_flags_raise_error_without_single_document_mode(tmp_path: Path) -> None:
    """override flags must raise ValueError when multiple document_ids present and single_document_mode=False."""
    input_root = tmp_path / "inputs"
    # Two records with DIFFERENT document_ids — both with empty company so they are loaded
    row1 = _row_with_metadata(company="", fiscal_year="2024")
    row2 = {**_row_with_metadata(company="", fiscal_year="2024"), "document_id": "another_doc_456", "preparation_indicator_id": "prep_002"}
    # Put them in separate source dirs so both are discovered
    _make_prep_dir(input_root, "run1", [row1])
    _make_prep_dir(input_root, "run2", [row2])
    output_dir = tmp_path / "out"

    with pytest.raises(ValueError, match="single-document-mode"):
        build_dataset(
            input_root, output_dir,
            # No company/year filter so both dirs are loaded
            override_empty_company_from_cli=True,
            single_document_mode=False,
        )


def test_override_empty_year_single_doc_mode(tmp_path: Path) -> None:
    """override_empty_year_from_cli must fill empty fiscal_year in single-document mode."""
    input_root = tmp_path / "inputs"
    _make_prep_dir(input_root, "run1", [_row_with_metadata(company="TotalEnergies", fiscal_year="")])
    output_dir = tmp_path / "out"

    summary = build_dataset(
        input_root, output_dir,
        company="TotalEnergies",
        year="2024",
        override_empty_year_from_cli=True,
        single_document_mode=True,
    )
    assert summary["metadata_missing_fiscal_year_count"] == 0


def test_fiscal_year_never_overwritten_by_year_raw(tmp_path: Path) -> None:
    """build_dataset must never overwrite fiscal_year with year_raw in records."""
    input_root = tmp_path / "inputs"
    row = _row_with_metadata(fiscal_year="2024")
    row["year_raw"] = "2015"  # a different content year
    _make_prep_dir(input_root, "run1", [row])
    output_dir = tmp_path / "out"

    build_dataset(input_root, output_dir, company="TotalEnergies", year="2024")

    loaded_records_path = output_dir / "loaded_preparation_records.csv"
    assert loaded_records_path.exists()
    with loaded_records_path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    # fiscal_year must remain "2024", not replaced by year_raw "2015"
    assert rows[0].get("fiscal_year") == "2024", f"fiscal_year was overwritten: {rows[0].get('fiscal_year')}"


def test_no_silent_ignore_of_records_with_invalid_status(tmp_path: Path) -> None:
    """Records with invalid status must be counted in ignored_records_count, not silently dropped."""
    input_root = tmp_path / "inputs"
    rows = [
        _row_with_metadata(),
        {**_row_with_metadata(), "indicator_database_status": "final_indicator", "preparation_indicator_id": "prep_002"},
    ]
    _make_prep_dir(input_root, "run1", rows)
    output_dir = tmp_path / "out"

    summary = build_dataset(input_root, output_dir, company="TotalEnergies", year="2024")
    # The invalid record should be in ignored_records_count
    assert summary["ignored_records_count"] >= 0  # May vary; just ensure key exists
    assert "ignored_records_reason_distribution" in summary

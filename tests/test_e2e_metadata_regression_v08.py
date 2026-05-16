"""E2E metadata regression tests using TotalEnergies 2024 synthetic fixtures — v0.8.

These tests reproduce the exact bug found in production:
- ESGIndicatorDatabase had 2 rows (human_capital=102887, water_consumption=92 Mm3)
- BUT company was EMPTY → ESGVariableDatasetBuilder produced 0 found values

The fixtures test both the positive case (metadata present) and the negative case (metadata absent).
"""
from __future__ import annotations

import csv
import json
import logging
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "ESGVariableDatasetBuilder" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from esg_variable_dataset_builder.dataset_builder import build_dataset

FIXTURES_DIR = ROOT / "tests" / "fixtures" / "metadata_regression_totalenergies_2024"
FIXTURE_WITH_METADATA = FIXTURES_DIR / "indicator_preparation_database_with_metadata.csv"
FIXTURE_MISSING_COMPANY = FIXTURES_DIR / "indicator_preparation_database_missing_company.csv"

PREP_FIELDS = [
    "preparation_indicator_id", "indicator_database_status", "candidate_id", "review_item_id",
    "document_id", "company", "fiscal_year", "source_engine", "information_type",
    "validation_status", "review_status", "indicator_family", "indicator_key",
    "indicator_label", "value_raw", "unit_raw", "year_raw", "value_prepared",
    "unit_prepared", "year_prepared", "value_source", "unit_source", "year_source",
    "preparation_quality_status", "page_number", "quote", "evidence_id",
    "table_id", "cell_id", "figure_id", "reviewer", "decision_reason",
    "reviewer_notes", "created_from_review_decision", "is_final_indicator", "score_produced",
    "indicator_domain", "indicator_topic", "indicator_metric_name", "indicator_unit_category",
    "indicator_period_type", "indicator_scope", "indicator_geography", "indicator_methodology",
    "indicator_standard_reference", "indicator_schema_confidence", "schema_mapping_notes",
]


def _make_input_root_from_fixture(tmp_path: Path, fixture_csv: Path) -> Path:
    """Create a minimal input_root directory from a fixture CSV."""
    input_root = tmp_path / "input_root"
    run_dir = input_root / "totalenergies_2024_run"
    run_dir.mkdir(parents=True)
    shutil.copy(fixture_csv, run_dir / "indicator_preparation_database.csv")
    with (run_dir / "indicator_evidence_links.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["preparation_indicator_id", "evidence_id", "document_id"])
        writer.writeheader()
    (run_dir / "indicator_lineage.jsonl").write_text("", encoding="utf-8")
    (run_dir / "indicator_database_summary.json").write_text('{"status":"preparation_only"}\n', encoding="utf-8")
    return input_root


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── Positive tests (metadata present) ────────────────────────────────────────

def test_builder_produces_human_capital_found_when_metadata_present(tmp_path: Path) -> None:
    """Builder must find human_capital when company/fiscal_year are present."""
    input_root = _make_input_root_from_fixture(tmp_path, FIXTURE_WITH_METADATA)
    output_dir = tmp_path / "out"

    summary = build_dataset(input_root, output_dir, company="TotalEnergies", year="2024")

    selected_path = output_dir / "selected_variable_values.csv"
    assert selected_path.exists()
    rows = _read_csv(selected_path)
    human_capital_rows = [r for r in rows if r.get("variable_name") == "human_capital" and r.get("company") == "TotalEnergies"]
    assert human_capital_rows, "human_capital row not found in selection output"
    found_rows = [r for r in human_capital_rows if r.get("selected_status") == "found"]
    assert found_rows, f"human_capital status is not 'found': {[r.get('selected_status') for r in human_capital_rows]}"


def test_builder_produces_water_consumption_found_when_metadata_present(tmp_path: Path) -> None:
    """Builder must find water_consumption when company/fiscal_year are present."""
    input_root = _make_input_root_from_fixture(tmp_path, FIXTURE_WITH_METADATA)
    output_dir = tmp_path / "out"

    build_dataset(input_root, output_dir, company="TotalEnergies", year="2024")

    rows = _read_csv(output_dir / "selected_variable_values.csv")
    water_rows = [r for r in rows if r.get("variable_name") == "water_consumption" and r.get("company") == "TotalEnergies"]
    assert water_rows, "water_consumption row not found in selection output"
    found_rows = [r for r in water_rows if r.get("selected_status") == "found"]
    assert found_rows, f"water_consumption status is not 'found': {[r.get('selected_status') for r in water_rows]}"


def test_found_values_count_equals_two_when_metadata_present(tmp_path: Path) -> None:
    """Exactly 2 variables must have status='found' (human_capital + water_consumption)."""
    input_root = _make_input_root_from_fixture(tmp_path, FIXTURE_WITH_METADATA)
    output_dir = tmp_path / "out"

    build_dataset(input_root, output_dir, company="TotalEnergies", year="2024")

    rows = _read_csv(output_dir / "selected_variable_values.csv")
    found_count = sum(1 for r in rows if r.get("selected_status") == "found" and r.get("company") == "TotalEnergies")
    assert found_count == 2, f"Expected 2 found values, got {found_count}"


def test_fiscal_year_stays_2024_despite_year_raw_2015(tmp_path: Path) -> None:
    """fiscal_year must remain 2024 even when year_raw=2015 appears in content (water_consumption row)."""
    input_root = _make_input_root_from_fixture(tmp_path, FIXTURE_WITH_METADATA)
    output_dir = tmp_path / "out"

    build_dataset(input_root, output_dir, company="TotalEnergies", year="2024")

    # loaded_preparation_records.csv must have fiscal_year=2024 for all rows
    loaded_path = output_dir / "loaded_preparation_records.csv"
    assert loaded_path.exists()
    rows = _read_csv(loaded_path)
    for row in rows:
        assert row.get("fiscal_year") == "2024", (
            f"fiscal_year was modified to '{row.get('fiscal_year')}' for indicator_key={row.get('indicator_key')}"
        )

    # water_consumption row should have year_raw=2015 but fiscal_year=2024
    water_row = next((r for r in rows if r.get("indicator_key") == "water_consumption"), None)
    if water_row:
        assert water_row.get("year_raw") == "2015", f"year_raw expected 2015, got: {water_row.get('year_raw')}"
        assert water_row.get("fiscal_year") == "2024", f"fiscal_year must not be overwritten by year_raw"


def test_summary_metadata_missing_counts_zero_when_metadata_present(tmp_path: Path) -> None:
    """Summary must show 0 metadata missing counts when company/fiscal_year are present."""
    input_root = _make_input_root_from_fixture(tmp_path, FIXTURE_WITH_METADATA)
    output_dir = tmp_path / "out"

    summary = build_dataset(input_root, output_dir, company="TotalEnergies", year="2024")
    assert summary.get("metadata_missing_company_count") == 0
    assert summary.get("metadata_missing_fiscal_year_count") == 0


# ── Negative tests (metadata absent) ─────────────────────────────────────────

def test_builder_produces_warning_when_company_empty(tmp_path: Path, caplog) -> None:
    """Builder must log a warning when company is empty in loaded records."""
    input_root = _make_input_root_from_fixture(tmp_path, FIXTURE_MISSING_COMPANY)
    output_dir = tmp_path / "out"

    with caplog.at_level(logging.WARNING, logger="esg_variable_dataset_builder.dataset_builder"):
        build_dataset(input_root, output_dir)

    warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("metadata_missing_company" in msg for msg in warning_messages), (
        f"Expected 'metadata_missing_company' warning, got: {warning_messages}"
    )


def test_builder_not_silently_filling_company_from_directory_guessing(tmp_path: Path) -> None:
    """Builder must NOT silently fill company from directory name when metadata is absent."""
    # Create input_root with directory named after company (heuristic bait)
    input_root = tmp_path / "input_root"
    run_dir = input_root / "totalenergies_2024"   # directory name hints at company
    run_dir.mkdir(parents=True)
    shutil.copy(FIXTURE_MISSING_COMPANY, run_dir / "indicator_preparation_database.csv")
    with (run_dir / "indicator_evidence_links.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["preparation_indicator_id", "evidence_id", "document_id"])
        writer.writeheader()
    (run_dir / "indicator_lineage.jsonl").write_text("", encoding="utf-8")
    (run_dir / "indicator_database_summary.json").write_text('{"status":"preparation_only"}\n', encoding="utf-8")
    output_dir = tmp_path / "out"

    summary = build_dataset(input_root, output_dir)

    # metadata_missing_company_count must be > 0 — builder must NOT have silently filled company
    assert summary.get("metadata_missing_company_count", 0) > 0, (
        "Builder silently filled company from directory name — this is prohibited"
    )


def test_builder_missing_company_produces_no_found_values(tmp_path: Path) -> None:
    """When company is empty, builder must produce 0 'found' values (reproduces the real bug)."""
    input_root = _make_input_root_from_fixture(tmp_path, FIXTURE_MISSING_COMPANY)
    output_dir = tmp_path / "out"

    # No company/year passed to builder — mirrors the original buggy state
    build_dataset(input_root, output_dir)

    selected_path = output_dir / "selected_variable_values.csv"
    assert selected_path.exists()
    rows = _read_csv(selected_path)
    # When company is empty, no (company, year) pair exists → no selections → 0 found
    found_count = sum(1 for r in rows if r.get("selected_status") == "found")
    assert found_count == 0, (
        f"Builder produced {found_count} found values despite empty company — "
        "this reproduces the original bug if it passes"
    )

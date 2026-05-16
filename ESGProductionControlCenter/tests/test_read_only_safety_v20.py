"""
test_read_only_safety_v20.py — Verify that v2.0 data loading never modifies source files.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ESGProductionControlCenter.src.esg_production_control_center.data_loader import (
    build_candidate_table,
    build_document_index,
    find_review_workspaces,
    load_all_review_workspaces,
    load_pilot_summary,
    load_review_quality_audit,
)
from ESGProductionControlCenter.src.esg_production_control_center.filters import (
    apply_all_filters,
    get_priority_queue,
)


def _make_pilot(tmp_path: Path) -> Path:
    root = tmp_path / "pilot"
    root.mkdir()
    slug = "acme"
    doc_id = "doc_001"
    ws = root / slug / "2024" / "01_annual_report" / doc_id / "04_review_workspace"
    ws.mkdir(parents=True)

    rows = [
        {
            "review_item_id": "ri_001",
            "document_id": doc_id,
            "company": slug,
            "fiscal_year": "2024",
            "validation_status": "possible_indicator",
            "indicator_family": "ghg_emissions",
            "raw_value": "100",
            "raw_unit": "tCO2e",
            "quote": "The company reduced emissions by 100 tCO2e in FY2024.",
            "label": "scope 1",
            "page_number": "12",
            "source_engine": "csv",
        }
    ]
    csv_path = ws / "manual_review_workspace.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "documents_selected": 1,
        "documents_processed": 1,
        "documents_success": 1,
        "documents_failed": 0,
        "per_document": [{
            "document_id": doc_id,
            "company_slug": slug,
            "company_name": "Acme Corp",
            "fiscal_year": "2024",
            "official_doc_type": "01_annual_report",
            "status": "success",
            "steps_completed": ["step_01"],
            "error": None,
            "review_workspace_produced": True,
        }],
    }
    (root / "pilot_run_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return root


def _snapshot(root: Path) -> dict[str, float]:
    return {
        str(p.relative_to(root)): p.stat().st_mtime
        for p in root.rglob("*") if p.is_file()
    }


def test_read_only_no_source_modification(tmp_path):
    """load_all_review_workspaces must never modify any file in the run root."""
    pilot = _make_pilot(tmp_path)
    before = _snapshot(pilot)

    _ = load_all_review_workspaces(pilot)
    _ = load_pilot_summary(pilot)
    _ = build_document_index(pilot)
    _ = build_candidate_table(pilot)
    _ = find_review_workspaces(pilot)

    after = _snapshot(pilot)
    assert before == after, (
        "Data loader modified source files (read-only violated).\n"
        f"Changed: {set(after.items()) - set(before.items())}"
    )


def test_read_only_filters_do_not_modify_source(tmp_path):
    """apply_all_filters on the loaded DataFrame must not touch disk."""
    pilot = _make_pilot(tmp_path)
    before = _snapshot(pilot)

    df = load_all_review_workspaces(pilot)
    _ = apply_all_filters(df, status="possible_indicator")
    _ = get_priority_queue(df)

    after = _snapshot(pilot)
    assert before == after


def test_load_json_does_not_create_files(tmp_path):
    from ESGProductionControlCenter.src.esg_production_control_center.data_loader import load_json
    before = list(tmp_path.rglob("*"))
    _ = load_json(tmp_path / "nonexistent.json")
    after = list(tmp_path.rglob("*"))
    assert before == after, "load_json created unexpected files"


def test_get_missing_files_does_not_create_files(tmp_path):
    from ESGProductionControlCenter.src.esg_production_control_center.data_loader import get_missing_files
    before = list(tmp_path.rglob("*"))
    _ = get_missing_files(tmp_path)
    after = list(tmp_path.rglob("*"))
    assert before == after

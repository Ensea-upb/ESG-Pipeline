"""
test_data_loader_v20.py — Tests for data_loader.py (ESGProductionControlCenter v2.0).
All tests use synthetic fixtures — no real pilot run required.
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
    get_missing_files,
    load_csv,
    load_json,
    load_pilot_summary,
    load_review_quality_audit,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_pilot_root(tmp_path: Path, n_docs: int = 2) -> Path:
    root = tmp_path / "run"
    root.mkdir()

    per_doc = []
    for i in range(n_docs):
        slug = f"company{i}"
        doc_id = f"doc_{i:03d}"
        ws = root / slug / "2024" / "01_annual_report" / doc_id / "04_review_workspace"
        ws.mkdir(parents=True)

        # Write workspace CSV
        csv_path = ws / "manual_review_workspace.csv"
        rows = [
            {
                "review_item_id": f"ri_{i:03d}_001",
                "document_id": doc_id,
                "company": slug,
                "fiscal_year": "2024",
                "validation_status": "possible_indicator",
                "indicator_family": "ghg_emissions",
                "raw_value": "100",
                "raw_unit": "tCO2e",
                "quote": "The company emitted 100 tCO2e in 2024.",
                "label": "scope 1 emissions",
                "page_number": "12",
                "source_engine": "csv",
            },
            {
                "review_item_id": f"ri_{i:03d}_002",
                "document_id": doc_id,
                "company": slug,
                "fiscal_year": "2024",
                "validation_status": "needs_review",
                "indicator_family": "unknown",
                "raw_value": "",
                "raw_unit": "",
                "quote": "",
                "label": "some metric",
                "page_number": "",
                "source_engine": "csv",
            },
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        per_doc.append({
            "document_id": doc_id,
            "company_slug": slug,
            "company_name": slug.title(),
            "fiscal_year": "2024",
            "official_doc_type": "01_annual_report",
            "status": "success",
            "steps_completed": ["step_01", "step_02", "step_03", "step_04"],
            "error": None,
            "review_workspace_produced": True,
        })

    summary = {
        "documents_selected": n_docs,
        "documents_processed": n_docs,
        "documents_success": n_docs,
        "documents_failed": 0,
        "per_document": per_doc,
    }
    (root / "pilot_run_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_data_loader_finds_review_workspaces(tmp_path):
    root = _make_pilot_root(tmp_path, n_docs=3)
    ws = find_review_workspaces(root)
    assert len(ws) == 3
    for w in ws:
        assert w.name == "04_review_workspace"


def test_data_loader_finds_no_workspaces_missing_root(tmp_path):
    ws = find_review_workspaces(tmp_path / "nonexistent")
    assert ws == []


def test_data_loader_loads_pilot_summary(tmp_path):
    root = _make_pilot_root(tmp_path, n_docs=2)
    summary = load_pilot_summary(root)
    assert summary["documents_selected"] == 2
    assert summary["documents_success"] == 2
    assert len(summary["per_document"]) == 2


def test_data_loader_loads_pilot_summary_missing_file(tmp_path):
    summary = load_pilot_summary(tmp_path / "nonexistent")
    assert summary == {}


def test_data_loader_loads_candidate_tables(tmp_path):
    root = _make_pilot_root(tmp_path, n_docs=2)
    df = build_candidate_table(root)
    # 2 docs × 2 rows = 4 total
    assert len(df) == 4
    assert "_company_slug" in df.columns
    assert "_document_id" in df.columns
    assert "validation_status" in df.columns


def test_data_loader_build_document_index(tmp_path):
    root = _make_pilot_root(tmp_path, n_docs=3)
    df = build_document_index(root)
    assert len(df) == 3
    assert "company_slug" in df.columns
    assert "status" in df.columns


def test_data_loader_load_json_invalid(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not valid json", encoding="utf-8")
    result = load_json(bad)
    assert result == {}


def test_data_loader_load_csv_missing(tmp_path):
    import pandas as pd
    df = load_csv(tmp_path / "nonexistent.csv")
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_data_loader_get_missing_files_all_missing(tmp_path):
    missing = get_missing_files(tmp_path)
    assert len(missing) > 0
    assert "pilot_run_summary.json" in missing


def test_data_loader_get_missing_files_partial(tmp_path):
    root = _make_pilot_root(tmp_path, n_docs=1)
    missing = get_missing_files(root)
    # pilot_run_summary.json exists, audit files still missing
    assert "pilot_run_summary.json" not in missing
    assert any("_review_quality_audit" in m for m in missing)


def test_data_loader_load_review_quality_audit_missing(tmp_path):
    result = load_review_quality_audit(tmp_path)
    assert result == {}

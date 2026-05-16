"""
test_exports_v20.py — Tests for export_utils.py (ESGProductionControlCenter v2.0).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ESGProductionControlCenter.src.esg_production_control_center.export_utils import (
    MANUAL_BASELINE_COLUMNS,
    V1_ERROR_TYPES,
    export_manual_baseline_template,
    export_quality_decision_report,
    export_review_queue,
)


def _sample_candidates() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "review_item_id": "ri_001",
            "_company_slug": "acme",
            "_fiscal_year": "2024",
            "_official_doc_type": "01_annual_report",
            "page_number": "12",
            "indicator_family": "ghg_emissions",
            "label": "scope 1 emissions",
            "raw_value": "100",
            "raw_unit": "tCO2e",
            "normalized_value": "100",
            "normalized_unit": "tCO2e",
            "quote": "Scope 1 emissions were 100 tCO2e in 2024.",
            "confidence": "0.9",
            "review_priority": "high",
            "suggested_review_action": "confirm",
        }
    ])


def _sample_metrics() -> dict:
    return {
        "documents_selected": 10,
        "documents_success": 10,
        "candidate_count_total": 6027,
        "possible_indicator_rate": 16.9,
        "missing_value_rate": 52.3,
        "review_burden_hours": 127.5,
    }


def _sample_reasons() -> list[dict]:
    return [
        {"Critère": "Workspaces produits", "Résultat": "10/10", "Statut": "✅"},
        {"Critère": "Valeurs manquantes", "Résultat": "52.3 %", "Statut": "❌"},
    ]


def test_export_review_queue(tmp_path):
    df = _sample_candidates()
    out_path = export_review_queue(df, tmp_path / "exports")
    assert out_path.exists()
    assert out_path.name == "review_queue_export.csv"
    result = pd.read_csv(out_path, dtype=str)
    assert len(result) == 1
    assert "indicator_family" in result.columns


def test_export_review_queue_creates_dir(tmp_path):
    df = _sample_candidates()
    nested = tmp_path / "a" / "b" / "c"
    out_path = export_review_queue(df, nested)
    assert out_path.exists()


def test_export_quality_decision_report(tmp_path):
    path = export_quality_decision_report(
        decision="GO_WITH_FIXES",
        metrics=_sample_metrics(),
        reasons=_sample_reasons(),
        output_dir=tmp_path,
    )
    assert path.exists()
    assert path.name == "quality_decision_report.md"
    content = path.read_text(encoding="utf-8")
    assert "GO_WITH_FIXES" in content
    assert "Workspaces produits" in content
    assert "52.3" in content


def test_export_quality_decision_report_contains_all_criteria(tmp_path):
    reasons = [
        {"Critère": f"Critère {i}", "Résultat": f"Résultat {i}", "Statut": "✅"}
        for i in range(6)
    ]
    path = export_quality_decision_report("GO", {}, reasons, tmp_path)
    content = path.read_text(encoding="utf-8")
    for i in range(6):
        assert f"Critère {i}" in content


def test_manual_baseline_template_columns(tmp_path):
    path = export_manual_baseline_template(tmp_path)
    assert path.exists()
    assert path.name == "manual_baseline_template.csv"
    result = pd.read_csv(path, dtype=str)
    assert len(result) == 0  # empty template
    for col in MANUAL_BASELINE_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"


def test_manual_baseline_columns_include_error_type():
    assert "v1_error_type" in MANUAL_BASELINE_COLUMNS


def test_v1_error_types_complete():
    required = [
        "true_positive",
        "false_positive",
        "missed_indicator",
        "wrong_family",
        "section_number_false_positive",
        "iso_standard_false_positive",
    ]
    for r in required:
        assert r in V1_ERROR_TYPES, f"Missing error type: {r}"


def test_export_does_not_overwrite_unrelated_files(tmp_path):
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_text("do not touch", encoding="utf-8")

    export_review_queue(_sample_candidates(), tmp_path)
    export_manual_baseline_template(tmp_path)

    assert sentinel.read_text(encoding="utf-8") == "do not touch"

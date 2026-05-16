"""
test_metrics_v20.py — Tests for metrics.py (ESGProductionControlCenter v2.0).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ESGProductionControlCenter.src.esg_production_control_center.metrics import (
    average_candidates_per_document,
    candidate_count_total,
    compute_all_metrics,
    documents_success_rate,
    evidence_coverage_rate,
    high_risk_rate,
    max_candidates_per_document,
    missing_quote_rate,
    missing_unit_rate,
    missing_value_rate,
    needs_review_rate,
    possible_indicator_rate,
    reject_candidate_rate,
    review_burden_hours,
    unknown_boundary_rate,
)


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, dtype=str)


def _status_row(status: str, family: str = "ghg_emissions", value: str = "100",
                unit: str = "tCO2e", quote: str = "Long enough quote for testing purposes.") -> dict:
    return {
        "validation_status": status,
        "indicator_family": family,
        "raw_value": value,
        "raw_unit": unit,
        "quote": quote,
        "_document_id": "doc_001",
    }


def test_metrics_candidate_rates():
    df = _make_df([
        _status_row("possible_indicator"),
        _status_row("possible_indicator"),
        _status_row("needs_review"),
        _status_row("reject_candidate"),
    ])
    assert candidate_count_total(df) == 4
    assert abs(possible_indicator_rate(df) - 50.0) < 0.01
    assert abs(needs_review_rate(df) - 25.0) < 0.01
    assert abs(reject_candidate_rate(df) - 25.0) < 0.01


def test_metrics_candidate_rates_empty():
    df = pd.DataFrame()
    assert candidate_count_total(df) == 0
    assert possible_indicator_rate(df) == 0.0
    assert needs_review_rate(df) == 0.0
    assert reject_candidate_rate(df) == 0.0


def test_metrics_missing_value_rate():
    df = _make_df([
        _status_row("possible_indicator", value="100"),
        _status_row("possible_indicator", value=""),
        _status_row("needs_review", value=""),
        _status_row("needs_review", value="50"),
    ])
    rate = missing_value_rate(df)
    assert abs(rate - 50.0) < 0.01


def test_metrics_missing_unit_rate():
    df = _make_df([
        _status_row("possible_indicator", unit="tCO2e"),
        _status_row("possible_indicator", unit=""),
    ])
    rate = missing_unit_rate(df)
    assert abs(rate - 50.0) < 0.01


def test_metrics_missing_quote_rate():
    df = _make_df([
        _status_row("possible_indicator", quote="Long quote with enough chars"),
        _status_row("needs_review", quote=""),
        _status_row("needs_review", quote="short"),
        _status_row("reject_candidate", quote="Another valid long enough quote here."),
    ])
    rate = missing_quote_rate(df)
    # 2 short/empty out of 4
    assert abs(rate - 50.0) < 0.01


def test_metrics_unknown_boundary_rate():
    df = _make_df([
        _status_row("possible_indicator", family="ghg_emissions"),
        _status_row("needs_review", family="unknown"),
        _status_row("needs_review", family="boundary"),
        _status_row("reject_candidate", family="energy"),
    ])
    rate = unknown_boundary_rate(df)
    assert abs(rate - 50.0) < 0.01


def test_metrics_review_burden_hours():
    df = _make_df([
        _status_row("possible_indicator"),   # 3 min
        _status_row("possible_indicator"),   # 3 min
        _status_row("needs_review"),         # 1 min
        _status_row("reject_candidate"),     # 0.3 min
    ])
    hours = review_burden_hours(df)
    expected_minutes = 2 * 3.0 + 1 * 1.0 + 1 * 0.3
    assert abs(hours - expected_minutes / 60.0) < 0.001


def test_metrics_documents_success_rate():
    summary = {"documents_processed": 10, "documents_success": 10, "documents_failed": 0}
    assert documents_success_rate(summary) == 100.0

    summary2 = {"documents_processed": 10, "documents_success": 7, "documents_failed": 3}
    assert abs(documents_success_rate(summary2) - 70.0) < 0.01

    summary3 = {"documents_processed": 0}
    assert documents_success_rate(summary3) == 0.0


def test_metrics_average_per_document():
    df = _make_df([
        {**_status_row("possible_indicator"), "_document_id": "doc_001"},
        {**_status_row("needs_review"), "_document_id": "doc_001"},
        {**_status_row("possible_indicator"), "_document_id": "doc_002"},
    ])
    avg = average_candidates_per_document(df)
    assert abs(avg - 1.5) < 0.01


def test_metrics_max_per_document():
    df = _make_df([
        {**_status_row("possible_indicator"), "_document_id": "doc_001"},
        {**_status_row("needs_review"), "_document_id": "doc_001"},
        {**_status_row("possible_indicator"), "_document_id": "doc_002"},
    ])
    assert max_candidates_per_document(df) == 2


def test_metrics_high_risk_rate():
    fp_df = pd.DataFrame([
        {"risk_level": "high"},
        {"risk_level": "medium"},
        {"risk_level": "medium"},
    ])
    rate = high_risk_rate(fp_df, total=100)
    assert abs(rate - 1.0) < 0.01

    assert high_risk_rate(pd.DataFrame(), total=0) == 0.0


def test_metrics_evidence_coverage_rate():
    df = _make_df([
        _status_row("possible_indicator", value="100", quote="A long enough quote with info"),
        _status_row("needs_review", value="", quote="Another good long quote here"),
        _status_row("reject_candidate", value="50", quote=""),
    ])
    rate = evidence_coverage_rate(df)
    # Only first row has both value and long quote
    assert abs(rate - 100.0 / 3.0) < 1.0


def test_compute_all_metrics_keys():
    pilot_summary = {
        "documents_selected": 10, "documents_processed": 10,
        "documents_success": 10, "documents_failed": 0,
    }
    df = _make_df([_status_row("possible_indicator")])
    fp_df = pd.DataFrame()
    result = compute_all_metrics(pilot_summary, df, fp_df)

    required_keys = [
        "candidate_count_total", "possible_indicator_rate", "needs_review_rate",
        "missing_value_rate", "missing_quote_rate", "unknown_boundary_rate",
        "review_burden_hours", "documents_success_rate",
    ]
    for k in required_keys:
        assert k in result, f"Missing key: {k}"

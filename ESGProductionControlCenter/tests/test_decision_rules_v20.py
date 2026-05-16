"""
test_decision_rules_v20.py — Tests for decision_rules.py (ESGProductionControlCenter v2.0).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ESGProductionControlCenter.src.esg_production_control_center.decision_rules import (
    GO_EXPLANATION,
    NEXT_STEPS,
    compute_decision,
    get_decision_reasons,
)


def _metrics(**kwargs) -> dict:
    base = {
        "documents_selected": 10,
        "documents_processed": 10,
        "documents_success": 10,
        "documents_failed": 0,
        "documents_success_rate": 100.0,
        "missing_quote_rate": 0.0,
        "missing_value_rate": 10.0,
        "unknown_boundary_rate": 20.0,
        "review_burden_hours": 30.0,
        "high_risk_rate": 0.5,
        "false_positive_risk_rate": 2.0,
    }
    base.update(kwargs)
    return base


def test_decision_rules_go():
    m = _metrics(
        missing_quote_rate=2.0,
        missing_value_rate=15.0,
        unknown_boundary_rate=20.0,
        review_burden_hours=30.0,
        high_risk_rate=0.5,
    )
    assert compute_decision(m) == "GO"


def test_decision_rules_go_with_fixes_current_state():
    """Reflects the real pilot state: GO_WITH_FIXES."""
    m = _metrics(
        missing_value_rate=52.3,
        unknown_boundary_rate=62.2,
        review_burden_hours=127.5,
        high_risk_rate=0.07,
        missing_quote_rate=0.0,
    )
    assert compute_decision(m) == "GO_WITH_FIXES"


def test_decision_rules_go_with_fixes_high_burden():
    m = _metrics(review_burden_hours=80.0)
    assert compute_decision(m) == "GO_WITH_FIXES"


def test_decision_rules_go_with_fixes_high_noise():
    m = _metrics(unknown_boundary_rate=55.0)
    assert compute_decision(m) == "GO_WITH_FIXES"


def test_decision_rules_no_go_missing_workspaces():
    m = _metrics(
        documents_success=3,
        documents_selected=10,
        documents_success_rate=30.0,
    )
    assert compute_decision(m) == "NO_GO"


def test_decision_rules_no_go_zero_success():
    m = _metrics(
        documents_success=0,
        documents_selected=5,
        documents_success_rate=0.0,
    )
    assert compute_decision(m) == "NO_GO"


def test_decision_rules_no_go_missing_quotes():
    m = _metrics(missing_quote_rate=60.0)
    assert compute_decision(m) == "NO_GO"


def test_decision_rules_get_reasons_returns_list():
    m = _metrics()
    reasons = get_decision_reasons(m)
    assert isinstance(reasons, list)
    assert len(reasons) >= 4
    for r in reasons:
        assert "Critère" in r
        assert "Résultat" in r
        assert "Statut" in r


def test_decision_rules_reasons_include_pass_fail():
    m = _metrics(
        missing_value_rate=52.3,
        unknown_boundary_rate=62.2,
        review_burden_hours=127.5,
        missing_quote_rate=0.0,
        high_risk_rate=0.07,
    )
    reasons = get_decision_reasons(m)
    statuses = [r["Statut"] for r in reasons]
    assert "✅" in statuses, "Expected at least one passing criterion"
    assert "❌" in statuses, "Expected at least one failing criterion"


def test_go_explanation_keys():
    for key in ["GO", "GO_WITH_FIXES", "NO_GO"]:
        assert key in GO_EXPLANATION
        assert len(GO_EXPLANATION[key]) > 10


def test_next_steps_structure():
    for key in ["GO", "GO_WITH_FIXES", "NO_GO"]:
        assert key in NEXT_STEPS
        assert isinstance(NEXT_STEPS[key], list)
        assert len(NEXT_STEPS[key]) >= 1


def test_decision_rules_empty_selected():
    m = _metrics(documents_selected=0)
    result = compute_decision(m)
    assert result in {"GO", "GO_WITH_FIXES", "NO_GO"}

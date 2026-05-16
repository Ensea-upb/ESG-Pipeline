"""
metrics.py — KPI calculation for ESGProductionControlCenter v2.0.
No Streamlit dependency. Pure functions on dicts / DataFrames.
"""
from __future__ import annotations

import pandas as pd

MINUTES_POSSIBLE = 3.0
MINUTES_NEEDS_REVIEW = 1.0
MINUTES_REJECT = 0.3


def documents_success_rate(pilot_summary: dict) -> float:
    total = pilot_summary.get("documents_processed", 0)
    success = pilot_summary.get("documents_success", 0)
    if total == 0:
        return 0.0
    return success / total * 100.0


def candidate_count_total(df: pd.DataFrame) -> int:
    return len(df)


def _status_count(df: pd.DataFrame, status: str) -> int:
    if df.empty or "validation_status" not in df.columns:
        return 0
    return int((df["validation_status"] == status).sum())


def possible_indicator_rate(df: pd.DataFrame) -> float:
    n = len(df)
    if n == 0:
        return 0.0
    return _status_count(df, "possible_indicator") / n * 100.0


def needs_review_rate(df: pd.DataFrame) -> float:
    n = len(df)
    if n == 0:
        return 0.0
    return _status_count(df, "needs_review") / n * 100.0


def reject_candidate_rate(df: pd.DataFrame) -> float:
    n = len(df)
    if n == 0:
        return 0.0
    return _status_count(df, "reject_candidate") / n * 100.0


def missing_value_rate(df: pd.DataFrame) -> float:
    if df.empty or "raw_value" not in df.columns:
        return 0.0
    empty = df["raw_value"].apply(lambda x: not str(x).strip()).sum()
    return empty / len(df) * 100.0


def missing_unit_rate(df: pd.DataFrame) -> float:
    if df.empty or "raw_unit" not in df.columns:
        return 0.0
    empty = df["raw_unit"].apply(lambda x: not str(x).strip()).sum()
    return empty / len(df) * 100.0


def missing_quote_rate(df: pd.DataFrame) -> float:
    if df.empty or "quote" not in df.columns:
        return 0.0
    short = df["quote"].apply(lambda x: len(str(x).strip()) < 10).sum()
    return short / len(df) * 100.0


def unknown_boundary_rate(df: pd.DataFrame) -> float:
    if df.empty or "indicator_family" not in df.columns:
        return 0.0
    noisy = df["indicator_family"].isin(["unknown", "boundary"]).sum()
    return noisy / len(df) * 100.0


def false_positive_risk_rate(fp_df: pd.DataFrame, total: int) -> float:
    if total == 0:
        return 0.0
    return len(fp_df) / total * 100.0


def high_risk_rate(fp_df: pd.DataFrame, total: int) -> float:
    if total == 0 or fp_df.empty or "risk_level" not in fp_df.columns:
        return 0.0
    return int((fp_df["risk_level"] == "high").sum()) / total * 100.0


def review_burden_hours(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    n_possible = _status_count(df, "possible_indicator")
    n_needs = _status_count(df, "needs_review")
    n_reject = _status_count(df, "reject_candidate")
    minutes = n_possible * MINUTES_POSSIBLE + n_needs * MINUTES_NEEDS_REVIEW + n_reject * MINUTES_REJECT
    return minutes / 60.0


def average_candidates_per_document(df: pd.DataFrame) -> float:
    col = "_document_id"
    if df.empty or col not in df.columns:
        return 0.0
    n_docs = df[col].nunique()
    return len(df) / n_docs if n_docs > 0 else 0.0


def max_candidates_per_document(df: pd.DataFrame) -> int:
    col = "_document_id"
    if df.empty or col not in df.columns:
        return 0
    return int(df.groupby(col).size().max())


def evidence_coverage_rate(df: pd.DataFrame) -> float:
    """Fraction of candidates that have both a value and a quote."""
    if df.empty:
        return 0.0
    has_val = df.get("raw_value", pd.Series(dtype=str)).apply(lambda x: bool(str(x).strip()))
    has_quote = df.get("quote", pd.Series(dtype=str)).apply(lambda x: len(str(x).strip()) >= 10)
    if len(has_val) == 0:
        return 0.0
    return (has_val & has_quote).sum() / len(df) * 100.0


def compute_all_metrics(pilot_summary: dict, df: pd.DataFrame, fp_df: pd.DataFrame) -> dict:
    total = len(df)
    return {
        "documents_selected": pilot_summary.get("documents_selected", 0),
        "documents_processed": pilot_summary.get("documents_processed", 0),
        "documents_success": pilot_summary.get("documents_success", 0),
        "documents_failed": pilot_summary.get("documents_failed", 0),
        "documents_success_rate": documents_success_rate(pilot_summary),
        "candidate_count_total": total,
        "possible_indicator_count": _status_count(df, "possible_indicator"),
        "needs_review_count": _status_count(df, "needs_review"),
        "reject_candidate_count": _status_count(df, "reject_candidate"),
        "possible_indicator_rate": possible_indicator_rate(df),
        "needs_review_rate": needs_review_rate(df),
        "reject_candidate_rate": reject_candidate_rate(df),
        "missing_value_rate": missing_value_rate(df),
        "missing_unit_rate": missing_unit_rate(df),
        "missing_quote_rate": missing_quote_rate(df),
        "unknown_boundary_rate": unknown_boundary_rate(df),
        "false_positive_count": len(fp_df),
        "false_positive_risk_rate": false_positive_risk_rate(fp_df, total),
        "high_risk_rate": high_risk_rate(fp_df, total),
        "review_burden_hours": review_burden_hours(df),
        "average_candidates_per_document": average_candidates_per_document(df),
        "max_candidates_per_document": max_candidates_per_document(df),
        "evidence_coverage_rate": evidence_coverage_rate(df),
    }

from __future__ import annotations

from typing import Any


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_review_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        priority, reason, action = _review_fields(row)
        row["review_priority"] = priority
        row["review_reason"] = reason
        row["review_action_suggested"] = action
        row["ready_for_manual_review"] = "True"
    return sorted(rows, key=lambda row: (PRIORITY_ORDER.get(row["review_priority"], 9), row["document_id"], row["page_number"], row["candidate_validation_id"]))


def _review_fields(row: dict[str, Any]) -> tuple[str, str, str]:
    if row["validation_status"] == "possible_indicator" and row.get("normalized_value") and row.get("normalized_unit") and row.get("normalized_year"):
        return "high", "possible indicator with value, unit, year and source", "verify_value"
    if row.get("duplicate_status") == "canonical":
        return "high", "canonical candidate from duplicate group", "compare_duplicate"
    if row["validation_status"] == "possible_indicator":
        return "medium", "possible indicator needs missing detail review", "verify_unit"
    if row["validation_status"] == "needs_review" and row.get("normalized_value"):
        return "medium", "candidate has numeric signal but needs context review", "inspect_quote"
    if row["indicator_family"] == "unknown":
        return "low", "unknown indicator family", "reject_if_not_esg"
    return "low", "contextual or qualitative candidate", "inspect_quote"

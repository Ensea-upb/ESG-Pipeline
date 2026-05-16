from __future__ import annotations


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2, "": 3}
ALLOWED_PROPOSED_DECISIONS = {"accept_candidate", "reject_candidate", "needs_more_evidence", "defer_decision", ""}
REVIEW_STATUS_BY_DECISION = {
    "accept_candidate": "accepted_candidate",
    "reject_candidate": "rejected_by_reviewer",
    "needs_more_evidence": "needs_more_evidence",
    "defer_decision": "decision_deferred",
    "": "missing_decision",
}


def sort_review_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda row: (
        0 if row.get("validation_status") == "possible_indicator" else 1,
        PRIORITY_ORDER.get(row.get("review_priority", ""), 9),
        row.get("document_id", ""),
        row.get("page_number", ""),
        row.get("review_item_id", ""),
    ))


def decision_to_status(decision: str) -> str:
    return REVIEW_STATUS_BY_DECISION.get(decision, "invalid_decision")

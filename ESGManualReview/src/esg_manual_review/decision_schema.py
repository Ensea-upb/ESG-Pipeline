from __future__ import annotations


DECISION_TEMPLATE_FIELDS = [
    "review_item_id", "candidate_id", "proposed_decision", "reviewer", "review_date",
    "decision_reason", "corrected_value", "corrected_unit", "corrected_year",
    "corrected_indicator_family", "corrected_indicator_key",
    "needs_more_evidence_reason", "reviewer_notes",
]

DECISION_SCHEMA = {
    "schema_version": "1.0.0",
    "allowed_proposed_decision": [
        "accept_candidate",
        "reject_candidate",
        "needs_more_evidence",
        "defer_decision",
    ],
    "note": "accept_candidate is not a final validated ESG indicator.",
}

from __future__ import annotations

import re


METRIC_TYPES = {"observed_metric", "table_metric_candidate", "visual_metric_candidate", "target"}
QUALITATIVE_TYPES = {"policy_or_commitment", "risk_statement", "boundary_context", "methodology_context", "visual_context_evidence", "visual_policy_evidence", "visual_risk_evidence"}

# Seuils de routage — réduisent la charge de revue humaine
AUTO_ACCEPT_THRESHOLD = 0.30   # possible_indicator avec confiance ≥ seuil → accepté sans revue
AUTO_REJECT_THRESHOLD = 0.20   # candidat avec confiance < seuil → rejeté automatiquement


def assign_validation_status(row: dict[str, str], normalized: dict[str, str], family: dict[str, object]) -> tuple[str, str]:
    if _has_forbidden_signal(row):
        return "reject_candidate", "score or validated indicator signal detected"
    if (row.get("review_required") or "True") != "True":
        return "reject_candidate", "review_required is not true"
    if (row.get("extraction_status") or "candidate_only") != "candidate_only":
        return "reject_candidate", "extraction_status is not candidate_only"
    if not row.get("quote"):
        return "reject_candidate", "missing quote"
    if not (row.get("evidence_id") or row.get("table_id") or row.get("figure_id")):
        return "reject_candidate", "missing source trace"
    if not row.get("page_number"):
        return "reject_candidate", "missing page number"
    info_type = row.get("information_type", "")
    if info_type in METRIC_TYPES:
        if not normalized.get("normalized_value"):
            return "reject_candidate", "metric-like candidate has no usable numeric value"
        if family.get("indicator_family") != "unknown" and normalized.get("normalized_year"):
            return "possible_indicator", "metric-like candidate has value, source, page and family mapping"
        return "needs_review", "metric-like candidate needs unit, year or family review"
    if info_type in QUALITATIVE_TYPES:
        return "needs_review", "qualitative ESG candidate requires human review"
    return "needs_review", "candidate requires human review"


_SCORE_INJECTION_RE = re.compile(r"\bscore\s*=\s*\d", re.IGNORECASE)


def _has_forbidden_signal(row: dict[str, str]) -> bool:
    if str(row.get("is_validated_indicator", "")).lower() == "true":
        return True
    if str(row.get("validation_status", "")).lower() == "validated":
        return True
    if str(row.get("score_produced", "")).lower() == "true":
        return True
    # Detect "score=<number>" smuggled into arbitrary field values (pre-scored data injection).
    for val in row.values():
        if _SCORE_INJECTION_RE.search(str(val or "")):
            return True
    return False

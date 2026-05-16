from __future__ import annotations

from typing import Any


def build_lineage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lineage = []
    for row in rows:
        corrections = []
        if row.get("value_source") == "corrected_value":
            corrections.append("corrected_value")
        if row.get("unit_source") == "corrected_unit":
            corrections.append("corrected_unit")
        if row.get("year_source") == "corrected_year":
            corrections.append("corrected_year")
        complete = all(row.get(field) for field in ["candidate_id", "document_id", "quote", "page_number"]) and bool(row.get("review_status"))
        lineage.append({
            "preparation_indicator_id": row.get("preparation_indicator_id", ""),
            "candidate_id": row.get("candidate_id", ""),
            "review_item_id": row.get("review_item_id", ""),
            "document_id": row.get("document_id", ""),
            "source_engine": row.get("source_engine", ""),
            "original_extraction_status": "candidate_only",
            "validation_status": row.get("validation_status", ""),
            "human_review_status": row.get("review_status", ""),
            "indicator_database_status": row.get("indicator_database_status", ""),
            "source_modules": ["ESGManualReview", "ESGIndicatorValidation", "ESGExtractionOrchestrator"],
            "input_files_used": ["accepted_candidate_inputs.csv", "reviewed_candidates.csv"],
            "transformations_applied": ["schema_mapping", "value_preparation", "evidence_linking"],
            "corrections_applied": corrections,
            "lineage_complete": complete,
            "lineage_warnings": [] if complete else ["missing_required_traceability_or_review_status"],
        })
    return lineage

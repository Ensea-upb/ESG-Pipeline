from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io_utils import write_csv, write_jsonl


LONG_FIELDS = [
    "company", "year", "variable_name", "value", "unit", "status", "source_document",
    "page_number", "quote", "confidence", "selection_reason", "lineage_id",
]

EVIDENCE_FIELDS = [
    "company", "year", "variable_name", "preparation_indicator_id", "candidate_id",
    "document_id", "source_engine", "page_number", "quote", "evidence_id", "table_id",
    "cell_id", "figure_id", "evidence_role", "evidence_quality_status",
]

MISSING_FIELDS = ["company", "year", "variable_name", "status", "reason", "recommended_action"]


def build_traceability_outputs(selected: list[dict[str, Any]], output_dir: Path) -> dict[str, int]:
    long_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    lineage_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []

    for index, row in enumerate(selected, start=1):
        lineage_id = f"lineage_{index:06d}"
        status = row.get("selected_status", "")
        long_rows.append(
            {
                "company": row.get("company", ""),
                "year": row.get("year", ""),
                "variable_name": row.get("variable_name", ""),
                "value": row.get("selected_value", ""),
                "unit": row.get("selected_unit", ""),
                "status": status,
                "source_document": row.get("selected_source_document", ""),
                "page_number": row.get("selected_page_number", ""),
                "quote": row.get("selected_quote", ""),
                "confidence": row.get("selected_confidence", ""),
                "selection_reason": row.get("selection_reason", ""),
                "lineage_id": lineage_id,
            }
        )

        has_evidence = any(
            row.get(field, "") for field in ("preparation_indicator_id", "evidence_id", "selected_quote", "cell_id", "figure_id")
        )
        if status in {"found", "qualitative_only", "conflicting_values", "needs_review"} and has_evidence:
            evidence_rows.append(
                {
                    "company": row.get("company", ""),
                    "year": row.get("year", ""),
                    "variable_name": row.get("variable_name", ""),
                    "preparation_indicator_id": row.get("preparation_indicator_id", ""),
                    "candidate_id": row.get("candidate_id", ""),
                    "document_id": row.get("selected_source_document", ""),
                    "source_engine": row.get("source_engine", ""),
                    "page_number": row.get("selected_page_number", ""),
                    "quote": row.get("selected_quote", ""),
                    "evidence_id": row.get("evidence_id", ""),
                    "table_id": row.get("table_id", ""),
                    "cell_id": row.get("cell_id", ""),
                    "figure_id": row.get("figure_id", ""),
                    "evidence_role": "selected" if status == "found" else status,
                    "evidence_quality_status": "present",
                }
            )

        if status != "found":
            missing_rows.append(
                {
                    "company": row.get("company", ""),
                    "year": row.get("year", ""),
                    "variable_name": row.get("variable_name", ""),
                    "status": status,
                    "reason": row.get("selection_reason", "") or "No usable corpus value selected.",
                    "recommended_action": _recommended_action(status),
                }
            )

        lineage_rows.append(
            {
                "lineage_id": lineage_id,
                "company": row.get("company", ""),
                "year": row.get("year", ""),
                "variable_name": row.get("variable_name", ""),
                "status": status,
                "final_dataset_field": row.get("variable_name", ""),
                "preparation_indicator_id": row.get("preparation_indicator_id", ""),
                "candidate_id": row.get("candidate_id", ""),
                "document_id": row.get("selected_source_document", ""),
                "source_engine": row.get("source_engine", ""),
                "lineage_note": "final variable -> preparation database -> review/validation/extraction lineage where available",
            }
        )

    write_csv(output_dir / "esg_variables_long.csv", long_rows, LONG_FIELDS)
    write_csv(output_dir / "esg_variables_evidence.csv", evidence_rows, EVIDENCE_FIELDS)
    write_jsonl(output_dir / "esg_variables_lineage.jsonl", lineage_rows)
    write_csv(output_dir / "esg_variables_missing_report.csv", missing_rows, MISSING_FIELDS)
    return {
        "long_rows_count": len(long_rows),
        "evidence_rows_count": len(evidence_rows),
        "lineage_records_count": len(lineage_rows),
        "missing_rows_count": len(missing_rows),
    }


def _recommended_action(status: str) -> str:
    if status == "missing_from_corpus":
        return "Confirm whether the corpus PDFs disclose this variable."
    if status == "conflicting_values":
        return "Review all candidate values and select the correct disclosed value."
    if status == "qualitative_only":
        return "Keep qualitative status or add numeric disclosure if found in PDFs."
    if status == "needs_review":
        return "Review incomplete candidate evidence before using the value."
    if status == "not_disclosed":
        return "Record explicit non-disclosure if supported by PDF evidence."
    return "Review variable status."

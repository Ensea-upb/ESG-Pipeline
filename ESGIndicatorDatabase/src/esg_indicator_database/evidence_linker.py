from __future__ import annotations

from typing import Any


EVIDENCE_FIELDS = [
    "evidence_link_id", "preparation_indicator_id", "candidate_id", "document_id",
    "page_number", "quote", "source_engine", "evidence_id", "table_id", "cell_id",
    "figure_id", "source_trace_type", "evidence_quality_status", "evidence_notes",
]


def build_evidence_links(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links = []
    for idx, row in enumerate(rows, start=1):
        quality = "available"
        notes = []
        if not row.get("quote"):
            quality = "missing_quote"
            notes.append("missing_quote")
        if not row.get("page_number"):
            quality = "missing_page"
            notes.append("missing_page")
        links.append({
            "evidence_link_id": f"evidence_link_{idx:06d}",
            "preparation_indicator_id": row.get("preparation_indicator_id", ""),
            "candidate_id": row.get("candidate_id", ""),
            "document_id": row.get("document_id", ""),
            "page_number": row.get("page_number", ""),
            "quote": row.get("quote", ""),
            "source_engine": row.get("source_engine", ""),
            "evidence_id": row.get("evidence_id", ""),
            "table_id": row.get("table_id", ""),
            "cell_id": row.get("cell_id", ""),
            "figure_id": row.get("figure_id", ""),
            "source_trace_type": _trace_type(row),
            "evidence_quality_status": quality,
            "evidence_notes": "|".join(notes),
        })
    return links


def _trace_type(row: dict[str, Any]) -> str:
    has_text = bool(row.get("evidence_id"))
    has_table = bool(row.get("table_id") or row.get("cell_id"))
    has_visual = bool(row.get("figure_id"))
    if sum([has_text, has_table, has_visual]) > 1:
        return "mixed"
    if has_table:
        return "table_cell"
    if has_visual:
        return "visual_figure"
    if has_text:
        return "text_evidence"
    return "unknown"

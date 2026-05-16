from __future__ import annotations

from collections import defaultdict
from typing import Any

from .io_utils import normalize


def reconstruct_tables(tables: list[dict[str, Any]], cells: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    cells_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cell in cells:
        cells_by_table[str(cell.get("table_id", ""))].append(cell)
    reconstructed: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for table in tables:
        table_id = str(table.get("table_id", ""))
        row_count = int(table.get("row_count") or 0)
        column_count = int(table.get("column_count") or 0)
        matrix = [["" for _ in range(column_count)] for _ in range(row_count)]
        non_empty = 0
        for cell in cells_by_table.get(table_id, []):
            r = int(cell.get("row_index") or 0)
            c = int(cell.get("column_index") or 0)
            if 0 <= r < row_count and 0 <= c < column_count:
                text = normalize(cell.get("normalized_text") or cell.get("text"))
                matrix[r][c] = text
                if text:
                    non_empty += 1
        total = row_count * column_count
        empty = max(total - non_empty, 0)
        status = "empty_table" if non_empty == 0 else "reconstructed"
        confidence = 0.2 if status == "empty_table" else min(float(table.get("table_confidence") or 0.4), 0.8)
        reconstructed.append({
            "schema_version": "0.2.0",
            "document_id": table.get("document_id", ""),
            "table_id": table_id,
            "page_number": table.get("page_number"),
            "section_id": table.get("section_id") or "",
            "row_count": row_count,
            "column_count": column_count,
            "matrix": matrix,
            "non_empty_cells_count": non_empty,
            "empty_cells_count": empty,
            "reconstruction_status": status,
            "reconstruction_confidence": round(confidence, 2),
            "review_required": True,
            "source_extraction_status": table.get("extraction_status", ""),
            "table_quality_flags": table.get("table_quality_flags") or [],
        })
        audit.append({
            "schema_version": "0.2.0",
            "table_id": table_id,
            "status": status,
            "message": f"{non_empty}/{total} non-empty cells reconstructed.",
            "review_required": True,
        })
    summary = {
        "schema_version": "0.2.0",
        "reconstructed_tables_count": len(reconstructed),
        "empty_tables_count": sum(1 for row in reconstructed if row["reconstruction_status"] == "empty_table"),
        "low_confidence_tables_count": sum(1 for row in tables if row.get("extraction_status") == "low_confidence"),
    }
    return reconstructed, audit, summary

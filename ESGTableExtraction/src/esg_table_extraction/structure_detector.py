from __future__ import annotations

import re
from typing import Any


YEAR_RE = re.compile(r"\b(?:FY)?(20[0-4]\d|19[8-9]\d)\b", re.IGNORECASE)
UNIT_RE = re.compile(
    r"\b(%|(?:k|m|g)?tco2e?|co2eq?|gwh|mwh|kwh|gj|mj|tep|toe"
    r"|hm3|m3|m²|tonnes?|(?<!\w)ha(?!\w)|hectares?|km2|m2"
    r"|employees?|headcount|hours?|heures?|accidents?|fte"
    r"|(?<!\w)kt(?!\w)|(?<!\w)mt(?!\w))\b",
    re.IGNORECASE,
)
NUM_RE = re.compile(r"\d")

# Maximum number of rows scanned from the top of a table to detect headers.
_HEADER_SCAN_ROWS = 5


def detect_structures(reconstructed: list[dict[str, Any]], fiscal_year: str = "") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table in reconstructed:
        matrix = table.get("matrix") or []
        header_rows = [idx for idx, row in enumerate(matrix[:_HEADER_SCAN_ROWS]) if any(YEAR_RE.search(str(cell)) or UNIT_RE.search(str(cell)) for cell in row)]
        if not header_rows and matrix:
            header_rows = [0]
        year_cols: list[dict[str, Any]] = []
        unit_cells: list[dict[str, Any]] = []
        label_cols: list[int] = []
        for r, row in enumerate(matrix):
            for c, cell in enumerate(row):
                text = str(cell)
                for match in YEAR_RE.finditer(text):
                    year_cols.append({"row_index": r, "column_index": c, "year": match.group(1), "inferred_year": False})
                if UNIT_RE.search(text):
                    unit_cells.append({"row_index": r, "column_index": c, "unit": UNIT_RE.search(text).group(1)})
        for c in range(int(table.get("column_count") or 0)):
            values = [str(row[c]) for row in matrix if c < len(row)]
            text_cells = [v for v in values if len(v) > 3 and not NUM_RE.search(v)]
            if len(text_cells) >= max(1, len(values) // 4):
                label_cols.append(c)
        warnings = []
        if not year_cols and fiscal_year:
            year_cols.append({"row_index": None, "column_index": None, "year": fiscal_year, "inferred_year": True})
            warnings.append("year_inferred_from_document")
        if not unit_cells:
            warnings.append("unit_not_detected")
        rows.append({
            "schema_version": "0.3.0",
            "document_id": table.get("document_id", ""),
            "table_id": table.get("table_id", ""),
            "page_number": table.get("page_number"),
            "header_row_indices": header_rows,
            "candidate_year_columns": year_cols,
            "candidate_unit_cells": unit_cells,
            "candidate_label_columns": label_cols,
            "has_year_headers": any(not item.get("inferred_year") for item in year_cols),
            "has_unit_context": bool(unit_cells),
            "structure_confidence": 0.55 if year_cols or unit_cells else 0.25,
            "structure_warnings": warnings,
            "review_required": True,
        })
    summary = {
        "schema_version": "0.3.0",
        "tables_structured_count": len(rows),
        "tables_with_year_headers_count": sum(1 for row in rows if row["has_year_headers"]),
        "tables_with_unit_context_count": sum(1 for row in rows if row["has_unit_context"]),
        "tables_with_inferred_year_count": sum(1 for row in rows if any(item.get("inferred_year") for item in row["candidate_year_columns"])),
    }
    return rows, summary

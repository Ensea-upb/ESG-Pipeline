from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json, read_jsonl


def load_table_inputs(input_dir: Path) -> dict[str, Any]:
    if not (input_dir / "table_index.jsonl").exists():
        raise FileNotFoundError(f"table_index.jsonl is required: {input_dir / 'table_index.jsonl'}")
    if not (input_dir / "table_cells.jsonl").exists():
        raise FileNotFoundError(f"table_cells.jsonl is required: {input_dir / 'table_cells.jsonl'}")
    inventory = read_json(input_dir / "document_inventory.json")
    summary = read_json(input_dir / "extraction_summary.json")
    tables = read_jsonl(input_dir / "table_index.jsonl")
    cells = read_jsonl(input_dir / "table_cells.jsonl")
    stats = read_json(input_dir / "table_statistics.json")
    document_id = str(inventory.get("document_id") or summary.get("document_id") or input_dir.name)
    pdf_path = str(inventory.get("pdf_path") or summary.get("pdf_path") or "")
    return {
        "document_id": document_id,
        "pdf_path": pdf_path,
        "inventory": inventory,
        "summary": summary,
        "tables": tables,
        "cells": cells,
        "table_statistics": stats,
    }


def table_items(tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "schema_version": "0.1.0",
        "document_id": row.get("document_id", ""),
        "table_id": row.get("table_id", ""),
        "page_number": row.get("page_number"),
        "section_id": row.get("section_id") or "",
        "extraction_status": row.get("extraction_status", ""),
        "row_count": row.get("row_count", 0),
        "column_count": row.get("column_count", 0),
        "cell_count": row.get("cell_count", 0),
        "table_confidence": row.get("table_confidence", 0),
        "review_required": True,
        "table_quality_flags": row.get("table_quality_flags") or [],
        "is_quarantined_table": bool(row.get("is_quarantined_table", False)),
    } for row in tables]


def loaded_cells(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "schema_version": "0.1.0",
        "document_id": row.get("document_id", ""),
        "cell_id": row.get("cell_id", ""),
        "table_id": row.get("table_id", ""),
        "page_number": row.get("page_number"),
        "row_index": row.get("row_index", 0),
        "column_index": row.get("column_index", 0),
        "text": row.get("text", ""),
        "normalized_text": row.get("normalized_text", row.get("text", "")),
        "is_header_cell": bool(row.get("is_header_cell", False)),
        "cell_confidence": row.get("cell_confidence", 0),
    } for row in cells]

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from .candidate_extractor import ESGTableExtractor
from .contract import validate_table_outputs
from .io_utils import read_json, utcnow, write_json


SUMMARY = "multi_document_table_audit_summary.json"
CSV_FILE = "multi_document_table_audit.csv"
MD_FILE = "multi_document_table_audit.md"
FIELDS = ["input_dir", "output_dir", "document_id", "tables_count", "cells_count", "candidates_count", "candidates_without_unit", "candidates_without_year", "candidates_from_low_confidence_tables", "contract_status"]


def find_inputs(root: Path) -> list[Path]:
    return [
        path for path in sorted(root.rglob("*"), key=lambda p: str(p).lower())
        if path.is_dir() and (path / "table_index.jsonl").exists() and (path / "table_cells.jsonl").exists()
    ]


def run_multi_document_table_audit(input_root: Path, output_dir: Path, contract_path: Path, overwrite: bool = False, max_documents: int | None = None) -> dict[str, Any]:
    inputs = find_inputs(input_root)
    if max_documents:
        inputs = inputs[:max_documents]
    if output_dir.exists() and any((output_dir / f).exists() for f in [SUMMARY, CSV_FILE, MD_FILE]) and not overwrite:
        raise FileExistsError("multi-document table audit outputs already exist")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    family_counter: Counter[str] = Counter()
    for input_dir in inputs:
        doc_out = output_dir / "documents" / input_dir.name
        result = ESGTableExtractor(input_dir, doc_out, overwrite=overwrite).run()
        validation = validate_table_outputs(doc_out, contract_path)
        audit = read_json(doc_out / "table_audit_summary.json")
        rows.append({
            "input_dir": str(input_dir.resolve()),
            "output_dir": str(doc_out.resolve()),
            "document_id": result.summary.get("document_id", input_dir.name),
            "tables_count": result.summary.get("tables_read_count", 0),
            "cells_count": result.summary.get("cells_read_count", 0),
            "candidates_count": result.summary.get("table_candidates_count", 0),
            "candidates_without_unit": audit.get("checks", {}).get("candidates_without_unit", 0),
            "candidates_without_year": audit.get("checks", {}).get("candidates_without_year", 0),
            "candidates_from_low_confidence_tables": audit.get("checks", {}).get("candidates_from_low_confidence_tables", 0),
            "contract_status": validation["status"],
        })
        family_counter.update(result.summary.get("metric_family_distribution", {}))
    summary = {
        "schema_version": "0.9.0", "generated_at": utcnow(), "input_root": str(input_root.resolve()), "output_dir": str(output_dir.resolve()),
        "documents_tested_count": len(rows), "companies_detected": [], "years_detected": [],
        "tables_count_total": sum(int(row["tables_count"]) for row in rows),
        "cells_count_total": sum(int(row["cells_count"]) for row in rows),
        "candidates_count_total": sum(int(row["candidates_count"]) for row in rows),
        "candidates_by_metric_family": dict(family_counter),
        "candidates_without_unit_total": sum(int(row["candidates_without_unit"]) for row in rows),
        "candidates_without_year_total": sum(int(row["candidates_without_year"]) for row in rows),
        "candidates_from_low_confidence_tables_total": sum(int(row["candidates_from_low_confidence_tables"]) for row in rows),
        "real_world_table_audit_pending": len(rows) < 3,
    }
    write_json(output_dir / SUMMARY, summary)
    with (output_dir / CSV_FILE).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Multi-document Table Audit", "", f"- documents_tested_count: {len(rows)}", f"- candidates_count_total: {summary['candidates_count_total']}", "", "## Metric Families"]
    lines += [f"- {k}: {v}" for k, v in sorted(family_counter.items())]
    (output_dir / MD_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from .io_utils import read_json, utcnow, write_json
from .runner import FullExtractionRunner


def find_inputs(root: Path) -> list[Path]:
    return [p for p in sorted(root.rglob("*"), key=lambda x: str(x).lower()) if p.is_dir() and (p / "multimodal_evidence_index.jsonl").exists() and (p / "table_index.jsonl").exists() and (p / "figure_index.jsonl").exists()]


def run_multi_document_full_extraction(input_root: Path, output_dir: Path, overwrite: bool = False, max_documents: int | None = None) -> dict[str, Any]:
    inputs = find_inputs(input_root)
    if max_documents:
        inputs = inputs[:max_documents]
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    dist: Counter[str] = Counter()
    for input_dir in inputs:
        doc_out = output_dir / "documents" / input_dir.name
        result = FullExtractionRunner(input_dir, doc_out, overwrite=overwrite).run()
        summary = result.summary
        rows.append({
            "input_dir": str(input_dir.resolve()),
            "output_dir": str(doc_out.resolve()),
            "document_id": read_json(input_dir / "document_inventory.json").get("document_id", input_dir.name),
            "csv_candidates_count": summary["csv_candidates_count"],
            "visual_candidates_count": summary["visual_candidates_count"],
            "table_candidates_count": summary["table_candidates_count"],
            "consolidated_candidates_count": summary["consolidated_candidates_count"],
        })
        dist.update(summary.get("source_engine_distribution", {}))
    summary = {
        "schema_version": "0.7.0",
        "generated_at": utcnow(),
        "input_root": str(input_root.resolve()),
        "output_dir": str(output_dir.resolve()),
        "documents_tested_count": len(rows),
        "consolidated_candidates_total": sum(int(row["consolidated_candidates_count"]) for row in rows),
        "source_engine_distribution": dict(dist),
    }
    write_json(output_dir / "multi_document_full_extraction_summary.json", summary)
    with (output_dir / "multi_document_full_extraction.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()) if rows else ["input_dir", "output_dir", "document_id", "consolidated_candidates_count"])
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "multi_document_full_extraction.md").write_text(f"# Multi-document Full Extraction\n\n- documents_tested_count: {len(rows)}\n- consolidated_candidates_total: {summary['consolidated_candidates_total']}\n", encoding="utf-8")
    return summary

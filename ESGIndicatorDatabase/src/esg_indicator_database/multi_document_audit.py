from __future__ import annotations

from pathlib import Path
from typing import Any

from .database_builder import IndicatorDatabaseBuilder
from .io_utils import write_csv, write_json
from .loader import CRITICAL_FILES


def run_multi_document(input_root: Path, output_dir: Path, overwrite: bool = False, max_documents: int | None = None) -> dict[str, Any]:
    if output_dir.exists() and not overwrite and any(output_dir.iterdir()):
        raise FileExistsError("output-dir already exists and is not empty; use --overwrite")
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs = [p for p in sorted(input_root.rglob("*")) if p.is_dir() and all((p / name).exists() for name in CRITICAL_FILES)]
    if max_documents is not None:
        inputs = inputs[:max_documents]
    rows = []
    for idx, input_dir in enumerate(inputs, start=1):
        doc_out = output_dir / f"doc_{idx:04d}"
        result = IndicatorDatabaseBuilder(input_dir, doc_out, overwrite=True).run()
        s = result.summary
        rows.append({
            "input_dir": str(input_dir),
            "output_dir": str(doc_out),
            "accepted_candidates_count": s["accepted_candidates_loaded_count"],
            "preparation_indicators_count": s["preparation_indicators_count"],
            "empty_database_warning": s["empty_database_warning"],
            "final_indicators_count": s["final_indicators_count"],
            "score_produced_count": s["score_produced_count"],
        })
    summary = {
        "schema_version": "1.0.0",
        "documents_tested_count": len(rows),
        "accepted_candidates_total": sum(int(r["accepted_candidates_count"]) for r in rows),
        "preparation_indicators_total": sum(int(r["preparation_indicators_count"]) for r in rows),
        "empty_databases_count": sum(1 for r in rows if r["empty_database_warning"]),
        "final_indicators_total": 0,
        "scores_produced_total": 0,
        "real_world_indicator_database_pending": any(r["empty_database_warning"] for r in rows),
    }
    fields = list(rows[0].keys()) if rows else ["input_dir", "output_dir"]
    write_json(output_dir / "multi_document_indicator_database_summary.json", summary)
    write_csv(output_dir / "multi_document_indicator_database.csv", rows, fields)
    _write_md(output_dir, summary)
    return summary


def _write_md(output_dir: Path, summary: dict[str, Any]) -> None:
    lines = ["# Multi-document Indicator Database Audit", "", f"- documents tested: {summary['documents_tested_count']}", f"- preparation indicators: {summary['preparation_indicators_total']}", f"- empty databases: {summary['empty_databases_count']}", "- no final ESG indicator is produced"]
    (output_dir / "multi_document_indicator_database.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

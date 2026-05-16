from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .io_utils import read_csv, read_json, write_csv, write_json
from .validator import IndicatorValidator


def run_multi_document(input_root: Path, output_dir: Path, overwrite: bool = False, max_documents: int | None = None) -> dict[str, Any]:
    if output_dir.exists() and not overwrite and any(output_dir.iterdir()):
        raise FileExistsError("output-dir already exists and is not empty; use --overwrite")
    output_dir.mkdir(parents=True, exist_ok=True)
    input_dirs = [path for path in sorted(input_root.rglob("*")) if path.is_dir() and ((path / "consolidated_candidates.csv").exists() or (path / "consolidated_unique_candidates.csv").exists())]
    if max_documents is not None:
        input_dirs = input_dirs[:max_documents]
    rows: list[dict[str, Any]] = []
    family_counter: Counter[str] = Counter()
    priority_counter: Counter[str] = Counter()
    for idx, input_dir in enumerate(input_dirs, start=1):
        doc_out = output_dir / f"doc_{idx:04d}"
        result = IndicatorValidator(input_dir, doc_out, overwrite=True).run()
        summary = result.summary
        family_counter.update(summary.get("indicator_family_distribution", {}))
        priority_counter.update(summary.get("review_priority_distribution", {}))
        rows.append({
            "input_dir": str(input_dir),
            "output_dir": str(doc_out),
            "document_id": _document_id(doc_out),
            "input_candidates_count": summary.get("input_candidates_count", 0),
            "possible_indicators_count": summary.get("possible_indicators_count", 0),
            "needs_review_count": summary.get("needs_review_count", 0),
            "rejected_candidates_count": summary.get("rejected_candidates_count", 0),
            "unknown_family_count": summary.get("indicator_family_distribution", {}).get("unknown", 0),
            "validated_indicators_count": summary.get("validated_indicators_count", 0),
            "score_produced_count": summary.get("score_produced_count", 0),
        })
    summary = {
        "schema_version": "1.0.0",
        "documents_tested_count": len(rows),
        "input_candidates_total": sum(int(row["input_candidates_count"]) for row in rows),
        "possible_indicators_total": sum(int(row["possible_indicators_count"]) for row in rows),
        "needs_review_total": sum(int(row["needs_review_count"]) for row in rows),
        "rejected_candidates_total": sum(int(row["rejected_candidates_count"]) for row in rows),
        "indicator_family_distribution": dict(family_counter),
        "review_priority_distribution": dict(priority_counter),
        "unknown_family_total": family_counter.get("unknown", 0),
        "validated_indicators_total": sum(int(row["validated_indicators_count"]) for row in rows),
        "score_produced_total": sum(int(row["score_produced_count"]) for row in rows),
        "real_world_validation_audit_pending": len(rows) < 3,
    }
    fields = ["input_dir", "output_dir", "document_id", "input_candidates_count", "possible_indicators_count", "needs_review_count", "rejected_candidates_count", "unknown_family_count", "validated_indicators_count", "score_produced_count"]
    write_json(output_dir / "multi_document_indicator_validation_summary.json", summary)
    write_csv(output_dir / "multi_document_indicator_validation.csv", rows, fields)
    _write_md(output_dir, summary, rows)
    return summary


def _document_id(output_dir: Path) -> str:
    rows = read_csv(output_dir / "indicator_candidate_validations.csv")
    return rows[0].get("document_id", "") if rows else ""


def _write_md(output_dir: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Multi-document Indicator Validation Audit",
        "",
        f"- documents tested: {summary['documents_tested_count']}",
        f"- input candidates: {summary['input_candidates_total']}",
        f"- possible indicators: {summary['possible_indicators_total']}",
        f"- needs review: {summary['needs_review_total']}",
        f"- rejected candidates: {summary['rejected_candidates_total']}",
        f"- validated indicators: {summary['validated_indicators_total']}",
        f"- scores produced: {summary['score_produced_total']}",
        "",
        "## Documents",
    ]
    for row in rows:
        lines.append(f"- {row['document_id'] or row['input_dir']}: {row['input_candidates_count']} candidates")
    (output_dir / "multi_document_indicator_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

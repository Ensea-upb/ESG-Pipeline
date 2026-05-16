from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_csv, write_csv, write_json
from .loader import CRITICAL_FILES
from .review_workspace import ManualReviewWorkspaceBuilder


def run_multi_document(input_root: Path, output_dir: Path, overwrite: bool = False, max_documents: int | None = None) -> dict[str, Any]:
    if output_dir.exists() and not overwrite and any(output_dir.iterdir()):
        raise FileExistsError("output-dir already exists and is not empty; use --overwrite")
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = [p for p in sorted(input_root.rglob("*")) if p.is_dir() and (p / "indicator_candidate_validations.csv").exists()]
    inputs = [p for p in candidates if all((p / name).exists() for name in CRITICAL_FILES)]
    if max_documents is not None:
        inputs = inputs[:max_documents]
    rows = []
    for idx, input_dir in enumerate(inputs, start=1):
        doc_out = output_dir / f"doc_{idx:04d}"
        result = ManualReviewWorkspaceBuilder(input_dir, doc_out, overwrite=True).run()
        workspace = read_csv(doc_out / "manual_review_workspace.csv")
        rows.append({
            "input_dir": str(input_dir),
            "output_dir": str(doc_out),
            "review_items_count": result.items_count,
            "accepted_candidates_count": 0,
            "rejected_candidates_count": 0,
            "needs_more_evidence_count": 0,
            "deferred_candidates_count": 0,
            "missing_decisions_count": len(workspace),
            "validated_indicators_count": 0,
            "score_produced_count": 0,
        })
    summary = {
        "schema_version": "1.0.0",
        "documents_tested_count": len(rows),
        "review_items_total": sum(int(r["review_items_count"]) for r in rows),
        "accepted_candidates_total": 0,
        "rejected_candidates_total": 0,
        "needs_more_evidence_total": 0,
        "deferred_candidates_total": 0,
        "missing_decisions_total": sum(int(r["missing_decisions_count"]) for r in rows),
        "invalid_decisions_total": 0,
        "validated_indicators_total": 0,
        "score_produced_total": 0,
        "real_world_manual_review_pending": True,
    }
    fields = list(rows[0].keys()) if rows else ["input_dir", "output_dir", "review_items_count"]
    write_json(output_dir / "multi_document_manual_review_summary.json", summary)
    write_csv(output_dir / "multi_document_manual_review.csv", rows, fields)
    _write_md(output_dir, summary, rows)
    return summary


def _write_md(output_dir: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Multi-document Manual Review Audit",
        "",
        f"- documents tested: {summary['documents_tested_count']}",
        f"- review items total: {summary['review_items_total']}",
        f"- missing decisions total: {summary['missing_decisions_total']}",
        "- no final ESG indicator is produced",
    ]
    (output_dir / "multi_document_manual_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

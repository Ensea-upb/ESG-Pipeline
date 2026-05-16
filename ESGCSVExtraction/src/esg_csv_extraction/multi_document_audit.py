from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .extractor import ESGCSVExtractor, read_json


SUMMARY_FILE = "multi_document_candidate_audit_summary.json"
CSV_FILE = "multi_document_candidate_audit.csv"
MARKDOWN_FILE = "multi_document_candidate_audit.md"
OUTPUT_MARKER = "multimodal_evidence_index.jsonl"
CSV_FIELDS = [
    "input_dir",
    "output_dir",
    "document_id",
    "status",
    "candidates_count",
    "observed_metric_without_unit",
    "target_without_target_year",
    "visual_evidence_low_confidence",
    "confidence_above_0_6",
    "review_required_missing_or_false",
    "information_type_distribution",
]


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def find_input_dirs(input_root: Path, max_documents: int | None = None) -> list[Path]:
    candidates = [
        path for path in sorted(input_root.iterdir(), key=lambda item: item.name.lower())
        if path.is_dir() and (path / OUTPUT_MARKER).exists()
    ]
    if max_documents is not None:
        return candidates[:max_documents]
    return candidates


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def render_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Multi-document Candidate Audit",
        "",
        "## Summary",
        f"- input_root: {summary.get('input_root')}",
        f"- output_dir: {summary.get('output_dir')}",
        f"- documents_tested_count: {summary.get('documents_tested_count')}",
        f"- total_candidates_count: {summary.get('total_candidates_count')}",
        "",
        "## Distribution by Information Type",
    ]
    for key, value in sorted(dict(summary.get("information_type_distribution") or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Document Results",
    ])
    for row in rows:
        lines.append(
            f"- `{row.get('document_id')}`: {row.get('candidates_count')} candidate(s), "
            f"observed_metric_without_unit={row.get('observed_metric_without_unit')}, "
            f"target_without_target_year={row.get('target_without_target_year')}, "
            f"visual_evidence_low_confidence={row.get('visual_evidence_low_confidence')}"
        )
    lines.extend([
        "",
        "## Gate Decision",
        summary.get("gate_decision", ""),
        "",
        "## Limitations",
        "This audit is candidate-only. It does not validate ESG indicators, score companies, parse PDFs, or modify source outputs.",
        "",
    ])
    return "\n".join(lines)


def build_row(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    extraction_summary = read_json(output_dir / "extraction_summary.json")
    candidate_audit = read_json(output_dir / "candidate_audit_summary.json")
    checks = dict(candidate_audit.get("checks") or {})
    distribution = dict(extraction_summary.get("information_type_distribution") or {})
    return {
        "input_dir": str(input_dir.resolve()),
        "output_dir": str(output_dir.resolve()),
        "document_id": extraction_summary.get("document_id") or input_dir.name,
        "status": extraction_summary.get("status", "unknown"),
        "candidates_count": extraction_summary.get("candidates_count", 0),
        "observed_metric_without_unit": checks.get("observed_metric_without_unit", 0),
        "target_without_target_year": checks.get("target_without_target_year", 0),
        "visual_evidence_low_confidence": checks.get("visual_evidence_low_confidence", 0),
        "confidence_above_0_6": checks.get("confidence_above_0_6", 0),
        "review_required_missing_or_false": checks.get("review_required_missing_or_false", 0),
        "information_type_distribution": json.dumps(distribution, ensure_ascii=False, sort_keys=True),
    }


def gate_decision(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "blocked: no eligible ESGInformationExtraction outputs found."
    critical = [
        row for row in rows
        if int(row.get("confidence_above_0_6") or 0) > 0
        or int(row.get("review_required_missing_or_false") or 0) > 0
        or int(row.get("candidates_count") or 0) == 0
    ]
    if critical:
        return "blocked: at least one document has critical candidate audit issues."
    return "passed: no critical candidate audit issue detected. Continue only after human review of sample candidates."


def run_multi_document_audit(
    input_root: Path,
    output_dir: Path,
    overwrite: bool = False,
    max_documents: int | None = None,
) -> dict[str, Any]:
    input_dirs = find_input_dirs(input_root, max_documents=max_documents)
    if output_dir.exists() and any((output_dir / name).exists() for name in [SUMMARY_FILE, CSV_FILE, MARKDOWN_FILE]) and not overwrite:
        raise FileExistsError("Multi-document audit outputs already exist. Use --overwrite to replace them.")
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    distribution: Counter[str] = Counter()
    total_candidates = 0
    for input_dir in input_dirs:
        doc_output_dir = output_dir / "documents" / input_dir.name
        result = ESGCSVExtractor(input_dir=input_dir, output_dir=doc_output_dir, overwrite=overwrite).run()
        row = build_row(input_dir, doc_output_dir)
        rows.append(row)
        total_candidates += int(result.summary.get("candidates_count", 0))
        distribution.update(result.summary.get("information_type_distribution", {}))

    summary = {
        "schema_version": "0.3.0",
        "generated_at": utcnow(),
        "input_root": str(input_root.resolve()),
        "output_dir": str(output_dir.resolve()),
        "documents_tested_count": len(rows),
        "total_candidates_count": total_candidates,
        "information_type_distribution": dict(distribution),
        "observed_metric_without_unit_total": sum(int(row["observed_metric_without_unit"]) for row in rows),
        "target_without_target_year_total": sum(int(row["target_without_target_year"]) for row in rows),
        "visual_evidence_low_confidence_total": sum(int(row["visual_evidence_low_confidence"]) for row in rows),
        "confidence_above_0_6_total": sum(int(row["confidence_above_0_6"]) for row in rows),
        "review_required_missing_or_false_total": sum(int(row["review_required_missing_or_false"]) for row in rows),
        "gate_decision": gate_decision(rows),
    }
    write_json(output_dir / SUMMARY_FILE, summary)
    write_csv(output_dir / CSV_FILE, rows)
    (output_dir / MARKDOWN_FILE).write_text(render_markdown(summary, rows), encoding="utf-8")
    return summary

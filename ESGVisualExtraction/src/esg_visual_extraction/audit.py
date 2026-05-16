from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .classifier import ALLOWED_VISUAL_TYPES
from .loader import write_json, write_jsonl


AUDIT_SAMPLE_FIELDS = ["audit_check", "document_id", "figure_id", "page_number", "confidence", "raw_value", "raw_unit", "source_image_path", "caption"]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def build_visual_audit(output_dir: Path, crops: list[dict[str, Any]], ocr_rows: list[dict[str, Any]], classifications: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    checks = {
        "crops_not_created": [row for row in crops if row.get("crop_status") in {"missing_source_pdf", "failed"}],
        "crops_with_warnings": [row for row in crops if row.get("visual_warning")],
        "ocr_unavailable_or_failed": [row for row in ocr_rows if row.get("ocr_status") in {"ocr_unavailable", "ocr_failed"}],
        "candidates_without_source_image_path": [row for row in candidates if not row.get("source_image_path")],
        "candidates_without_figure_id": [row for row in candidates if not row.get("figure_id")],
        "confidence_above_0_5": [row for row in candidates if float(row.get("confidence") or 0) > 0.5],
        "review_required_missing_or_false": [row for row in candidates if row.get("review_required") is not True],
        "visual_type_unknown": [row for row in classifications if row.get("visual_type") == "unknown_visual"],
        "raw_value_without_unit": [row for row in candidates if row.get("raw_value") and not row.get("raw_unit")],
        "chart_candidate_without_ocr_text": [row for row in candidates if row.get("visual_type") == "chart" and not row.get("ocr_text")],
        "scanned_table_candidate_without_ocr_text": [row for row in candidates if row.get("visual_type") == "scanned_table" and not row.get("ocr_text")],
        "invalid_visual_type": [row for row in classifications if row.get("visual_type") not in ALLOWED_VISUAL_TYPES],
    }
    findings: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for index, (check_name, rows) in enumerate(checks.items(), start=1):
        count = len(rows)
        severity = "info" if count == 0 else "warning"
        if check_name in {"candidates_without_source_image_path", "candidates_without_figure_id", "confidence_above_0_5", "review_required_missing_or_false", "invalid_visual_type"} and count:
            severity = "error"
        findings.append({
            "schema_version": "0.6.0",
            "finding_id": f"visual_audit_{index:04d}",
            "check_name": check_name,
            "severity": severity,
            "status": "pass" if count == 0 else "needs_review",
            "count": count,
            "message": f"{check_name}: {count} item(s).",
        })
        for row in rows[:10]:
            samples.append({
                "audit_check": check_name,
                "document_id": row.get("document_id", ""),
                "figure_id": row.get("figure_id", ""),
                "page_number": row.get("page_number", ""),
                "confidence": row.get("confidence", row.get("visual_type_confidence", "")),
                "raw_value": row.get("raw_value", ""),
                "raw_unit": row.get("raw_unit", ""),
                "source_image_path": row.get("source_image_path", row.get("crop_image_path", "")),
                "caption": row.get("caption", ""),
            })
    summary = {
        "schema_version": "0.6.0",
        "checks_count": len(checks),
        "findings_count": len(findings),
        "errors_count": sum(1 for row in findings if row["severity"] == "error"),
        "warnings_count": sum(1 for row in findings if row["severity"] == "warning"),
        "checks": {name: len(rows) for name, rows in checks.items()},
    }
    write_json(output_dir / "visual_audit_summary.json", summary)
    write_jsonl(output_dir / "visual_audit_findings.jsonl", findings)
    write_csv(output_dir / "visual_audit_samples.csv", samples, AUDIT_SAMPLE_FIELDS)
    return summary


__all__ = ["build_visual_audit", "write_csv"]

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .io_utils import write_csv, write_json, write_jsonl


AUDIT_FIELDS = ["audit_check", "document_id", "table_id", "cell_id", "metric_family", "raw_value", "raw_unit", "reported_year", "confidence", "validation_notes"]


def build_table_audit(output_dir: Path, candidates: list[dict[str, Any]], fields: list[str]) -> dict[str, Any]:
    duplicate_keys = Counter((row.get("table_id"), row.get("cell_id"), row.get("metric_key")) for row in candidates)
    checks = {
        "candidates_without_unit": [row for row in candidates if not row.get("raw_unit")],
        "candidates_without_year": [row for row in candidates if not row.get("reported_year")],
        "candidates_with_inferred_year": [row for row in candidates if str(row.get("inferred_year")) in {"True", "true", "1"} or row.get("inferred_year") is True],
        "candidates_from_low_confidence_tables": [row for row in candidates if "low_confidence_table" in str(row.get("validation_notes"))],
        "duplicate_candidates": [row for row in candidates if duplicate_keys[(row.get("table_id"), row.get("cell_id"), row.get("metric_key"))] > 1],
        "raw_value_not_numeric": [row for row in candidates if not str(row.get("raw_value", "")).replace(",", "").replace(" ", "").replace(".", "").isdigit()],
        "confidence_above_0_6": [row for row in candidates if float(row.get("confidence") or 0) > 0.6],
        "review_required_missing_or_false": [row for row in candidates if row.get("review_required") is not True],
        "extraction_status_not_candidate_only": [row for row in candidates if row.get("extraction_status") != "candidate_only"],
        "score_column_detected": fields_with_token(fields, "score"),
        "validated_metric_detected": fields_with_token(fields, "validated_metric"),
    }
    findings: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for idx, (name, rows) in enumerate(checks.items(), start=1):
        count = len(rows)
        severity = "info" if count == 0 else "warning"
        if name in {"confidence_above_0_6", "review_required_missing_or_false", "extraction_status_not_candidate_only", "score_column_detected", "validated_metric_detected"} and count:
            severity = "error"
        findings.append({"schema_version": "0.6.0", "finding_id": f"table_audit_{idx:04d}", "check_name": name, "severity": severity, "status": "pass" if count == 0 else "needs_review", "count": count, "message": f"{name}: {count}"})
        for row in rows[:10] if isinstance(rows, list) else []:
            samples.append({field: row.get(field, "") for field in AUDIT_FIELDS})
            samples[-1]["audit_check"] = name
    summary = {
        "schema_version": "0.6.0", "candidates_count": len(candidates),
        "candidates_by_metric_family": dict(Counter(row.get("metric_family", "") for row in candidates)),
        "candidates_by_esg_category": dict(Counter(row.get("esg_category", "") for row in candidates)),
        "checks": {name: len(rows) for name, rows in checks.items()},
        "findings_count": len(findings),
        "errors_count": sum(1 for row in findings if row["severity"] == "error"),
        "warnings_count": sum(1 for row in findings if row["severity"] == "warning"),
    }
    write_json(output_dir / "table_audit_summary.json", summary)
    write_jsonl(output_dir / "table_audit_findings.jsonl", findings)
    write_csv(output_dir / "table_audit_samples.csv", samples, AUDIT_FIELDS)
    return summary


def fields_with_token(fields: list[str], token: str) -> list[dict[str, Any]]:
    return [{"field": field} for field in fields if token in field.lower()]

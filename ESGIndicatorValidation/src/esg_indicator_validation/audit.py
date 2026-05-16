from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from .io_utils import write_csv, write_json, write_jsonl


def build_audit(rows: list[dict[str, Any]], duplicate_groups: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    checks = {
        "input_candidates_count": rows,
        "validation_records_count": rows,
        "possible_indicators_count": [r for r in rows if r["validation_status"] == "possible_indicator"],
        "rejected_candidates_count": [r for r in rows if r["validation_status"] == "reject_candidate"],
        "needs_review_count": [r for r in rows if r["validation_status"] == "needs_review"],
        "validated_indicators_count": [r for r in rows if r.get("is_validated_indicator") != "False"],
        "score_produced_count": [r for r in rows if r.get("score_produced") != "False"],
        "records_without_quote_count": [r for r in rows if not r.get("quote")],
        "records_without_source_count": [r for r in rows if not (r.get("evidence_id") or r.get("table_id") or r.get("figure_id"))],
        "records_without_page_count": [r for r in rows if not r.get("page_number")],
        "possible_indicator_without_value_count": [r for r in rows if r["validation_status"] == "possible_indicator" and not r.get("normalized_value")],
        "possible_indicator_without_unit_count": [r for r in rows if r["validation_status"] == "possible_indicator" and not r.get("normalized_unit")],
        "possible_indicator_without_year_count": [r for r in rows if r["validation_status"] == "possible_indicator" and not r.get("normalized_year")],
        "duplicate_groups_count": duplicate_groups,
        "duplicate_candidates_count": [r for r in rows if r["duplicate_status"] == "duplicate_candidate"],
        "unknown_indicator_family": [r for r in rows if r["indicator_family"] == "unknown"],
    }
    findings = []
    samples = []
    critical = {"validated_indicators_count", "score_produced_count"}
    warning_checks = {
        "records_without_quote_count", "records_without_source_count", "records_without_page_count",
        "possible_indicator_without_value_count", "possible_indicator_without_unit_count",
        "possible_indicator_without_year_count", "duplicate_candidates_count", "unknown_indicator_family",
    }
    for idx, (name, items) in enumerate(checks.items(), start=1):
        count = len(items)
        severity = "info"
        if count and name in critical:
            severity = "error"
        elif count and name in warning_checks:
            severity = "warning"
        findings.append({
            "schema_version": "1.0.0",
            "finding_id": f"indicator_validation_finding_{idx:04d}",
            "check_name": name,
            "severity": severity,
            "status": "pass" if count == 0 and name in critical.union(warning_checks) else "needs_review",
            "count": count,
            "message": f"{name}: {count}",
        })
        for row in items[:5]:
            if isinstance(row, dict):
                sample = {"audit_check": name}
                sample.update({key: row.get(key, "") for key in ["candidate_validation_id", "document_id", "validation_status", "indicator_family", "raw_value", "raw_unit", "normalized_year", "quote"]})
                samples.append(sample)
    summary = {
        "schema_version": "1.0.0",
        "input_candidates_count": len(rows),
        "validation_records_count": len(rows),
        "validation_status_distribution": dict(Counter(r["validation_status"] for r in rows)),
        "indicator_family_distribution": dict(Counter(r["indicator_family"] for r in rows)),
        "review_priority_distribution": dict(Counter(r["review_priority"] for r in rows)),
        "checks": {name: len(items) for name, items in checks.items()},
        "findings_count": len(findings),
        "errors_count": sum(1 for f in findings if f["severity"] == "error"),
        "warnings_count": sum(1 for f in findings if f["severity"] == "warning"),
    }
    write_json(output_dir / "indicator_validation_audit_summary.json", summary)
    write_jsonl(output_dir / "indicator_validation_audit_findings.jsonl", findings)
    write_csv(output_dir / "indicator_validation_audit_samples.csv", samples, ["audit_check", "candidate_validation_id", "document_id", "validation_status", "indicator_family", "raw_value", "raw_unit", "normalized_year", "quote"])
    return summary

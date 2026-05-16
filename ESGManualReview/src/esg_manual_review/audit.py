from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import write_csv, write_json, write_jsonl


def build_decision_audit(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    checks = {
        "review_items_count": rows,
        "decisions_count": [r for r in rows if r.get("proposed_decision")],
        "accepted_candidates_count": [r for r in rows if r["review_status"] == "accepted_candidate"],
        "rejected_candidates_count": [r for r in rows if r["review_status"] == "rejected_by_reviewer"],
        "needs_more_evidence_count": [r for r in rows if r["review_status"] == "needs_more_evidence"],
        "deferred_candidates_count": [r for r in rows if r["review_status"] == "decision_deferred"],
        "missing_decision_count": [r for r in rows if r["review_status"] == "missing_decision"],
        "invalid_decision_count": [r for r in rows if r["review_status"] == "invalid_decision"],
        "accepted_without_reviewer_count": [r for r in rows if r["review_status"] == "accepted_candidate" and not r.get("reviewer")],
        "accepted_without_reason_count": [r for r in rows if r["review_status"] == "accepted_candidate" and not r.get("decision_reason")],
        "corrected_value_count": [r for r in rows if r.get("corrected_value")],
        "corrected_unit_count": [r for r in rows if r.get("corrected_unit")],
        "corrected_year_count": [r for r in rows if r.get("corrected_year")],
        "validated_indicator_detected_count": [r for r in rows if r.get("validated_indicator") != "False"],
        "score_detected_count": [r for r in rows if r.get("score_produced") != "False"],
        "missing_traceability": [r for r in rows if not (r.get("candidate_id") and r.get("document_id") and r.get("page_number") and r.get("quote"))],
        "correction_without_reason": [r for r in rows if (r.get("corrected_value") or r.get("corrected_unit") or r.get("corrected_year")) and not r.get("decision_reason")],
        "input_modified_check": [],
    }
    findings = []
    samples = []
    error_checks = {"invalid_decision_count", "validated_indicator_detected_count", "score_detected_count", "missing_traceability"}
    warning_checks = {"missing_decision_count", "accepted_without_reviewer_count", "accepted_without_reason_count", "correction_without_reason"}
    for idx, (name, items) in enumerate(checks.items(), start=1):
        severity = "info"
        if items and name in error_checks:
            severity = "error"
        elif items and name in warning_checks:
            severity = "warning"
        findings.append({
            "schema_version": "1.0.0",
            "finding_id": f"manual_review_finding_{idx:04d}",
            "check_name": name,
            "severity": severity,
            "status": "pass" if not items and name in error_checks.union(warning_checks) else "needs_review",
            "count": len(items),
            "message": f"{name}: {len(items)}",
        })
        for row in items[:5]:
            sample = {k: row.get(k, "") for k in ["review_item_id", "candidate_id", "review_status", "document_id", "page_number", "quote"]}
            sample["audit_check"] = name
            samples.append(sample)
    summary = {
        "schema_version": "1.0.0",
        "checks": {name: len(items) for name, items in checks.items()},
        "findings_count": len(findings),
        "errors_count": sum(1 for f in findings if f["severity"] == "error"),
        "warnings_count": sum(1 for f in findings if f["severity"] == "warning"),
    }
    write_json(output_dir / "manual_review_audit_summary.json", summary)
    write_jsonl(output_dir / "manual_review_audit_findings.jsonl", findings)
    write_csv(output_dir / "manual_review_audit_samples.csv", samples, ["audit_check", "review_item_id", "candidate_id", "review_status", "document_id", "page_number", "quote"])
    write_jsonl(output_dir / "review_decision_audit_findings.jsonl", findings)
    return summary

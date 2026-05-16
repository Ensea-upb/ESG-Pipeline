from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import write_csv, write_json, write_jsonl


def build_database_audit(records: list[dict[str, Any]], links: list[dict[str, Any]], lineage: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    link_ids = {link.get("preparation_indicator_id") for link in links}
    lineage_ids = {item.get("preparation_indicator_id") for item in lineage}
    checks = {
        "accepted_candidates_loaded_count": records,
        "preparation_indicators_count": records,
        "empty_database_warning": [{}] if not records else [],
        "preparation_only_count": [r for r in records if r.get("indicator_database_status") == "preparation_only"],
        "final_indicator_detected_count": [r for r in records if r.get("is_final_indicator") != "False"],
        "score_detected_count": [r for r in records if r.get("score_produced") != "False"],
        "records_without_candidate_id_count": [r for r in records if not r.get("candidate_id")],
        "records_without_document_id_count": [r for r in records if not r.get("document_id")],
        "records_without_quote_count": [r for r in records if not r.get("quote")],
        "records_without_page_count": [r for r in records if not r.get("page_number")],
        "records_without_evidence_link_count": [r for r in records if r.get("preparation_indicator_id") not in link_ids],
        "records_without_lineage_count": [r for r in records if r.get("preparation_indicator_id") not in lineage_ids],
        "records_with_corrected_values_count": [r for r in records if r.get("value_source") == "corrected_value" or r.get("unit_source") == "corrected_unit" or r.get("year_source") == "corrected_year"],
        "records_with_unknown_domain_count": [r for r in records if r.get("indicator_domain") == "unknown"],
        "records_with_unknown_topic_count": [r for r in records if r.get("indicator_topic") == "unknown"],
        "records_needing_value_review_count": [r for r in records if "needs_value_review" in r.get("preparation_quality_status", "")],
        "records_needing_unit_review_count": [r for r in records if "needs_unit_review" in r.get("preparation_quality_status", "")],
        "records_needing_year_review_count": [r for r in records if "needs_year_review" in r.get("preparation_quality_status", "")],
    }
    errors = {"final_indicator_detected_count", "score_detected_count", "records_without_candidate_id_count", "records_without_document_id_count"}
    warnings = set(checks) - errors - {"accepted_candidates_loaded_count", "preparation_indicators_count", "preparation_only_count"}
    findings = []
    samples = []
    for idx, (name, items) in enumerate(checks.items(), start=1):
        severity = "info"
        if items and name in errors:
            severity = "error"
        elif items and name in warnings:
            severity = "warning"
        findings.append({"schema_version": "1.0.0", "finding_id": f"indicator_database_finding_{idx:04d}", "check_name": name, "severity": severity, "status": "pass" if not items and name in errors.union(warnings) else "needs_review", "count": len(items), "message": f"{name}: {len(items)}"})
        for row in items[:5]:
            sample = {"audit_check": name}
            sample.update({k: row.get(k, "") for k in ["preparation_indicator_id", "candidate_id", "document_id", "indicator_database_status", "indicator_domain", "preparation_quality_status", "quote"]})
            samples.append(sample)
    summary = {"schema_version": "1.0.0", "checks": {k: len(v) for k, v in checks.items()}, "findings_count": len(findings), "errors_count": sum(1 for f in findings if f["severity"] == "error"), "warnings_count": sum(1 for f in findings if f["severity"] == "warning")}
    write_json(output_dir / "indicator_database_audit_summary.json", summary)
    write_jsonl(output_dir / "indicator_database_audit_findings.jsonl", findings)
    write_csv(output_dir / "indicator_database_audit_samples.csv", samples, ["audit_check", "preparation_indicator_id", "candidate_id", "document_id", "indicator_database_status", "indicator_domain", "preparation_quality_status", "quote"])
    return summary

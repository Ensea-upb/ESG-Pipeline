from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .candidate_consolidator import CONSOLIDATED_FIELDS
from .io_utils import read_csv, write_csv, write_json, write_jsonl


SAMPLE_FIELDS = ["audit_check", *CONSOLIDATED_FIELDS]


def build_consolidated_audit(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    duplicate_keys = Counter((row.get("document_id"), row.get("information_type"), row.get("raw_value"), row.get("page_number"), row.get("quote")) for row in rows)
    checks = {
        "review_required_missing_or_false": [row for row in rows if row.get("review_required") != "True"],
        "extraction_status_not_candidate_only": [row for row in rows if row.get("extraction_status") != "candidate_only"],
        "confidence_above_allowed_threshold": [row for row in rows if _confidence_too_high(row)],
        "score_column_detected": [{"field": f} for f in CONSOLIDATED_FIELDS if "score" in f.lower()],
        "validated_indicator_detected": [{"field": f} for f in CONSOLIDATED_FIELDS if "validated" in f.lower()],
        "probable_duplicates": [row for row in rows if duplicate_keys[(row.get("document_id"), row.get("information_type"), row.get("raw_value"), row.get("page_number"), row.get("quote"))] > 1],
        "deduplicated_duplicate_candidates": [row for row in rows if row.get("deduplication_status") == "duplicate_candidate"],
        "source_engine_information_type_mismatch": [row for row in rows if _source_engine_information_type_mismatch(row)],
        "candidates_without_source": [row for row in rows if not (row.get("evidence_id") or row.get("table_id") or row.get("figure_id"))],
        "candidates_without_quote": [row for row in rows if not row.get("quote")],
    }
    findings: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for idx, (name, items) in enumerate(checks.items(), start=1):
        count = len(items)
        severity = "info" if count == 0 else "warning"
        if name in {"review_required_missing_or_false", "extraction_status_not_candidate_only", "confidence_above_allowed_threshold", "score_column_detected", "validated_indicator_detected"} and count:
            severity = "error"
        findings.append({"schema_version": "0.4.0", "finding_id": f"consolidated_audit_{idx:04d}", "check_name": name, "severity": severity, "status": "pass" if count == 0 else "needs_review", "count": count, "message": f"{name}: {count}"})
        for row in items[:10]:
            sample = {field: row.get(field, "") for field in CONSOLIDATED_FIELDS}
            sample["audit_check"] = name
            samples.append(sample)
    summary = {
        "schema_version": "0.4.0",
        "candidates_count": len(rows),
        "unique_candidates_count": sum(1 for row in rows if row.get("deduplication_status") != "duplicate_candidate"),
        "duplicate_candidates_count": sum(1 for row in rows if row.get("deduplication_status") == "duplicate_candidate"),
        "duplicate_groups_count": len(read_csv(output_dir / "consolidated_duplicate_groups.csv")),
        "source_engine_distribution": dict(Counter(row.get("source_engine", "") for row in rows)),
        "information_type_distribution": dict(Counter(row.get("information_type", "") for row in rows)),
        "source_engine_information_type_distribution": dict(Counter(f"{row.get('source_engine', '')}:{row.get('information_type', '')}" for row in rows)),
        "deduplication_status_distribution": dict(Counter(row.get("deduplication_status", "") for row in rows)),
        "checks": {name: len(items) for name, items in checks.items()},
        "findings_count": len(findings),
        "errors_count": sum(1 for item in findings if item["severity"] == "error"),
        "warnings_count": sum(1 for item in findings if item["severity"] == "warning"),
    }
    write_json(output_dir / "consolidated_audit_summary.json", summary)
    write_jsonl(output_dir / "consolidated_audit_findings.jsonl", findings)
    write_csv(output_dir / "consolidated_audit_samples.csv", samples, SAMPLE_FIELDS)
    return summary


def _confidence_too_high(row: dict[str, Any]) -> bool:
    try:
        value = float(row.get("confidence") or 0)
    except ValueError:
        return True
    return value > {"csv": 0.6, "table": 0.6, "visual": 0.5}.get(row.get("source_engine"), 0.6)


def _source_engine_information_type_mismatch(row: dict[str, Any]) -> bool:
    engine = row.get("source_engine")
    information_type = row.get("information_type", "")
    csv_types = {
        "observed_metric", "target", "policy_or_commitment", "risk_statement",
        "boundary_context", "methodology_context", "visual_evidence",
    }
    if engine == "table":
        return information_type != "table_metric_candidate"
    if engine == "visual":
        return not information_type.startswith("visual_")
    if engine == "csv":
        return information_type not in csv_types
    return True


def render_report(output_dir: Path, collected: dict[str, Any], rows: list[dict[str, Any]], audit: dict[str, Any]) -> None:
    dist = audit.get("source_engine_distribution", {})
    lines = [
        "# Full ESG Candidate Extraction Report",
        "",
        "## Summary",
        f"- total candidates: {len(rows)}",
        f"- unique candidates: {audit.get('unique_candidates_count', 0)}",
        f"- duplicate candidates retained for audit: {audit.get('duplicate_candidates_count', 0)}",
        f"- csv candidates: {dist.get('csv', 0)}",
        f"- table candidates: {dist.get('table', 0)}",
        f"- visual candidates: {dist.get('visual', 0)}",
        "",
        "## Information Types",
    ]
    for key, value in sorted((audit.get("information_type_distribution") or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Warnings",
        f"- consolidated warnings: {audit.get('warnings_count', 0)}",
        f"- consolidated errors: {audit.get('errors_count', 0)}",
        f"- duplicate groups: {audit.get('duplicate_groups_count', 0)}",
        "",
        "## Limitations",
        "- All rows are candidate_only.",
        "- All rows require human review.",
        "- Duplicate candidates are retained in consolidated_candidates and only separated in consolidated_unique_candidates.",
        "- No ESG score or validated indicator is produced.",
    ])
    (output_dir / "full_extraction_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

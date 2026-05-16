from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io_utils import read_csv, write_json, write_jsonl
from .variable_dictionary import FINAL_VARIABLES


def build_quality_report(output_dir: Path) -> dict[str, Any]:
    long_rows = read_csv(output_dir / "esg_variables_long.csv")
    evidence_rows = read_csv(output_dir / "esg_variables_evidence.csv")
    evidence_keys = {
        (row.get("company", ""), row.get("year", ""), row.get("variable_name", ""))
        for row in evidence_rows
    }
    findings: list[dict[str, Any]] = []

    for row in long_rows:
        key = (row.get("company", ""), row.get("year", ""), row.get("variable_name", ""))
        status = row.get("status", "")
        if status == "found" and key not in evidence_keys:
            findings.append(_finding("error", "found_without_evidence", row))
        if status == "missing_from_corpus":
            findings.append(_finding("warning", "missing_variable", row))
        if status == "needs_review":
            findings.append(_finding("warning", "needs_review_variable", row))
        if status == "qualitative_only":
            findings.append(_finding("warning", "qualitative_only_variable", row))
        if status == "conflicting_values":
            findings.append(_finding("major", "conflicting_values", row))
        if status == "found" and not row.get("unit", ""):
            findings.append(_finding("warning", "unit_missing", row))
        if row.get("value", "").lower().find("score") >= 0 or row.get("variable_name", "").lower().find("score") >= 0:
            findings.append(_finding("error", "score_detected", row))
        joined = json.dumps(row, ensure_ascii=False).lower()
        if "external_source" in joined or "http://" in joined or "https://" in joined:
            findings.append(_finding("error", "external_source_detected", row))
        if "final_indicator" in joined:
            findings.append(_finding("error", "final_indicator_claim_detected", row))

    status_counts: dict[str, int] = {}
    for row in long_rows:
        status_counts[row.get("status", "")] = status_counts.get(row.get("status", ""), 0) + 1

    company_years = {(row.get("company", ""), row.get("year", "")) for row in long_rows}
    report = {
        "company_year_rows_count": len(company_years),
        "variables_count": len({row.get("variable_name", "") for row in long_rows}),
        "expected_variables_count": len(FINAL_VARIABLES),
        "found_values_count": status_counts.get("found", 0),
        "missing_values_count": status_counts.get("missing_from_corpus", 0),
        "needs_review_count": status_counts.get("needs_review", 0),
        "qualitative_only_count": status_counts.get("qualitative_only", 0),
        "conflicting_values_count": status_counts.get("conflicting_values", 0),
        "not_disclosed_count": status_counts.get("not_disclosed", 0),
        "found_without_evidence_count": sum(1 for item in findings if item["finding_type"] == "found_without_evidence"),
        "variables_with_multiple_candidates_count": _count_multiple_candidates(output_dir),
        "variables_with_unit_missing_count": sum(1 for item in findings if item["finding_type"] == "unit_missing"),
        "variables_with_year_missing_count": sum(1 for row in long_rows if not row.get("year", "")),
        "final_score_detected_count": sum(1 for item in findings if item["finding_type"] == "score_detected"),
        "external_source_detected_count": sum(1 for item in findings if item["finding_type"] == "external_source_detected"),
        "findings_count": len(findings),
        "status_counts": status_counts,
    }
    write_json(output_dir / "esg_variables_quality_report.json", report)
    write_jsonl(output_dir / "esg_variables_quality_findings.jsonl", findings)
    _write_markdown(output_dir / "esg_variables_quality_report.md", report, findings)
    return report


def _finding(severity: str, finding_type: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "severity": severity,
        "finding_type": finding_type,
        "company": row.get("company", ""),
        "year": row.get("year", ""),
        "variable_name": row.get("variable_name", ""),
        "status": row.get("status", ""),
        "message": row.get("selection_reason", "") or finding_type,
    }


def _count_multiple_candidates(output_dir: Path) -> int:
    rows = read_csv(output_dir / "selected_variable_values.csv")
    return sum(1 for row in rows if str(row.get("alternatives_count", "0")).isdigit() and int(row.get("alternatives_count", "0")) > 0)


def _write_markdown(path: Path, report: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    lines = [
        "# ESG Variables Quality Report",
        "",
        f"- company_year_rows_count: {report['company_year_rows_count']}",
        f"- variables_count: {report['variables_count']}",
        f"- found_values_count: {report['found_values_count']}",
        f"- missing_values_count: {report['missing_values_count']}",
        f"- needs_review_count: {report['needs_review_count']}",
        f"- qualitative_only_count: {report['qualitative_only_count']}",
        f"- conflicting_values_count: {report['conflicting_values_count']}",
        f"- found_without_evidence_count: {report['found_without_evidence_count']}",
        f"- final_score_detected_count: {report['final_score_detected_count']}",
        f"- external_source_detected_count: {report['external_source_detected_count']}",
        "",
        "## Findings",
    ]
    if not findings:
        lines.append("- none")
    for item in findings[:200]:
        lines.append(f"- {item['severity']} {item['finding_type']}: {item['company']} {item['year']} {item['variable_name']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

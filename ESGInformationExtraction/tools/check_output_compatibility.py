#!/usr/bin/env python
"""Check compatibility of an existing output directory with contract v1.0.

This tool does not parse PDFs and does not regenerate documentary outputs. By
default it only prints a JSON diagnostic. With --write-report it writes the
three compatibility report files. With --annotate-summary it updates only
extraction_summary.json with compatibility metadata.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ESGInformationExtraction.tools.validate_output_contract import validate_contract


REPORT_FILES = (
    "compatibility_report.json",
    "compatibility_findings.jsonl",
    "compatibility_report.md",
)
CORE_DOCUMENTARY_FILES = (
    "page_index.jsonl",
    "text_blocks.jsonl",
    "evidence_store.jsonl",
)
AUDIT_FILES = (
    "consistency_report.json",
    "audit_findings.jsonl",
    "document_audit_report.md",
)


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def finding(
    document_id: str,
    severity: str,
    status: str,
    category: str,
    message: str,
    recommendation: str,
    related_file: str = "",
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "document_id": document_id,
        "severity": severity,
        "status": status,
        "category": category,
        "message": message,
        "related_file": related_file,
        "recommendation": recommendation,
    }


def classify_errors(errors: list[str], output_dir: Path) -> tuple[str, list[dict[str, Any]]]:
    summary_path = output_dir / "extraction_summary.json"
    document_id = output_dir.name
    if summary_path.exists():
        try:
            document_id = str(read_json(summary_path).get("document_id") or document_id)
        except Exception:
            pass

    findings: list[dict[str, Any]] = []
    missing_core = [name for name in CORE_DOCUMENTARY_FILES if not (output_dir / name).exists()]
    missing_audit = [name for name in AUDIT_FILES if not (output_dir / name).exists()]
    only_contract_version_missing = bool(errors) and all(
        "extraction_summary.json[0] missing required field: engine_contract_version" == error
        for error in errors
    )

    if missing_core:
        for name in missing_core:
            findings.append(finding(
                document_id,
                "critical",
                "fail",
                "core_files",
                f"Core documentary file is missing: {name}.",
                "Regenerate the output with the current PDF engine.",
                name,
            ))
        return "incompatible", findings

    if not errors:
        findings.append(finding(
            document_id,
            "info",
            "pass",
            "contract",
            "Output validates against contract v1.0.",
            "No migration required.",
        ))
        return "compatible", findings

    if only_contract_version_missing:
        findings.append(finding(
            document_id,
            "minor",
            "warning",
            "contract_metadata",
            "Only engine_contract_version is missing from extraction_summary.json.",
            "Output is compatible with warnings; annotate summary or regenerate with v1.0 if strict validation is required.",
            "extraction_summary.json",
        ))
        return "compatible_with_warnings", findings

    if missing_audit:
        for name in missing_audit:
            findings.append(finding(
                document_id,
                "major",
                "warning",
                "audit_outputs",
                f"Audit output is missing: {name}.",
                "Run run_document_audit.py or regenerate with the current engine.",
                name,
            ))
        return "migration_required", findings

    for error in errors:
        findings.append(finding(
            document_id,
            "major",
            "fail",
            "contract",
            error,
            "Inspect the mismatch. Regenerate with v1.0 if the discrepancy is real.",
        ))
    return "incompatible", findings


def build_report(output_dir: Path, contract_path: Path) -> tuple[int, dict[str, Any], list[dict[str, Any]]]:
    validation_code, validation_payload = validate_contract(output_dir, contract_path)
    errors = list(validation_payload.get("errors") or [])
    compatibility_status, findings = classify_errors(errors, output_dir)
    report = {
        "schema_version": "1.0.0",
        "generated_at": utcnow(),
        "output_dir": str(output_dir.resolve()),
        "contract_path": str(contract_path.resolve()),
        "contract_version": validation_payload.get("contract_version"),
        "compatibility_status": compatibility_status,
        "validation_status": validation_payload.get("status"),
        "validation_errors_count": validation_payload.get("errors_count", 0),
        "validation_warnings_count": validation_payload.get("warnings_count", 0),
        "missing_core_files": [name for name in CORE_DOCUMENTARY_FILES if not (output_dir / name).exists()],
        "missing_audit_files": [name for name in AUDIT_FILES if not (output_dir / name).exists()],
        "findings_count": len(findings),
        "findings": findings,
        "recommendation": recommendation_for_status(compatibility_status),
    }
    return_code = 0 if compatibility_status in {"compatible", "compatible_with_warnings", "migration_required"} else 1
    return return_code, report, findings


def recommendation_for_status(status: str) -> str:
    return {
        "compatible": "Output can be validated directly against contract v1.0.",
        "compatible_with_warnings": "Output is usable, but contract metadata should be annotated or regenerated.",
        "migration_required": "Regenerate audit outputs or run the standalone audit CLI before strict contract validation.",
        "incompatible": "Regenerate the output with the current PDF engine.",
    }.get(status, "Inspect compatibility findings.")


def render_markdown(report: dict[str, Any], findings: list[dict[str, Any]]) -> str:
    lines = [
        "# Output Compatibility Report",
        "",
        f"- output_dir: {report.get('output_dir')}",
        f"- contract_version: {report.get('contract_version')}",
        f"- compatibility_status: {report.get('compatibility_status')}",
        f"- validation_status: {report.get('validation_status')}",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Findings",
    ]
    for item in findings:
        lines.append(
            f"- [{item.get('severity')}] {item.get('category')}: {item.get('message')} "
            f"Recommendation: {item.get('recommendation')}"
        )
    return "\n".join(lines) + "\n"


def write_reports(output_dir: Path, report: dict[str, Any], findings: list[dict[str, Any]], overwrite: bool) -> None:
    existing = [name for name in REPORT_FILES if (output_dir / name).exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Compatibility reports already exist. Use --overwrite to replace: "
            + ", ".join(existing)
        )
    write_json(output_dir / "compatibility_report.json", report)
    write_jsonl(output_dir / "compatibility_findings.jsonl", findings)
    (output_dir / "compatibility_report.md").write_text(render_markdown(report, findings), encoding="utf-8")


def annotate_summary(output_dir: Path, report: dict[str, Any]) -> None:
    summary_path = output_dir / "extraction_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError("Cannot annotate missing extraction_summary.json")
    summary = read_json(summary_path)
    summary["compatibility_check_status"] = report.get("compatibility_status")
    summary["compatibility_contract_version"] = report.get("contract_version")
    summary["compatibility_checked_at"] = report.get("generated_at")
    if report.get("compatibility_status") == "compatible_with_warnings" and "engine_contract_version" not in summary:
        summary["engine_contract_version"] = report.get("contract_version")
    write_json(summary_path, summary)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check output compatibility with contract v1.0.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--contract-path", required=True)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--annotate-summary", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir)
    contract_path = Path(args.contract_path)
    try:
        return_code, report, findings = build_report(output_dir, contract_path)
        files_written: list[str] = []
        if args.write_report:
            write_reports(output_dir, report, findings, overwrite=args.overwrite)
            files_written.extend(REPORT_FILES)
        if args.annotate_summary:
            annotate_summary(output_dir, report)
            files_written.append("extraction_summary.json")
        payload = {
            "status": "success" if return_code == 0 else "failed",
            "output_dir": str(output_dir.resolve()),
            "compatibility_status": report.get("compatibility_status"),
            "contract_version": report.get("contract_version"),
            "findings_count": len(findings),
            "files_written": files_written,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return return_code
    except Exception as exc:
        print(json.dumps({
            "status": "failed",
            "output_dir": str(output_dir.resolve()),
            "errors": [str(exc)],
        }, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

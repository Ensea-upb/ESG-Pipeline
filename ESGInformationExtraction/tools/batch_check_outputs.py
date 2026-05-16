#!/usr/bin/env python
"""Batch compatibility scanner for ESGInformationExtraction output folders.

The scanner is non-destructive: it never edits scanned output directories. When
--write-report is used, it writes only batch reports under
<outputs-root>/batch_compatibility_report/.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ESGInformationExtraction.tools.check_output_compatibility import build_report


BATCH_REPORT_DIRNAME = "batch_compatibility_report"
BATCH_FILES = (
    "batch_compatibility_summary.json",
    "batch_compatibility_table.csv",
    "batch_compatibility_report.md",
)
REMEDIATION_FILES = (
    "batch_remediation_plan.json",
    "batch_remediation_plan.csv",
    "batch_remediation_plan.md",
)
CHECKLIST_FILES = (
    "batch_execution_checklist.json",
    "batch_execution_checklist.csv",
    "batch_execution_checklist.md",
)
OUTPUT_MARKERS = {
    "extraction_summary.json",
    "document_record.json",
    "evidence_store.jsonl",
    "document_inventory.json",
}
IGNORED_DIRS = {"__pycache__", ".pytest_tmp", BATCH_REPORT_DIRNAME}
CSV_COLUMNS = [
    "output_dir",
    "document_id",
    "compatibility_status",
    "engine_contract_version",
    "extraction_readiness_status",
    "findings_count",
    "critical_findings_count",
    "major_findings_count",
    "warnings_count",
]
REMEDIATION_CSV_COLUMNS = [
    "output_dir",
    "document_id",
    "compatibility_status",
    "recommended_action",
    "action_priority",
    "risk_level",
    "action_reason",
    "minimal_command",
]
CHECKLIST_CSV_COLUMNS = [
    "execution_order",
    "output_dir",
    "document_id",
    "compatibility_status",
    "recommended_action",
    "action_priority",
    "risk_level",
    "command_to_run",
    "verification_command",
    "completion_criteria",
]
CORE_DOCUMENTARY_FILES = ("page_index.jsonl", "text_blocks.jsonl", "evidence_store.jsonl")
AUDIT_FILES = ("consistency_report.json", "audit_findings.jsonl", "document_audit_report.md")
MULTIMODAL_FILES = ("document_inventory.json", "multimodal_evidence_index.jsonl", "multimodal_statistics.json")
ACTION_PRIORITY_ORDER = {
    "no_action_needed": 0,
    "annotate_summary_only": 1,
    "rerun_audit_standalone": 2,
    "rerun_contract_validation": 3,
    "regenerate_with_current_engine": 4,
    "manual_review_required": 5,
}


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def is_output_like(path: Path) -> bool:
    if not path.is_dir() or path.name in IGNORED_DIRS:
        return False
    return any((path / marker).exists() for marker in OUTPUT_MARKERS)


def iter_candidate_dirs(root: Path, max_depth: int) -> list[Path]:
    root = root.resolve()
    candidates: list[Path] = []
    if is_output_like(root):
        candidates.append(root)
    for path in root.rglob("*"):
        if not path.is_dir() or path.name in IGNORED_DIRS:
            continue
        try:
            rel_depth = len(path.relative_to(root).parts)
        except ValueError:
            continue
        if rel_depth > max_depth:
            continue
        if is_output_like(path):
            candidates.append(path)
    return sorted(set(candidates), key=lambda item: str(item).lower())


def output_row(output_dir: Path, report: dict[str, Any]) -> dict[str, Any]:
    summary = read_json(output_dir / "extraction_summary.json")
    inventory = read_json(output_dir / "document_inventory.json")
    findings = list(report.get("findings") or [])
    return {
        "output_dir": str(output_dir.resolve()),
        "document_id": summary.get("document_id") or inventory.get("document_id") or output_dir.name,
        "compatibility_status": report.get("compatibility_status"),
        "engine_contract_version": summary.get("engine_contract_version"),
        "extraction_readiness_status": (
            summary.get("extraction_readiness_status")
            or inventory.get("extraction_readiness_status")
        ),
        "findings_count": len(findings),
        "critical_findings_count": sum(1 for finding in findings if finding.get("severity") == "critical"),
        "major_findings_count": sum(1 for finding in findings if finding.get("severity") == "major"),
        "warnings_count": sum(1 for finding in findings if finding.get("status") == "warning"),
    }


def build_batch_summary(outputs_root: Path, contract_path: Path, max_depth: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for output_dir in iter_candidate_dirs(outputs_root, max_depth=max_depth):
        _return_code, report, _findings = build_report(output_dir, contract_path)
        rows.append(output_row(output_dir, report))

    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("compatibility_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "schema_version": "1.0.0",
        "contract_version": read_json(contract_path).get("engine_contract_version"),
        "outputs_root": str(outputs_root.resolve()),
        "generated_at": utcnow(),
        "outputs_scanned_count": len(rows),
        "compatible_count": status_counts.get("compatible", 0),
        "compatible_with_warnings_count": status_counts.get("compatible_with_warnings", 0),
        "migration_required_count": status_counts.get("migration_required", 0),
        "incompatible_count": status_counts.get("incompatible", 0),
        "failed_checks_count": sum(int(row.get("critical_findings_count") or 0) for row in rows),
        "status_distribution": status_counts,
        "outputs": rows,
    }


def write_batch_reports(report_dir: Path, summary: dict[str, Any], overwrite: bool) -> list[str]:
    existing = [name for name in BATCH_FILES if (report_dir / name).exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Batch compatibility reports already exist. Use --overwrite to replace: "
            + ", ".join(existing)
        )
    report_dir.mkdir(parents=True, exist_ok=True)

    summary_path = report_dir / "batch_compatibility_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    table_path = report_dir / "batch_compatibility_table.csv"
    with table_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in summary.get("outputs", []):
            writer.writerow({column: row.get(column, "") for column in CSV_COLUMNS})

    markdown_path = report_dir / "batch_compatibility_report.md"
    markdown_path.write_text(render_markdown(summary), encoding="utf-8")
    return [str(report_dir / name) for name in BATCH_FILES]


def path_exists(output_dir: Path, name: str) -> bool:
    return (output_dir / name).exists()


def minimal_command_for_action(
    action: str,
    output_dir: Path,
    contract_path: Path,
    document_id: str,
) -> str:
    output_arg = str(output_dir)
    contract_arg = str(contract_path)
    if action == "annotate_summary_only":
        return (
            f'python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "{output_arg}" '
            f'--contract-path "{contract_arg}" --annotate-summary'
        )
    if action == "rerun_audit_standalone":
        return (
            f'python ESGInformationExtraction/tools/run_document_audit.py --output-dir "{output_arg}" '
            f'--contract-path "{contract_arg}" --overwrite'
        )
    if action == "rerun_contract_validation":
        return (
            f'python ESGInformationExtraction/tools/validate_output_contract.py --output-dir "{output_arg}" '
            f'--contract-path "{contract_arg}"'
        )
    if action == "regenerate_with_current_engine":
        summary = read_json(output_dir / "extraction_summary.json")
        document = read_json(output_dir / "document_record.json")
        pdf_path = document.get("document_path") or summary.get("pdf_path")
        if pdf_path:
            return (
                f'python ESGInformationExtraction/run_pdf_extraction.py --pdf-path "{pdf_path}" '
                f'--document-id "{document_id}" --output-dir "{output_arg}" --overwrite'
            )
        return "Regenerate this output with run_pdf_extraction.py using the original PDF path."
    if action == "manual_review_required":
        return "Inspect compatibility_report.json and output files manually before taking action."
    return "No command required."


def remediation_for_output(row: dict[str, Any], contract_path: Path) -> dict[str, Any]:
    output_dir = Path(str(row.get("output_dir") or ""))
    status = str(row.get("compatibility_status") or "unknown")
    document_id = str(row.get("document_id") or output_dir.name)
    summary = read_json(output_dir / "extraction_summary.json")

    missing_core = [name for name in CORE_DOCUMENTARY_FILES if not path_exists(output_dir, name)]
    missing_audit = [name for name in AUDIT_FILES if not path_exists(output_dir, name)]
    missing_multimodal = [name for name in MULTIMODAL_FILES if not path_exists(output_dir, name)]
    blockers: list[str] = []

    if status == "compatible":
        action = "no_action_needed"
        priority = "none"
        risk = "low"
        reason = "Output is compatible with contract v1.0."
        expected = "No remediation required."
    elif status == "compatible_with_warnings":
        only_contract_version_missing = not summary.get("engine_contract_version")
        if only_contract_version_missing:
            action = "annotate_summary_only"
            priority = "low"
            risk = "low"
            reason = "Only engine_contract_version appears to be missing from extraction_summary.json."
            expected = "Summary receives compatibility metadata and can be validated more strictly."
        else:
            action = "manual_review_required"
            priority = "medium"
            risk = "medium"
            reason = "Compatibility warnings are not limited to missing engine_contract_version."
            expected = "A human determines whether annotation or regeneration is appropriate."
    elif status == "migration_required":
        if missing_audit and not missing_core:
            action = "rerun_audit_standalone"
            priority = "medium"
            risk = "low"
            reason = "Core documentary files exist, but audit outputs are missing."
            expected = "Standalone audit regenerates missing audit files without PDF extraction."
        elif missing_multimodal and path_exists(output_dir, "evidence_store.jsonl"):
            action = "regenerate_with_current_engine"
            priority = "high"
            risk = "medium"
            reason = "Evidence exists, but multimodal v1 outputs are missing."
            expected = "Current engine regenerates full v1-compatible output from the original PDF."
        else:
            action = "manual_review_required"
            priority = "medium"
            risk = "medium"
            reason = "Migration cause is ambiguous."
            expected = "A human reviews files and selects the safest remediation."
    elif status == "incompatible":
        if missing_core:
            action = "regenerate_with_current_engine"
            priority = "high"
            risk = "high"
            reason = "One or more core documentary files are missing: " + ", ".join(missing_core) + "."
            expected = "Output is regenerated from the original PDF with the current engine."
            blockers.extend(missing_core)
        else:
            action = "manual_review_required"
            priority = "high"
            risk = "high"
            reason = "Output is incompatible for reasons requiring inspection."
            expected = "A human reviews the incompatibility before regeneration or migration."
    else:
        action = "manual_review_required"
        priority = "medium"
        risk = "medium"
        reason = f"Unknown compatibility status: {status}."
        expected = "A human reviews the output before any remediation."

    return {
        "output_dir": str(output_dir),
        "document_id": document_id,
        "compatibility_status": status,
        "recommended_action": action,
        "action_priority": priority,
        "action_reason": reason,
        "minimal_command": minimal_command_for_action(action, output_dir, contract_path, document_id),
        "expected_result": expected,
        "risk_level": risk,
        "blockers": blockers,
    }


def build_remediation_plan(summary: dict[str, Any], contract_path: Path) -> dict[str, Any]:
    outputs = [
        remediation_for_output(row, contract_path)
        for row in list(summary.get("outputs") or [])
    ]
    action_counts: dict[str, int] = {}
    for row in outputs:
        action = str(row.get("recommended_action") or "manual_review_required")
        action_counts[action] = action_counts.get(action, 0) + 1
    return {
        "schema_version": "1.0.0",
        "contract_version": summary.get("contract_version"),
        "outputs_root": summary.get("outputs_root"),
        "generated_at": utcnow(),
        "outputs_scanned_count": len(outputs),
        "remediation_summary": {
            "no_action_needed_count": action_counts.get("no_action_needed", 0),
            "annotate_summary_only_count": action_counts.get("annotate_summary_only", 0),
            "rerun_audit_standalone_count": action_counts.get("rerun_audit_standalone", 0),
            "rerun_contract_validation_count": action_counts.get("rerun_contract_validation", 0),
            "regenerate_with_current_engine_count": action_counts.get("regenerate_with_current_engine", 0),
            "manual_review_required_count": action_counts.get("manual_review_required", 0),
        },
        "actions_distribution": action_counts,
        "outputs": outputs,
    }


def render_remediation_markdown(plan: dict[str, Any]) -> str:
    outputs = list(plan.get("outputs") or [])

    def section_for(action: str, title: str) -> list[str]:
        selected = [row for row in outputs if row.get("recommended_action") == action]
        lines = [f"## {title}"]
        if not selected:
            lines.append("None.")
        for row in selected:
            lines.append(f"- `{row.get('output_dir')}`: {row.get('action_reason')}")
            command = row.get("minimal_command")
            if command and command != "No command required.":
                lines.append(f"  - command: `{command}`")
        lines.append("")
        return lines

    lines = [
        "# Batch Remediation Plan",
        "",
        "Ce plan ne modifie aucun output. Il recommande uniquement les actions minimales a effectuer.",
        "",
        "## Summary",
        f"- outputs_root: {plan.get('outputs_root')}",
        f"- contract_version: {plan.get('contract_version')}",
        f"- outputs_scanned_count: {plan.get('outputs_scanned_count')}",
        "",
        "## Actions Distribution",
    ]
    for action, count in sorted(dict(plan.get("actions_distribution") or {}).items()):
        lines.append(f"- {action}: {count}")
    lines.append("")
    lines.extend(section_for("no_action_needed", "No Action Needed"))
    lines.extend(section_for("annotate_summary_only", "Annotate Summary Only"))
    lines.extend(section_for("rerun_audit_standalone", "Rerun Audit Standalone"))
    lines.extend(section_for("regenerate_with_current_engine", "Regenerate With Current Engine"))
    lines.extend(section_for("manual_review_required", "Manual Review Required"))
    lines.extend([
        "## Recommended Execution Order",
        "1. Run no automatic command for `no_action_needed` outputs.",
        "2. Annotate summaries for low-risk compatibility warnings if desired.",
        "3. Regenerate standalone audits for `migration_required` outputs with intact core files.",
        "4. Regenerate incompatible outputs only after confirming the original PDF path.",
        "5. Review ambiguous outputs manually before any destructive or expensive operation.",
        "",
        "## Limitations",
        "The remediation plan is advisory. It does not execute commands, repair outputs, parse PDFs, or perform ESG extraction.",
        "",
    ])
    return "\n".join(lines)


def write_remediation_plan(report_dir: Path, plan: dict[str, Any], overwrite: bool) -> list[str]:
    existing = [name for name in REMEDIATION_FILES if (report_dir / name).exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Batch remediation plan already exists. Use --overwrite to replace: "
            + ", ".join(existing)
        )
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = report_dir / "batch_remediation_plan.json"
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_path = report_dir / "batch_remediation_plan.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REMEDIATION_CSV_COLUMNS)
        writer.writeheader()
        for row in plan.get("outputs", []):
            writer.writerow({column: row.get(column, "") for column in REMEDIATION_CSV_COLUMNS})

    markdown_path = report_dir / "batch_remediation_plan.md"
    markdown_path.write_text(render_remediation_markdown(plan), encoding="utf-8")
    return [str(report_dir / name) for name in REMEDIATION_FILES]


def verification_command_for_item(output_dir: str, contract_path: Path) -> str:
    return (
        f'python ESGInformationExtraction/tools/check_output_compatibility.py --output-dir "{output_dir}" '
        f'--contract-path "{contract_path}"'
    )


def completion_criteria_for_action(action: str) -> str:
    return {
        "no_action_needed": "Output remains compatible; no remediation command is required.",
        "annotate_summary_only": "Compatibility check reports compatible or compatible_with_warnings with only metadata warnings.",
        "rerun_audit_standalone": "Audit files exist and compatibility status is no longer migration_required for missing audit files.",
        "rerun_contract_validation": "Contract validator completes with zero errors.",
        "regenerate_with_current_engine": "A fresh output validates against contract v1.0 or has only documented warnings.",
        "manual_review_required": "A human has inspected the blockers and selected a safe next action.",
    }.get(action, "A human has verified the output state.")


def manual_instruction_for_action(action: str) -> str:
    return {
        "no_action_needed": "No manual remediation is needed.",
        "annotate_summary_only": "Run the proposed annotation command manually if you want strict contract metadata.",
        "rerun_audit_standalone": "Run the standalone audit command manually to regenerate audit files only.",
        "rerun_contract_validation": "Run contract validation manually and inspect any reported errors.",
        "regenerate_with_current_engine": "Locate the original PDF and run the current PDF engine manually.",
        "manual_review_required": "Inspect the output folder and compatibility findings before choosing a command.",
    }.get(action, "Inspect this item manually.")


def build_execution_checklist(remediation_plan: dict[str, Any], contract_path: Path) -> dict[str, Any]:
    sorted_outputs = sorted(
        list(remediation_plan.get("outputs") or []),
        key=lambda row: (
            ACTION_PRIORITY_ORDER.get(str(row.get("recommended_action")), 99),
            str(row.get("output_dir") or "").lower(),
        ),
    )
    items: list[dict[str, Any]] = []
    action_counts: dict[str, int] = {}
    for index, row in enumerate(sorted_outputs, start=1):
        action = str(row.get("recommended_action") or "manual_review_required")
        action_counts[action] = action_counts.get(action, 0) + 1
        output_dir = str(row.get("output_dir") or "")
        items.append({
            "checklist_item_id": f"checklist_item_{index:04d}",
            "execution_order": index,
            "output_dir": output_dir,
            "document_id": row.get("document_id"),
            "compatibility_status": row.get("compatibility_status"),
            "recommended_action": action,
            "action_priority": row.get("action_priority"),
            "risk_level": row.get("risk_level"),
            "is_automatic_execution_allowed": False,
            "command_to_run": row.get("minimal_command"),
            "manual_instruction": manual_instruction_for_action(action),
            "expected_result": row.get("expected_result"),
            "verification_command": verification_command_for_item(output_dir, contract_path),
            "completion_criteria": completion_criteria_for_action(action),
            "warnings": [
                "This checklist never executes commands automatically.",
                "Review paths and risks before running any command manually.",
            ],
        })

    return {
        "schema_version": "1.0.0",
        "contract_version": remediation_plan.get("contract_version"),
        "outputs_root": remediation_plan.get("outputs_root"),
        "generated_at": utcnow(),
        "checklist_items_count": len(items),
        "checklist_summary": {
            "automatic_execution_allowed": False,
            "actions_distribution": action_counts,
        },
        "items": items,
    }


def render_execution_checklist_markdown(checklist: dict[str, Any]) -> str:
    items = list(checklist.get("items") or [])

    def section_for(priority: int, action: str, title: str) -> list[str]:
        selected = [row for row in items if row.get("recommended_action") == action]
        lines = [f"## Priority {priority} - {title}"]
        if not selected:
            lines.append("None.")
        for row in selected:
            lines.append(f"- [{row.get('execution_order')}] `{row.get('output_dir')}`")
            lines.append(f"  - instruction: {row.get('manual_instruction')}")
            lines.append(f"  - command: `{row.get('command_to_run')}`")
            lines.append(f"  - verification: `{row.get('verification_command')}`")
        lines.append("")
        return lines

    lines = [
        "# Batch Execution Checklist",
        "",
        "## Summary",
        f"- outputs_root: {checklist.get('outputs_root')}",
        f"- contract_version: {checklist.get('contract_version')}",
        f"- checklist_items_count: {checklist.get('checklist_items_count')}",
        "",
        "## Important Safety Note",
        "- Cette checklist n'execute aucune commande.",
        "- Les commandes proposees doivent etre lancees manuellement.",
        "- Aucune extraction ESG n'est realisee.",
        "- Les outputs sources ne sont pas modifies par la generation de cette checklist.",
        "",
        "## Execution Order",
        "Follow the priority sections from 0 to 5. Within each section, follow `execution_order`.",
        "",
    ]
    lines.extend(section_for(0, "no_action_needed", "No Action Needed"))
    lines.extend(section_for(1, "annotate_summary_only", "Annotate Summary Only"))
    lines.extend(section_for(2, "rerun_audit_standalone", "Rerun Audit Standalone"))
    lines.extend(section_for(3, "rerun_contract_validation", "Rerun Contract Validation"))
    lines.extend(section_for(4, "regenerate_with_current_engine", "Regenerate With Current Engine"))
    lines.extend(section_for(5, "manual_review_required", "Manual Review Required"))
    lines.extend([
        "## Final Verification",
        "Run the compatibility scanner again after manual remediation and confirm that no fragile output is marked as ready without review.",
        "",
    ])
    return "\n".join(lines)


def write_execution_checklist(report_dir: Path, checklist: dict[str, Any], overwrite: bool) -> list[str]:
    existing = [name for name in CHECKLIST_FILES if (report_dir / name).exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Batch execution checklist already exists. Use --overwrite to replace: "
            + ", ".join(existing)
        )
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = report_dir / "batch_execution_checklist.json"
    json_path.write_text(json.dumps(checklist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_path = report_dir / "batch_execution_checklist.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CHECKLIST_CSV_COLUMNS)
        writer.writeheader()
        for row in checklist.get("items", []):
            writer.writerow({column: row.get(column, "") for column in CHECKLIST_CSV_COLUMNS})

    markdown_path = report_dir / "batch_execution_checklist.md"
    markdown_path.write_text(render_execution_checklist_markdown(checklist), encoding="utf-8")
    return [str(report_dir / name) for name in CHECKLIST_FILES]


def render_markdown(summary: dict[str, Any]) -> str:
    outputs = list(summary.get("outputs") or [])

    def section_for(status: str) -> list[str]:
        lines = [f"## {status.replace('_', ' ').title()}"]
        selected = [row for row in outputs if row.get("compatibility_status") == status]
        if not selected:
            lines.append("None.")
        for row in selected:
            lines.append(f"- `{row.get('output_dir')}` ({row.get('document_id')})")
        lines.append("")
        return lines

    lines = [
        "# Batch Compatibility Report",
        "",
        "## Summary",
        f"- outputs_root: {summary.get('outputs_root')}",
        f"- contract_version: {summary.get('contract_version')}",
        f"- outputs_scanned_count: {summary.get('outputs_scanned_count')}",
        "",
        "## Status Distribution",
        f"- compatible: {summary.get('compatible_count')}",
        f"- compatible_with_warnings: {summary.get('compatible_with_warnings_count')}",
        f"- migration_required: {summary.get('migration_required_count')}",
        f"- incompatible: {summary.get('incompatible_count')}",
        "",
    ]
    lines.extend(section_for("compatible"))
    lines.extend(section_for("compatible_with_warnings"))
    lines.extend(section_for("migration_required"))
    lines.extend(section_for("incompatible"))
    lines.extend([
        "## Recommended Actions",
        "- compatible: can be validated directly against contract v1.0.",
        "- compatible_with_warnings: usable with attention; consider annotation or regeneration.",
        "- migration_required: regenerate audits or annotate compatibility metadata.",
        "- incompatible: regenerate outputs with the current engine.",
        "",
        "## Limitations",
        "This batch scanner is non-destructive and performs no ESG extraction, scoring, OCR, RAG, vector indexing, or PDF parsing.",
        "",
    ])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch check ESGInformationExtraction outputs.")
    parser.add_argument("--outputs-root", required=True)
    parser.add_argument("--contract-path", required=True)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--write-remediation-plan", action="store_true")
    parser.add_argument("--write-execution-checklist", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    outputs_root = Path(args.outputs_root)
    contract_path = Path(args.contract_path)
    try:
        if not outputs_root.exists() or not outputs_root.is_dir():
            raise FileNotFoundError(f"outputs-root does not exist: {outputs_root}")
        summary = build_batch_summary(outputs_root, contract_path, max_depth=args.max_depth)
        files_written: list[str] = []
        if args.write_report:
            files_written = write_batch_reports(
                outputs_root / BATCH_REPORT_DIRNAME,
                summary,
                overwrite=args.overwrite,
            )
        actions_distribution: dict[str, int] = {}
        remediation_plan: dict[str, Any] | None = None
        if args.write_remediation_plan or args.write_execution_checklist:
            remediation_plan = build_remediation_plan(summary, contract_path)
            actions_distribution = dict(remediation_plan.get("actions_distribution") or {})
        if args.write_remediation_plan and remediation_plan is not None:
            files_written.extend(write_remediation_plan(
                outputs_root / BATCH_REPORT_DIRNAME,
                remediation_plan,
                overwrite=args.overwrite,
            ))
        if args.write_execution_checklist and remediation_plan is not None:
            checklist = build_execution_checklist(remediation_plan, contract_path)
            files_written.extend(write_execution_checklist(
                outputs_root / BATCH_REPORT_DIRNAME,
                checklist,
                overwrite=args.overwrite,
            ))
        payload = {
            "status": "success",
            "outputs_scanned_count": summary["outputs_scanned_count"],
            "compatible_count": summary["compatible_count"],
            "compatible_with_warnings_count": summary["compatible_with_warnings_count"],
            "migration_required_count": summary["migration_required_count"],
            "incompatible_count": summary["incompatible_count"],
            "actions_distribution": actions_distribution,
            "files_written": files_written,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=None if args.quiet else 2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

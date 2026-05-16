#!/usr/bin/env python
from __future__ import annotations

import argparse
import ast
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODULE_CANDIDATES = ["parsing", "section_detection", "extraction", "evidence", "quality_control", "document_base"]
SCHEMA_FILES = [
    "schemas/document_record.py", "schemas/page_record.py", "schemas/section_record.py",
    "schemas/evidence_record.py", "schemas/metric_record.py", "schemas/quality_check_record.py",
]
CONFIG_FILES = ["config/extraction_config.yaml", "config/metric_catalog_v0.yaml", "config/section_taxonomy_v0.yaml"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    project = root / "ESGInformationExtraction"
    out = Path(args.output_dir)
    if out.exists() and any(out.iterdir()) and not args.overwrite:
        print(json.dumps({"status": "failed", "errors": ["output-dir already exists; use --overwrite"]}, indent=2))
        return 1
    out.mkdir(parents=True, exist_ok=True)
    report = build_report(project)
    findings = build_findings(report)
    write_json(out / "architecture_hygiene_report.json", report)
    write_jsonl(out / "architecture_hygiene_findings.jsonl", findings)
    write_markdown(out / "architecture_hygiene_report.md", report, findings)
    print(json.dumps({"status": "success", "output_dir": str(out), "findings_count": len(findings)}, indent=2))
    return 0


def build_report(project: Path) -> dict[str, Any]:
    engine = project / "run_pdf_extraction.py"
    source = engine.read_text(encoding="utf-8") if engine.exists() else ""
    functions = []
    if source:
        tree = ast.parse(source)
        functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    written_files = sorted(set(_extract_written_files(source)))
    modules = []
    for name in MODULE_CANDIDATES:
        path = project / name
        modules.append({
            "path": name + "/",
            "exists": path.exists(),
            "python_files_count": len(list(path.rglob("*.py"))) if path.exists() else 0,
            "used_by_run_pdf_extraction": name in source,
            "status": "legacy_or_experimental" if path.exists() and name not in source else "active_or_referenced",
        })
    schemas = [{"path": rel, "exists": (project / rel).exists()} for rel in SCHEMA_FILES]
    configs = [{"path": rel, "exists": (project / rel).exists(), "used_by_run_pdf_extraction": Path(rel).name in source} for rel in CONFIG_FILES]
    return {
        "schema_version": "1.5.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "active_engine": {
            "path": "run_pdf_extraction.py",
            "exists": engine.exists(),
            "line_count": len(source.splitlines()),
            "top_level_functions": functions,
            "written_files_detected": written_files,
        },
        "schemas": schemas,
        "module_candidates": modules,
        "configs": configs,
        "architecture_summary": "run_pdf_extraction.py is the active production engine; several package directories are visible but not the production source of truth.",
    }


def _extract_written_files(source: str) -> list[str]:
    names = []
    for marker in ['output_dir / "', "output_dir / '"]:
        start = 0
        while True:
            idx = source.find(marker, start)
            if idx == -1:
                break
            quote = marker[-1]
            value_start = idx + len(marker)
            value_end = source.find(quote, value_start)
            if value_end != -1:
                names.append(source[value_start:value_end])
            start = value_start
    return [name for name in names if "." in name]


def build_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    findings = [{
        "schema_version": "1.5.0",
        "finding_id": "architecture_hygiene_0001",
        "severity": "info",
        "category": "active_engine",
        "check_name": "active_engine_identified",
        "status": "pass",
        "message": "run_pdf_extraction.py identified as active production engine.",
        "recommendation": "Treat run_pdf_extraction.py as source of truth until a documented refactor occurs.",
    }]
    idx = 2
    for module in report["module_candidates"]:
        if module["exists"] and not module["used_by_run_pdf_extraction"]:
            findings.append({
                "schema_version": "1.5.0",
                "finding_id": f"architecture_hygiene_{idx:04d}",
                "severity": "minor",
                "category": "module_usage",
                "check_name": "module_not_referenced_by_active_engine",
                "status": "warning",
                "message": f"{module['path']} exists but is not referenced by run_pdf_extraction.py.",
                "recommendation": "Document as legacy_or_experimental unless integrated by a future refactor.",
            })
            idx += 1
    return findings


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    lines = [
        "# Architecture Hygiene Report",
        "",
        "## Active Engine",
        "- run_pdf_extraction.py is the active production engine.",
        f"- line_count: {report['active_engine']['line_count']}",
        "",
        "## Potentially Orphan Modules",
    ]
    for module in report["module_candidates"]:
        lines.append(f"- {module['path']} — exists={module['exists']} used_by_run_pdf_extraction={module['used_by_run_pdf_extraction']} status={module['status']}")
    lines.extend(["", "## Findings"])
    for finding in findings:
        lines.append(f"- {finding['severity']} | {finding['check_name']} | {finding['message']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

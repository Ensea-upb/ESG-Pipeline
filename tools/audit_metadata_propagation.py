#!/usr/bin/env python
"""Audit metadata propagation across an ESG pipeline E2E run output root.

Produces:
  - metadata_propagation_report.json
  - metadata_propagation_findings.jsonl
  - metadata_propagation_report.md
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


METADATA_FIELDS = ["company", "fiscal_year", "official_doc_type", "final_path", "document_id"]

LAYER_FILES = {
    "ESGInformationExtraction_document_record": "document_record.json",
    "ESGInformationExtraction_document_inventory": "document_inventory.json",
    "ESGInformationExtraction_evidence_store": "evidence_store.jsonl",
    "ESGInformationExtraction_multimodal_evidence_index": "multimodal_evidence_index.jsonl",
    "ESGExtractionOrchestrator_consolidated_candidates": "consolidated_candidates.csv",
    "ESGIndicatorValidation_indicator_candidate_validations": "indicator_candidate_validations.csv",
    "ESGManualReview_manual_review_workspace": "manual_review_workspace.csv",
    "ESGManualReview_accepted_candidate_inputs": "accepted_candidate_inputs.csv",
    "ESGIndicatorDatabase_indicator_preparation_database": "indicator_preparation_database.csv",
    "ESGVariableDatasetBuilder_esg_variables_long": "esg_variables_long.csv",
    "ESGVariableDatasetBuilder_esg_variables_dataset": "esg_variables_dataset.csv",
}

SAMPLE_LIMIT = 5


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_jsonl_sample(path: Path, n: int = SAMPLE_LIMIT) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
                if len(rows) >= n:
                    break
    except Exception:
        pass
    return rows


def read_csv_sample(path: Path, n: int = SAMPLE_LIMIT) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append(dict(row))
                if len(rows) >= n:
                    break
    except Exception:
        pass
    return rows


def check_fields(rows: list[dict[str, Any]], source: str) -> dict[str, Any]:
    """For a list of sample rows, check presence/absence/empty of METADATA_FIELDS."""
    if not rows:
        return {
            "source": source,
            "rows_sampled": 0,
            "fields": {},
            "findings": [{"severity": "warning", "message": f"No rows found in {source}"}],
        }

    field_status: dict[str, dict[str, int]] = {}
    for field in METADATA_FIELDS:
        field_status[field] = {"present": 0, "empty": 0, "absent": 0}

    for row in rows:
        for field in METADATA_FIELDS:
            if field not in row:
                field_status[field]["absent"] += 1
            elif not str(row[field]).strip():
                field_status[field]["empty"] += 1
            else:
                field_status[field]["present"] += 1

    findings = []
    for field, counts in field_status.items():
        if counts["absent"] > 0:
            findings.append({
                "severity": "error",
                "field": field,
                "message": f"Field '{field}' absent in {counts['absent']}/{len(rows)} rows of {source}",
            })
        elif counts["empty"] > 0:
            findings.append({
                "severity": "warning",
                "field": field,
                "message": f"Field '{field}' empty in {counts['empty']}/{len(rows)} rows of {source}",
            })

    return {
        "source": source,
        "rows_sampled": len(rows),
        "fields": field_status,
        "findings": findings,
    }


def check_json_record(record: dict[str, Any], source: str) -> dict[str, Any]:
    """Check a single JSON record (not a list) for metadata fields."""
    findings = []
    field_status: dict[str, str] = {}
    for field in METADATA_FIELDS:
        if field not in record:
            field_status[field] = "absent"
            findings.append({
                "severity": "info",
                "field": field,
                "message": f"Field '{field}' absent in {source}",
            })
        elif not str(record[field]).strip():
            field_status[field] = "empty"
            findings.append({
                "severity": "warning",
                "field": field,
                "message": f"Field '{field}' empty in {source}",
            })
        else:
            field_status[field] = "present"
    return {
        "source": source,
        "rows_sampled": 1,
        "fields": field_status,
        "findings": findings,
    }


def find_files_in_root(input_root: Path) -> dict[str, Path]:
    """Walk input_root recursively and match known layer files."""
    found: dict[str, Path] = {}
    for path in input_root.rglob("*"):
        if not path.is_file():
            continue
        for layer_name, filename in LAYER_FILES.items():
            if path.name == filename and layer_name not in found:
                found[layer_name] = path
    return found


def audit_path(layer_name: str, path: Path) -> dict[str, Any]:
    """Dispatch to appropriate reader and check depending on file type."""
    if path.suffix == ".json":
        record = read_json(path)
        return check_json_record(record, layer_name)
    elif path.suffix == ".jsonl":
        rows = read_jsonl_sample(path)
        return check_fields(rows, layer_name)
    elif path.suffix == ".csv":
        rows = read_csv_sample(path)
        return check_fields(rows, layer_name)
    else:
        return {"source": layer_name, "rows_sampled": 0, "fields": {}, "findings": [{"severity": "warning", "message": f"Unknown file type for {path}"}]}


def run_audit(input_root: Path, output_dir: Path) -> dict[str, Any]:
    found_files = find_files_in_root(input_root)
    layers_checked: list[dict[str, Any]] = []
    all_findings: list[dict[str, Any]] = []

    for layer_name, filename in LAYER_FILES.items():
        if layer_name in found_files:
            path = found_files[layer_name]
            result = audit_path(layer_name, path)
            result["file_path"] = str(path)
            result["file_found"] = True
        else:
            result = {
                "source": layer_name,
                "file_found": False,
                "file_path": None,
                "rows_sampled": 0,
                "fields": {},
                "findings": [{"severity": "info", "message": f"File '{filename}' not found under {input_root}"}],
            }
        layers_checked.append(result)
        for finding in result.get("findings", []):
            all_findings.append({**finding, "layer": layer_name, "file_path": result.get("file_path")})

    errors = sum(1 for f in all_findings if f.get("severity") == "error")
    warnings = sum(1 for f in all_findings if f.get("severity") == "warning")

    report = {
        "schema_version": "1.0.0",
        "generated_at": utcnow(),
        "input_root": str(input_root),
        "output_dir": str(output_dir),
        "layers_checked": len(layers_checked),
        "files_found": sum(1 for layer in layers_checked if layer.get("file_found")),
        "files_missing": sum(1 for layer in layers_checked if not layer.get("file_found")),
        "total_findings": len(all_findings),
        "errors": errors,
        "warnings": warnings,
        "layers": layers_checked,
    }
    return report, all_findings


def write_markdown(report: dict[str, Any], output_path: Path) -> None:
    lines = [
        "# Metadata Propagation Audit Report",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Input root: `{report['input_root']}`",
        f"- Layers checked: `{report['layers_checked']}`",
        f"- Files found: `{report['files_found']}`",
        f"- Files missing: `{report['files_missing']}`",
        f"- Errors: `{report['errors']}`",
        f"- Warnings: `{report['warnings']}`",
        "",
        "## Layer Results",
        "",
    ]
    for layer in report.get("layers", []):
        status = "FOUND" if layer.get("file_found") else "MISSING"
        lines.append(f"### {layer['source']} ({status})")
        if layer.get("file_path"):
            lines.append(f"- File: `{layer['file_path']}`")
        lines.append(f"- Rows sampled: `{layer.get('rows_sampled', 0)}`")
        findings = layer.get("findings", [])
        if findings:
            lines.append("- Findings:")
            for finding in findings:
                sev = finding.get("severity", "info").upper()
                lines.append(f"  - [{sev}] {finding.get('message', '')}")
        else:
            lines.append("- No findings.")
        lines.append("")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit metadata propagation across an ESG pipeline E2E run.")
    parser.add_argument("--input-root", required=True, help="Root directory containing all module outputs.")
    parser.add_argument("--output-dir", required=True, help="Directory to write audit reports.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_root = Path(args.input_root)
    output_dir = Path(args.output_dir)

    if not input_root.exists():
        print(f"ERROR: input-root does not exist: {input_root}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)

    json_report_path = output_dir / "metadata_propagation_report.json"
    findings_path = output_dir / "metadata_propagation_findings.jsonl"
    markdown_path = output_dir / "metadata_propagation_report.md"

    for path in [json_report_path, findings_path, markdown_path]:
        if path.exists() and not args.overwrite:
            print(f"ERROR: Output file already exists (use --overwrite): {path}", file=sys.stderr)
            return 2

    report, all_findings = run_audit(input_root, output_dir)

    json_report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with findings_path.open("w", encoding="utf-8", newline="\n") as fh:
        for finding in all_findings:
            fh.write(json.dumps(finding, ensure_ascii=False, separators=(",", ":")) + "\n")

    write_markdown(report, markdown_path)

    print(json.dumps({
        "status": "success",
        "layers_checked": report["layers_checked"],
        "files_found": report["files_found"],
        "errors": report["errors"],
        "warnings": report["warnings"],
        "output_dir": str(output_dir),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

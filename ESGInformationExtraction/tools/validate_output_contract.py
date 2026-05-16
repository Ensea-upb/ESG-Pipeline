#!/usr/bin/env python
"""Validate an ESGInformationExtraction output directory against output_contract_v1.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_records(output_dir: Path, filename: str) -> list[dict[str, Any]]:
    path = output_dir / filename
    if filename.endswith(".jsonl"):
        return read_jsonl(path)
    if filename.endswith(".json"):
        return [read_json(path)]
    return []


def validate_required_fields(
    output_dir: Path,
    contract: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> dict[str, list[dict[str, Any]]]:
    loaded: dict[str, list[dict[str, Any]]] = {}
    required_by_file = contract.get("required_fields_by_file", {}) or {}
    for filename in contract.get("required_output_files", []) or []:
        path = output_dir / filename
        if not path.exists():
            errors.append(f"Missing required output file: {filename}")
            loaded[filename] = []
            continue
        if filename.endswith(".md"):
            loaded[filename] = []
            continue
        try:
            records = load_records(output_dir, filename)
        except Exception as exc:
            errors.append(f"Could not read {filename}: {exc}")
            loaded[filename] = []
            continue
        loaded[filename] = records
        required_fields = required_by_file.get(filename, [])
        for idx, record in enumerate(records):
            for field in required_fields:
                if field not in record:
                    errors.append(f"{filename}[{idx}] missing required field: {field}")
    for filename in contract.get("optional_output_files", []) or []:
        if not (output_dir / filename).exists():
            warnings.append(f"Optional file missing: {filename}")
    return loaded


def validate_allowed_values(
    contract: dict[str, Any],
    loaded: dict[str, list[dict[str, Any]]],
    errors: list[str],
) -> None:
    allowed = contract.get("allowed_values_by_field", {}) or {}

    def check(filename: str, field: str, allowed_key: str | None = None) -> None:
        values = set(allowed.get(allowed_key or field, []))
        if not values:
            return
        for idx, record in enumerate(loaded.get(filename, [])):
            value = record.get(field)
            if value is not None and value not in values:
                errors.append(f"{filename}[{idx}] invalid {field}: {value!r}")

    for filename in ["evidence_store.jsonl", "section_index.jsonl", "multimodal_evidence_index.jsonl"]:
        check(filename, "evidence_policy")
    check("multimodal_evidence_index.jsonl", "downstream_use_policy")
    check("multimodal_evidence_index.jsonl", "source_modality")
    for filename in ["evidence_store.jsonl", "multimodal_evidence_index.jsonl"]:
        check(filename, "evidence_type")
    check("table_index.jsonl", "extraction_status", "table_extraction_status")
    check("figure_index.jsonl", "extraction_status", "figure_extraction_status")
    check("consistency_report.json", "overall_status")
    check("document_inventory.json", "extraction_readiness_status")
    check("quality_report.jsonl", "status", "quality_status")
    check("audit_findings.jsonl", "status", "finding_status")
    check("audit_findings.jsonl", "severity", "finding_severity")


def validate_invariants(loaded: dict[str, list[dict[str, Any]]], errors: list[str]) -> None:
    evidence = loaded.get("evidence_store.jsonl", [])
    multimodal = loaded.get("multimodal_evidence_index.jsonl", [])
    tables = loaded.get("table_index.jsonl", [])
    figures = loaded.get("figure_index.jsonl", [])
    sections = loaded.get("section_index.jsonl", [])

    evidence_ids = [str(record.get("evidence_id") or "") for record in evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        errors.append("Invariant failed: evidence_id values are not unique.")

    evidence_id_set = set(evidence_ids)
    multimodal_ids = {str(record.get("evidence_id") or "") for record in multimodal}
    if evidence_id_set != multimodal_ids:
        errors.append("Invariant failed: evidence_store evidence IDs do not match multimodal_evidence_index.")

    for idx, record in enumerate(multimodal):
        downstream = record.get("downstream_use_policy")
        if record.get("is_quarantined_evidence") and downstream == "eligible_for_future_extraction":
            errors.append(f"Invariant failed: quarantined multimodal evidence is eligible at row {idx}.")
        if record.get("review_required") and downstream == "eligible_for_future_extraction":
            errors.append(f"Invariant failed: review_required multimodal evidence is eligible at row {idx}.")

    table_ids = {str(record.get("table_id") or "") for record in tables}
    figure_ids = {str(record.get("figure_id") or "") for record in figures}
    section_ids = {str(record.get("section_id") or "") for record in sections}
    for idx, record in enumerate(evidence):
        if record.get("evidence_type") == "table":
            table_id = str(record.get("table_id") or record.get("source_element_id") or "")
            if table_id and table_id not in table_ids:
                errors.append(f"Invariant failed: table evidence row {idx} references missing table_id {table_id}.")
        if record.get("evidence_type") == "figure":
            figure_id = str(record.get("figure_id") or record.get("source_element_id") or "")
            if figure_id and figure_id not in figure_ids:
                errors.append(f"Invariant failed: figure evidence row {idx} references missing figure_id {figure_id}.")
        section_id = str(record.get("section_id") or "")
        if section_id and section_id not in section_ids:
            errors.append(f"Invariant failed: evidence row {idx} references missing section_id {section_id}.")


def validate_contract(output_dir: Path, contract_path: Path) -> tuple[int, dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        contract = read_json(contract_path)
    except Exception as exc:
        return 1, {
            "status": "failed",
            "contract_version": None,
            "output_dir": str(output_dir),
            "errors_count": 1,
            "errors": [f"Could not read contract: {exc}"],
        }

    loaded = validate_required_fields(output_dir, contract, errors, warnings)
    validate_allowed_values(contract, loaded, errors)
    validate_invariants(loaded, errors)
    checks_count = (
        len(contract.get("required_output_files", []) or [])
        + sum(len(v) for v in (contract.get("required_fields_by_file", {}) or {}).values())
        + len(contract.get("cross_file_invariants", []) or [])
    )
    status = "failed" if errors else "success"
    payload = {
        "status": status,
        "contract_version": contract.get("engine_contract_version"),
        "output_dir": str(output_dir.resolve()),
        "checks_count": checks_count,
        "errors_count": len(errors),
        "warnings_count": len(warnings),
    }
    if errors:
        payload["errors"] = errors
    if warnings:
        payload["warnings"] = warnings
    return (1 if errors else 0), payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ESGInformationExtraction output contract.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--contract-path", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return_code, payload = validate_contract(Path(args.output_dir), Path(args.contract_path))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())

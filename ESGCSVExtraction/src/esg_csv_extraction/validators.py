from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .contract import load_contract


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def validate_csv_outputs(output_dir: Path, contract_path: Path) -> dict[str, Any]:
    contract = load_contract(contract_path)
    version = str(contract.get("contract_version", "unknown"))
    errors: list[str] = []
    warnings: list[str] = []
    checks_count = 0

    required_files = list(contract.get("required_files") or [])
    required_columns = list(contract.get("required_columns") or [])
    typed_files = dict(contract.get("typed_csv_files") or {})
    candidate_csv_files = set(contract.get("candidate_csv_files") or [*typed_files.values(), "esg_information_candidates.csv"])
    allowed_information_types = set(contract.get("allowed_values", {}).get("information_type", []))

    file_rows: dict[str, list[dict[str, str]]] = {}
    file_headers: dict[str, list[str]] = {}

    for file_name in required_files:
        path = output_dir / file_name
        checks_count += 1
        if not path.exists():
            errors.append(f"required file missing: {file_name}")
            continue
        if file_name.endswith(".csv"):
            headers, rows = read_csv_rows(path)
            file_headers[file_name] = headers
            file_rows[file_name] = rows
            forbidden = [column for column in headers if "score" in column.lower() or column == "validated_metric"]
            if forbidden:
                errors.append(f"{file_name}: forbidden column(s): {', '.join(forbidden)}")
            if file_name in candidate_csv_files:
                missing = [column for column in required_columns if column not in headers]
                if missing:
                    errors.append(f"{file_name}: missing required column(s): {', '.join(missing)}")

    for file_name, rows in file_rows.items():
        if file_name not in candidate_csv_files:
            continue
        for index, row in enumerate(rows, start=2):
            prefix = f"{file_name}:{index}"
            checks_count += 1
            information_type = row.get("information_type", "")
            if information_type and information_type not in allowed_information_types:
                errors.append(f"{prefix}: invalid information_type={information_type}")
            if row.get("review_required") != "True":
                errors.append(f"{prefix}: review_required must be true")
            if row.get("extraction_status") != "candidate_only":
                errors.append(f"{prefix}: extraction_status must be candidate_only")
            confidence = row.get("confidence", "")
            try:
                if float(confidence) > 0.6:
                    errors.append(f"{prefix}: confidence above 0.6")
            except ValueError:
                errors.append(f"{prefix}: confidence is not numeric")

    global_rows = file_rows.get("esg_information_candidates.csv", [])
    global_count = len(global_rows)
    typed_total = sum(len(file_rows.get(file_name, [])) for file_name in typed_files.values())
    checks_count += 1
    if global_count != typed_total:
        errors.append(f"typed CSV row total {typed_total} does not match global CSV row count {global_count}")

    global_distribution = Counter(row.get("information_type", "") for row in global_rows)
    for information_type, file_name in typed_files.items():
        checks_count += 1
        typed_rows = file_rows.get(file_name, [])
        wrong = [row for row in typed_rows if row.get("information_type") != information_type]
        if wrong:
            errors.append(f"{file_name}: contains rows outside {information_type}")
        if len(typed_rows) != global_distribution.get(information_type, 0):
            errors.append(
                f"{file_name}: count {len(typed_rows)} does not match global {information_type} count "
                f"{global_distribution.get(information_type, 0)}"
            )

    status = "success" if not errors else "failed"
    return {
        "status": status,
        "contract_version": version,
        "output_dir": str(output_dir),
        "checks_count": checks_count,
        "errors_count": len(errors),
        "warnings_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


__all__ = ["validate_csv_outputs", "print_json"]

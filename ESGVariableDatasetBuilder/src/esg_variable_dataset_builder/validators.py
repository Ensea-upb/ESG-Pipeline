from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_csv, read_json
from .variable_dictionary import ALLOWED_STATUSES, FINAL_VARIABLES, load_variable_dictionary


def validate_dataset(output_dir: Path, contract_path: Path, dictionary_path: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    required_files = [
        "esg_variables_dataset.csv",
        "esg_variables_dataset_enriched.csv",
        "esg_variables_long.csv",
        "esg_variables_evidence.csv",
        "esg_variables_quality_report.json",
    ]
    for file_name in required_files:
        if not (output_dir / file_name).exists():
            errors.append(f"missing_file:{file_name}")

    contract = read_json(contract_path)
    expected_variables = contract.get("variables", FINAL_VARIABLES)
    dataset_rows = read_csv(output_dir / "esg_variables_dataset.csv")
    long_rows = read_csv(output_dir / "esg_variables_long.csv")
    evidence_rows = read_csv(output_dir / "esg_variables_evidence.csv")

    if dataset_rows:
        columns = set(dataset_rows[0].keys())
        for column in ["company", "year", *expected_variables]:
            if column not in columns:
                errors.append(f"missing_column:{column}")
        for column in columns:
            if "score" in column.lower():
                errors.append(f"score_column_detected:{column}")

    seen: set[tuple[str, str]] = set()
    for row in dataset_rows:
        key = (row.get("company", ""), row.get("year", ""))
        if key in seen:
            errors.append(f"duplicate_company_year:{key[0]}:{key[1]}")
        seen.add(key)

    evidence_keys = {
        (row.get("company", ""), row.get("year", ""), row.get("variable_name", ""))
        for row in evidence_rows
    }
    for row in long_rows:
        status = row.get("status", "")
        if status not in ALLOWED_STATUSES:
            errors.append(f"invalid_status:{row.get('variable_name', '')}:{status}")
        key = (row.get("company", ""), row.get("year", ""), row.get("variable_name", ""))
        if status == "found" and key not in evidence_keys:
            errors.append(f"found_without_evidence:{key[0]}:{key[1]}:{key[2]}")
        if "http://" in str(row).lower() or "https://" in str(row).lower() or "external_source" in str(row).lower():
            errors.append(f"external_source_detected:{key[2]}")

    if dictionary_path:
        dictionary_variables = {item["variable_name"] for item in load_variable_dictionary(dictionary_path)}
        for variable in expected_variables:
            if variable not in dictionary_variables:
                errors.append(f"variable_missing_from_dictionary:{variable}")

    return {
        "status": "passed" if not errors else "failed",
        "errors_count": len(errors),
        "errors": errors,
    }

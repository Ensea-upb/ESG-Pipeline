from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def validate_outputs(output_dir: Path, contract_path: Path) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    checks = 0
    for name in contract.get("required_files", []):
        checks += 1
        if not (output_dir / name).exists():
            errors.append(f"required file missing: {name}")
    rows = _read_csv(output_dir / "indicator_candidate_validations.csv")
    headers = list(rows[0].keys()) if rows else _headers(output_dir / "indicator_candidate_validations.csv")
    missing = [field for field in contract.get("required_columns", []) if field not in headers]
    if missing:
        errors.append(f"missing columns: {missing}")
    forbidden = [field for field in headers if "score" in field.lower() and field != "score_produced"]
    if forbidden:
        errors.append(f"forbidden score columns: {forbidden}")
    for line_no, row in enumerate(rows, start=2):
        checks += 1
        if row.get("review_required") != "True":
            errors.append(f"{line_no}: review_required must be True")
        if row.get("extraction_status") != "candidate_only":
            errors.append(f"{line_no}: extraction_status must be candidate_only")
        if row.get("validation_status") not in contract.get("allowed_validation_status", []):
            errors.append(f"{line_no}: invalid validation_status")
        if row.get("review_priority") not in contract.get("allowed_review_priority", []):
            errors.append(f"{line_no}: invalid review_priority")
        if row.get("is_validated_indicator") != "False":
            errors.append(f"{line_no}: is_validated_indicator must be False")
        if row.get("score_produced") != "False":
            errors.append(f"{line_no}: score_produced must be False")
        if row.get("validation_status") == "validated":
            errors.append(f"{line_no}: validation_status=validated is forbidden")
        try:
            confidence = float(row.get("confidence") or 0)
        except ValueError:
            errors.append(f"{line_no}: confidence must be numeric")
            confidence = 0
        if confidence > contract.get("max_confidence", 0.5):
            errors.append(f"{line_no}: confidence above allowed maximum")
    _validate_typed_file(output_dir / "possible_indicators.csv", "possible_indicator", errors)
    _validate_typed_file(output_dir / "rejected_candidates.csv", "reject_candidate", errors)
    return {
        "status": "success" if not errors else "failed",
        "contract_version": contract.get("contract_version", "unknown"),
        "output_dir": str(output_dir),
        "checks_count": checks,
        "errors_count": len(errors),
        "warnings_count": 0,
        "errors": errors,
        "warnings": [],
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _headers(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file).fieldnames or [])


def _validate_typed_file(path: Path, expected_status: str, errors: list[str]) -> None:
    for line_no, row in enumerate(_read_csv(path), start=2):
        if row.get("validation_status") != expected_status:
            errors.append(f"{path.name}:{line_no}: expected {expected_status}")

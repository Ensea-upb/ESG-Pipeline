from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def validate_manual_review_outputs(output_dir: Path, contract_path: Path) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    checks = 0
    for name in contract.get("required_files", []):
        checks += 1
        if not (output_dir / name).exists():
            errors.append(f"required file missing: {name}")
    rows = _read_csv(output_dir / "reviewed_candidates.csv")
    headers = list(rows[0].keys()) if rows else _headers(output_dir / "reviewed_candidates.csv")
    missing = [field for field in contract.get("required_columns", []) if field not in headers]
    if missing:
        errors.append(f"missing columns: {missing}")
    forbidden = [field for field in headers if "score" in field.lower() and field != "score_produced"]
    if forbidden:
        errors.append(f"forbidden score columns: {forbidden}")
    for line_no, row in enumerate(rows, start=2):
        checks += 1
        if row.get("review_status") not in contract.get("allowed_review_status", []):
            errors.append(f"{line_no}: invalid review_status")
        if row.get("proposed_decision") not in contract.get("allowed_proposed_decision", []):
            errors.append(f"{line_no}: invalid proposed_decision")
        if row.get("validated_indicator") != "False":
            errors.append(f"{line_no}: validated_indicator must be False")
        if row.get("score_produced") != "False":
            errors.append(f"{line_no}: score_produced must be False")
        if row.get("review_status") == "accepted_candidate" and row.get("indicator_key_candidate", "").startswith("final_indicator"):
            errors.append(f"{line_no}: accepted candidate cannot be presented as final_indicator")
        for field in ["candidate_id", "document_id", "page_number", "quote"]:
            if not row.get(field):
                errors.append(f"{line_no}: missing traceability field {field}")
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

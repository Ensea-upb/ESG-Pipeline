from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def validate_table_outputs(output_dir: Path, contract_path: Path) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    checks = 0
    for file_name in contract.get("required_files", []):
        checks += 1
        if not (output_dir / file_name).exists():
            errors.append(f"required file missing: {file_name}")
    candidate_files = contract.get("candidate_csv_files", [])
    required = contract.get("required_candidate_columns", [])
    allowed_families = set(contract.get("allowed_values", {}).get("metric_family", []))
    total_typed = 0
    global_count = 0
    for file_name in candidate_files:
        path = output_dir / file_name
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            headers = list(reader.fieldnames or [])
            forbidden = [h for h in headers if "score" in h.lower() or h == "validated_metric"]
            if forbidden:
                errors.append(f"{file_name}: forbidden columns {forbidden}")
            missing = [h for h in required if h not in headers]
            if missing:
                errors.append(f"{file_name}: missing columns {missing}")
            rows = list(reader)
            if file_name == "table_metric_candidates.csv":
                global_count = len(rows)
            else:
                total_typed += len(rows)
            for line_no, row in enumerate(rows, start=2):
                checks += 1
                if row.get("review_required") != "True":
                    errors.append(f"{file_name}:{line_no}: review_required must be true")
                if row.get("extraction_status") != "candidate_only":
                    errors.append(f"{file_name}:{line_no}: extraction_status must be candidate_only")
                if row.get("metric_family") not in allowed_families:
                    errors.append(f"{file_name}:{line_no}: invalid metric_family={row.get('metric_family')}")
                try:
                    if float(row.get("confidence") or 0) > 0.6:
                        errors.append(f"{file_name}:{line_no}: confidence above 0.6")
                except ValueError:
                    errors.append(f"{file_name}:{line_no}: confidence not numeric")
    checks += 1
    if global_count != total_typed:
        errors.append(f"typed csv rows {total_typed} do not match global candidates {global_count}")
    return {"status": "success" if not errors else "failed", "contract_version": contract.get("contract_version", "unknown"), "output_dir": str(output_dir), "checks_count": checks, "errors_count": len(errors), "warnings_count": 0, "errors": errors, "warnings": []}

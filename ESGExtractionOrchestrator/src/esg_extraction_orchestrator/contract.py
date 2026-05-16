from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def validate_full_outputs(output_dir: Path, contract_path: Path) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    checks = 0
    for name in contract.get("required_files", []):
        checks += 1
        if not (output_dir / name).exists():
            errors.append(f"required file missing: {name}")
    path = output_dir / "consolidated_candidates.csv"
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            headers = list(reader.fieldnames or [])
            forbidden = [h for h in headers if "score" in h.lower() or "validated" in h.lower()]
            if forbidden:
                errors.append(f"forbidden columns: {forbidden}")
            missing = [h for h in contract.get("required_columns", []) if h not in headers]
            if missing:
                errors.append(f"missing columns: {missing}")
            for line_no, row in enumerate(reader, start=2):
                checks += 1
                if row.get("review_required") != "True":
                    errors.append(f"{line_no}: review_required must be true")
                if row.get("extraction_status") != "candidate_only":
                    errors.append(f"{line_no}: extraction_status must be candidate_only")
                if row.get("source_engine") not in contract.get("allowed_source_engines", []):
                    errors.append(f"{line_no}: invalid source_engine")
    return {"status": "success" if not errors else "failed", "contract_version": contract.get("contract_version", "unknown"), "output_dir": str(output_dir), "checks_count": checks, "errors_count": len(errors), "warnings_count": 0, "errors": errors, "warnings": []}

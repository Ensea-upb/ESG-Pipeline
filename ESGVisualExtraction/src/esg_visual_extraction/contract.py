from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def load_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_visual_outputs(output_dir: Path, contract_path: Path) -> dict[str, Any]:
    contract = load_contract(contract_path)
    errors: list[str] = []
    checks_count = 0
    for file_name in contract.get("required_files", []):
        checks_count += 1
        if not (output_dir / file_name).exists():
            errors.append(f"required file missing: {file_name}")
    candidate_path = output_dir / "visual_candidates.csv"
    required_columns = list(contract.get("required_candidate_columns") or [])
    allowed_visual_types = set(contract.get("allowed_values", {}).get("visual_type", []))
    allowed_information_types = set(contract.get("allowed_values", {}).get("information_type", []))
    if candidate_path.exists():
        with candidate_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            headers = list(reader.fieldnames or [])
            forbidden = [column for column in headers if "score" in column.lower() or column == "validated_metric"]
            if forbidden:
                errors.append(f"forbidden column(s): {', '.join(forbidden)}")
            missing = [column for column in required_columns if column not in headers]
            if missing:
                errors.append(f"visual_candidates.csv missing column(s): {', '.join(missing)}")
            for line_no, row in enumerate(reader, start=2):
                checks_count += 1
                if row.get("review_required") != "True":
                    errors.append(f"visual_candidates.csv:{line_no}: review_required must be true")
                if row.get("extraction_status") != "candidate_only":
                    errors.append(f"visual_candidates.csv:{line_no}: extraction_status must be candidate_only")
                if row.get("visual_type") not in allowed_visual_types:
                    errors.append(f"visual_candidates.csv:{line_no}: invalid visual_type={row.get('visual_type')}")
                if row.get("information_type") not in allowed_information_types:
                    errors.append(f"visual_candidates.csv:{line_no}: invalid information_type={row.get('information_type')}")
                try:
                    if float(row.get("confidence") or 0) > 0.5:
                        errors.append(f"visual_candidates.csv:{line_no}: confidence above 0.5")
                except ValueError:
                    errors.append(f"visual_candidates.csv:{line_no}: confidence is not numeric")
                for required in ["document_id", "figure_id", "page_number", "source_image_path"]:
                    if not row.get(required):
                        errors.append(f"visual_candidates.csv:{line_no}: missing {required}")
    return {
        "status": "success" if not errors else "failed",
        "contract_version": contract.get("contract_version", "unknown"),
        "output_dir": str(output_dir),
        "checks_count": checks_count,
        "errors_count": len(errors),
        "warnings_count": 0,
        "errors": errors,
        "warnings": [],
    }


__all__ = ["load_contract", "validate_visual_outputs"]

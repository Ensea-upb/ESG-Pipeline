from __future__ import annotations

from pathlib import Path

from .io_utils import read_csv, read_json


CRITICAL_FILES = [
    "indicator_candidate_validations.csv",
    "possible_indicators.csv",
    "rejected_candidates.csv",
    "validation_review_queue.csv",
    "indicator_validation_audit_summary.json",
    "indicator_validation_summary.json",
]

ALLOWED_VALIDATION_STATUS = {"possible_indicator", "needs_review", "reject_candidate"}


def load_indicator_validation_outputs(input_dir: Path) -> tuple[list[dict[str, str]], dict]:
    missing = [name for name in CRITICAL_FILES if not (input_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing critical ESGIndicatorValidation files: {missing}")
    rows = [row for row in read_csv(input_dir / "indicator_candidate_validations.csv") if row.get("validation_status") in ALLOWED_VALIDATION_STATUS]
    inventory = {
        "schema_version": "1.0.0",
        "input_dir": str(input_dir.resolve()),
        "critical_files_present": len(missing) == 0,
        "loaded_candidates_count": len(rows),
        "indicator_validation_summary": read_json(input_dir / "indicator_validation_summary.json"),
        "indicator_validation_audit_summary": read_json(input_dir / "indicator_validation_audit_summary.json"),
    }
    return rows, inventory

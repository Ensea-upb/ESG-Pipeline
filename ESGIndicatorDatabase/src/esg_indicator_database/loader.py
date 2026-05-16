from __future__ import annotations

from pathlib import Path

from .io_utils import read_csv, read_json


CRITICAL_FILES = ["accepted_candidate_inputs.csv", "reviewed_candidates.csv", "review_decision_summary.json", "manual_review_audit_summary.json"]


def load_manual_review_outputs(input_dir: Path) -> tuple[list[dict[str, str]], dict]:
    missing = [name for name in CRITICAL_FILES if not (input_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing critical ESGManualReview files: {missing}")
    rows = read_csv(input_dir / "accepted_candidate_inputs.csv")
    inventory = {
        "schema_version": "1.0.0",
        "input_dir": str(input_dir.resolve()),
        "accepted_candidates_loaded_count": len(rows),
        "reviewed_candidates_count": len(read_csv(input_dir / "reviewed_candidates.csv")),
        "review_decision_summary": read_json(input_dir / "review_decision_summary.json"),
        "manual_review_audit_summary": read_json(input_dir / "manual_review_audit_summary.json"),
    }
    return rows, inventory

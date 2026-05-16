from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "ESGIndicatorDatabase" / "scripts" / "build_indicator_database.py"
VALIDATE = ROOT / "ESGIndicatorDatabase" / "scripts" / "validate_indicator_database_outputs.py"
MULTI = ROOT / "ESGIndicatorDatabase" / "scripts" / "run_multi_document_indicator_database.py"
CONTRACT = ROOT / "ESGIndicatorDatabase" / "contracts" / "indicator_database_contract_v0.json"

FIELDS = [
    "review_item_id", "candidate_id", "document_id", "company", "fiscal_year",
    "source_engine", "information_type", "validation_status", "indicator_family",
    "indicator_key_candidate", "label", "raw_value", "raw_unit", "normalized_value",
    "normalized_unit", "normalized_year", "corrected_value", "corrected_unit",
    "corrected_year", "corrected_indicator_family", "corrected_indicator_key",
    "page_number", "quote", "evidence_id", "table_id", "cell_id", "figure_id",
    "reviewer", "decision_reason", "reviewer_notes", "review_status",
    "validated_indicator", "score_produced",
]


def make_manual_review_output(tmp_path: Path, accepted: bool = True) -> Path:
    path = tmp_path / "manual_review"
    path.mkdir(parents=True)
    row = {
        "review_item_id": "ri1", "candidate_id": "c1", "document_id": "doc1", "company": "LVMH", "fiscal_year": "2024",
        "source_engine": "csv", "information_type": "observed_metric", "validation_status": "possible_indicator", "indicator_family": "ghg_emissions",
        "indicator_key_candidate": "ghg:scope_1", "label": "Scope 1", "raw_value": "1,200", "raw_unit": "tCO2e", "normalized_value": "1200",
        "normalized_unit": "tCO2e", "normalized_year": "2024", "corrected_value": "1199", "corrected_unit": "", "corrected_year": "",
        "corrected_indicator_family": "", "corrected_indicator_key": "", "page_number": "4", "quote": "Scope 1 emissions were 1200 tCO2e.",
        "evidence_id": "ev1", "table_id": "", "cell_id": "", "figure_id": "", "reviewer": "qa", "decision_reason": "checked",
        "reviewer_notes": "ok", "review_status": "accepted_candidate", "validated_indicator": "False", "score_produced": "False",
    }
    accepted_rows = [row] if accepted else []
    for name, rows in [
        ("accepted_candidate_inputs.csv", accepted_rows),
        ("reviewed_candidates.csv", [row] if accepted else []),
        ("rejected_review_candidates.csv", []),
        ("needs_more_evidence_candidates.csv", []),
        ("deferred_candidates.csv", []),
    ]:
        _write_csv(path / name, rows, FIELDS)
    _write_json(path / "review_decision_summary.json", {"accepted_candidates_count": len(accepted_rows)})
    _write_json(path / "manual_review_audit_summary.json", {"errors_count": 0})
    (path / "manual_review_audit_findings.jsonl").write_text("", encoding="utf-8")
    return path


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def hash_tree(path: Path) -> dict[str, str]:
    return {str(f.relative_to(path)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(path.rglob("*")) if f.is_file()}


def run_build(input_dir: Path, output_dir: Path, *extra: str):
    return subprocess.run([sys.executable, str(BUILD), "--input-dir", str(input_dir), "--output-dir", str(output_dir), *extra], cwd=ROOT, text=True, capture_output=True)


def run_validate(output_dir: Path):
    return subprocess.run([sys.executable, str(VALIDATE), "--output-dir", str(output_dir), "--contract-path", str(CONTRACT)], cwd=ROOT, text=True, capture_output=True)

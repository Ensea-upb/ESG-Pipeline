from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "ESGManualReview" / "scripts" / "build_review_workspace.py"
APPLY = ROOT / "ESGManualReview" / "scripts" / "apply_review_decisions.py"
VALIDATE = ROOT / "ESGManualReview" / "scripts" / "validate_manual_review_outputs.py"
MULTI = ROOT / "ESGManualReview" / "scripts" / "run_multi_document_manual_review_audit.py"
CONTRACT = ROOT / "ESGManualReview" / "contracts" / "manual_review_contract_v0.json"


FIELDS = [
    "candidate_id", "candidate_validation_id", "document_id", "company", "fiscal_year",
    "source_engine", "information_type", "original_information_type", "esg_category", "label",
    "raw_value", "raw_unit", "year", "normalized_value", "normalized_unit",
    "normalized_year", "page_number", "section_id", "evidence_id", "table_id",
    "cell_id", "figure_id", "quote", "confidence", "validation_status",
    "validation_reason", "indicator_family", "indicator_key_candidate",
    "review_priority", "review_reason", "review_action_suggested",
]


def make_indicator_output(tmp_path: Path) -> Path:
    path = tmp_path / "indicator"
    path.mkdir(parents=True)
    rows = [
        {
            "candidate_id": "c1", "candidate_validation_id": "v1", "document_id": "doc1", "company": "LVMH", "fiscal_year": "2024",
            "source_engine": "csv", "information_type": "observed_metric", "original_information_type": "observed_metric", "esg_category": "climate", "label": "scope 1",
            "raw_value": "1200", "raw_unit": "tCO2e", "year": "2024", "normalized_value": "1200", "normalized_unit": "tCO2e",
            "normalized_year": "2024", "page_number": "4", "section_id": "s1", "evidence_id": "ev1", "table_id": "",
            "cell_id": "", "figure_id": "", "quote": "Scope 1 emissions were 1200 tCO2e.", "confidence": "0.5", "validation_status": "possible_indicator",
            "validation_reason": "value and source", "indicator_family": "ghg_emissions", "indicator_key_candidate": "ghg:scope_1",
            "review_priority": "high", "review_reason": "possible indicator", "review_action_suggested": "verify_value",
        },
        {
            "candidate_id": "c2", "candidate_validation_id": "v2", "document_id": "doc1", "company": "LVMH", "fiscal_year": "2024",
            "source_engine": "csv", "information_type": "boundary_context", "original_information_type": "boundary_context", "esg_category": "general", "label": "boundary",
            "raw_value": "", "raw_unit": "", "year": "2024", "normalized_value": "", "normalized_unit": "",
            "normalized_year": "2024", "page_number": "5", "section_id": "s1", "evidence_id": "ev2", "table_id": "",
            "cell_id": "", "figure_id": "", "quote": "The boundary is the Group.", "confidence": "0.4", "validation_status": "needs_review",
            "validation_reason": "context", "indicator_family": "boundary", "indicator_key_candidate": "boundary:group",
            "review_priority": "low", "review_reason": "context", "review_action_suggested": "inspect_quote",
        },
        {
            "candidate_id": "c3", "candidate_validation_id": "v3", "document_id": "doc1", "company": "LVMH", "fiscal_year": "2024",
            "source_engine": "visual", "information_type": "visual_metric_candidate", "original_information_type": "visual_metric_candidate", "esg_category": "general", "label": "weak visual",
            "raw_value": "", "raw_unit": "", "year": "2024", "normalized_value": "", "normalized_unit": "",
            "normalized_year": "2024", "page_number": "6", "section_id": "s1", "evidence_id": "", "table_id": "",
            "cell_id": "", "figure_id": "fig1", "quote": "Weak chart evidence.", "confidence": "0.3", "validation_status": "reject_candidate",
            "validation_reason": "insufficient", "indicator_family": "unknown", "indicator_key_candidate": "unknown:visual",
            "review_priority": "low", "review_reason": "weak", "review_action_suggested": "reject_if_not_esg",
        },
    ]
    for name in ["indicator_candidate_validations.csv", "possible_indicators.csv", "rejected_candidates.csv", "validation_review_queue.csv", "normalized_indicator_candidates.csv"]:
        subset = rows
        if name == "possible_indicators.csv":
            subset = [rows[0]]
        if name == "rejected_candidates.csv":
            subset = [rows[2]]
        _write_csv(path / name, subset, FIELDS)
    _write_json(path / "indicator_validation_audit_summary.json", {"errors_count": 0})
    _write_json(path / "indicator_validation_summary.json", {"validations_count": 3})
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


def run_apply(workspace_dir: Path, decisions_file: Path, output_dir: Path, *extra: str):
    return subprocess.run([sys.executable, str(APPLY), "--workspace-dir", str(workspace_dir), "--decisions-file", str(decisions_file), "--output-dir", str(output_dir), *extra], cwd=ROOT, text=True, capture_output=True)


def run_validate(output_dir: Path):
    return subprocess.run([sys.executable, str(VALIDATE), "--output-dir", str(output_dir), "--contract-path", str(CONTRACT)], cwd=ROOT, text=True, capture_output=True)

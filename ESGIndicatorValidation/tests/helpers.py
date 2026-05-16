from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "ESGIndicatorValidation" / "scripts" / "run_indicator_validation.py"
VALIDATE = ROOT / "ESGIndicatorValidation" / "scripts" / "validate_indicator_validation_outputs.py"
CONTRACT = ROOT / "ESGIndicatorValidation" / "contracts" / "indicator_validation_contract_v0.json"


def make_orchestrator_output(tmp_path: Path) -> Path:
    input_dir = tmp_path / "orchestrator_out"
    input_dir.mkdir(parents=True)
    fields = [
        "document_id", "source_engine", "information_type", "esg_category", "label",
        "raw_value", "raw_unit", "year", "source_modality", "page_number", "section_id",
        "evidence_id", "table_id", "cell_id", "figure_id", "quote", "confidence",
        "review_required", "extraction_status", "deduplication_status",
    ]
    rows = [
        {
            "document_id": "doc1", "source_engine": "csv", "information_type": "observed_metric",
            "esg_category": "climate", "label": "scope 1 emissions", "raw_value": "1200",
            "raw_unit": "tCO2e", "year": "2024", "source_modality": "text", "page_number": "4",
            "section_id": "sec1", "evidence_id": "ev1", "table_id": "", "cell_id": "",
            "figure_id": "", "quote": "Scope 1 emissions were 1,200 tCO2e.", "confidence": "0.60",
            "review_required": "True", "extraction_status": "candidate_only", "deduplication_status": "unique_candidate",
        },
        {
            "document_id": "doc1", "source_engine": "table", "information_type": "table_metric_candidate",
            "esg_category": "energy", "label": "energy consumption", "raw_value": "20",
            "raw_unit": "GWh", "year": "2024", "source_modality": "table", "page_number": "5",
            "section_id": "sec1", "evidence_id": "", "table_id": "tbl1", "cell_id": "cell1",
            "figure_id": "", "quote": "Energy consumption 20 GWh", "confidence": "0.55",
            "review_required": "True", "extraction_status": "candidate_only", "deduplication_status": "unique_candidate",
        },
        {
            "document_id": "doc1", "source_engine": "visual", "information_type": "visual_metric_candidate",
            "esg_category": "general", "label": "visual metric", "raw_value": "",
            "raw_unit": "", "year": "2024", "source_modality": "figure", "page_number": "6",
            "section_id": "sec1", "evidence_id": "", "table_id": "", "cell_id": "",
            "figure_id": "fig1", "quote": "Chart with numeric annotation", "confidence": "0.50",
            "review_required": "True", "extraction_status": "candidate_only", "deduplication_status": "unique_candidate",
        },
        {
            "document_id": "doc1", "source_engine": "csv", "information_type": "boundary_context",
            "esg_category": "general", "label": "reporting boundary", "raw_value": "",
            "raw_unit": "", "year": "2024", "source_modality": "text", "page_number": "7",
            "section_id": "sec1", "evidence_id": "ev2", "table_id": "", "cell_id": "",
            "figure_id": "", "quote": "The reporting boundary includes the Group.", "confidence": "0.40",
            "review_required": "True", "extraction_status": "candidate_only", "deduplication_status": "unique_candidate",
        },
        {
            "document_id": "doc1", "source_engine": "csv", "information_type": "observed_metric",
            "esg_category": "climate", "label": "scope 1 emissions", "raw_value": "1,200",
            "raw_unit": "tCO2e", "year": "2024", "source_modality": "text", "page_number": "4",
            "section_id": "sec1", "evidence_id": "ev3", "table_id": "", "cell_id": "",
            "figure_id": "", "quote": "Scope 1 emissions were 1,200 tCO2e.", "confidence": "0.50",
            "review_required": "True", "extraction_status": "candidate_only", "deduplication_status": "unique_candidate",
        },
    ]
    with (input_dir / "consolidated_unique_candidates.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return input_dir


def make_invalid_orchestrator_output(tmp_path: Path, **overrides) -> Path:
    input_dir = make_orchestrator_output(tmp_path)
    rows = read_csv(input_dir / "consolidated_unique_candidates.csv")
    rows[0].update(overrides)
    fields = list(rows[0].keys())
    with (input_dir / "consolidated_unique_candidates.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return input_dir


def run_validation(input_dir: Path, output_dir: Path, *extra: str):
    return subprocess.run([sys.executable, str(RUN), "--input-dir", str(input_dir), "--output-dir", str(output_dir), *extra], cwd=ROOT, text=True, capture_output=True)


def validate_output(output_dir: Path):
    return subprocess.run([sys.executable, str(VALIDATE), "--output-dir", str(output_dir), "--contract-path", str(CONTRACT)], cwd=ROOT, text=True, capture_output=True)


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def hash_tree(path: Path) -> dict[str, str]:
    return {str(file.relative_to(path)): hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(path.rglob("*")) if file.is_file()}

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from .helpers import CONTRACT, MULTI, hash_tree, make_input, read_json, run_full, validate


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_runner_simple_and_complete_outputs(tmp_path: Path):
    input_dir = make_input(tmp_path)
    before = hash_tree(input_dir)
    output_dir = tmp_path / "out"
    result = run_full(input_dir, output_dir)
    assert result.returncode == 0, result.stdout
    assert (output_dir / "csv" / "esg_information_candidates.csv").exists()
    assert (output_dir / "visual" / "visual_candidates.csv").exists()
    assert (output_dir / "table" / "table_metric_candidates.csv").exists()
    assert before == hash_tree(input_dir)


def test_consolidated_candidates_schema_and_policy(tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_full(make_input(tmp_path), output_dir)
    assert result.returncode == 0, result.stdout
    rows = read_csv(output_dir / "consolidated_candidates.csv")
    assert rows
    assert {"csv", "visual", "table"}.issubset({row["source_engine"] for row in rows})
    assert {row["review_required"] for row in rows} == {"True"}
    assert {row["extraction_status"] for row in rows} == {"candidate_only"}
    assert all("score" not in key.lower() for key in rows[0])


def test_consolidated_audit_and_report(tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_full(make_input(tmp_path), output_dir)
    assert result.returncode == 0, result.stdout
    assert (output_dir / "consolidated_audit_summary.json").exists()
    assert (output_dir / "consolidated_audit_findings.jsonl").exists()
    assert (output_dir / "consolidated_audit_samples.csv").exists()
    assert "Full ESG Candidate Extraction Report" in (output_dir / "full_extraction_report.md").read_text(encoding="utf-8")
    summary = read_json(output_dir / "full_extraction_summary.json")
    assert summary["consolidated_candidates_count"] > 0


def test_contract_validation(tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_full(make_input(tmp_path), output_dir)
    assert result.returncode == 0, result.stdout
    validation = validate(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode == 0, validation.stdout
    assert payload["status"] == "success"
    assert CONTRACT.exists()


def test_multi_document_full_extraction(tmp_path: Path):
    root = tmp_path / "inputs"
    make_input(root / "doc1")
    make_input(root / "doc2")
    before = hash_tree(root)
    out = tmp_path / "multi"
    result = subprocess.run([sys.executable, str(MULTI), "--input-root", str(root), "--output-dir", str(out), "--overwrite"], cwd=Path(__file__).resolve().parents[2], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout
    summary = read_json(out / "multi_document_full_extraction_summary.json")
    assert summary["documents_tested_count"] == 2
    assert summary["consolidated_candidates_total"] > 0
    assert (out / "multi_document_full_extraction.csv").exists()
    assert (out / "multi_document_full_extraction.md").exists()
    assert before == hash_tree(root)


def test_release_docs_exist():
    root = Path(__file__).resolve().parents[2] / "ESGExtractionOrchestrator"
    assert (root / "README.md").exists()
    assert (root / "docs" / "FULL_EXTRACTION_OUTPUT_CONTRACT_V0.md").exists()
    assert (root / "docs" / "RELEASE_NOTES_V1_0.md").exists()
    assert (root / "docs" / "ARCHITECTURE_OVERVIEW_V1_0.md").exists()
    assert (root / "docs" / "VALIDATION_COMMANDS_V1_0.md").exists()

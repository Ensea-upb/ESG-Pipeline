from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_CLI = PROJECT_ROOT / "ESGCSVExtraction" / "scripts" / "run_csv_extraction.py"
VALIDATE_CLI = PROJECT_ROOT / "ESGCSVExtraction" / "scripts" / "validate_csv_outputs.py"
CONTRACT = PROJECT_ROOT / "ESGCSVExtraction" / "contracts" / "csv_output_contract_v0.json"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def make_input(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    write_json(input_dir / "document_inventory.json", {
        "document_id": "lvmh_2024_test",
        "pdf_path": "ESGFinalCorpus/lvmh/2024/x/document.pdf",
    })
    write_json(input_dir / "extraction_summary.json", {"document_id": "lvmh_2024_test"})
    write_jsonl(input_dir / "multimodal_evidence_index.jsonl", [
        {
            "evidence_id": "ev_metric",
            "source_modality": "text",
            "evidence_type": "paragraph",
            "page_number": 1,
            "section_id": "sec",
            "quote": "Scope 1 emissions were 12,500 tCO2e in 2024.",
            "downstream_use_policy": "eligible_for_future_extraction",
        },
        {
            "evidence_id": "ev_target",
            "source_modality": "text",
            "evidence_type": "paragraph",
            "page_number": 2,
            "section_id": "sec",
            "quote": "Target to reduce Scope 1 emissions by 30% by 2030.",
            "downstream_use_policy": "review_before_extraction",
        },
    ])
    return input_dir


def run_extraction(input_dir: Path, output_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(RUN_CLI), "--input-dir", str(input_dir), "--output-dir", str(output_dir)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout


def run_validator(output_dir: Path):
    return subprocess.run(
        [sys.executable, str(VALIDATE_CLI), "--output-dir", str(output_dir), "--contract-path", str(CONTRACT)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def rewrite_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def test_csv_contract_files_exist():
    assert CONTRACT.exists()
    assert VALIDATE_CLI.exists()
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["contract_version"] == "0.9.0"


def test_validate_csv_outputs_succeeds_on_valid_output(tmp_path: Path):
    output_dir = tmp_path / "out"
    run_extraction(make_input(tmp_path), output_dir)
    result = run_validator(output_dir)
    payload = json.loads(result.stdout)
    assert result.returncode == 0, result.stdout
    assert payload["status"] == "success"
    assert payload["errors_count"] == 0


def test_validate_csv_outputs_fails_when_required_column_missing(tmp_path: Path):
    output_dir = tmp_path / "out"
    run_extraction(make_input(tmp_path), output_dir)
    headers, rows = read_csv(output_dir / "esg_information_candidates.csv")
    headers.remove("evidence_id")
    rewrite_csv(output_dir / "esg_information_candidates.csv", rows, headers)
    result = run_validator(output_dir)
    payload = json.loads(result.stdout)
    assert result.returncode != 0
    assert payload["status"] == "failed"
    assert any("evidence_id" in error for error in payload["errors"])


def test_validate_csv_outputs_fails_when_review_required_false(tmp_path: Path):
    output_dir = tmp_path / "out"
    run_extraction(make_input(tmp_path), output_dir)
    headers, rows = read_csv(output_dir / "esg_information_candidates.csv")
    rows[0]["review_required"] = "False"
    rewrite_csv(output_dir / "esg_information_candidates.csv", rows, headers)
    result = run_validator(output_dir)
    payload = json.loads(result.stdout)
    assert result.returncode != 0
    assert any("review_required" in error for error in payload["errors"])


def test_validate_csv_outputs_fails_when_score_column_detected(tmp_path: Path):
    output_dir = tmp_path / "out"
    run_extraction(make_input(tmp_path), output_dir)
    headers, rows = read_csv(output_dir / "targets.csv")
    headers.append("risk_score")
    for row in rows:
        row["risk_score"] = "0"
    rewrite_csv(output_dir / "targets.csv", rows, headers)
    result = run_validator(output_dir)
    payload = json.loads(result.stdout)
    assert result.returncode != 0
    assert any("forbidden" in error for error in payload["errors"])

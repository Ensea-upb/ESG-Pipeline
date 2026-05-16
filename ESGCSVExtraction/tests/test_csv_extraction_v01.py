from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esg_csv_extraction.extractor import CANDIDATE_FIELDS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLI = PROJECT_ROOT / "ESGCSVExtraction" / "scripts" / "run_csv_extraction.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def hash_tree(path: Path) -> dict[str, str]:
    return {
        str(file.relative_to(path)): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def make_input(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    write_json(input_dir / "document_inventory.json", {
        "document_id": "lvmh_2024_test",
        "pdf_path": "C:/Users/hp/Desktop/ESG/ESGFinalCorpus/lvmh/2024/02_sustainability_statement_csrd_esrs/document.pdf",
    })
    write_json(input_dir / "extraction_summary.json", {
        "document_id": "lvmh_2024_test",
        "status": "success",
    })
    write_jsonl(input_dir / "multimodal_evidence_index.jsonl", [
        {
            "evidence_id": "ev_001",
            "document_id": "lvmh_2024_test",
            "evidence_type": "paragraph",
            "source_modality": "text",
            "page_number": 12,
            "section_id": "sec_001",
            "quote": "The Group reported greenhouse gas emissions of 12,500 tCO2e in 2024.",
            "review_required": False,
            "is_quarantined_evidence": False,
            "downstream_use_policy": "eligible_for_future_extraction",
        },
        {
            "evidence_id": "ev_002",
            "document_id": "lvmh_2024_test",
            "evidence_type": "paragraph",
            "source_modality": "text",
            "page_number": 13,
            "section_id": "sec_001",
            "quote": "The company has a target to reduce energy consumption by 30% by 2030.",
            "review_required": True,
            "is_quarantined_evidence": False,
            "downstream_use_policy": "review_before_extraction",
        },
        {
            "evidence_id": "ev_003",
            "document_id": "lvmh_2024_test",
            "evidence_type": "table",
            "source_modality": "table",
            "page_number": 14,
            "section_id": "sec_002",
            "quote": "Table detected on page 14 with 8 rows and 5 columns",
            "review_required": True,
            "is_quarantined_evidence": False,
            "downstream_use_policy": "review_before_extraction",
        },
    ])
    return input_dir


def run_cli(input_dir: Path, output_dir: Path, *extra: str):
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            *extra,
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def test_csv_extraction_produces_expected_files(tmp_path: Path):
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    assert (output_dir / "esg_information_candidates.csv").exists()
    assert (output_dir / "esg_information_candidates.jsonl").exists()
    assert (output_dir / "extraction_audit.csv").exists()
    assert (output_dir / "candidate_audit_summary.json").exists()
    assert (output_dir / "candidate_audit_findings.jsonl").exists()
    assert (output_dir / "candidate_audit_samples.csv").exists()
    assert (output_dir / "extraction_summary.json").exists()


def test_candidates_are_candidate_only_and_review_required(tmp_path: Path):
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    rows = read_csv(output_dir / "esg_information_candidates.csv")
    assert rows
    assert {row["extraction_status"] for row in rows} == {"candidate_only"}
    assert {row["review_required"] for row in rows} == {"True"}
    assert {"observed_metric", "target", "visual_evidence"}.issubset({row["information_type"] for row in rows})


def test_csv_contains_required_columns(tmp_path: Path):
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    with (output_dir / "esg_information_candidates.csv").open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames == CANDIDATE_FIELDS


def test_summary_counts_distribution(tmp_path: Path):
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    summary = read_json(output_dir / "extraction_summary.json")
    assert summary["candidate_only"] is True
    assert summary["review_required_count"] == summary["candidates_count"]
    assert summary["information_type_distribution"]["observed_metric"] >= 1
    assert summary["company"] == "lvmh"
    assert summary["fiscal_year"] == "2024"
    assert "candidate_audit_findings_count" in summary


def test_input_outputs_are_not_modified(tmp_path: Path):
    input_dir = make_input(tmp_path)
    before = hash_tree(input_dir)
    output_dir = tmp_path / "out"
    result = run_cli(input_dir, output_dir)
    assert result.returncode == 0, result.stdout
    after = hash_tree(input_dir)
    assert before == after


def test_without_overwrite_refuses_existing_outputs(tmp_path: Path):
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    first = run_cli(input_dir, output_dir)
    assert first.returncode == 0, first.stdout
    second = run_cli(input_dir, output_dir)
    payload = json.loads(second.stdout)
    assert second.returncode != 0
    assert payload["status"] == "failed"

    third = run_cli(input_dir, output_dir, "--overwrite")
    assert third.returncode == 0, third.stdout


def test_candidate_audit_outputs_are_created_and_consistent(tmp_path: Path):
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    audit_summary = read_json(output_dir / "candidate_audit_summary.json")
    assert audit_summary["candidate_only"] is True
    assert audit_summary["checks_count"] >= 9
    assert "information_type_distribution" in audit_summary
    assert "source_modality_distribution" in audit_summary
    assert "confidence_above_0_6" in audit_summary["checks"]
    assert audit_summary["checks"]["confidence_above_0_6"] == 0
    assert audit_summary["checks"]["review_required_missing_or_false"] == 0

    findings = [
        json.loads(line)
        for line in (output_dir / "candidate_audit_findings.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(findings) == audit_summary["checks_count"]
    assert {finding["check_name"] for finding in findings} >= {
        "observed_metric_without_unit",
        "target_without_target_year",
        "confidence_above_0_6",
        "duplicate_evidence_type_label",
        "ineligible_evidence_candidates",
    }


def test_candidate_audit_samples_csv_has_expected_columns(tmp_path: Path):
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    with (output_dir / "candidate_audit_samples.csv").open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames == [
            "audit_check",
            "document_id",
            "information_type",
            "evidence_id",
            "page_number",
            "confidence",
            "raw_value",
            "raw_unit",
            "year",
            "quote",
        ]

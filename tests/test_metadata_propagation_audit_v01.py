"""Tests for tools/audit_metadata_propagation.py — v0.1."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = PROJECT_ROOT / "tools" / "audit_metadata_propagation.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({f: row.get(f, "") for f in fields})


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build_fixture_with_metadata(input_root: Path) -> list[Path]:
    """Create a minimal fixture with correct company/fiscal_year metadata."""
    doc_record = input_root / "document_record.json"
    _write_json(doc_record, {
        "document_id": "test_doc_001",
        "company": "TestCo",
        "fiscal_year": "2024",
    })
    prep_db = input_root / "indicator_preparation_database.csv"
    _write_csv(prep_db, [
        {"company": "TestCo", "fiscal_year": "2024", "document_id": "test_doc_001",
         "official_doc_type": "URD", "final_path": "/data/test_doc_001.pdf"},
    ], ["company", "fiscal_year", "document_id", "official_doc_type", "final_path"])
    return [doc_record, prep_db]


def _build_fixture_empty_company(input_root: Path) -> list[Path]:
    """Create a fixture where company is empty in indicator_preparation_database."""
    prep_db = input_root / "indicator_preparation_database.csv"
    _write_csv(prep_db, [
        {"company": "", "fiscal_year": "2024", "document_id": "test_doc_002",
         "official_doc_type": "", "final_path": ""},
    ], ["company", "fiscal_year", "document_id", "official_doc_type", "final_path"])
    return [prep_db]


def _build_fixture_missing_fiscal_year(input_root: Path) -> list[Path]:
    """Create a fixture where fiscal_year column is absent from CSV."""
    prep_db = input_root / "indicator_preparation_database.csv"
    _write_csv(prep_db, [
        {"company": "TestCo", "document_id": "test_doc_003"},
    ], ["company", "document_id"])
    return [prep_db]


def test_audit_script_runs_and_produces_three_output_files(tmp_path: Path) -> None:
    """Script must exit 0 and produce all 3 output files."""
    input_root = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    _build_fixture_with_metadata(input_root)

    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--input-root", str(input_root), "--output-dir", str(output_dir)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr

    assert (output_dir / "metadata_propagation_report.json").exists()
    assert (output_dir / "metadata_propagation_findings.jsonl").exists()
    assert (output_dir / "metadata_propagation_report.md").exists()


def test_audit_report_json_has_expected_keys(tmp_path: Path) -> None:
    """JSON report must contain top-level summary keys."""
    input_root = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    _build_fixture_with_metadata(input_root)

    subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--input-root", str(input_root), "--output-dir", str(output_dir)],
        capture_output=True, text=True, check=True,
    )
    report = json.loads((output_dir / "metadata_propagation_report.json").read_text(encoding="utf-8"))
    for key in ("generated_at", "layers_checked", "files_found", "errors", "warnings", "layers"):
        assert key in report, f"Missing key '{key}' in report"


def test_audit_detects_empty_company(tmp_path: Path) -> None:
    """Audit must flag a warning when company field is empty."""
    input_root = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    _build_fixture_empty_company(input_root)

    subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--input-root", str(input_root), "--output-dir", str(output_dir)],
        capture_output=True, text=True, check=True,
    )
    findings_text = (output_dir / "metadata_propagation_findings.jsonl").read_text(encoding="utf-8")
    findings = [json.loads(line) for line in findings_text.splitlines() if line.strip()]

    company_findings = [f for f in findings if f.get("field") == "company"]
    assert company_findings, "Expected a finding about the 'company' field being empty"
    severities = {f.get("severity") for f in company_findings}
    assert severities & {"warning", "error"}, f"Expected warning or error severity, got: {severities}"


def test_audit_detects_missing_fiscal_year(tmp_path: Path) -> None:
    """Audit must flag a finding when fiscal_year column is absent."""
    input_root = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    _build_fixture_missing_fiscal_year(input_root)

    subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--input-root", str(input_root), "--output-dir", str(output_dir)],
        capture_output=True, text=True, check=True,
    )
    findings_text = (output_dir / "metadata_propagation_findings.jsonl").read_text(encoding="utf-8")
    findings = [json.loads(line) for line in findings_text.splitlines() if line.strip()]

    fiscal_findings = [f for f in findings if f.get("field") == "fiscal_year"]
    assert fiscal_findings, "Expected a finding about the 'fiscal_year' field being absent or empty"


def test_audit_does_not_modify_input_files(tmp_path: Path) -> None:
    """Input files must not be modified during audit (hash check)."""
    input_root = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    input_files = _build_fixture_with_metadata(input_root)

    hashes_before = {f: _sha256(f) for f in input_files}

    subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--input-root", str(input_root), "--output-dir", str(output_dir)],
        capture_output=True, text=True, check=True,
    )

    for f in input_files:
        assert _sha256(f) == hashes_before[f], f"Input file was modified: {f}"


def test_audit_overwrite_flag_required_for_existing_output(tmp_path: Path) -> None:
    """Running audit twice without --overwrite should fail on second run."""
    input_root = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    _build_fixture_with_metadata(input_root)

    subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--input-root", str(input_root), "--output-dir", str(output_dir)],
        capture_output=True, text=True, check=True,
    )
    result2 = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--input-root", str(input_root), "--output-dir", str(output_dir)],
        capture_output=True, text=True,
    )
    assert result2.returncode != 0, "Second run without --overwrite should fail"


def test_audit_overwrite_flag_allows_rerun(tmp_path: Path) -> None:
    """Running audit twice with --overwrite must succeed on second run."""
    input_root = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    _build_fixture_with_metadata(input_root)

    for _ in range(2):
        result = subprocess.run(
            [sys.executable, str(AUDIT_SCRIPT), "--input-root", str(input_root), "--output-dir", str(output_dir), "--overwrite"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

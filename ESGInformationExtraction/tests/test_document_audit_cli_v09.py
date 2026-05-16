from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from .conftest import PROJECT_ROOT, read_json, read_jsonl, run_cli


CLI_PATH = PROJECT_ROOT / "ESGInformationExtraction" / "tools" / "run_document_audit.py"
AUDIT_FILES = {
    "consistency_report.json",
    "audit_findings.jsonl",
    "document_audit_report.md",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_audit_cli(output_dir: Path, overwrite: bool = False):
    command = [
        sys.executable,
        str(CLI_PATH),
        "--output-dir",
        str(output_dir),
    ]
    if overwrite:
        command.append("--overwrite")
    return subprocess.run(command, text=True, capture_output=True, cwd=PROJECT_ROOT)


def _prepare_output(require_pdfplumber, pdf_path: Path, tmp_path: Path) -> Path:
    output_dir = tmp_path / "out"
    result = run_cli(pdf_path, output_dir, document_id="v09_cli_source")
    assert result.returncode == 0, result.stderr
    return output_dir


def test_cli_regenerates_audit_files(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    for name in AUDIT_FILES:
        (output_dir / name).unlink()

    result = _run_audit_cli(output_dir)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["status"] == "success"
    assert payload["audit_overall_status"] in {"pass", "warning", "fail"}
    assert set(payload["files_written"]) == AUDIT_FILES
    for name in AUDIT_FILES:
        assert (output_dir / name).exists()


def test_cli_refuses_without_overwrite(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    result = _run_audit_cli(output_dir, overwrite=False)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "overwrite" in payload["errors"][0].lower()


def test_cli_overwrite_rewrites_only_audit_files(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    protected = ["evidence_store.jsonl", "table_index.jsonl", "figure_index.jsonl"]
    before = {name: _sha(output_dir / name) for name in protected}
    audit_before = {name: _sha(output_dir / name) for name in AUDIT_FILES}

    result = _run_audit_cli(output_dir, overwrite=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["status"] == "success"
    assert set(payload["files_written"]) == AUDIT_FILES
    after = {name: _sha(output_dir / name) for name in protected}
    assert after == before
    assert all((output_dir / name).exists() for name in AUDIT_FILES)
    assert set(audit_before) == AUDIT_FILES


def test_cli_outputs_json_summary(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    result = _run_audit_cli(output_dir, overwrite=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    for key in {
        "status",
        "output_dir",
        "audit_overall_status",
        "findings_count",
        "critical_findings_count",
        "major_findings_count",
        "files_written",
    }:
        assert key in payload


def test_cli_missing_required_file_fails_cleanly(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    (output_dir / "evidence_store.jsonl").unlink()
    for name in AUDIT_FILES:
        if (output_dir / name).exists():
            (output_dir / name).unlink()

    result = _run_audit_cli(output_dir)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert any("evidence_store.jsonl" in error for error in payload["errors"])
    assert (output_dir / "consistency_report.json").exists()
    report = read_json(output_dir / "consistency_report.json")
    assert report["overall_status"] == "fail"


def test_cli_audit_outputs_are_readable(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    result = _run_audit_cli(output_dir, overwrite=True)
    assert result.returncode == 0, result.stderr

    report = read_json(output_dir / "consistency_report.json")
    findings = read_jsonl(output_dir / "audit_findings.jsonl")
    markdown = (output_dir / "document_audit_report.md").read_text(encoding="utf-8")

    assert "overall_status" in report
    assert findings
    assert "Document Audit Report" in markdown

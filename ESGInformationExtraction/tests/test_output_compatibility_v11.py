from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from .conftest import PROJECT_ROOT, read_json, run_cli


CONTRACT_JSON = PROJECT_ROOT / "ESGInformationExtraction" / "contracts" / "output_contract_v1.json"
CLI = PROJECT_ROOT / "ESGInformationExtraction" / "tools" / "check_output_compatibility.py"


def _run_compat(output_dir: Path, *extra: str):
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--output-dir",
            str(output_dir),
            "--contract-path",
            str(CONTRACT_JSON),
            *extra,
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def _prepare_output(require_pdfplumber, small_pdf: Path, tmp_path: Path) -> Path:
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="v11_compat")
    assert result.returncode == 0, result.stderr
    return output_dir


def _sha_all(output_dir: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in output_dir.iterdir()
        if path.is_file()
    }


def test_cli_returns_json_console(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    result = _run_compat(output_dir)
    payload = json.loads(result.stdout)
    assert "compatibility_status" in payload
    assert "files_written" in payload


def test_valid_v10_output_is_compatible(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    result = _run_compat(output_dir)
    payload = json.loads(result.stdout)
    assert result.returncode == 0, result.stdout
    assert payload["compatibility_status"] == "compatible"


def test_missing_engine_contract_version_is_warning(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    summary = read_json(output_dir / "extraction_summary.json")
    summary.pop("engine_contract_version", None)
    (output_dir / "extraction_summary.json").write_text(json.dumps(summary) + "\n", encoding="utf-8")

    result = _run_compat(output_dir)
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["compatibility_status"] == "compatible_with_warnings"


def test_missing_audit_files_is_migration_required(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    for name in ["consistency_report.json", "audit_findings.jsonl", "document_audit_report.md"]:
        (output_dir / name).unlink()

    result = _run_compat(output_dir)
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["compatibility_status"] == "migration_required"


def test_missing_evidence_store_is_incompatible(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    (output_dir / "evidence_store.jsonl").unlink()

    result = _run_compat(output_dir)
    payload = json.loads(result.stdout)
    assert result.returncode != 0
    assert payload["compatibility_status"] == "incompatible"


def test_write_report_outputs_three_files(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    result = _run_compat(output_dir, "--write-report")
    payload = json.loads(result.stdout)
    assert result.returncode == 0, result.stdout
    assert set(payload["files_written"]) == {
        "compatibility_report.json",
        "compatibility_findings.jsonl",
        "compatibility_report.md",
    }
    for name in payload["files_written"]:
        assert (output_dir / name).exists()


def test_write_report_refuses_without_overwrite(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    first = _run_compat(output_dir, "--write-report")
    assert first.returncode == 0, first.stdout
    second = _run_compat(output_dir, "--write-report")
    payload = json.loads(second.stdout)
    assert second.returncode != 0
    assert payload["status"] == "failed"


def test_annotate_summary_modifies_only_summary(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    before = _sha_all(output_dir)
    result = _run_compat(output_dir, "--annotate-summary")
    assert result.returncode == 0, result.stdout
    after = _sha_all(output_dir)
    changed = {name for name in before if before[name] != after.get(name)}
    assert changed == {"extraction_summary.json"}
    summary = read_json(output_dir / "extraction_summary.json")
    assert summary["compatibility_check_status"] == "compatible"


def test_without_annotate_summary_modifies_no_existing_files(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = _prepare_output(require_pdfplumber, small_pdf, tmp_path)
    before = _sha_all(output_dir)
    result = _run_compat(output_dir)
    assert result.returncode == 0, result.stdout
    after = _sha_all(output_dir)
    assert before == after

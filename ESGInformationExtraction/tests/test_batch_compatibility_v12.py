from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .conftest import PROJECT_ROOT, read_json, run_cli


CONTRACT_JSON = PROJECT_ROOT / "ESGInformationExtraction" / "contracts" / "output_contract_v1.json"
BATCH_CLI = PROJECT_ROOT / "ESGInformationExtraction" / "tools" / "batch_check_outputs.py"
BATCH_DIRNAME = "batch_compatibility_report"
BATCH_FILES = {
    "batch_compatibility_summary.json",
    "batch_compatibility_table.csv",
    "batch_compatibility_report.md",
}


def _run_batch(outputs_root: Path, *extra: str):
    return subprocess.run(
        [
            sys.executable,
            str(BATCH_CLI),
            "--outputs-root",
            str(outputs_root),
            "--contract-path",
            str(CONTRACT_JSON),
            *extra,
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def _prepare_base_output(require_pdfplumber, small_pdf: Path, tmp_path: Path) -> Path:
    base = tmp_path / "base_output"
    result = run_cli(small_pdf, base, document_id="v12_batch_base")
    assert result.returncode == 0, result.stderr
    return base


def _copy_output(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    return target


def _remove_engine_contract_version(output_dir: Path) -> None:
    summary_path = output_dir / "extraction_summary.json"
    summary = read_json(summary_path)
    summary.pop("engine_contract_version", None)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _remove_audit_files(output_dir: Path) -> None:
    for name in ["consistency_report.json", "audit_findings.jsonl", "document_audit_report.md"]:
        path = output_dir / name
        if path.exists():
            path.unlink()


def _make_incompatible(output_dir: Path) -> None:
    path = output_dir / "evidence_store.jsonl"
    if path.exists():
        path.unlink()


def _hash_tree(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and BATCH_DIRNAME not in file_path.parts:
            result[str(file_path.relative_to(path))] = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return result


def _prepare_status_outputs(require_pdfplumber, small_pdf: Path, tmp_path: Path) -> Path:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir()
    base = _prepare_base_output(require_pdfplumber, small_pdf, tmp_path)

    _copy_output(base, outputs_root / "compatible")
    warning = _copy_output(base, outputs_root / "compatible_with_warnings")
    _remove_engine_contract_version(warning)

    migration = _copy_output(base, outputs_root / "migration_required")
    _remove_audit_files(migration)

    incompatible = _copy_output(base, outputs_root / "incompatible")
    _make_incompatible(incompatible)

    (outputs_root / "not_an_output").mkdir()
    (outputs_root / "__pycache__").mkdir()
    (outputs_root / ".pytest_tmp").mkdir()
    return outputs_root


def test_batch_cli_detects_multiple_outputs_and_ignores_non_outputs(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_status_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root)
    payload = json.loads(result.stdout)

    assert result.returncode == 0, result.stdout
    assert payload["status"] == "success"
    assert payload["outputs_scanned_count"] == 4


def test_batch_cli_writes_expected_reports(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_status_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-report")
    payload = json.loads(result.stdout)

    assert result.returncode == 0, result.stdout
    report_dir = outputs_root / BATCH_DIRNAME
    assert set(Path(path).name for path in payload["files_written"]) == BATCH_FILES
    for name in BATCH_FILES:
        assert (report_dir / name).exists()


def test_batch_cli_refuses_to_overwrite_existing_reports(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_status_outputs(require_pdfplumber, small_pdf, tmp_path)
    first = _run_batch(outputs_root, "--write-report")
    assert first.returncode == 0, first.stdout

    second = _run_batch(outputs_root, "--write-report")
    payload = json.loads(second.stdout)
    assert second.returncode != 0
    assert payload["status"] == "failed"


def test_batch_cli_overwrite_rewrites_only_batch_reports(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_status_outputs(require_pdfplumber, small_pdf, tmp_path)
    first = _run_batch(outputs_root, "--write-report")
    assert first.returncode == 0, first.stdout
    before = _hash_tree(outputs_root)

    second = _run_batch(outputs_root, "--write-report", "--overwrite")
    assert second.returncode == 0, second.stdout
    after = _hash_tree(outputs_root)

    assert before == after
    assert (outputs_root / BATCH_DIRNAME / "batch_compatibility_summary.json").exists()


def test_batch_status_counts_and_summary_are_correct(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_status_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-report")
    assert result.returncode == 0, result.stdout
    payload = json.loads(result.stdout)

    assert payload["compatible_count"] == 1
    assert payload["compatible_with_warnings_count"] == 1
    assert payload["migration_required_count"] == 1
    assert payload["incompatible_count"] == 1

    summary = read_json(outputs_root / BATCH_DIRNAME / "batch_compatibility_summary.json")
    assert summary["outputs_scanned_count"] == 4
    assert summary["status_distribution"] == {
        "compatible": 1,
        "compatible_with_warnings": 1,
        "migration_required": 1,
        "incompatible": 1,
    }


def test_batch_csv_contains_expected_columns(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_status_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-report")
    assert result.returncode == 0, result.stdout

    csv_path = outputs_root / BATCH_DIRNAME / "batch_compatibility_table.csv"
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames == [
            "output_dir",
            "document_id",
            "compatibility_status",
            "engine_contract_version",
            "extraction_readiness_status",
            "findings_count",
            "critical_findings_count",
            "major_findings_count",
            "warnings_count",
        ]
        rows = list(reader)
    assert len(rows) == 4


def test_batch_markdown_contains_title(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_status_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-report")
    assert result.returncode == 0, result.stdout

    markdown = (outputs_root / BATCH_DIRNAME / "batch_compatibility_report.md").read_text(encoding="utf-8")
    assert "Batch Compatibility Report" in markdown

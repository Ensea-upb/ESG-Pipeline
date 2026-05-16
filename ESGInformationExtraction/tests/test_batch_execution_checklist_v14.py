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
ACTION_ORDER = {
    "no_action_needed": 0,
    "annotate_summary_only": 1,
    "rerun_audit_standalone": 2,
    "rerun_contract_validation": 3,
    "regenerate_with_current_engine": 4,
    "manual_review_required": 5,
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


def _copy_output(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    return target


def _hash_tree(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and BATCH_DIRNAME not in file_path.parts:
            result[str(file_path.relative_to(path))] = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return result


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


def _remove_evidence_store(output_dir: Path) -> None:
    path = output_dir / "evidence_store.jsonl"
    if path.exists():
        path.unlink()


def _prepare_outputs(require_pdfplumber, small_pdf: Path, tmp_path: Path) -> Path:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir()

    base = tmp_path / "base_output"
    result = run_cli(small_pdf, base, document_id="v14_checklist_base")
    assert result.returncode == 0, result.stderr

    _copy_output(base, outputs_root / "compatible")

    warning = _copy_output(base, outputs_root / "compatible_with_warnings")
    _remove_engine_contract_version(warning)

    migration = _copy_output(base, outputs_root / "migration_required")
    _remove_audit_files(migration)

    incompatible = _copy_output(base, outputs_root / "incompatible")
    _remove_evidence_store(incompatible)
    return outputs_root


def test_batch_writes_execution_checklist_files(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-execution-checklist")
    payload = json.loads(result.stdout)

    assert result.returncode == 0, result.stdout
    assert payload["status"] == "success"
    report_dir = outputs_root / BATCH_DIRNAME
    assert (report_dir / "batch_execution_checklist.json").exists()
    assert (report_dir / "batch_execution_checklist.csv").exists()
    assert (report_dir / "batch_execution_checklist.md").exists()


def test_checklist_items_have_execution_order_and_no_auto_execution(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-execution-checklist")
    assert result.returncode == 0, result.stdout

    checklist = read_json(outputs_root / BATCH_DIRNAME / "batch_execution_checklist.json")
    assert checklist["checklist_items_count"] == 4
    for item in checklist["items"]:
        assert item["execution_order"] >= 1
        assert item["is_automatic_execution_allowed"] is False
        assert item["command_to_run"]
        assert item["verification_command"]
        assert item["completion_criteria"]


def test_checklist_items_are_ordered_by_priority(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-execution-checklist")
    assert result.returncode == 0, result.stdout

    checklist = read_json(outputs_root / BATCH_DIRNAME / "batch_execution_checklist.json")
    priorities = [ACTION_ORDER[item["recommended_action"]] for item in checklist["items"]]
    assert priorities == sorted(priorities)
    assert [item["execution_order"] for item in checklist["items"]] == list(range(1, len(checklist["items"]) + 1))


def test_checklist_markdown_contains_title_and_safety_note(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-execution-checklist")
    assert result.returncode == 0, result.stdout

    markdown = (outputs_root / BATCH_DIRNAME / "batch_execution_checklist.md").read_text(encoding="utf-8")
    assert "Batch Execution Checklist" in markdown
    assert "Cette checklist n'execute aucune commande" in markdown
    assert "Aucune extraction ESG n'est realisee" in markdown


def test_checklist_csv_contains_expected_columns(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-execution-checklist")
    assert result.returncode == 0, result.stdout

    with (outputs_root / BATCH_DIRNAME / "batch_execution_checklist.csv").open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames == [
            "execution_order",
            "output_dir",
            "document_id",
            "compatibility_status",
            "recommended_action",
            "action_priority",
            "risk_level",
            "command_to_run",
            "verification_command",
            "completion_criteria",
        ]
        rows = list(reader)
    assert len(rows) == 4


def test_execution_checklist_does_not_modify_scanned_outputs(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    before = _hash_tree(outputs_root)
    result = _run_batch(outputs_root, "--write-report", "--write-remediation-plan", "--write-execution-checklist")
    assert result.returncode == 0, result.stdout
    after = _hash_tree(outputs_root)
    assert before == after

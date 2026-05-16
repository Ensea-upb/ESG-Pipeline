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


def _hash_tree(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and BATCH_DIRNAME not in file_path.parts:
            result[str(file_path.relative_to(path))] = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return result


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


def _remove_evidence_store(output_dir: Path) -> None:
    path = output_dir / "evidence_store.jsonl"
    if path.exists():
        path.unlink()


def _prepare_outputs(require_pdfplumber, small_pdf: Path, tmp_path: Path) -> Path:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir()

    base = tmp_path / "base_output"
    result = run_cli(small_pdf, base, document_id="v13_remediation_base")
    assert result.returncode == 0, result.stderr

    _copy_output(base, outputs_root / "compatible")

    warning = _copy_output(base, outputs_root / "compatible_with_warnings")
    _remove_engine_contract_version(warning)

    migration = _copy_output(base, outputs_root / "migration_required")
    _remove_audit_files(migration)

    incompatible = _copy_output(base, outputs_root / "incompatible")
    _remove_evidence_store(incompatible)
    return outputs_root


def _plan_by_status(plan: dict, status: str) -> dict:
    matches = [row for row in plan["outputs"] if row["compatibility_status"] == status]
    assert len(matches) == 1
    return matches[0]


def test_batch_writes_remediation_files(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-remediation-plan")
    payload = json.loads(result.stdout)

    assert result.returncode == 0, result.stdout
    assert payload["status"] == "success"
    report_dir = outputs_root / BATCH_DIRNAME
    assert (report_dir / "batch_remediation_plan.json").exists()
    assert (report_dir / "batch_remediation_plan.csv").exists()
    assert (report_dir / "batch_remediation_plan.md").exists()


def test_remediation_actions_match_compatibility_statuses(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-remediation-plan")
    assert result.returncode == 0, result.stdout

    plan = read_json(outputs_root / BATCH_DIRNAME / "batch_remediation_plan.json")
    assert _plan_by_status(plan, "compatible")["recommended_action"] == "no_action_needed"
    assert _plan_by_status(plan, "compatible_with_warnings")["recommended_action"] == "annotate_summary_only"
    assert _plan_by_status(plan, "migration_required")["recommended_action"] == "rerun_audit_standalone"
    assert _plan_by_status(plan, "incompatible")["recommended_action"] == "regenerate_with_current_engine"


def test_remediation_rows_contain_required_action_fields(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-remediation-plan")
    assert result.returncode == 0, result.stdout

    plan = read_json(outputs_root / BATCH_DIRNAME / "batch_remediation_plan.json")
    for row in plan["outputs"]:
        assert row["recommended_action"]
        assert row["action_priority"] in {"none", "low", "medium", "high"}
        assert row["action_reason"]
        assert row["minimal_command"]
        assert row["risk_level"] in {"low", "medium", "high"}


def test_remediation_markdown_contains_title(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-remediation-plan")
    assert result.returncode == 0, result.stdout

    markdown = (outputs_root / BATCH_DIRNAME / "batch_remediation_plan.md").read_text(encoding="utf-8")
    assert "Batch Remediation Plan" in markdown
    assert "Ce plan ne modifie aucun output" in markdown


def test_remediation_csv_contains_expected_columns(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    result = _run_batch(outputs_root, "--write-remediation-plan")
    assert result.returncode == 0, result.stdout

    with (outputs_root / BATCH_DIRNAME / "batch_remediation_plan.csv").open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames == [
            "output_dir",
            "document_id",
            "compatibility_status",
            "recommended_action",
            "action_priority",
            "risk_level",
            "action_reason",
            "minimal_command",
        ]
        rows = list(reader)
    assert len(rows) == 4


def test_remediation_plan_does_not_modify_scanned_outputs(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    before = _hash_tree(outputs_root)
    result = _run_batch(outputs_root, "--write-report", "--write-remediation-plan")
    assert result.returncode == 0, result.stdout
    after = _hash_tree(outputs_root)
    assert before == after


def test_remediation_overwrite_guard(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    outputs_root = _prepare_outputs(require_pdfplumber, small_pdf, tmp_path)
    first = _run_batch(outputs_root, "--write-remediation-plan")
    assert first.returncode == 0, first.stdout

    second = _run_batch(outputs_root, "--write-remediation-plan")
    payload = json.loads(second.stdout)
    assert second.returncode != 0
    assert payload["status"] == "failed"

    third = _run_batch(outputs_root, "--write-remediation-plan", "--overwrite")
    assert third.returncode == 0, third.stdout

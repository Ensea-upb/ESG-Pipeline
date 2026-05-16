"""
test_strict_index_pilot_runner_v10.py
======================================
Synthetic-fixture tests for run_strict_index_pilot.py.

All tests use tmp_path fixtures and synthetic data — the real ESG pipeline
is NEVER executed.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

# Ensure the ESG project root is on the path so we can import the script.
ESG_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ESG_ROOT))

import importlib.util

_SCRIPT_PATH = ESG_ROOT / "run_strict_index_pilot.py"


def _load_module():
    """Load run_strict_index_pilot as a module without executing __main__."""
    spec = importlib.util.spec_from_file_location("run_strict_index_pilot", _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_INDEX_FILENAME = "extraction_index_strict_likely_valid.csv"

INDEX_COLUMNS = [
    "company_name",
    "company_slug",
    "fiscal_year",
    "official_doc_type",
    "official_doc_type_label",
    "selected_canonical_document_id",
    "sha256",
    "final_path",
    "final_file_exists",
    "page_count",
    "audit_bucket",
    "audit_priority",
    "validation_status_merged",
    "selection_status",
    "company_name_detected_in_text",
]


def make_index_csv(tmp_path: Path, filename: str = VALID_INDEX_FILENAME, rows: list[dict] | None = None) -> Path:
    """Write a synthetic index CSV and return its path."""
    path = tmp_path / filename
    if rows is None:
        rows = [
            {
                "company_name": "TotalEnergies",
                "company_slug": "totalenergies",
                "fiscal_year": "2024",
                "official_doc_type": "01_urd_annual_report",
                "official_doc_type_label": "URD / annual report",
                "selected_canonical_document_id": "canonical_abc123",
                "sha256": "aabbcc",
                "final_path": str(tmp_path / "fake_doc.pdf"),
                "final_file_exists": "True",
                "page_count": "100",
                "audit_bucket": "KEEP_LIKELY_VALID",
                "audit_priority": "4",
                "validation_status_merged": "likely_valid",
                "selection_status": "selected",
                "company_name_detected_in_text": "True",
            },
            {
                "company_name": "TotalEnergies",
                "company_slug": "totalenergies",
                "fiscal_year": "2024",
                "official_doc_type": "17_cdp_response",
                "official_doc_type_label": "CDP response",
                "selected_canonical_document_id": "canonical_def456",
                "sha256": "ddeeff",
                "final_path": str(tmp_path / "fake_doc2.pdf"),
                "final_file_exists": "True",
                "page_count": "50",
                "audit_bucket": "KEEP_LIKELY_VALID",
                "audit_priority": "4",
                "validation_status_merged": "likely_valid",
                "selection_status": "selected",
                "company_name_detected_in_text": "True",
            },
            {
                "company_name": "Air Liquide",
                "company_slug": "air-liquide",
                "fiscal_year": "2024",
                "official_doc_type": "01_urd_annual_report",
                "official_doc_type_label": "URD / annual report",
                "selected_canonical_document_id": "canonical_ghi789",
                "sha256": "gghhii",
                "final_path": str(tmp_path / "fake_doc3.pdf"),
                "final_file_exists": "True",
                "page_count": "57",
                "audit_bucket": "KEEP_LIKELY_VALID",
                "audit_priority": "4",
                "validation_status_merged": "likely_valid",
                "selection_status": "selected",
                "company_name_detected_in_text": "True",
            },
        ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


# ---------------------------------------------------------------------------
# 1. test_pilot_runner_script_exists
# ---------------------------------------------------------------------------

def test_pilot_runner_script_exists():
    """run_strict_index_pilot.py must exist at the ESG project root."""
    assert _SCRIPT_PATH.exists(), f"Script not found: {_SCRIPT_PATH}"
    assert _SCRIPT_PATH.is_file()


# ---------------------------------------------------------------------------
# 2. test_refuses_non_strict_index
# ---------------------------------------------------------------------------

def test_refuses_non_strict_index(tmp_path):
    """A CSV named 'extraction_index_large.csv' must be refused."""
    bad_index = make_index_csv(tmp_path, filename="extraction_index_large.csv")
    mod = _load_module()

    with pytest.raises((SystemExit, ValueError)) as exc_info:
        mod.main([
            "--index-path", str(bad_index),
            "--output-root", str(tmp_path / "out"),
            "--max-documents", "5",
        ])

    # SystemExit with non-zero code, or ValueError
    if isinstance(exc_info.value, SystemExit):
        assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# 3. test_requires_max_documents_for_execute
# ---------------------------------------------------------------------------

def test_requires_max_documents_for_execute(tmp_path):
    """--execute without --max-documents must raise SystemExit."""
    index = make_index_csv(tmp_path)
    mod = _load_module()

    with pytest.raises(SystemExit) as exc_info:
        mod.main([
            "--index-path", str(index),
            "--output-root", str(tmp_path / "out"),
            "--execute",
            # no --max-documents
        ])

    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# 4. test_refuses_too_many_documents
# ---------------------------------------------------------------------------

def test_refuses_too_many_documents(tmp_path):
    """--max-documents=25 must raise SystemExit (hard limit is 20)."""
    index = make_index_csv(tmp_path)
    mod = _load_module()

    with pytest.raises(SystemExit) as exc_info:
        mod.main([
            "--index-path", str(index),
            "--output-root", str(tmp_path / "out"),
            "--max-documents", "25",
        ])

    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# 5. test_dry_run_default_no_subprocess
# ---------------------------------------------------------------------------

def test_dry_run_default_no_subprocess(tmp_path, monkeypatch):
    """
    Without --execute:
    - pilot_run_summary.json produced with dry_run=True
    - documents_processed == 0
    - no real subprocess launched
    """
    index = make_index_csv(tmp_path)
    out = tmp_path / "out"
    mod = _load_module()

    # Patch subprocess.run to detect any accidental call
    called = []

    def fake_run(*args, **kwargs):
        called.append(args)
        raise AssertionError("subprocess.run must NOT be called in dry-run mode")

    monkeypatch.setattr("subprocess.run", fake_run)

    mod.main([
        "--index-path", str(index),
        "--output-root", str(out),
        "--max-documents", "5",
    ])

    summary_path = out / "pilot_run_summary.json"
    assert summary_path.exists(), "pilot_run_summary.json must be produced"

    with summary_path.open(encoding="utf-8") as fh:
        summary = json.load(fh)

    assert summary["dry_run"] is True
    assert summary["execute"] is False
    assert summary["documents_processed"] == 0
    assert not called, "subprocess.run must not be called in dry-run mode"


# ---------------------------------------------------------------------------
# 6. test_loads_and_filters_by_company_slug
# ---------------------------------------------------------------------------

def test_loads_and_filters_by_company_slug(tmp_path):
    """Filtering by company_slug='totalenergies' should yield 2 rows."""
    index = make_index_csv(tmp_path)  # 3 rows: 2 totalenergies, 1 air-liquide
    mod = _load_module()

    rows = mod.load_index(index)
    selected, skipped = mod.filter_documents(
        rows,
        company_slug="totalenergies",
        fiscal_year=None,
        doc_type=None,
        max_documents=None,
    )

    assert len(selected) == 2
    assert all(r["company_slug"] == "totalenergies" for r in selected)
    assert len(skipped) == 1
    assert skipped[0]["company_slug"] == "air-liquide"


# ---------------------------------------------------------------------------
# 7. test_skips_missing_files
# ---------------------------------------------------------------------------

def test_skips_missing_files(tmp_path):
    """Rows with final_file_exists='False' must be excluded from selection."""
    rows_data = [
        {
            "company_name": "Company A",
            "company_slug": "company-a",
            "fiscal_year": "2024",
            "official_doc_type": "01_urd_annual_report",
            "official_doc_type_label": "URD",
            "selected_canonical_document_id": "canonical_1",
            "sha256": "aa",
            "final_path": "/nonexistent/a.pdf",
            "final_file_exists": "True",
            "page_count": "10",
            "audit_bucket": "KEEP",
            "audit_priority": "4",
            "validation_status_merged": "valid",
            "selection_status": "selected",
            "company_name_detected_in_text": "True",
        },
        {
            "company_name": "Company B",
            "company_slug": "company-b",
            "fiscal_year": "2024",
            "official_doc_type": "01_urd_annual_report",
            "official_doc_type_label": "URD",
            "selected_canonical_document_id": "canonical_2",
            "sha256": "bb",
            "final_path": "/nonexistent/b.pdf",
            "final_file_exists": "False",
            "page_count": "20",
            "audit_bucket": "KEEP",
            "audit_priority": "4",
            "validation_status_merged": "valid",
            "selection_status": "selected",
            "company_name_detected_in_text": "True",
        },
    ]
    index = make_index_csv(tmp_path, rows=rows_data)
    mod = _load_module()

    rows = mod.load_index(index)
    selected, skipped = mod.filter_documents(rows, None, None, None, None)

    assert len(selected) == 1
    assert selected[0]["company_slug"] == "company-a"
    assert len(skipped) == 1
    assert skipped[0]["company_slug"] == "company-b"


# ---------------------------------------------------------------------------
# 8. test_prepare_review_does_not_auto_accept
# ---------------------------------------------------------------------------

def test_prepare_review_does_not_auto_accept():
    """
    The script source code must never generate proposed_decision='accept_candidate'.
    Inspect source for the forbidden pattern.
    """
    source = _SCRIPT_PATH.read_text(encoding="utf-8")

    # The string "accept_candidate" must not appear as an assigned value
    # The only permissible occurrence is inside a comment or docstring
    # explaining the prohibition (which we explicitly check for as well).

    # Look specifically for assignment patterns — not mere mentions in comments/docstrings
    forbidden_assignment_patterns = [
        '= "accept_candidate"',
        "= 'accept_candidate'",
    ]

    for line in source.splitlines():
        stripped = line.strip()
        # Skip pure comment lines
        if stripped.startswith("#"):
            continue
        for pattern in forbidden_assignment_patterns:
            if pattern in stripped:
                pytest.fail(
                    f"Found forbidden auto-accept assignment '{pattern}' in source line: {stripped!r}"
                )


# ---------------------------------------------------------------------------
# 9. test_top_review_candidates_generation
# ---------------------------------------------------------------------------

def test_top_review_candidates_generation(tmp_path):
    """
    build_top_review_candidates should sort possible_indicator before needs_review.
    """
    mod = _load_module()

    workspace_dir = tmp_path / "04_review_workspace"
    workspace_dir.mkdir()

    workspace_csv = workspace_dir / "manual_review_workspace.csv"
    workspace_rows = [
        {
            "company": "TotalEnergies",
            "fiscal_year": "2024",
            "document_id": "canonical_abc",
            "official_doc_type": "01_urd_annual_report",
            "page_number": "12",
            "indicator_family": "environment",
            "indicator_key_candidate": "ghg_scope1",
            "raw_value": "123",
            "raw_unit": "tCO2",
            "normalized_value": "123000",
            "normalized_unit": "kgCO2",
            "quote": "Emissions were 123 tCO2",
            "review_status": "needs_review",
        },
        {
            "company": "TotalEnergies",
            "fiscal_year": "2024",
            "document_id": "canonical_abc",
            "official_doc_type": "01_urd_annual_report",
            "page_number": "8",
            "indicator_family": "environment",
            "indicator_key_candidate": "energy_consumption",
            "raw_value": "500",
            "raw_unit": "GWh",
            "normalized_value": "500",
            "normalized_unit": "GWh",
            "quote": "Energy consumed was 500 GWh",
            "review_status": "possible_indicator",
        },
    ]
    with workspace_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(workspace_rows[0].keys()))
        writer.writeheader()
        writer.writerows(workspace_rows)

    output_csv = tmp_path / "top_review_candidates.csv"
    row_meta = {
        "company_name": "TotalEnergies",
        "fiscal_year": "2024",
        "selected_canonical_document_id": "canonical_abc",
        "official_doc_type": "01_urd_annual_report",
    }

    summary = mod.build_top_review_candidates(workspace_dir, row_meta, output_csv)

    assert output_csv.exists()
    assert summary["nb_candidates"] == 2
    assert summary["nb_possible_indicator"] == 1
    assert summary["nb_needs_review"] == 1

    # Check ordering: possible_indicator must come first
    with output_csv.open(newline="", encoding="utf-8") as fh:
        result_rows = list(csv.DictReader(fh))

    assert len(result_rows) == 2
    assert result_rows[0]["indicator_key_candidate"] == "energy_consumption"  # possible_indicator
    assert result_rows[1]["indicator_key_candidate"] == "ghg_scope1"           # needs_review


# ---------------------------------------------------------------------------
# 10. test_apply_review_requires_decisions_root
# ---------------------------------------------------------------------------

def test_apply_review_requires_decisions_root(tmp_path):
    """mode=apply-review-and-build-dataset without --decisions-root must raise SystemExit."""
    index = make_index_csv(tmp_path)
    mod = _load_module()

    with pytest.raises(SystemExit) as exc_info:
        mod.main([
            "--index-path", str(index),
            "--output-root", str(tmp_path / "out"),
            "--max-documents", "5",
            "--mode", "apply-review-and-build-dataset",
            # no --decisions-root
        ])

    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# 11. test_summary_schema_keys
# ---------------------------------------------------------------------------

def test_summary_schema_keys(tmp_path):
    """pilot_run_summary.json must contain all required schema keys."""
    index = make_index_csv(tmp_path)
    out = tmp_path / "out"
    mod = _load_module()

    mod.main([
        "--index-path", str(index),
        "--output-root", str(out),
        "--max-documents", "5",
    ])

    summary_path = out / "pilot_run_summary.json"
    assert summary_path.exists()

    with summary_path.open(encoding="utf-8") as fh:
        summary = json.load(fh)

    required_keys = [
        "corpus_run_id",
        "mode",
        "dry_run",
        "execute",
        "max_documents",
        "documents_selected",
        "documents_processed",
        "documents_success",
        "documents_failed",
        "documents_skipped",
        "review_workspaces_produced",
        "indicator_databases_produced",
        "variable_dataset_produced",
        "found_values_count",
        "per_document",
        "output_root",
    ]
    for key in required_keys:
        assert key in summary, f"Missing key in pilot_run_summary.json: '{key}'"


# ---------------------------------------------------------------------------
# 12. test_subprocess_uses_sys_executable
# ---------------------------------------------------------------------------

def test_subprocess_uses_sys_executable():
    """
    Every subprocess call in the script source must use sys.executable.
    Hard-coded 'python' or 'python3' strings in command lists are forbidden.
    """
    source = _SCRIPT_PATH.read_text(encoding="utf-8")

    forbidden_patterns = [
        '"python"',
        "'python'",
        '"python3"',
        "'python3'",
    ]

    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pattern in forbidden_patterns:
            if pattern in stripped:
                pytest.fail(
                    f"Hard-coded Python executable found in source line: {stripped!r}\n"
                    "Use sys.executable instead."
                )


# ---------------------------------------------------------------------------
# Helpers for contract-path tests
# ---------------------------------------------------------------------------

def _make_row(tmp_path: Path) -> dict:
    return {
        "company_name": "Test Company",
        "company_slug": "test-co",
        "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report",
        "selected_canonical_document_id": "canonical_test001",
        "final_path": str(tmp_path / "doc.pdf"),
    }


def _capture_run_step(mod, monkeypatch):
    """Monkeypatch run_step to capture (step_name, cmd_list) tuples and always succeed."""
    captured = []

    def fake_run_step(step_name, cmd, log_file, cmd_log, dry_run):
        captured.append((step_name, [str(c) for c in cmd]))
        return True, ""

    monkeypatch.setattr(mod, "run_step", fake_run_step)
    return captured


def _find_validator_cmd(captured: list, step_name_fragment: str) -> list[str]:
    """Return the cmd list for the first captured step whose name contains the fragment."""
    for name, cmd in captured:
        if step_name_fragment in name:
            return cmd
    return []


# ---------------------------------------------------------------------------
# 13. test_information_extraction_validator_has_contract_path
# ---------------------------------------------------------------------------

def test_information_extraction_validator_has_contract_path(tmp_path, monkeypatch):
    """validate_output_contract must be called with --contract-path output_contract_v1.json."""
    mod = _load_module()
    captured = _capture_run_step(mod, monkeypatch)

    row = _make_row(tmp_path)
    cmd_log = mod.CommandLog(tmp_path / "log.jsonl")

    mod.step_01_information_extraction(
        row, tmp_path / "doc_out", "pilot_test", None, False, cmd_log, dry_run=True
    )

    val_cmd = _find_validator_cmd(captured, "01_validate_output_contract")
    assert val_cmd, "01_validate_output_contract step was not called"

    cmd_str = " ".join(val_cmd)
    assert "validate_output_contract.py" in cmd_str, f"Script not found in: {cmd_str}"
    assert "--output-dir" in cmd_str, f"--output-dir not found in: {cmd_str}"
    assert "--contract-path" in cmd_str, f"--contract-path missing from validator call: {cmd_str}"
    assert "output_contract_v1.json" in cmd_str, f"output_contract_v1.json not found in: {cmd_str}"


# ---------------------------------------------------------------------------
# 14. test_orchestrator_validator_has_contract_path
# ---------------------------------------------------------------------------

def test_orchestrator_validator_has_contract_path(tmp_path, monkeypatch):
    """validate_full_extraction_outputs must be called with --contract-path full_extraction_output_contract_v0.json."""
    mod = _load_module()
    captured = _capture_run_step(mod, monkeypatch)

    row = _make_row(tmp_path)
    cmd_log = mod.CommandLog(tmp_path / "log.jsonl")

    mod.step_02_orchestrator(row, tmp_path / "doc_out", False, cmd_log, dry_run=True)

    val_cmd = _find_validator_cmd(captured, "02_validate_full_extraction")
    assert val_cmd, "02_validate_full_extraction step was not called"

    cmd_str = " ".join(val_cmd)
    assert "validate_full_extraction_outputs.py" in cmd_str, f"Script not found in: {cmd_str}"
    assert "--contract-path" in cmd_str, f"--contract-path missing from validator call: {cmd_str}"
    assert "full_extraction_output_contract_v0.json" in cmd_str, f"Contract file not found in: {cmd_str}"


# ---------------------------------------------------------------------------
# 15. test_indicator_validation_validator_has_contract_path
# ---------------------------------------------------------------------------

def test_indicator_validation_validator_has_contract_path(tmp_path, monkeypatch):
    """validate_indicator_validation_outputs must be called with --contract-path indicator_validation_contract_v0.json."""
    mod = _load_module()
    captured = _capture_run_step(mod, monkeypatch)

    row = _make_row(tmp_path)
    cmd_log = mod.CommandLog(tmp_path / "log.jsonl")

    mod.step_03_indicator_validation(row, tmp_path / "doc_out", False, cmd_log, dry_run=True)

    val_cmd = _find_validator_cmd(captured, "03_validate_indicator_validation")
    assert val_cmd, "03_validate_indicator_validation step was not called"

    cmd_str = " ".join(val_cmd)
    assert "validate_indicator_validation_outputs.py" in cmd_str, f"Script not found in: {cmd_str}"
    assert "--contract-path" in cmd_str, f"--contract-path missing from validator call: {cmd_str}"
    assert "indicator_validation_contract_v0.json" in cmd_str, f"Contract file not found in: {cmd_str}"


# ---------------------------------------------------------------------------
# 16. test_manual_review_validator_has_contract_path
# ---------------------------------------------------------------------------

def test_manual_review_validator_has_contract_path(tmp_path, monkeypatch):
    """validate_manual_review_outputs must be called with --contract-path manual_review_contract_v0.json."""
    mod = _load_module()
    captured = _capture_run_step(mod, monkeypatch)

    row = _make_row(tmp_path)
    cmd_log = mod.CommandLog(tmp_path / "log.jsonl")
    decisions_file = tmp_path / "decisions.csv"

    mod.step_05_apply_review(row, tmp_path / "doc_out", decisions_file, False, cmd_log, dry_run=True)

    val_cmd = _find_validator_cmd(captured, "05_validate_manual_review")
    assert val_cmd, "05_validate_manual_review step was not called"

    cmd_str = " ".join(val_cmd)
    assert "validate_manual_review_outputs.py" in cmd_str, f"Script not found in: {cmd_str}"
    assert "--contract-path" in cmd_str, f"--contract-path missing from validator call: {cmd_str}"
    assert "manual_review_contract_v0.json" in cmd_str, f"Contract file not found in: {cmd_str}"


# ---------------------------------------------------------------------------
# 17. test_indicator_database_validator_has_contract_path
# ---------------------------------------------------------------------------

def test_indicator_database_validator_has_contract_path(tmp_path, monkeypatch):
    """validate_indicator_database_outputs must be called with --contract-path indicator_database_contract_v0.json."""
    mod = _load_module()
    captured = _capture_run_step(mod, monkeypatch)

    row = _make_row(tmp_path)
    cmd_log = mod.CommandLog(tmp_path / "log.jsonl")

    mod.step_06_indicator_database(row, tmp_path / "doc_out", False, cmd_log, dry_run=True)

    val_cmd = _find_validator_cmd(captured, "06_validate_indicator_database")
    assert val_cmd, "06_validate_indicator_database step was not called"

    cmd_str = " ".join(val_cmd)
    assert "validate_indicator_database_outputs.py" in cmd_str, f"Script not found in: {cmd_str}"
    assert "--contract-path" in cmd_str, f"--contract-path missing from validator call: {cmd_str}"
    assert "indicator_database_contract_v0.json" in cmd_str, f"Contract file not found in: {cmd_str}"


# ---------------------------------------------------------------------------
# 18. test_variable_dataset_validator_has_contract_path
# ---------------------------------------------------------------------------

def test_variable_dataset_validator_has_contract_path(tmp_path, monkeypatch):
    """validate_esg_variables_dataset must be called with --contract-path esg_variables_dataset_contract_v0.json."""
    mod = _load_module()
    captured = _capture_run_step(mod, monkeypatch)

    cmd_log = mod.CommandLog(tmp_path / "log.jsonl")

    mod.step_08_variable_dataset(tmp_path / "output_root", False, cmd_log, dry_run=True)

    val_cmd = _find_validator_cmd(captured, "08_validate_variable_dataset")
    assert val_cmd, "08_validate_variable_dataset step was not called"

    cmd_str = " ".join(val_cmd)
    assert "validate_esg_variables_dataset.py" in cmd_str, f"Script not found in: {cmd_str}"
    assert "--contract-path" in cmd_str, f"--contract-path missing from validator call: {cmd_str}"
    assert "esg_variables_dataset_contract_v0.json" in cmd_str, f"Contract file not found in: {cmd_str}"

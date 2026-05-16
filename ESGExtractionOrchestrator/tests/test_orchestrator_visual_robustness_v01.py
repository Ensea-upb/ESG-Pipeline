"""
test_orchestrator_visual_robustness_v01.py
==========================================
Tests for ESGExtractionOrchestrator resilience when visual crops fail.

- Orchestrator continues with CSV and Table when visual has warnings.
- consolidated_candidates.csv is always produced.
- engine_run_manifest records the visual status accurately.
- Existing outputs still pass the contract.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .helpers import CONTRACT, make_input, read_json, run_full, validate


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# 3. test_orchestrator_continues_when_visual_crop_missing
# ---------------------------------------------------------------------------

def test_orchestrator_continues_when_visual_crop_missing(tmp_path: Path):
    """
    Even when visual crop rendering fails (placeholder PDF cannot be rendered),
    the orchestrator must:
    - return rc=0
    - produce consolidated_candidates.csv
    - include CSV candidates in consolidated output
    - not fail the whole document
    """
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_full(input_dir, output_dir)

    assert result.returncode == 0, (
        f"Orchestrator must not fail when visual crops cannot be rendered.\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )

    # consolidated_candidates.csv must always be produced
    consolidated_csv = output_dir / "consolidated_candidates.csv"
    assert consolidated_csv.exists(), "consolidated_candidates.csv must be produced"

    rows = _read_csv(consolidated_csv)
    assert rows, "consolidated_candidates.csv must not be empty"

    # CSV engine candidates must be present
    source_engines = {row.get("source_engine") for row in rows}
    assert "csv" in source_engines, (
        f"CSV candidates must be in consolidated output. Found engines: {source_engines}"
    )


# ---------------------------------------------------------------------------
# 4. test_engine_manifest_records_visual_warning
# ---------------------------------------------------------------------------

def test_engine_manifest_records_visual_status(tmp_path: Path):
    """
    engine_run_manifest['visual']['status'] must be a valid status.
    If the visual engine had warnings, status should be 'warning'.
    Otherwise 'ran' or 'reused_existing'.
    """
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_full(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    summary = read_json(output_dir / "full_extraction_summary.json")
    manifest = summary.get("engine_run_manifest", {})
    assert "visual" in manifest, "engine_run_manifest must contain 'visual' entry"

    visual_entry = manifest["visual"]
    valid_statuses = {"ran", "reran", "reused_existing", "warning", "partial"}
    assert visual_entry["status"] in valid_statuses, (
        f"visual engine status must be one of {valid_statuses}, got: {visual_entry['status']}"
    )
    assert "candidates_count" in visual_entry, "visual entry must have candidates_count"


def test_engine_manifest_visual_warning_has_warning_field(tmp_path: Path):
    """
    When visual status is 'warning', the manifest entry must include a 'warning' field.
    """
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_full(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    summary = read_json(output_dir / "full_extraction_summary.json")
    manifest = summary.get("engine_run_manifest", {})
    visual_entry = manifest.get("visual", {})

    if visual_entry.get("status") == "warning":
        assert "warning" in visual_entry, (
            "When visual status is 'warning', a 'warning' field must describe the issue"
        )


# ---------------------------------------------------------------------------
# 5. test_existing_visual_outputs_still_pass_contract
# ---------------------------------------------------------------------------

def test_existing_orchestrator_outputs_still_pass_contract(tmp_path: Path):
    """Orchestrator outputs must still pass the full extraction contract after the fix."""
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_full(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    validation = validate(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode == 0, (
        f"Contract validation failed after visual robustness fix.\n"
        f"stdout={validation.stdout}\nstderr={validation.stderr}"
    )
    assert payload["status"] == "success"


def test_full_extraction_summary_contains_visual_candidates_count(tmp_path: Path):
    """full_extraction_summary.json must have visual_candidates_count (even if 0)."""
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_full(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    summary = read_json(output_dir / "full_extraction_summary.json")
    assert "visual_candidates_count" in summary
    assert isinstance(summary["visual_candidates_count"], int)
    assert summary["visual_candidates_count"] >= 0

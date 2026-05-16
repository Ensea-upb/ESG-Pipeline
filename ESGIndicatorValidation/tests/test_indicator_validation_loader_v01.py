from __future__ import annotations

import json
from pathlib import Path

from .helpers import hash_tree, make_orchestrator_output, run_validation


def test_cli_produces_core_files_and_preserves_input(tmp_path: Path):
    input_dir = make_orchestrator_output(tmp_path)
    before = hash_tree(input_dir)
    output_dir = tmp_path / "out"
    result = run_validation(input_dir, output_dir, "--overwrite")
    assert result.returncode == 0, result.stdout
    for name in [
        "indicator_candidate_validations.csv",
        "indicator_candidate_validations.jsonl",
        "indicator_validation_audit_summary.json",
        "indicator_validation_audit_findings.jsonl",
        "indicator_validation_summary.json",
    ]:
        assert (output_dir / name).exists()
    assert before == hash_tree(input_dir)


def test_missing_input_fails_cleanly(tmp_path: Path):
    input_dir = tmp_path / "empty"
    input_dir.mkdir()
    result = run_validation(input_dir, tmp_path / "out", "--overwrite")
    assert result.returncode != 0
    assert json.loads(result.stdout)["status"] == "failed"

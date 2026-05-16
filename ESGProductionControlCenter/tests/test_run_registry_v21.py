"""
test_run_registry_v21.py
========================
Tests for run discovery — verifies that discover_runs() finds both legacy
EXTERNAL_AUDIT_RUNS format and new audit_e2e_*/audit_batch_* format.
"""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ESGProductionControlCenter.src.esg_production_control_center.run_registry import (
    discover_runs,
    get_default_run_root,
    resolve_run_root,
)


class TestDiscoverRuns:
    def test_returns_list(self, tmp_path):
        result = discover_runs(tmp_path)
        assert isinstance(result, list)

    def test_empty_when_no_runs(self, tmp_path):
        result = discover_runs(tmp_path)
        assert result == []

    def test_finds_legacy_audit_run(self, tmp_path):
        d = tmp_path / "EXTERNAL_AUDIT_RUNS" / "my_run_v1"
        d.mkdir(parents=True)
        (d / "pilot_run_summary.json").write_text("{}", encoding="utf-8")
        result = discover_runs(tmp_path)
        assert "EXTERNAL_AUDIT_RUNS/my_run_v1" in result

    def test_finds_audit_e2e_with_metric_candidates(self, tmp_path):
        d = tmp_path / "audit_e2e_v5"
        d.mkdir()
        (d / "metric_candidates.jsonl").write_text('{"metric_id":"ghg_scope_1"}\n', encoding="utf-8")
        result = discover_runs(tmp_path)
        assert "audit_e2e_v5" in result

    def test_finds_audit_batch_with_recall_report(self, tmp_path):
        d = tmp_path / "audit_batch_v1"
        d.mkdir()
        (d / "recall_report.json").write_text('{"recall_metric_level": 1.0}', encoding="utf-8")
        result = discover_runs(tmp_path)
        assert "audit_batch_v1" in result

    def test_does_not_find_dir_without_marker_files(self, tmp_path):
        (tmp_path / "audit_e2e_incomplete").mkdir()
        result = discover_runs(tmp_path)
        assert "audit_e2e_incomplete" not in result

    def test_ignores_non_audit_dirs(self, tmp_path):
        (tmp_path / "random_dir").mkdir()
        result = discover_runs(tmp_path)
        assert "random_dir" not in result


class TestResolveRunRoot:
    def test_absolute_path_returned_as_is(self, tmp_path):
        result = resolve_run_root(tmp_path, str(tmp_path))
        assert result == tmp_path

    def test_relative_path_resolved_against_project_root(self, tmp_path):
        result = resolve_run_root(tmp_path, "audit_e2e_v5")
        assert result == tmp_path / "audit_e2e_v5"

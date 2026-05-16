from __future__ import annotations

import subprocess
from pathlib import Path

from tools.run_project_validation import run_step, run_validation


def test_run_step_reports_failed_mock_command(tmp_path: Path) -> None:
    def failing_runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 7, stdout="out", stderr="boom")

    step = run_step("mock_failure", ["mock"], tmp_path, runner=failing_runner)

    assert step.status == "failed"
    assert step.returncode == 7
    assert "boom" in step.stderr_tail


def test_run_validation_writes_reports_with_mock_runner(tmp_path: Path) -> None:
    def passing_runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    json_report = tmp_path / "summary.json"
    md_report = tmp_path / "report.md"
    steps = run_validation(
        project_root=tmp_path,
        full=False,
        skip_retrievers=True,
        json_report=json_report,
        markdown_report=md_report,
        runner=passing_runner,
    )

    assert steps
    assert json_report.exists()
    assert md_report.exists()

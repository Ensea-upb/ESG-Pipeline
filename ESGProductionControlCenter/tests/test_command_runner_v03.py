import sys

from ESGProductionControlCenter.src.esg_production_control_center.command_runner import run_command


def test_dry_run_does_not_execute(tmp_path):
    plan = {"module_name": "mock", "command": [sys.executable, "-c", "raise SystemExit(2)"], "dry_run": True}
    state = run_command(plan, tmp_path, allow_execute=False)
    assert state["status"] == "dry_run"
    assert (tmp_path / state["run_id"] / "run_state.json").exists()


def test_mock_success_and_failure_capture_logs(tmp_path):
    ok = run_command({"module_name": "mock", "command": [sys.executable, "-c", "print('ok')"], "dry_run": False}, tmp_path, allow_execute=True)
    bad = run_command({"module_name": "mock", "command": [sys.executable, "-c", "import sys; print('bad', file=sys.stderr); raise SystemExit(3)"], "dry_run": False}, tmp_path, allow_execute=True)
    assert ok["status"] == "success"
    assert bad["status"] == "failed"


def test_timeout(tmp_path):
    state = run_command({"module_name": "mock", "command": [sys.executable, "-c", "import time; time.sleep(2)"], "dry_run": False}, tmp_path, allow_execute=True, timeout_seconds=1)
    assert state["status"] == "timeout"

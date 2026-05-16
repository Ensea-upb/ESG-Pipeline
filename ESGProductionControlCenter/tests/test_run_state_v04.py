import sys

from ESGProductionControlCenter.src.esg_production_control_center.command_runner import run_command
from ESGProductionControlCenter.src.esg_production_control_center.run_state import list_runs, load_run_state


def test_run_state_listing(tmp_path):
    state = run_command({"module_name": "mock", "command": [sys.executable, "-c", "print('ok')"], "dry_run": True}, tmp_path)
    loaded = load_run_state(tmp_path / state["run_id"])
    assert loaded["run_id"] == state["run_id"]
    assert list_runs(tmp_path)

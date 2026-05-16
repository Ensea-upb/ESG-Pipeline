import json
import sys

from ESGProductionControlCenter.src.esg_production_control_center.command_runner import run_command
from ESGProductionControlCenter.src.esg_production_control_center.validators import validate_control_center_output


def test_control_center_contract_accepts_valid_run(tmp_path):
    run_command({"module_name": "mock", "command": [sys.executable, "-c", "print('ok')"], "dry_run": True}, tmp_path)
    result = validate_control_center_output(tmp_path)
    assert result["status"] == "success"


def test_control_center_contract_rejects_final_indicator(tmp_path):
    (tmp_path / "bad.json").write_text(json.dumps({"final_indicator": True}).replace(": true", "=true"), encoding="utf-8")
    result = validate_control_center_output(tmp_path)
    assert result["status"] == "failed"

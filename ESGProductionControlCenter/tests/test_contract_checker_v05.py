import json

from ESGProductionControlCenter.src.esg_production_control_center.contract_checker import write_contract_results


def test_contract_result_summary_blocks_failed(tmp_path):
    result = {"module_name": "mock", "validation_status": "failed", "errors_count": 1, "warnings_count": 0}
    files = write_contract_results(tmp_path, [result], overwrite=True)
    summary = json.loads((tmp_path / "contract_validation_summary.json").read_text())
    assert summary["failed_count"] == 1
    assert len(files) == 2

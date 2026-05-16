from pathlib import Path

from ESGProductionControlCenter.src.esg_production_control_center.output_discovery import discover_outputs, write_discovery_outputs


def test_discovery_detects_outputs_and_writes_reports(tmp_path):
    outputs = discover_outputs(".")
    assert outputs
    assert all(o["module_name"] and o["output_dir"] for o in outputs)
    files = write_discovery_outputs(tmp_path, outputs, overwrite=True)
    assert (tmp_path / "control_center_inventory.json").exists()
    assert (tmp_path / "discovered_outputs.jsonl").exists()
    assert (tmp_path / "discovery_summary.json").exists()
    assert len(files) == 3


def test_discovery_handles_missing_project(tmp_path):
    outputs = discover_outputs(tmp_path)
    assert outputs == []

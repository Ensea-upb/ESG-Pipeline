import json

from ESGProductionControlCenter.src.esg_production_control_center.audit import write_batch_summary


def test_batch_summary_outputs(tmp_path):
    rows = [{"document_id": "d1", "input_dir": "input", "status": "dry_run", "run_id": "r1"}]
    files = write_batch_summary(tmp_path, rows, overwrite=True)
    assert (tmp_path / "batch_production_summary.json").exists()
    assert (tmp_path / "batch_production_table.csv").exists()
    assert (tmp_path / "batch_production_report.md").exists()
    assert (tmp_path / "batch_run_log.jsonl").exists()
    assert json.loads((tmp_path / "batch_production_summary.json").read_text())["documents_count"] == 1

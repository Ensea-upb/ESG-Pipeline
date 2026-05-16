import json

from .helpers import make_manual_review_output, run_build


def test_lineage_traces_corrections(tmp_path):
    out = tmp_path / "out"
    assert run_build(make_manual_review_output(tmp_path), out, "--overwrite").returncode == 0
    lines = [json.loads(line) for line in (out / "indicator_lineage.jsonl").read_text(encoding="utf-8").splitlines()]
    assert lines[0]["lineage_complete"] is True
    assert "corrected_value" in lines[0]["corrections_applied"]
    assert "ESGManualReview" in lines[0]["source_modules"]

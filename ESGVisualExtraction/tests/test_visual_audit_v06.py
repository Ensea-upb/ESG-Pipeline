from __future__ import annotations

from pathlib import Path

from .helpers import hash_tree, make_visual_input, read_json, read_jsonl, run_visual


def test_visual_audit_outputs_exist_and_have_findings(tmp_path: Path):
    input_dir = make_visual_input(tmp_path)
    before = hash_tree(input_dir)
    output_dir = tmp_path / "out"
    result = run_visual(input_dir, output_dir)
    assert result.returncode == 0, result.stdout
    assert (output_dir / "visual_audit_summary.json").exists()
    assert (output_dir / "visual_audit_findings.jsonl").exists()
    assert (output_dir / "visual_audit_samples.csv").exists()
    summary = read_json(output_dir / "visual_audit_summary.json")
    findings = read_jsonl(output_dir / "visual_audit_findings.jsonl")
    assert summary["checks_count"] == len(findings)
    assert {row["check_name"] for row in findings} >= {
        "confidence_above_0_5",
        "review_required_missing_or_false",
        "visual_type_unknown",
    }
    assert before == hash_tree(input_dir)

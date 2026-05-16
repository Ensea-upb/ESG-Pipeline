from .helpers import make_orchestrator_output, read_csv, read_json, run_validation


def test_deduplication_outputs(tmp_path):
    out = tmp_path / "out"
    assert run_validation(make_orchestrator_output(tmp_path), out, "--overwrite").returncode == 0
    assert (out / "indicator_duplicate_groups.jsonl").exists()
    assert (out / "indicator_candidate_validations_deduplicated.csv").exists()
    summary = read_json(out / "indicator_deduplication_summary.json")
    rows = read_csv(out / "indicator_candidate_validations.csv")
    dedup = read_csv(out / "indicator_candidate_validations_deduplicated.csv")
    assert summary["duplicate_groups_count"] >= 1
    assert len(dedup) < len(rows)
    assert sum(1 for row in rows if row["duplicate_status"] == "canonical") == summary["duplicate_groups_count"]

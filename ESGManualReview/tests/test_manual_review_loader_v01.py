import json

from .helpers import hash_tree, make_indicator_output, read_csv, run_build


def test_loader_outputs_and_non_destructive(tmp_path):
    inp = make_indicator_output(tmp_path)
    before = hash_tree(inp)
    out = tmp_path / "workspace"
    result = run_build(inp, out, "--overwrite")
    assert result.returncode == 0, result.stdout
    assert (out / "manual_review_input_inventory.json").exists()
    assert (out / "manual_review_loaded_candidates.csv").exists()
    assert (out / "manual_review_loaded_candidates.jsonl").exists()
    assert (out / "manual_review_summary.json").exists()
    rows = read_csv(out / "manual_review_loaded_candidates.csv")
    assert all(row["candidate_id"] for row in rows)
    assert all(row["quote"] for row in rows)
    assert before == hash_tree(inp)


def test_missing_critical_file_fails_cleanly(tmp_path):
    inp = make_indicator_output(tmp_path)
    (inp / "possible_indicators.csv").unlink()
    result = run_build(inp, tmp_path / "out", "--overwrite")
    assert result.returncode != 0
    assert json.loads(result.stdout)["status"] == "failed"

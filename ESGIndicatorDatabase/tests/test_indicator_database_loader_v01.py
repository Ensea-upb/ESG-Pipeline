import json

from .helpers import hash_tree, make_manual_review_output, read_csv, run_build


def test_loader_and_empty_accepted_file(tmp_path):
    inp = make_manual_review_output(tmp_path, accepted=False)
    before = hash_tree(inp)
    out = tmp_path / "out"
    result = run_build(inp, out, "--overwrite")
    assert result.returncode == 0, result.stdout
    assert (out / "indicator_database_input_inventory.json").exists()
    assert (out / "accepted_candidates_loaded.csv").exists()
    assert (out / "accepted_candidates_loaded.jsonl").exists()
    assert (out / "indicator_database_summary.json").exists()
    assert read_csv(out / "indicator_preparation_database.csv") == []
    assert before == hash_tree(inp)


def test_missing_input_fails_cleanly(tmp_path):
    inp = make_manual_review_output(tmp_path)
    (inp / "accepted_candidate_inputs.csv").unlink()
    result = run_build(inp, tmp_path / "out", "--overwrite")
    assert result.returncode != 0
    assert json.loads(result.stdout)["status"] == "failed"

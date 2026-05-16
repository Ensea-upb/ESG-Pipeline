from .helpers import make_invalid_orchestrator_output, make_orchestrator_output, read_csv, run_validation


def test_status_files_are_coherent(tmp_path):
    out = tmp_path / "out"
    assert run_validation(make_orchestrator_output(tmp_path), out, "--overwrite").returncode == 0
    possible = read_csv(out / "possible_indicators.csv")
    rejected = read_csv(out / "rejected_candidates.csv")
    queue = read_csv(out / "validation_review_queue.csv")
    assert possible
    assert all(row["validation_status"] == "possible_indicator" for row in possible)
    assert all(row["validation_status"] == "reject_candidate" for row in rejected)
    assert all(row["validation_status"] in {"needs_review", "possible_indicator", "reject_candidate"} for row in queue)
    assert all(row["is_validated_indicator"] == "False" and row["score_produced"] == "False" for row in queue)


def test_missing_quote_and_score_are_rejected(tmp_path):
    out = tmp_path / "out"
    assert run_validation(make_invalid_orchestrator_output(tmp_path, quote=""), out, "--overwrite").returncode == 0
    rows = read_csv(out / "indicator_candidate_validations.csv")
    assert rows[0]["validation_status"] == "reject_candidate"

    out2 = tmp_path / "out2"
    assert run_validation(make_invalid_orchestrator_output(tmp_path / "case2", label="score=99"), out2, "--overwrite").returncode == 0
    rows2 = read_csv(out2 / "indicator_candidate_validations.csv")
    assert rows2[0]["validation_status"] == "reject_candidate"

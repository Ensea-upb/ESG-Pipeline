from .helpers import make_orchestrator_output, read_csv, read_json, run_validation


def test_review_queue_priority_order(tmp_path):
    out = tmp_path / "out"
    assert run_validation(make_orchestrator_output(tmp_path), out, "--overwrite").returncode == 0
    rows = read_csv(out / "validation_review_queue.csv")
    order = {"high": 0, "medium": 1, "low": 2}
    assert rows
    assert [order[row["review_priority"]] for row in rows] == sorted(order[row["review_priority"]] for row in rows)
    assert all(row["review_required"] == "True" for row in rows)
    assert all(row["ready_for_manual_review"] == "True" for row in rows)
    assert read_json(out / "review_queue_summary.json")["review_queue_count"] == len(rows)

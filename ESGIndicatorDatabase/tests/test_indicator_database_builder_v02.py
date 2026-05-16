from .helpers import make_manual_review_output, read_csv, read_json, run_build


def test_preparation_database_values_and_status(tmp_path):
    out = tmp_path / "out"
    assert run_build(make_manual_review_output(tmp_path), out, "--overwrite").returncode == 0
    rows = read_csv(out / "indicator_preparation_database.csv")
    assert len(rows) == 1
    row = rows[0]
    assert row["indicator_database_status"] == "preparation_only"
    assert row["is_final_indicator"] == "False"
    assert row["score_produced"] == "False"
    assert row["value_raw"] == "1,200"
    assert row["value_prepared"] == "1199"
    assert row["value_source"] == "corrected_value"
    assert read_json(out / "indicator_database_summary.json")["preparation_indicators_count"] == 1

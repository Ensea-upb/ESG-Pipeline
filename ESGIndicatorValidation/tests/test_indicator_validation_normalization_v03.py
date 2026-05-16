from .helpers import make_orchestrator_output, read_csv, run_validation


def test_value_unit_year_normalization(tmp_path):
    out = tmp_path / "out"
    assert run_validation(make_orchestrator_output(tmp_path), out, "--overwrite").returncode == 0
    rows = read_csv(out / "normalized_indicator_candidates.csv")
    scope = [row for row in rows if row["label"] == "scope 1 emissions"][0]
    assert scope["normalized_value"] == "1200"
    assert scope["normalized_unit"] == "tCO2e"
    assert scope["normalized_year"] == "2024"
    assert scope["year_inferred"] == "False"
    visual = [row for row in rows if row["source_engine"] == "visual"][0]
    assert visual["normalization_status"] in {"partial", "not_normalized"}

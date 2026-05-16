from .helpers import make_orchestrator_output, read_csv, run_validation


def test_family_mapping_examples(tmp_path):
    out = tmp_path / "out"
    assert run_validation(make_orchestrator_output(tmp_path), out, "--overwrite").returncode == 0
    rows = read_csv(out / "indicator_candidate_validations.csv")
    assert [row for row in rows if row["label"] == "scope 1 emissions"][0]["indicator_family"] == "ghg_emissions"
    assert [row for row in rows if row["label"] == "energy consumption"][0]["indicator_family"] == "energy"
    assert [row for row in rows if row["information_type"] == "boundary_context"][0]["indicator_family"] == "boundary"
    assert all(row["is_validated_indicator"] == "False" for row in rows)

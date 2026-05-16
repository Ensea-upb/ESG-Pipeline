from .helpers import make_manual_review_output, read_csv, run_build


def test_schema_mapping(tmp_path):
    out = tmp_path / "out"
    assert run_build(make_manual_review_output(tmp_path), out, "--overwrite").returncode == 0
    row = read_csv(out / "indicator_schema_mapping.csv")[0]
    assert row["indicator_domain"] == "environmental"
    assert row["indicator_topic"] == "ghg_emissions"
    assert row["indicator_unit_category"] == "emissions"

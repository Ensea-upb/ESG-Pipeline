from .helpers import make_indicator_output, read_csv, read_json, run_build


def test_decision_template_and_schema(tmp_path):
    out = tmp_path / "workspace"
    assert run_build(make_indicator_output(tmp_path), out, "--overwrite").returncode == 0
    template = read_csv(out / "review_decisions_template.csv")
    schema = read_json(out / "review_decision_schema.json")
    assert (out / "review_decision_instructions.md").exists()
    assert template
    assert {row["proposed_decision"] for row in template} == {""}
    assert "accept_candidate" in schema["allowed_proposed_decision"]

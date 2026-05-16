from .helpers import make_indicator_output, read_csv, run_build


def test_workspace_and_markdown(tmp_path):
    out = tmp_path / "workspace"
    assert run_build(make_indicator_output(tmp_path), out, "--overwrite").returncode == 0
    rows = read_csv(out / "manual_review_workspace.csv")
    assert (out / "manual_review_workspace.md").exists()
    assert rows[0]["validation_status"] == "possible_indicator"
    assert {row["human_decision"] for row in rows} == {""}
    assert any(row["validation_status"] == "needs_review" for row in rows)
    assert all(row["quote"] for row in rows)

from .helpers import make_manual_review_output, read_csv, read_json, run_build


def test_evidence_links(tmp_path):
    out = tmp_path / "out"
    assert run_build(make_manual_review_output(tmp_path), out, "--overwrite").returncode == 0
    links = read_csv(out / "indicator_evidence_links.csv")
    assert len(links) == 1
    assert links[0]["evidence_id"] == "ev1"
    assert links[0]["source_trace_type"] == "text_evidence"
    assert read_json(out / "evidence_link_summary.json")["evidence_links_count"] == 1

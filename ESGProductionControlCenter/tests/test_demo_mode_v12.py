import csv
import json
from pathlib import Path

from ESGProductionControlCenter.src.esg_production_control_center.business_document_selector import build_demo_business_document
from ESGProductionControlCenter.src.esg_production_control_center.demo_data import create_demo_workspace, write_demo_business_report


def test_create_demo_workspace(tmp_path):
    result = create_demo_workspace(tmp_path, overwrite=True)
    demo_dir = Path(result["demo_dir"])
    expected = [
        "consolidated_candidates.csv",
        "indicator_candidate_validations.csv",
        "validation_review_queue.csv",
        "manual_review_workspace.csv",
        "review_decisions_template.csv",
        "review_decisions_filled.csv",
        "accepted_candidate_inputs.csv",
        "indicator_preparation_database.csv",
        "indicator_evidence_links.csv",
        "indicator_lineage.jsonl",
        "demo_metadata.json",
    ]
    for name in expected:
        assert (demo_dir / name).exists()
    metadata = json.loads((demo_dir / "demo_metadata.json").read_text(encoding="utf-8"))
    assert metadata["demo_data"] is True
    assert metadata["synthetic_source"] is True
    with (demo_dir / "indicator_preparation_database.csv").open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) >= 3
    assert all(row["is_final_indicator"] == "false" for row in rows)
    assert all(row["score_produced"] == "false" for row in rows)
    assert all(row["demo_data"] == "true" for row in rows)


def test_demo_business_document_and_report(tmp_path):
    result = create_demo_workspace(tmp_path, overwrite=True)
    files = write_demo_business_report(result["demo_dir"])
    report = Path(result["demo_dir"]) / "business_demo_report.md"
    text = report.read_text(encoding="utf-8")
    assert "Données synthétiques" in text
    assert "Aucun score ESG" in text
    assert "Aucun indicateur final validé" in text
    assert len(files) == 3
    demo_doc = build_demo_business_document(".")
    assert demo_doc.company == "Demo Luxury Group"

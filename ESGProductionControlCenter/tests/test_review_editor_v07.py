import pandas as pd

from ESGProductionControlCenter.src.esg_production_control_center.review_editor import export_decisions, validate_decisions


def test_review_decision_export_and_validation(tmp_path):
    df = pd.DataFrame([{"review_item_id": "r1", "candidate_id": "c1", "proposed_decision": "defer_decision", "reviewer": "", "decision_reason": "", "raw_value": "1", "corrected_value": ""}])
    result = export_decisions(df, tmp_path, overwrite=True)
    assert result["status"] == "success"
    assert (tmp_path / "review_decisions_filled.csv").exists()


def test_accept_requires_reviewer_and_reason():
    df = pd.DataFrame([{"proposed_decision": "accept_candidate", "reviewer": "", "decision_reason": ""}])
    findings = validate_decisions(df)
    assert {f["finding"] for f in findings} == {"accept_without_reviewer", "accept_without_decision_reason"}

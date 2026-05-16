from pathlib import Path

from ESGProductionControlCenter.src.esg_production_control_center.business_document_selector import build_business_documents, filter_documents, get_companies, get_years
from ESGProductionControlCenter.src.esg_production_control_center.business_labels import get_business_step_description, get_business_step_name, get_business_step_order
from ESGProductionControlCenter.src.esg_production_control_center.business_progress import build_business_progress
from ESGProductionControlCenter.src.esg_production_control_center.business_report import write_business_run_report
from ESGProductionControlCenter.src.esg_production_control_center.business_results import TECHNICAL_COLUMNS, to_business_results
from ESGProductionControlCenter.src.esg_production_control_center.pipeline_control import build_pipeline_plan, inspect_step_outputs


def test_business_labels_are_safe():
    for module in get_business_step_order():
        name = get_business_step_name(module)
        desc = get_business_step_description(module)
        assert name
        assert "validated ESG indicator" not in name
        assert "validated ESG indicator" not in desc
    assert "préparatoire" in get_business_step_name("ESGIndicatorDatabase")
    assert "pas un indicateur final" in get_business_step_description("ESGManualReview")


def test_business_document_selector_outputs():
    docs = build_business_documents(".")
    assert docs
    companies = get_companies(docs)
    years = get_years(docs, companies[0])
    filtered = filter_documents(docs, companies[0], years[0])
    assert filtered
    assert filtered[0].company
    assert filtered[0].fiscal_year
    assert filtered[0].input_dir


def test_business_progress_and_report(tmp_path):
    plan = build_pipeline_plan(
        "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test",
        "ESGProductionControlCenter/outputs/business_ui_test",
        overwrite=True,
        dry_run=True,
    )
    steps = inspect_step_outputs(plan)
    progress = build_business_progress(steps, "ESGProductionControlCenter/outputs/business_ui_test")
    assert 0 <= progress["percent_complete"] <= 100
    assert "base préparatoire" in progress["database_message"]
    files = write_business_run_report(
        "ESGProductionControlCenter/outputs/business_ui_test",
        {"company": "Entreprise inconnue", "fiscal_year": "2024", "document_id": "doc"},
        steps,
        overwrite=True,
    )
    assert (Path("ESGProductionControlCenter/outputs/business_ui_test") / "business_run_report.md").exists()
    assert len(files) == 3


def test_business_results_hide_technical_columns_by_default():
    import pandas as pd

    raw = pd.DataFrame([{
        "company": "LVMH",
        "fiscal_year": "2024",
        "label": "energy",
        "quote": "energy 10 GWh",
        "candidate_id": "c1",
        "evidence_id": "e1",
    }])
    business = to_business_results(raw)
    assert "Entreprise" in business.columns
    for col in TECHNICAL_COLUMNS:
        assert col not in business.columns

from ESGProductionControlCenter.src.esg_production_control_center.pipeline_control import build_pipeline_plan, collect_business_summary, collect_quality_blockers, inspect_step_outputs, summarize_pipeline_status, write_pipeline_plan


def test_pipeline_plan_has_full_chain(tmp_path):
    plan = build_pipeline_plan(
        "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test",
        "ESGProductionControlCenter/outputs/test_pipeline_plan",
        dry_run=True,
        overwrite=True,
        reuse_existing=True,
    )
    assert [s["module_name"] for s in plan] == [
        "ESGExtractionOrchestrator",
        "ESGIndicatorValidation",
        "ESGManualReview",
        "ESGManualReviewApply",
        "ESGIndicatorDatabase",
    ]
    assert all(s["dry_run"] is True for s in plan)
    assert all(s["contract_command"] for s in plan)


def test_pipeline_plan_outputs_written(tmp_path):
    output_root = "ESGProductionControlCenter/outputs/test_pipeline_plan_pytest"
    plan = build_pipeline_plan(
        "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test",
        output_root,
        dry_run=True,
        overwrite=True,
    )
    inspected = inspect_step_outputs(plan)
    files = write_pipeline_plan(output_root, inspected, overwrite=True)
    from pathlib import Path
    assert (Path(output_root) / "production_run_summary.json").exists()
    assert (Path(output_root) / "production_run_steps.jsonl").exists()
    assert (Path(output_root) / "production_run_report.md").exists()
    assert len(files) == 3


def test_pipeline_status_summary_and_blockers():
    plan = build_pipeline_plan(
        "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test",
        "ESGProductionControlCenter/outputs/test_pipeline_status",
        dry_run=True,
        overwrite=True,
    )
    inspected = inspect_step_outputs(plan)
    status = summarize_pipeline_status(inspected)
    blockers = collect_quality_blockers(inspected)
    summary = collect_business_summary("ESGProductionControlCenter/outputs/test_pipeline_status")
    assert status["total_steps_count"] == 5
    assert status["next_step_id"] in {"step_01", "step_02", "step_03", "step_04", "step_05", None}
    assert isinstance(blockers, list)
    assert "consolidated_candidates" in summary

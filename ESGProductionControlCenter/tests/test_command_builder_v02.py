import pytest

from ESGProductionControlCenter.src.esg_production_control_center.command_builder import build_run_command, assert_safe_project_path
from ESGProductionControlCenter.src.esg_production_control_center.module_registry import get_module_registry


def test_registry_contains_all_modules():
    registry = get_module_registry()
    for name in ["ESGCSVExtraction", "ESGVisualExtraction", "ESGTableExtraction", "ESGExtractionOrchestrator", "ESGIndicatorValidation", "ESGManualReview", "ESGIndicatorDatabase"]:
        assert name in registry


def test_builds_key_commands():
    for module in ["ESGExtractionOrchestrator", "ESGIndicatorValidation", "ESGManualReview", "ESGIndicatorDatabase"]:
        plan = build_run_command(module, "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test", f"ESGProductionControlCenter/outputs/{module}", dry_run=True)
        assert plan["dry_run"] is True
        assert "--input-dir" in plan["command"]


def test_rejects_path_outside_project():
    with pytest.raises(ValueError):
        assert_safe_project_path("C:/Windows/System32", ".")

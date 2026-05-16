from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModuleSpec:
    module_name: str
    input_type: str
    output_type: str
    run_script: str
    validation_script: str
    contract_path: str
    required_input_files: list[str]
    expected_output_files: list[str]
    safe_default_options: dict[str, Any]


def get_module_registry() -> dict[str, ModuleSpec]:
    return {
        "ESGCSVExtraction": ModuleSpec("ESGCSVExtraction", "information_output", "csv_candidates", "ESGCSVExtraction/scripts/run_csv_extraction.py", "ESGCSVExtraction/scripts/validate_csv_outputs.py", "ESGCSVExtraction/contracts/csv_output_contract_v0.json", ["multimodal_evidence_index.jsonl"], ["esg_information_candidates.csv"], {"overwrite": False, "dry_run": True}),
        "ESGVisualExtraction": ModuleSpec("ESGVisualExtraction", "information_output", "visual_candidates", "ESGVisualExtraction/scripts/run_visual_extraction.py", "ESGVisualExtraction/scripts/validate_visual_outputs.py", "ESGVisualExtraction/contracts/visual_output_contract_v0.json", ["figure_index.jsonl"], ["visual_candidates.csv"], {"overwrite": False, "dry_run": True}),
        "ESGTableExtraction": ModuleSpec("ESGTableExtraction", "information_output", "table_candidates", "ESGTableExtraction/scripts/run_table_extraction.py", "ESGTableExtraction/scripts/validate_table_outputs.py", "ESGTableExtraction/contracts/table_output_contract_v0.json", ["table_index.jsonl", "table_cells.jsonl"], ["table_metric_candidates.csv"], {"overwrite": False, "dry_run": True}),
        "ESGExtractionOrchestrator": ModuleSpec("ESGExtractionOrchestrator", "information_output", "full_extraction", "ESGExtractionOrchestrator/scripts/run_full_extraction.py", "ESGExtractionOrchestrator/scripts/validate_full_extraction_outputs.py", "ESGExtractionOrchestrator/contracts/full_extraction_output_contract_v0.json", ["document_record.json"], ["consolidated_candidates.csv"], {"overwrite": False, "dry_run": True, "reuse_existing": False, "force_rerun": False}),
        "ESGIndicatorValidation": ModuleSpec("ESGIndicatorValidation", "full_extraction", "indicator_validation", "ESGIndicatorValidation/scripts/run_indicator_validation.py", "ESGIndicatorValidation/scripts/validate_indicator_validation_outputs.py", "ESGIndicatorValidation/contracts/indicator_validation_contract_v0.json", ["consolidated_candidates.csv"], ["indicator_candidate_validations.csv"], {"overwrite": False, "dry_run": True}),
        "ESGManualReview": ModuleSpec("ESGManualReview", "indicator_validation", "manual_review", "ESGManualReview/scripts/build_review_workspace.py", "ESGManualReview/scripts/validate_manual_review_outputs.py", "ESGManualReview/contracts/manual_review_contract_v0.json", ["indicator_candidate_validations.csv"], ["manual_review_workspace.csv"], {"overwrite": False, "dry_run": True}),
        "ESGIndicatorDatabase": ModuleSpec("ESGIndicatorDatabase", "manual_review", "indicator_database", "ESGIndicatorDatabase/scripts/build_indicator_database.py", "ESGIndicatorDatabase/scripts/validate_indicator_database_outputs.py", "ESGIndicatorDatabase/contracts/indicator_database_contract_v0.json", ["accepted_candidate_inputs.csv"], ["indicator_preparation_database.csv"], {"overwrite": False, "dry_run": True}),
    }


def registry_as_dict() -> list[dict[str, Any]]:
    return [asdict(spec) for spec in get_module_registry().values()]


def write_registry_outputs(output_dir: str | Path, planned_commands: list[dict[str, Any]] | None = None, overwrite: bool = False) -> list[str]:
    import json
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = [out / "module_registry.json", out / "planned_commands.jsonl", out / "command_plan_summary.json"]
    if not overwrite and any(p.exists() for p in files):
        raise FileExistsError("Refusing to overwrite command planning files")
    commands = planned_commands or []
    files[0].write_text(json.dumps({"modules": registry_as_dict()}, indent=2), encoding="utf-8")
    files[1].write_text("".join(json.dumps(c) + "\n" for c in commands), encoding="utf-8")
    files[2].write_text(json.dumps({"planned_commands_count": len(commands), "dry_run_default": True}, indent=2), encoding="utf-8")
    return [str(p) for p in files]

from __future__ import annotations

import json
import sys
import csv
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .command_builder import assert_safe_project_path, build_run_command, build_validation_command
from .command_runner import run_command
from .contract_checker import validate_contract


PIPELINE_STEPS = [
    "ESGExtractionOrchestrator",
    "ESGIndicatorValidation",
    "ESGManualReview",
    "ESGManualReviewApply",
    "ESGIndicatorDatabase",
]


@dataclass(frozen=True)
class PipelineStep:
    step_id: str
    module_name: str
    display_name: str
    input_dir: str
    output_dir: str
    command: list[str]
    validation_module_name: str | None
    contract_command: list[str] | None
    expected_files: list[str]
    status: str = "planned"
    contract_status: str = "not_run"
    errors_count: int = 0
    warnings_count: int = 0


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    return "_".join(part for part in cleaned.split("_") if part)[:80] or "run"


def build_pipeline_plan(input_dir: str | Path, base_output_dir: str | Path, project_root: str | Path = ".", overwrite: bool = False, dry_run: bool = True, reuse_existing: bool = False, force_rerun: bool = False) -> list[dict[str, Any]]:
    safe_input = assert_safe_project_path(input_dir, project_root)
    base = assert_safe_project_path(base_output_dir, project_root)
    orchestrator_out = base / "01_full_extraction"
    validation_out = base / "02_indicator_validation"
    review_out = base / "03_manual_review_workspace"
    review_applied_out = base / "04_manual_review_applied"
    database_out = base / "05_indicator_database"

    step1 = build_run_command("ESGExtractionOrchestrator", safe_input, orchestrator_out, project_root, overwrite, dry_run, reuse_existing, force_rerun)
    step2 = build_run_command("ESGIndicatorValidation", orchestrator_out, validation_out, project_root, overwrite, dry_run)
    step3 = build_run_command("ESGManualReview", validation_out, review_out, project_root, overwrite, dry_run)
    step4_command = [
        sys.executable,
        "ESGManualReview/scripts/apply_review_decisions.py",
        "--workspace-dir",
        str(review_out),
        "--decisions-file",
        str(review_out / "review_decisions_template.csv"),
        "--output-dir",
        str(review_applied_out),
    ]
    if overwrite:
        step4_command.append("--overwrite")
    step5 = build_run_command("ESGIndicatorDatabase", review_applied_out, database_out, project_root, overwrite, dry_run)

    raw_steps = [
        ("step_01", "ESGExtractionOrchestrator", "Full extraction consolidation", step1, "ESGExtractionOrchestrator", ["consolidated_candidates.csv", "full_extraction_summary.json"]),
        ("step_02", "ESGIndicatorValidation", "Indicator pre-validation", step2, "ESGIndicatorValidation", ["indicator_candidate_validations.csv", "validation_review_queue.csv"]),
        ("step_03", "ESGManualReview", "Build manual review workspace", step3, "ESGManualReview", ["manual_review_workspace.csv", "review_decisions_template.csv"]),
        ("step_04", "ESGManualReviewApply", "Apply human review decisions", {"module_name": "ESGManualReviewApply", "input_dir": str(review_out), "output_dir": str(review_applied_out), "command": step4_command, "dry_run": dry_run, "overwrite": overwrite}, "ESGManualReview", ["reviewed_candidates.csv", "accepted_candidate_inputs.csv"]),
        ("step_05", "ESGIndicatorDatabase", "Build preparation-only indicator database", step5, "ESGIndicatorDatabase", ["indicator_preparation_database.csv", "indicator_database_summary.json"]),
    ]
    steps: list[dict[str, Any]] = []
    for step_id, module_name, display, plan, validation_module, expected in raw_steps:
        try:
            contract = build_validation_command(validation_module, plan["output_dir"], project_root)
            contract_cmd = contract["command"]
        except Exception:
            contract_cmd = None
        steps.append(asdict(PipelineStep(
            step_id=step_id,
            module_name=module_name,
            display_name=display,
            input_dir=plan["input_dir"],
            output_dir=plan["output_dir"],
            command=plan["command"],
            validation_module_name=validation_module,
            contract_command=contract_cmd,
            expected_files=expected,
        )) | {"dry_run": dry_run, "overwrite": overwrite})
    return steps


def inspect_step_outputs(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inspected = []
    for step in steps:
        out = Path(step["output_dir"])
        found = [name for name in step.get("expected_files", []) if (out / name).exists()]
        status = "ready" if len(found) == len(step.get("expected_files", [])) and found else "missing"
        inspected.append(step | {"existing_files_found": found, "detected_status": status})
    return inspected


def summarize_pipeline_status(steps: list[dict[str, Any]]) -> dict[str, Any]:
    ready = sum(1 for s in steps if s.get("detected_status") == "ready")
    next_step = next((s for s in steps if s.get("detected_status") != "ready"), None)
    if ready == len(steps):
        message = "Pipeline outputs are complete. Review contracts and preparation-only database."
        status = "complete"
    elif ready == 0:
        message = "Start with step_01. Run dry-run first, then execute with confirmation."
        status = "not_started"
    else:
        message = f"Next recommended step: {next_step['step_id']} - {next_step['display_name']}"
        status = "in_progress"
    return {
        "status": status,
        "ready_steps_count": ready,
        "total_steps_count": len(steps),
        "next_step_id": next_step["step_id"] if next_step else None,
        "next_module_name": next_step["module_name"] if next_step else None,
        "message": message,
    }


def collect_business_summary(base_output_dir: str | Path) -> dict[str, Any]:
    base = Path(base_output_dir)

    def count_csv(name: str) -> int:
        matches = list(base.rglob(name))
        if not matches:
            return 0
        try:
            with matches[0].open("r", encoding="utf-8", newline="") as fh:
                return max(sum(1 for _ in csv.DictReader(fh)), 0)
        except Exception:
            return 0

    return {
        "consolidated_candidates": count_csv("consolidated_candidates.csv"),
        "possible_indicators": count_csv("possible_indicators.csv"),
        "needs_review_queue": count_csv("validation_review_queue.csv"),
        "rejected_candidates": count_csv("rejected_candidates.csv"),
        "accepted_candidates": count_csv("accepted_candidate_inputs.csv"),
        "preparation_database_rows": count_csv("indicator_preparation_database.csv"),
    }


def collect_quality_blockers(steps: list[dict[str, Any]], runs_dir: str | Path | None = None) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for step in steps:
        missing = [name for name in step.get("expected_files", []) if name not in step.get("existing_files_found", [])]
        if missing:
            blockers.append({
                "severity": "info",
                "step_id": step["step_id"],
                "type": "missing_expected_files",
                "message": "Missing expected files: " + ", ".join(missing),
            })
        out = Path(step["output_dir"])
        for csv_path in out.rglob("*.csv") if out.exists() else []:
            try:
                if csv_path.stat().st_size == 0:
                    blockers.append({"severity": "warning", "step_id": step["step_id"], "type": "empty_csv", "message": str(csv_path)})
            except OSError:
                pass
    if runs_dir:
        root = Path(runs_dir)
        if root.exists():
            for stderr in root.rglob("command_stderr.txt"):
                try:
                    text = stderr.read_text(encoding="utf-8", errors="ignore").strip()
                except Exception:
                    text = ""
                if text:
                    blockers.append({"severity": "warning", "step_id": "run", "type": "stderr_not_empty", "message": str(stderr)})
    return blockers


def execute_pipeline_step(step: dict[str, Any], runs_dir: str | Path, allow_execute: bool = False, timeout_seconds: int = 900) -> dict[str, Any]:
    plan = {
        "module_name": step["module_name"],
        "input_dir": step["input_dir"],
        "output_dir": step["output_dir"],
        "command": step["command"],
        "dry_run": step.get("dry_run", True),
        "overwrite": step.get("overwrite", False),
    }
    return run_command(plan, runs_dir, allow_execute=allow_execute, timeout_seconds=timeout_seconds)


def validate_pipeline_step_contract(step: dict[str, Any], results_dir: str | Path, project_root: str | Path = ".", stop_on_contract_failure: bool = True) -> dict[str, Any]:
    module = step.get("validation_module_name") or step["module_name"]
    return validate_contract(module, step["output_dir"], results_dir, project_root, stop_on_contract_failure)


def write_pipeline_plan(output_dir: str | Path, steps: list[dict[str, Any]], overwrite: bool = False) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = [out / "production_run_summary.json", out / "production_run_steps.jsonl", out / "production_run_report.md"]
    if not overwrite and any(p.exists() for p in files):
        raise FileExistsError("Refusing to overwrite production pipeline plan")
    summary = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "steps_count": len(steps),
        "dry_run": all(bool(s.get("dry_run", True)) for s in steps),
        "no_score_produced": True,
        "no_final_indicator_validated": True,
    }
    files[0].write_text(json.dumps(summary, indent=2), encoding="utf-8")
    files[1].write_text("".join(json.dumps(s) + "\n" for s in steps), encoding="utf-8")
    lines = ["# Production Pipeline Plan", "", "No ESG score or final validated indicator is produced.", ""]
    for step in steps:
        lines.append(f"- {step['step_id']} - {step['display_name']}: `{step['module_name']}`")
    files[2].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [str(p) for p in files]

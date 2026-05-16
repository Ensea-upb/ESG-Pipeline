from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ESGProductionControlCenter.src.esg_production_control_center.command_builder import build_run_command
from ESGProductionControlCenter.src.esg_production_control_center.command_runner import run_command
from ESGProductionControlCenter.src.esg_production_control_center.config import get_config, ensure_control_dirs
from ESGProductionControlCenter.src.esg_production_control_center.output_discovery import discover_outputs, write_discovery_outputs
from ESGProductionControlCenter.src.esg_production_control_center.module_registry import write_registry_outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--module-name", default="ESGExtractionOrchestrator")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    cfg = get_config(".")
    ensure_control_dirs(cfg)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    discovered = discover_outputs(".")
    write_discovery_outputs(output_dir, discovered, overwrite=args.overwrite)
    plan = build_run_command(args.module_name, args.input_dir, output_dir / "module_output", overwrite=args.overwrite, dry_run=args.dry_run or not args.execute)
    write_registry_outputs(output_dir, [plan], overwrite=args.overwrite)
    state = run_command(plan, cfg.runs_dir, allow_execute=args.execute, timeout_seconds=300)
    output_run_dir = output_dir / "runs" / state["run_id"]
    output_run_dir.mkdir(parents=True, exist_ok=True)
    source_run_dir = Path(state["run_dir"])
    for name in ["run_state.json", "run_log.jsonl", "command_stdout.txt", "command_stderr.txt", "executed_command.json"]:
        src = source_run_dir / name
        if src.exists():
            shutil.copy2(src, output_run_dir / name)
    summary = {
        "status": "success",
        "dry_run": plan["dry_run"],
        "run_id": state["run_id"],
        "run_status": state["status"],
        "outputs_discovered_count": len(discovered),
        "no_score_produced": True,
        "no_final_indicator_validated": True,
    }
    (output_dir / "production_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "production_run_steps.jsonl").write_text(json.dumps({"step_id": "step_001", **plan, "status": state["status"]}) + "\n", encoding="utf-8")
    (output_dir / "production_run_report.md").write_text("# Production Run Report\n\nNo ESG score or final validated indicator is produced.\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

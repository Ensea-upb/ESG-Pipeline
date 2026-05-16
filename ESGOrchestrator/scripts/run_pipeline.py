from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def resolve_project_root() -> Path:
    env_root = os.getenv("ESG_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve() / "ESGOrchestrator"
    return Path(__file__).resolve().parents[1]


PROJECT_ROOT = resolve_project_root()
sys.path.insert(0, str(PROJECT_ROOT))

from src.esg_orchestrator.pipeline_orchestrator import (
    PipelineOrchestrator,
    add_common_args,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ESG corpus pipeline orchestration.")
    add_common_args(parser)
    args = parser.parse_args()

    orchestrator = PipelineOrchestrator(project_root=PROJECT_ROOT)
    result = orchestrator.run(
        profile=args.profile,
        dry_run=args.dry_run,
        resume=not args.no_resume,
        run_id=args.run_id,
        postprocessing_only=args.postprocessing_only,
    )

    print("\n=== ESG Pipeline Orchestrator ===")
    print(f"run_id: {result['run_id']}")
    print(f"run_dir: {result['run_dir']}")
    print(f"task_count: {result['task_count']}")
    print(f"run_state: {result['state_path']}")
    print(f"task_log: {result['task_log_path']}")
    print(f"coverage_matrix: {result['coverage_matrix_path']}")
    print(f"final_summary: {result['final_summary_path']}")

    print("\n--- First 10 Tasks ---")
    for task in result["tasks"][:10]:
        print(
            f"{task.task_id} | {task.company_name} | {task.fiscal_year} | "
            f"{task.official_doc_type} | {task.status}"
        )


if __name__ == "__main__":
    main()

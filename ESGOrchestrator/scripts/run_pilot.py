from __future__ import annotations

import sys
import os
from pathlib import Path


def resolve_project_root() -> Path:
    env_root = os.getenv("ESG_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve() / "ESGOrchestrator"
    return Path(__file__).resolve().parents[1]


PROJECT_ROOT = resolve_project_root()
sys.path.insert(0, str(PROJECT_ROOT))

from src.esg_orchestrator.pipeline_orchestrator import PipelineOrchestrator


def main() -> None:
    result = PipelineOrchestrator(project_root=PROJECT_ROOT).run(
        profile="pilot",
        dry_run=False,
        resume=True,
    )
    print(f"Pilot run completed: {result['run_id']}")
    print(f"Tasks: {result['task_count']}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import yaml

from .company_universe import CompanyUniverse
from .models import RunConfig
from .postprocessing_runner import PostProcessingRunner
from .reporting import CoverageReporter
from .retriever_runner import RetrieverRunner
from .run_state import RunState
from .task_builder import TaskBuilder


class PipelineOrchestrator:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root).resolve()
        self.workspace_root = self.project_root.parent
        self.config_dir = self.project_root / "config"
        self.runs_dir = self.project_root / "runs"

    def run(
        self,
        profile: str,
        dry_run: bool = False,
        resume: bool = True,
        run_id: str | None = None,
        postprocessing_only: bool = False,
    ) -> dict:
        pipeline_config = self.load_yaml(self.config_dir / "pipeline.yaml")
        profile_config = self.load_profile(profile)

        years = [int(year) for year in profile_config.get("years") or pipeline_config["default_years"]]
        company_selector = profile_config.get("companies", "all")
        max_workers = int(profile_config.get("max_workers", 1))
        run_id = run_id or self.build_run_id(profile)

        companies = CompanyUniverse(self.config_dir / "companies_cac40.yaml").select(
            company_selector
        )

        min_score = float(pipeline_config.get("settings", {}).get("min_score", 80.0))
        task_builder = TaskBuilder(
            document_types_config_path=self.config_dir / "document_types.yaml",
            workspace_root=self.workspace_root,
            min_score=min_score,
        )
        tasks = task_builder.build_tasks(companies=companies, years=years)

        run_config = RunConfig(
            profile=profile,
            run_id=run_id,
            dry_run=dry_run,
            resume=bool(profile_config.get("resume", resume)),
            skip_existing_downloads=bool(
                profile_config.get(
                    "skip_existing_downloads",
                    pipeline_config.get("settings", {}).get(
                        "skip_existing_downloads",
                        True,
                    ),
                )
            ),
            max_workers=max_workers,
            years=years,
            companies=[company.name for company in companies],
        )

        run_dir = self.runs_dir / run_id
        state = RunState(run_dir=run_dir, run_config=run_config)

        runner = RetrieverRunner(workspace_root=self.workspace_root)
        run_ingestion = bool(pipeline_config.get("steps", {}).get("ingestion", True))
        if postprocessing_only:
            for task in tasks:
                if task.status != "skipped_not_applicable":
                    task.status = "skipped_existing"
                    task.message = "postprocessing_only: ingestion not executed"
            state.save(tasks)
        elif not run_ingestion:
            for task in tasks:
                if task.status != "skipped_not_applicable":
                    task.status = "skipped_not_applicable"
                    task.message = "ingestion step disabled"
            state.save(tasks)
        elif dry_run:
            for task in tasks:
                runner.run_task(task, dry_run=True)
        elif max_workers > 1:
            save_lock = threading.Lock()
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_task = {
                    executor.submit(runner.run_task, task, False): task
                    for task in tasks
                }
                for future in as_completed(future_to_task):
                    try:
                        future.result()
                    except Exception as exc:
                        task = future_to_task[future]
                        task.status = "failed"
                        task.message = str(exc)
                    with save_lock:
                        state.save(tasks)
        else:
            for task in tasks:
                runner.run_task(task, dry_run=False)
                state.save(tasks)

        postprocessing_results = []
        if pipeline_config.get("settings", {}).get("run_postprocessing_after_ingestion", True):
            enabled_steps = (
                pipeline_config.get("steps", {}).get("postprocessing", {})
            )
            postprocessing_scope = (
                profile_config.get("postprocessing_scope")
                or pipeline_config.get("settings", {}).get("postprocessing_scope", "run")
            )
            postprocessing_output_mode = (
                profile_config.get("postprocessing_output_mode")
                or pipeline_config.get("settings", {}).get(
                    "postprocessing_output_mode",
                    "run_isolated",
                )
            )
            postprocessing_results = PostProcessingRunner(
                workspace_root=self.workspace_root
            ).run_all(
                dry_run=dry_run,
                enabled_steps=enabled_steps,
                scope=postprocessing_scope,
                company_slugs=[company.company_slug for company in companies],
                years=years,
                run_dir=run_dir,
                output_mode=postprocessing_output_mode,
            )

        reporter = CoverageReporter(run_dir=run_dir)
        coverage_path = reporter.write_coverage_matrix(tasks)
        summary_path = reporter.write_final_summary(tasks, postprocessing_results)
        state.save(tasks)

        return {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "task_count": len(tasks),
            "state_path": str(state.state_path),
            "task_log_path": str(state.task_log_path),
            "coverage_matrix_path": str(coverage_path),
            "final_summary_path": str(summary_path),
            "tasks": tasks,
            "postprocessing_results": postprocessing_results,
        }

    def load_profile(self, profile: str) -> dict:
        payload = self.load_yaml(self.config_dir / "run_profiles.yaml")
        profiles = payload.get("profiles", {})
        if profile not in profiles:
            raise ValueError(f"Profil inconnu : {profile}")
        return profiles[profile]

    @staticmethod
    def load_yaml(path: Path) -> dict:
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    @staticmethod
    def build_run_id(profile: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_profile = "".join(char if char.isalnum() else "_" for char in profile)
        return f"{safe_profile}_{stamp}"


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", default="pilot")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--postprocessing-only",
        action="store_true",
        help="Skip retrievers and run only the configured post-processing steps.",
    )

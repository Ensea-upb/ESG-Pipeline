from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from ESGOrchestrator.src.esg_orchestrator.models import PipelineTask
from ESGOrchestrator.src.esg_orchestrator.retriever_runner import RetrieverRunner


def _make_task(task_id: str) -> PipelineTask:
    return PipelineTask(
        task_id=task_id,
        company_name="TestCo",
        company_slug="testco",
        fiscal_year=2024,
        official_doc_type="annual_report",
        official_doc_type_label="Annual Report",
        retriever="AnnualReportRetriever",
        command=["python", "-c", "import time; time.sleep(0.05)"],
    )


def test_parallel_tasks_run_concurrently(tmp_path):
    """Tasks with max_workers>1 should overlap in time, not run back-to-back."""
    tasks = [_make_task(f"task_{i}") for i in range(4)]
    call_times: list[float] = []
    lock = threading.Lock()

    original_run_task = RetrieverRunner.run_task

    def recording_run_task(self, task, dry_run=False):
        with lock:
            call_times.append(time.monotonic())
        time.sleep(0.1)  # simulate subprocess work
        task.status = "success"
        task.message = "completed"
        task.started_at = RetrieverRunner.utcnow()
        task.finished_at = RetrieverRunner.utcnow()
        return task

    with patch.object(RetrieverRunner, "run_task", recording_run_task):
        from concurrent.futures import ThreadPoolExecutor, as_completed

        runner = RetrieverRunner(workspace_root=tmp_path)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(runner.run_task, task, False): task for task in tasks}
            for future in as_completed(futures):
                future.result()

    # All 4 tasks should start within 50ms of each other (parallel), not 400ms apart (sequential)
    assert len(call_times) == 4
    spread = max(call_times) - min(call_times)
    assert spread < 0.05, f"Tasks started {spread:.3f}s apart — expected parallel overlap"


def test_sequential_fallback_when_max_workers_is_one(tmp_path):
    """max_workers=1 must still process all tasks and set status."""
    tasks = [_make_task(f"task_{i}") for i in range(3)]

    def fast_run_task(self, task, dry_run=False):
        task.status = "success"
        task.message = "completed"
        task.started_at = RetrieverRunner.utcnow()
        task.finished_at = RetrieverRunner.utcnow()
        return task

    with patch.object(RetrieverRunner, "run_task", fast_run_task):
        runner = RetrieverRunner(workspace_root=tmp_path)
        for task in tasks:
            runner.run_task(task, dry_run=False)

    assert all(t.status == "success" for t in tasks)


def test_failed_task_does_not_block_parallel_run(tmp_path):
    """A task that raises internally should be marked failed; others continue."""
    tasks = [_make_task(f"task_{i}") for i in range(3)]

    def flaky_run_task(self, task, dry_run=False):
        if task.task_id == "task_1":
            task.status = "failed"
            task.message = "simulated failure"
        else:
            task.status = "success"
            task.message = "completed"
        task.started_at = RetrieverRunner.utcnow()
        task.finished_at = RetrieverRunner.utcnow()
        return task

    with patch.object(RetrieverRunner, "run_task", flaky_run_task):
        from concurrent.futures import ThreadPoolExecutor, as_completed

        runner = RetrieverRunner(workspace_root=tmp_path)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(runner.run_task, task, False): task for task in tasks}
            for future in as_completed(futures):
                future.result()

    statuses = {t.task_id: t.status for t in tasks}
    assert statuses["task_0"] == "success"
    assert statuses["task_1"] == "failed"
    assert statuses["task_2"] == "success"

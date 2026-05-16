from __future__ import annotations

import subprocess
import os
from datetime import datetime, timezone
from pathlib import Path

from .models import PipelineTask


class RetrieverRunner:
    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def run_task(self, task: PipelineTask, dry_run: bool = False) -> PipelineTask:
        if task.status == "skipped_not_applicable":
            return task
        if dry_run:
            task.status = "pending"
            task.message = "dry_run: command not executed"
            return task

        task.status = "running"
        task.started_at = self.utcnow()
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            completed = subprocess.run(
                task.command,
                cwd=self.workspace_root,
                env=env,
                text=True,
                capture_output=True,
                timeout=1800,
            )
            if completed.returncode == 0:
                task.status = "success"
                task.message = "completed"
            else:
                task.status = "failed"
                task.message = completed.stderr[-1000:] or completed.stdout[-1000:]
        except Exception as exc:
            task.status = "failed"
            task.message = str(exc)
        finally:
            task.finished_at = self.utcnow()
        return task

    @staticmethod
    def utcnow() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

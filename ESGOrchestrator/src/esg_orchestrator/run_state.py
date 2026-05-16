from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import PipelineTask, RunConfig


class RunState:
    def __init__(self, run_dir: str | Path, run_config: RunConfig) -> None:
        self.run_dir = Path(run_dir)
        self.run_config = run_config
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.run_dir / "run_state.json"
        self.task_log_path = self.run_dir / "task_log.csv"

    def save(self, tasks: list[PipelineTask]) -> None:
        payload = {
            "run_config": asdict(self.run_config),
            "updated_at": self.utcnow(),
            "tasks": [task.to_dict() for task in tasks],
        }
        self.state_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.write_task_log(tasks)

    def write_task_log(self, tasks: list[PipelineTask]) -> None:
        fieldnames = [
            "task_id",
            "company_name",
            "company_slug",
            "fiscal_year",
            "official_doc_type",
            "official_doc_type_label",
            "retriever",
            "policy_type",
            "status",
            "message",
            "command",
            "started_at",
            "finished_at",
        ]
        with self.task_log_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for task in tasks:
                row = task.to_dict()
                row["command"] = " ".join(task.command)
                writer.writerow(row)

    @staticmethod
    def utcnow() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

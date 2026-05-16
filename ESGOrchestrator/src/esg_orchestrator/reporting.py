from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import PipelineTask


class CoverageReporter:
    def __init__(self, run_dir: str | Path) -> None:
        self.run_dir = Path(run_dir)

    def write_coverage_matrix(self, tasks: list[PipelineTask]) -> Path:
        output_path = self.run_dir / "coverage_matrix.csv"
        fieldnames = [
            "company_slug",
            "fiscal_year",
            "official_doc_type",
            "retriever",
            "status",
        ]
        with output_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for task in tasks:
                writer.writerow(
                    {
                        "company_slug": task.company_slug,
                        "fiscal_year": task.fiscal_year,
                        "official_doc_type": task.official_doc_type,
                        "retriever": task.retriever,
                        "status": task.status,
                    }
                )
        return output_path

    def write_final_summary(
        self,
        tasks: list[PipelineTask],
        postprocessing_results: list[dict] | None = None,
    ) -> Path:
        output_path = self.run_dir / "final_summary.json"
        status_counts = {}
        for task in tasks:
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
        payload = {
            "total_tasks": len(tasks),
            "status_counts": status_counts,
            "postprocessing_results": postprocessing_results or [],
        }
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

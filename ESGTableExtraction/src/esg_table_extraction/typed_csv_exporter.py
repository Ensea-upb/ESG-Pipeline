from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import write_csv


def write_typed_csvs(output_dir: Path, candidates: list[dict[str, Any]], fields: list[str]) -> dict[str, int]:
    observed = [
        row for row in candidates
        if "target" not in str(row.get("source_row_text", "")).lower()
        and row.get("metric_family") != "unknown"
    ]
    targets = [row for row in candidates if "target" in str(row.get("source_row_text", "")).lower()]
    contexts = [row for row in candidates if row.get("metric_family") in {"unknown"}]
    rejected: list[dict[str, Any]] = []
    files = {
        "table_observed_metrics.csv": observed,
        "table_targets.csv": targets,
        "table_contexts.csv": contexts,
        "table_rejected_candidates.csv": rejected,
    }
    for name, rows in files.items():
        write_csv(output_dir / name, rows, fields)
    return {name: len(rows) for name, rows in files.items()}

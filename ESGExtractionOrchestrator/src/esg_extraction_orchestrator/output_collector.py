from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_csv, read_json


def collect_engine_outputs(output_dir: Path) -> dict[str, Any]:
    return {
        "csv": {
            "summary": read_json(output_dir / "csv" / "extraction_summary.json"),
            "rows": read_csv(output_dir / "csv" / "esg_information_candidates.csv"),
        },
        "visual": {
            "summary": read_json(output_dir / "visual" / "visual_extraction_summary.json"),
            "rows": read_csv(output_dir / "visual" / "visual_candidates.csv"),
        },
        "table": {
            "summary": read_json(output_dir / "table" / "table_extraction_summary.json"),
            "rows": read_csv(output_dir / "table" / "table_metric_candidates.csv"),
        },
    }

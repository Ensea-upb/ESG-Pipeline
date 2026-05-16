from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import get_config
from .output_discovery import discover_outputs
from .run_state import list_runs


PAGES = ["Poste de contrôle", "Exploration", "Logs", "Guide"]


def build_dashboard_data(project_root: str | Path = ".") -> dict[str, Any]:
    cfg = get_config(project_root)
    outputs = discover_outputs(project_root)
    runs = list_runs(cfg.runs_dir)
    return {
        "safety_banner": "Aucun indicateur ESG final validé / aucun score produit. accepted_candidate != validated_indicator. indicator_database_status=preparation_only.",
        "pages": PAGES,
        "outputs_count": len(outputs),
        "runs_count": len(runs),
        "outputs": outputs,
        "runs": runs,
    }

from __future__ import annotations

from pathlib import Path
from typing import Any

from .business_labels import get_business_status_label, get_business_step_description, get_business_step_name
from .pipeline_control import collect_business_summary, collect_quality_blockers, summarize_pipeline_status


def build_business_progress(steps: list[dict[str, Any]], base_output_dir: str | Path, runs_dir: str | Path | None = None) -> dict[str, Any]:
    status = summarize_pipeline_status(steps)
    summary = collect_business_summary(base_output_dir)
    blockers = collect_quality_blockers(steps, runs_dir)
    percent = int((status["ready_steps_count"] / max(status["total_steps_count"], 1)) * 100)
    cards = []
    for step in steps:
        human_status = get_business_status_label(step.get("detected_status", "missing"))
        message = "Étape terminée." if step.get("detected_status") == "ready" else "Étape à lancer ou à compléter."
        if step["module_name"] == "ESGManualReview" and step.get("detected_status") == "ready":
            message = "Une revue humaine peut être réalisée."
        cards.append({
            "step_id": step["step_id"],
            "business_name": get_business_step_name(step["module_name"]),
            "description": get_business_step_description(step["module_name"]),
            "status": human_status,
            "message": message,
            "outputs": step.get("existing_files_found", []),
        })
    db_rows = summary.get("preparation_database_rows", 0)
    database_message = (
        f"La base préparatoire contient {db_rows} lignes."
        if db_rows else
        "La base préparatoire est vide car aucun candidat n’a encore été accepté dans la revue humaine."
    )
    return {
        "percent_complete": percent,
        "status": status,
        "business_summary": summary,
        "blockers": blockers,
        "cards": cards,
        "review_required": summary.get("needs_review_queue", 0) > 0,
        "database_message": database_message,
    }

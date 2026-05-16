"""
pipeline_status.py — Détection de l'état de complétion du pipeline par document.
Scanne EXTERNAL_AUDIT_RUNS/ pour trouver le répertoire le plus avancé de chaque doc.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Fichiers sentinelles pour chaque étape (plusieurs variantes possibles)
_SENTINELS: dict[str, list[str]] = {
    "01": [
        "01_information_extraction/extraction_summary.json",
        "01_information_extraction/esg_extraction_summary.json",
    ],
    "02": [
        "02_orchestrator/csv/esg_information_candidates.csv",
        "02_orchestrator/orchestrator_summary.json",
        "02_orchestrator",
    ],
    "03": [
        "03_validation/indicator_validation_summary.json",
        "03_indicator_validation/indicator_validation_summary.json",
        "03_validation",
    ],
    "04": [
        "04_review_workspace/manual_review_workspace.csv",
        "04_review_workspace/review_workspace_summary.json",
    ],
    "review": [
        "04_review_workspace/review_decisions_filled.csv",
    ],
    "05": [
        "05_review_applied/apply_review_summary.json",
        "05_review_applied",
    ],
    "06": [
        "06_indicator_database/indicator_database_summary.json",
        "06_indicator_database",
    ],
}


def _sentinel_ok(doc_dir: Path, candidates: list[str]) -> bool:
    for s in candidates:
        p = doc_dir / s
        if p.exists():
            return True
    return False


def find_document_dir(
    audit_root: Path,
    company: str,
    year: str,
    doc_type: str,
    canonical_id: str,
) -> Path | None:
    """Retourne le répertoire le plus avancé pour un document parmi tous les runs."""
    if not audit_root.exists():
        return None

    best: Path | None = None
    best_score = -1

    for run_dir in sorted(audit_root.iterdir()):
        if not run_dir.is_dir():
            continue
        if not (run_dir / "pilot_run_summary.json").exists():
            continue
        doc_dir = run_dir / company / year / doc_type / canonical_id
        if not doc_dir.exists():
            continue
        score = sum(
            1 for k, v in _SENTINELS.items() if _sentinel_ok(doc_dir, v)
        )
        if score > best_score:
            best_score = score
            best = doc_dir

    return best


def get_step_status(doc_dir: Path | None) -> dict[str, bool]:
    """Retourne un dict étape → complétée pour un document."""
    if doc_dir is None:
        return {k: False for k in _SENTINELS}
    return {k: _sentinel_ok(doc_dir, v) for k, v in _SENTINELS.items()}


def load_review_progress(doc_dir: Path | None) -> dict[str, int]:
    """Retourne les compteurs de progression de la revue humaine."""
    empty = {"total": 0, "decided": 0, "accepted": 0, "rejected": 0, "more_info": 0}
    if doc_dir is None:
        return empty

    workspace_path = doc_dir / "04_review_workspace" / "manual_review_workspace.csv"
    decisions_path = doc_dir / "04_review_workspace" / "review_decisions_filled.csv"

    total = 0
    if workspace_path.exists():
        try:
            total = len(pd.read_csv(workspace_path, usecols=["review_item_id"]))
        except Exception:
            pass

    decided = accepted = rejected = more_info = 0
    if decisions_path.exists():
        try:
            df = pd.read_csv(decisions_path)
            if "proposed_decision" in df.columns:
                d = df["proposed_decision"]
                decided = int(d.notna().sum() - (d == "").sum())
                accepted = int((d == "accept_candidate").sum())
                rejected = int((d == "reject_candidate").sum())
                more_info = int((d == "needs_more_evidence").sum())
        except Exception:
            pass

    return {
        "total": total,
        "decided": decided,
        "accepted": accepted,
        "rejected": rejected,
        "more_info": more_info,
    }


def get_all_statuses(project_root: Path, index_df: pd.DataFrame) -> list[dict]:
    """Agrège l'état pipeline de tous les documents de l'index."""
    audit_root = project_root / "EXTERNAL_AUDIT_RUNS"
    results: list[dict] = []

    for _, row in index_df.iterrows():
        doc_dir = find_document_dir(
            audit_root,
            row["company_slug"],
            str(row["fiscal_year"]),
            row["official_doc_type"],
            row["selected_canonical_document_id"],
        )
        steps = get_step_status(doc_dir)
        progress = load_review_progress(doc_dir)

        results.append(
            {
                "company_name": row.get("company_name", row["company_slug"]),
                "company_slug": row["company_slug"],
                "fiscal_year": str(row["fiscal_year"]),
                "doc_type": row["official_doc_type"],
                "doc_type_label": row.get("official_doc_type_label", row["official_doc_type"]),
                "canonical_id": row["selected_canonical_document_id"],
                "doc_dir": str(doc_dir) if doc_dir else None,
                "steps": steps,
                "review_progress": progress,
            }
        )

    return results

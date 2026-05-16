from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .business_progress import build_business_progress
from .business_results import load_first_available_csv, to_business_results


def write_business_run_report(output_dir: str | Path, document: dict[str, Any], steps: list[dict[str, Any]], overwrite: bool = True) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = [out / "business_run_report.md", out / "business_run_summary.json", out / "business_results_table.csv"]
    if not overwrite and any(p.exists() for p in files):
        raise FileExistsError("Refusing to overwrite business report")
    progress = build_business_progress(steps, out)
    _, df = load_first_available_csv(out, ["indicator_candidate_validations.csv", "consolidated_candidates.csv", "indicator_preparation_database.csv"])
    business_df = to_business_results(df)
    business_df.to_csv(files[2], index=False)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "company": document.get("company", "Entreprise inconnue"),
        "fiscal_year": document.get("fiscal_year", "Année inconnue"),
        "document_id": document.get("document_id"),
        "business_summary": progress["business_summary"],
        "warnings_count": len(progress["blockers"]),
        "no_esg_score": True,
        "no_final_validated_indicator": True,
    }
    files[1].write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    md = [
        "# Rapport métier de run",
        "",
        f"Entreprise: {summary['company']}",
        f"Année: {summary['fiscal_year']}",
        f"Document traité: {summary.get('document_id')}",
        "",
        "## Résumé",
        "",
        f"Candidats consolidés: {progress['business_summary'].get('consolidated_candidates', 0)}",
        f"Candidats à revoir: {progress['business_summary'].get('needs_review_queue', 0)}",
        f"Candidats acceptés pour préparation: {progress['business_summary'].get('accepted_candidates', 0)}",
        f"Candidats rejetés: {progress['business_summary'].get('rejected_candidates', 0)}",
        f"Base préparatoire: {progress['database_message']}",
        "",
        "## Note de prudence",
        "",
        "Aucun score ESG n’est produit.",
        "Aucun indicateur final validé n’est produit.",
    ]
    files[0].write_text("\n".join(md) + "\n", encoding="utf-8")
    return [str(p) for p in files]

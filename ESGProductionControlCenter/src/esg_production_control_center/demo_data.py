from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEMO_COMPANY = "Demo Luxury Group"
DEMO_YEAR = "2024"
DEMO_DOCUMENT = "Sustainability Statement Demo"


THEMES = [
    ("ghg_emissions", "Scope 1 greenhouse gas emissions", "1200", "tCO2e"),
    ("ghg_emissions", "Scope 2 market-based emissions", "850", "tCO2e"),
    ("energy", "Renewable electricity consumption", "42", "%"),
    ("energy", "Total energy consumption", "125", "GWh"),
    ("water", "Water withdrawal", "310000", "m3"),
    ("workforce", "Total employees", "24500", "employees"),
    ("diversity", "Women in management", "48", "%"),
    ("health_safety", "Lost time injury frequency rate", "1.2", "accident rate"),
    ("governance", "Independent board members", "55", "%"),
    ("waste", "Waste recycled", "67", "%"),
]


def _candidate_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    statuses = ["possible_indicator"] * 5 + ["needs_review"] * 10 + ["reject_candidate"] * 3 + ["needs_review"] * 7
    for idx in range(25):
        theme, label, value, unit = THEMES[idx % len(THEMES)]
        status = statuses[idx]
        source = ["csv", "table", "visual"][idx % 3]
        rows.append({
            "candidate_id": f"demo_candidate_{idx+1:03d}",
            "review_item_id": f"demo_review_item_{idx+1:03d}",
            "document_id": "demo_luxury_group_2024_sustainability_statement",
            "company": DEMO_COMPANY,
            "fiscal_year": DEMO_YEAR,
            "source_engine": source,
            "information_type": "observed_metric" if idx % 4 else "target",
            "esg_category": theme,
            "indicator_family": theme,
            "indicator_key_candidate": f"demo_{theme}_{idx+1:03d}",
            "label": label,
            "raw_value": value,
            "raw_unit": unit,
            "normalized_value": value,
            "normalized_unit": unit,
            "year": DEMO_YEAR,
            "normalized_year": DEMO_YEAR,
            "page_number": 10 + idx,
            "quote": f"Synthetic demo excerpt: {label} reported as {value} {unit} in {DEMO_YEAR}.",
            "confidence": "0.50",
            "validation_status": status,
            "review_priority": "high" if status == "possible_indicator" else ("medium" if status == "needs_review" else "low"),
            "review_required": "true",
            "extraction_status": "candidate_only",
            "is_validated_indicator": "false",
            "score_produced": "false",
            "demo_data": "true",
            "synthetic_source": "true",
        })
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def create_demo_workspace(output_root: str | Path = "ESGProductionControlCenter/outputs/demo", overwrite: bool = False) -> dict[str, Any]:
    root = Path(output_root) / "demo_company_2024"
    if root.exists() and not overwrite:
        raise FileExistsError(f"Demo workspace already exists: {root}")
    root.mkdir(parents=True, exist_ok=True)
    rows = _candidate_rows()
    possible = [r for r in rows if r["validation_status"] == "possible_indicator"]
    review = [r for r in rows if r["validation_status"] == "needs_review"]
    rejected = [r for r in rows if r["validation_status"] == "reject_candidate"]
    decisions = []
    for idx, row in enumerate(rows[:5]):
        decision = ["accept_candidate", "accept_candidate", "accept_candidate", "needs_more_evidence", "defer_decision"][idx]
        decisions.append({
            "review_item_id": row["review_item_id"],
            "candidate_id": row["candidate_id"],
            "proposed_decision": decision,
            "reviewer": "Demo reviewer" if decision == "accept_candidate" else "",
            "review_date": "2026-05-11",
            "decision_reason": "Synthetic demo decision for interface testing." if decision == "accept_candidate" else "",
            "corrected_value": "",
            "corrected_unit": "",
            "corrected_year": "",
            "corrected_indicator_family": "",
            "corrected_indicator_key": "",
            "needs_more_evidence_reason": "Synthetic missing source detail." if decision == "needs_more_evidence" else "",
            "reviewer_notes": "Demo only.",
            "demo_data": "true",
            "synthetic_source": "true",
        })
    accepted = []
    for row in rows[:3]:
        accepted.append(row | {
            "human_review_status": "accepted_candidate",
            "reviewer": "Demo reviewer",
            "decision_reason": "Synthetic demo decision for interface testing.",
            "is_final_indicator": "false",
            "indicator_database_status": "preparation_only",
        })
    database = []
    for idx, row in enumerate(accepted):
        database.append({
            "preparation_indicator_id": f"demo_preparation_indicator_{idx+1:03d}",
            "indicator_database_status": "preparation_only",
            "candidate_id": row["candidate_id"],
            "review_item_id": row["review_item_id"],
            "document_id": row["document_id"],
            "company": DEMO_COMPANY,
            "fiscal_year": DEMO_YEAR,
            "source_engine": row["source_engine"],
            "indicator_family": row["indicator_family"],
            "indicator_key": row["indicator_key_candidate"],
            "indicator_label": row["label"],
            "value_raw": row["raw_value"],
            "unit_raw": row["raw_unit"],
            "year_raw": row["year"],
            "value_prepared": row["normalized_value"],
            "unit_prepared": row["normalized_unit"],
            "year_prepared": row["normalized_year"],
            "page_number": row["page_number"],
            "quote": row["quote"],
            "reviewer": "Demo reviewer",
            "decision_reason": "Synthetic demo decision for interface testing.",
            "created_from_review_decision": "true",
            "is_final_indicator": "false",
            "score_produced": "false",
            "demo_data": "true",
            "synthetic_source": "true",
        })

    _write_csv(root / "consolidated_candidates.csv", rows)
    _write_csv(root / "indicator_candidate_validations.csv", rows)
    _write_csv(root / "validation_review_queue.csv", possible + review)
    _write_csv(root / "possible_indicators.csv", possible)
    _write_csv(root / "rejected_candidates.csv", rejected)
    _write_csv(root / "manual_review_workspace.csv", possible + review)
    _write_csv(root / "review_decisions_template.csv", [{k: d.get(k, "") for k in decisions[0]} for d in [{**decisions[0], "proposed_decision": "", "reviewer": "", "decision_reason": ""}] + decisions[1:]])
    _write_csv(root / "review_decisions_filled.csv", decisions)
    _write_csv(root / "accepted_candidate_inputs.csv", accepted)
    _write_csv(root / "indicator_preparation_database.csv", database)
    _write_csv(root / "indicator_evidence_links.csv", [{
        "evidence_link_id": f"demo_link_{idx+1:03d}",
        "preparation_indicator_id": row["preparation_indicator_id"],
        "candidate_id": row["candidate_id"],
        "document_id": row["document_id"],
        "page_number": row["page_number"],
        "quote": row["quote"],
        "source_engine": row["source_engine"],
        "source_trace_type": "text_evidence",
        "demo_data": "true",
        "synthetic_source": "true",
    } for idx, row in enumerate(database)])
    _write_jsonl(root / "indicator_lineage.jsonl", [{
        "preparation_indicator_id": row["preparation_indicator_id"],
        "candidate_id": row["candidate_id"],
        "source_modules": ["ESGProductionControlCenter.demo"],
        "lineage_complete": True,
        "demo_data": True,
        "synthetic_source": True,
    } for row in database])
    metadata = {
        "demo_data": True,
        "synthetic_source": True,
        "company": DEMO_COMPANY,
        "fiscal_year": DEMO_YEAR,
        "document": DEMO_DOCUMENT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warning": "Données synthétiques — démonstration uniquement. Aucun score ESG. Aucun indicateur final validé.",
        "candidates_count": len(rows),
        "possible_indicator_count": len(possible),
        "needs_review_count": len(review),
        "reject_candidate_count": len(rejected),
        "accepted_candidate_count": len(accepted),
        "preparation_database_rows": len(database),
    }
    (root / "demo_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "success", "demo_dir": str(root), **metadata}


def write_demo_business_report(demo_dir: str | Path) -> list[str]:
    root = Path(demo_dir)
    metadata = json.loads((root / "demo_metadata.json").read_text(encoding="utf-8"))
    files = [root / "business_demo_report.md", root / "business_demo_summary.json", root / "business_demo_results.csv"]
    results = list(csv.DictReader((root / "indicator_candidate_validations.csv").open("r", encoding="utf-8")))
    _write_csv(files[2], results)
    files[1].write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    files[0].write_text(
        "\n".join([
            "# Rapport métier démo",
            "",
            "Données synthétiques — démonstration uniquement.",
            f"Entreprise: {metadata['company']}",
            f"Année: {metadata['fiscal_year']}",
            f"Document: {metadata['document']}",
            f"Informations candidates: {metadata['candidates_count']}",
            f"Informations à revoir: {metadata['needs_review_count']}",
            f"Décisions humaines simulées: {metadata['accepted_candidate_count'] + 2}",
            f"Base préparatoire: {metadata['preparation_database_rows']} lignes",
            "",
            "Aucun score ESG n’est produit.",
            "Aucun indicateur final validé n’est produit.",
        ]) + "\n",
        encoding="utf-8",
    )
    return [str(p) for p in files]

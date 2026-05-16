from __future__ import annotations

import csv
from pathlib import Path


PREP_FIELDS = [
    "preparation_indicator_id", "indicator_database_status", "candidate_id", "document_id",
    "company", "fiscal_year", "source_engine", "indicator_family", "indicator_key",
    "indicator_label", "value_raw", "unit_raw", "year_raw", "value_prepared",
    "unit_prepared", "year_prepared", "page_number", "quote", "evidence_id",
    "table_id", "cell_id", "figure_id", "reviewer", "decision_reason",
    "is_final_indicator", "score_produced",
]


def make_indicator_output(root: Path, name: str, rows: list[dict[str, str]]) -> Path:
    output_dir = root / name
    output_dir.mkdir(parents=True)
    with (output_dir / "indicator_preparation_database.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREP_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            base = {field: "" for field in PREP_FIELDS}
            base.update(row)
            base.setdefault("indicator_database_status", "preparation_only")
            writer.writerow(base)
    with (output_dir / "indicator_evidence_links.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["preparation_indicator_id", "evidence_id", "document_id"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "preparation_indicator_id": row.get("preparation_indicator_id", ""),
                "evidence_id": row.get("evidence_id", ""),
                "document_id": row.get("document_id", ""),
            })
    (output_dir / "indicator_lineage.jsonl").write_text("", encoding="utf-8")
    (output_dir / "indicator_database_summary.json").write_text('{"status":"preparation_only"}\n', encoding="utf-8")
    return output_dir


def sample_rows() -> list[dict[str, str]]:
    return [
        {
            "preparation_indicator_id": "prep_1",
            "candidate_id": "cand_1",
            "document_id": "doc_lvmh_2024",
            "company": "LVMH",
            "fiscal_year": "2024",
            "source_engine": "table",
            "indicator_family": "environment",
            "indicator_key": "ghg_emissions_scope_1_2",
            "indicator_label": "GHG emissions",
            "value_prepared": "12.5",
            "unit_prepared": "tCO2e",
            "year_prepared": "2024",
            "page_number": "10",
            "quote": "GHG emissions were 12.5 tCO2e.",
            "evidence_id": "ev_1",
            "cell_id": "cell_1",
            "decision_reason": "accept_candidate",
        },
        {
            "preparation_indicator_id": "prep_2",
            "candidate_id": "cand_2",
            "document_id": "doc_lvmh_2024",
            "company": "LVMH",
            "fiscal_year": "2024",
            "source_engine": "text",
            "indicator_family": "governance",
            "indicator_key": "roe",
            "indicator_label": "ROE",
            "value_prepared": "8.1",
            "unit_prepared": "%",
            "year_prepared": "2024",
            "page_number": "30",
            "quote": "ROE reached 8.1%.",
            "evidence_id": "ev_2",
        },
    ]

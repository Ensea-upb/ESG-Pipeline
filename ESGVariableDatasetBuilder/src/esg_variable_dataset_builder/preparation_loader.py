from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_csv, read_jsonl, write_csv, write_json, write_jsonl


PREPARATION_FIELDS = [
    "preparation_indicator_id", "candidate_id", "document_id", "company", "fiscal_year",
    "source_engine", "indicator_family", "indicator_key", "indicator_label", "value_raw",
    "unit_raw", "year_raw", "corrected_value", "normalized_value", "value_prepared", "unit_prepared", "year_prepared",
    "page_number", "quote", "evidence_id", "table_id", "cell_id", "figure_id",
    "reviewer", "decision_reason", "indicator_database_status", "is_final_indicator",
    "score_produced",
]


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def load_preparation_output(source_dir: Path) -> dict[str, Any]:
    prep_rows = read_csv(source_dir / "indicator_preparation_database.csv")
    evidence_rows = read_csv(source_dir / "indicator_evidence_links.csv")
    lineage_rows = read_jsonl(source_dir / "indicator_lineage.jsonl")
    loaded = []
    findings = []
    for row in prep_rows:
        if row.get("indicator_database_status") and row.get("indicator_database_status") != "preparation_only":
            findings.append({"severity": "error", "category": "invalid_status", "preparation_indicator_id": row.get("preparation_indicator_id", "")})
            continue
        if _truthy(row.get("is_final_indicator", "")):
            findings.append({"severity": "error", "category": "final_indicator_claim", "preparation_indicator_id": row.get("preparation_indicator_id", "")})
            continue
        if _truthy(row.get("score_produced", "")):
            findings.append({"severity": "error", "category": "score_produced", "preparation_indicator_id": row.get("preparation_indicator_id", "")})
            continue
        normalized = {field: row.get(field, "") for field in PREPARATION_FIELDS}
        if not normalized["indicator_key"]:
            normalized["indicator_key"] = row.get("indicator_key_candidate", "") or row.get("corrected_indicator_key", "")
        loaded.append(normalized)
    return {
        "records": loaded,
        "evidence_links": evidence_rows,
        "lineage": lineage_rows,
        "findings": findings,
        "empty_database_warning": len(prep_rows) == 0,
    }


def write_preparation_loading_outputs(loaded: dict[str, Any], output_dir: Path) -> None:
    records = loaded["records"]
    write_csv(output_dir / "loaded_preparation_records.csv", records, PREPARATION_FIELDS)
    write_jsonl(output_dir / "loaded_preparation_records.jsonl", records)
    evidence = loaded["evidence_links"]
    evidence_fields = list(evidence[0].keys()) if evidence else ["preparation_indicator_id", "evidence_id"]
    write_csv(output_dir / "loaded_evidence_links.csv", evidence, evidence_fields)
    write_jsonl(output_dir / "loaded_lineage.jsonl", loaded["lineage"])
    write_json(
        output_dir / "preparation_loading_summary.json",
        {
            "records_count": len(records),
            "evidence_links_count": len(evidence),
            "lineage_records_count": len(loaded["lineage"]),
            "findings_count": len(loaded["findings"]),
            "empty_database_warning": loaded["empty_database_warning"],
            "findings": loaded["findings"],
        },
    )

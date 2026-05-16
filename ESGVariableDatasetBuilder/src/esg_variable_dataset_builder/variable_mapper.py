from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .io_utils import write_csv, write_json, write_jsonl
from .variable_dictionary import load_variable_dictionary


MAPPING_FIELDS = [
    "company", "year", "document_id", "preparation_indicator_id", "variable_name",
    "mapping_status", "mapping_confidence", "mapping_reason", "indicator_family",
    "indicator_key", "indicator_label", "value_prepared", "unit_prepared",
    "year_prepared", "page_number", "quote", "candidate_id", "source_engine",
    "evidence_id", "table_id", "cell_id", "figure_id", "reviewer", "decision_reason",
]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def _match_record(record: dict[str, Any], variables: list[dict[str, Any]]) -> list[tuple[str, float, str]]:
    hay_key = _norm(record.get("indicator_key", ""))
    hay_family = _norm(record.get("indicator_family", ""))
    hay_label = _norm(record.get("indicator_label", ""))
    hay_quote = _norm(record.get("quote", ""))
    matches = []
    for variable in variables:
        score = 0.0
        reasons = []
        keys = [_norm(item) for item in variable.get("mapped_indicator_keys", [])]
        families = [_norm(item) for item in variable.get("mapped_indicator_families", [])]
        keywords = [_norm(item) for item in variable.get("keywords_en", []) + variable.get("keywords_fr", [])]
        if hay_key and any(key and key in hay_key for key in keys):
            score += 0.7
            reasons.append("indicator_key")
        if hay_family and any(family and family in hay_family for family in families):
            score += 0.45
            reasons.append("indicator_family")
        if hay_label and any(keyword and keyword in hay_label for keyword in keywords):
            score += 0.35
            reasons.append("indicator_label_keyword")
        if hay_quote and any(keyword and keyword in hay_quote for keyword in keywords):
            score += 0.2
            reasons.append("quote_keyword")
        if score > 0:
            matches.append((variable["variable_name"], min(score, 1.0), "+".join(reasons)))
    return sorted(matches, key=lambda item: item[1], reverse=True)


def map_records(records: list[dict[str, Any]], dictionary_path: Path) -> list[dict[str, Any]]:
    variables = load_variable_dictionary(dictionary_path)
    candidates = []
    for record in records:
        matches = _match_record(record, variables)
        if not matches:
            status, variable_name, confidence, reason = "no_match", "", 0.0, "no dictionary match"
        elif len(matches) > 1 and matches[0][1] == matches[1][1]:
            status, variable_name, confidence, reason = "ambiguous", matches[0][0], matches[0][1], "multiple equal matches"
        else:
            status, variable_name, confidence, reason = "mapped", matches[0][0], matches[0][1], matches[0][2]
        candidates.append(
            {
                "company": record.get("company", ""),
                "year": record.get("fiscal_year", "") or record.get("year_prepared", ""),
                "document_id": record.get("document_id", ""),
                "preparation_indicator_id": record.get("preparation_indicator_id", ""),
                "variable_name": variable_name,
                "mapping_status": status,
                "mapping_confidence": confidence,
                "mapping_reason": reason,
                "indicator_family": record.get("indicator_family", ""),
                "indicator_key": record.get("indicator_key", ""),
                "indicator_label": record.get("indicator_label", ""),
                "value_prepared": record.get("corrected_value", "") or record.get("value_prepared", "") or record.get("normalized_value", "") or record.get("value_raw", ""),
                "unit_prepared": record.get("unit_prepared", "") or record.get("unit_raw", ""),
                "year_prepared": record.get("year_prepared", "") or record.get("year_raw", ""),
                "page_number": record.get("page_number", ""),
                "quote": record.get("quote", ""),
                "candidate_id": record.get("candidate_id", ""),
                "source_engine": record.get("source_engine", ""),
                "evidence_id": record.get("evidence_id", ""),
                "table_id": record.get("table_id", ""),
                "cell_id": record.get("cell_id", ""),
                "figure_id": record.get("figure_id", ""),
                "reviewer": record.get("reviewer", ""),
                "decision_reason": record.get("decision_reason", ""),
            }
        )
    return candidates


def write_mapping_outputs(candidates: list[dict[str, Any]], output_dir: Path) -> None:
    write_csv(output_dir / "variable_mapping_candidates.csv", candidates, MAPPING_FIELDS)
    write_jsonl(output_dir / "variable_mapping_candidates.jsonl", candidates)
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate["mapping_status"]] = counts.get(candidate["mapping_status"], 0) + 1
    write_json(output_dir / "variable_mapping_summary.json", {"mapping_candidates_count": len(candidates), "status_counts": counts})

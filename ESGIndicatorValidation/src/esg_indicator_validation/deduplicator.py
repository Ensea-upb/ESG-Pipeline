from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

log = logging.getLogger(__name__)


def apply_deduplication(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_key(row)].append(row)
    duplicate_groups: list[dict[str, Any]] = []
    group_index = 1
    for group in groups.values():
        if len(group) == 1:
            row = group[0]
            row["duplicate_status"] = "unique"
            row["canonical_validation_candidate_id"] = row["candidate_validation_id"]
            continue
        group_id = f"indicator_duplicate_group_{group_index:04d}"
        group_index += 1
        canonical = _canonical(group)
        duplicates = [r for r in group if r is not canonical]
        log.debug(
            "Duplicate group %s: %d duplicates removed (canonical=%s)",
            group_id, len(duplicates), canonical.get("candidate_validation_id", "?"),
        )
        for row in group:
            row["duplicate_group_id"] = group_id
            row["canonical_validation_candidate_id"] = canonical["candidate_validation_id"]
            row["duplicate_status"] = "canonical" if row is canonical else "duplicate_candidate"
            row["duplicate_reason"] = "same_document_family_value_unit_year_page_quote"
            if row is not canonical:
                row["validation_status"] = "reject_candidate"
                row["validation_reason"] = "duplicate candidate; canonical retained for review"
        duplicate_groups.append({
            "schema_version": "1.0.0",
            "duplicate_group_id": group_id,
            "canonical_validation_candidate_id": canonical["candidate_validation_id"],
            "group_size": len(group),
            "duplicate_reason": "same_document_family_value_unit_year_page_quote",
            "document_id": canonical.get("document_id", ""),
            "indicator_family": canonical.get("indicator_family", ""),
            "normalized_value": canonical.get("normalized_value", ""),
            "normalized_unit": canonical.get("normalized_unit", ""),
            "normalized_year": canonical.get("normalized_year", ""),
            "page_number": canonical.get("page_number", ""),
        })
    return duplicate_groups


def _key(row: dict[str, Any]) -> str:
    quote = " ".join(str(row.get("quote", "")).lower().split())[:160]
    return "|".join(str(row.get(field, "")).lower() for field in [
        "document_id", "indicator_family", "indicator_key_candidate",
        "normalized_value", "normalized_unit", "normalized_year", "page_number",
    ]) + "|" + quote


def _canonical(group: list[dict[str, Any]]) -> dict[str, Any]:
    source_priority = {"table": 0, "csv": 1, "visual": 2}
    return sorted(group, key=lambda row: (
        source_priority.get(row.get("source_engine", ""), 9),
        0 if row.get("normalized_value") else 1,
        0 if row.get("normalized_unit") else 1,
        0 if row.get("normalized_year") else 1,
        -float(row.get("confidence") or 0),
        -len(row.get("quote", "")),
    ))[0]

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Any

from .io_utils import write_csv, write_json, write_jsonl
from .variable_dictionary import FINAL_VARIABLES


SELECTED_FIELDS = [
    "company", "year", "variable_name", "selected_value", "selected_unit", "selected_status",
    "selected_source_document", "selected_page_number", "selected_quote", "selected_confidence",
    "selection_reason", "alternatives_count", "preparation_indicator_id", "candidate_id",
    "source_engine", "evidence_id", "table_id", "cell_id", "figure_id",
]


def _has_numeric(value: str) -> bool:
    return any(ch.isdigit() for ch in str(value))


_UNIT_SCALE: dict[str, float] = {
    "tco2e": 1.0, "ktco2e": 1_000.0, "mtco2e": 1_000_000.0,
    "gwh": 1.0, "mwh": 0.001, "kwh": 0.000_001,
    "m3": 1.0, "hm3": 1_000_000.0,
    "t": 1.0, "kt": 1_000.0, "mt": 1_000_000.0,
}


def _canonical_numeric(value: str, unit: str = "") -> str:
    """Return a scale-normalized numeric string for conflict detection.

    Values with commensurable units (e.g. 1 MtCO2e vs 1,000,000 tCO2e)
    are normalized to the base unit before comparison, so they do not
    trigger a spurious conflict flag.
    """
    text = str(value).strip().replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return text.lower()
    number = float(match.group(0))
    unit_key = re.sub(r"[^a-z0-9]", "", str(unit).lower())
    scale = _UNIT_SCALE.get(unit_key, 1.0)
    normalized = number * scale
    return f"{normalized:g}"


_ACCEPT_SIGNALS = re.compile(
    r"\b(?:accept|approve[ds]?|valid(?:at(?:e[ds]?|ion))?|confirm(?:e[ds]?|ation)?|oui|yes|ok)\b",
    re.IGNORECASE,
)


def _rank(row: dict[str, Any]) -> tuple[int, int, int, int, int]:
    decision = str(row.get("decision_reason", "") or "")
    reviewer_ok = bool(row.get("reviewer") or _ACCEPT_SIGNALS.search(decision))
    return (
        1 if reviewer_ok else 0,
        1 if row.get("value_prepared") else 0,
        1 if row.get("cell_id") else 0,
        len(str(row.get("quote", "") or "")),  # plus long = plus de contexte
        1 if row.get("quote") else 0,
    )


def select_values(
    mapping_candidates: list[dict[str, Any]],
    company_years: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in mapping_candidates:
        if row.get("mapping_status") == "mapped" and row.get("variable_name"):
            grouped[(row["company"], str(row["year"]), row["variable_name"])].append(row)

    selected = []
    for company, year in sorted(set(company_years)):
        for variable in FINAL_VARIABLES:
            rows = grouped.get((company, str(year), variable), [])
            if not rows:
                selected.append(_empty_selection(company, str(year), variable, "missing_from_corpus", "No mapped candidate in corpus outputs."))
                continue
            numeric_rows = [row for row in rows if _has_numeric(row.get("value_prepared", ""))]
            if numeric_rows:
                values = {_canonical_numeric(row.get("value_prepared", ""), row.get("unit_prepared", "")) for row in numeric_rows}
                if len(values) > 1:
                    selected.append(_conflict_selection(company, str(year), variable, numeric_rows))
                    continue
                chosen = sorted(numeric_rows, key=_rank, reverse=True)[0]
                selected.append(_selection_from_row(chosen, "found", "Best mapped numeric candidate selected.", len(rows)))
                continue
            qualitative_rows = [row for row in rows if row.get("quote")]
            if qualitative_rows:
                chosen = sorted(qualitative_rows, key=_rank, reverse=True)[0]
                selected.append(_selection_from_row(chosen, "qualitative_only", "Only qualitative PDF evidence available.", len(rows)))
            else:
                selected.append(_empty_selection(company, str(year), variable, "needs_review", "Mapped candidate lacks value and quote."))
    return selected


def _empty_selection(company: str, year: str, variable: str, status: str, reason: str) -> dict[str, Any]:
    return {
        "company": company, "year": year, "variable_name": variable,
        "selected_value": "", "selected_unit": "", "selected_status": status,
        "selected_source_document": "", "selected_page_number": "", "selected_quote": "",
        "selected_confidence": "", "selection_reason": reason, "alternatives_count": 0,
        "preparation_indicator_id": "", "candidate_id": "", "source_engine": "",
        "evidence_id": "", "table_id": "", "cell_id": "", "figure_id": "",
    }


def _selection_from_row(row: dict[str, Any], status: str, reason: str, alternatives_count: int) -> dict[str, Any]:
    return {
        "company": row.get("company", ""), "year": str(row.get("year", "")), "variable_name": row.get("variable_name", ""),
        "selected_value": row.get("value_prepared", ""), "selected_unit": row.get("unit_prepared", ""),
        "selected_status": status, "selected_source_document": row.get("document_id", ""),
        "selected_page_number": row.get("page_number", ""), "selected_quote": row.get("quote", ""),
        "selected_confidence": row.get("mapping_confidence", ""), "selection_reason": reason,
        "alternatives_count": max(0, alternatives_count - 1), "preparation_indicator_id": row.get("preparation_indicator_id", ""),
        "candidate_id": row.get("candidate_id", ""), "source_engine": row.get("source_engine", ""),
        "evidence_id": row.get("evidence_id", ""), "table_id": row.get("table_id", ""),
        "cell_id": row.get("cell_id", ""), "figure_id": row.get("figure_id", ""),
    }


def _conflict_selection(company: str, year: str, variable: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = sorted({str(row.get("value_prepared", "")).strip() for row in rows})
    item = _selection_from_row(rows[0], "conflicting_values", f"Incompatible values detected: {values}", len(rows))
    item["company"] = company
    item["year"] = year
    item["variable_name"] = variable
    item["selected_value"] = ""
    return item


def write_selection_outputs(selected: list[dict[str, Any]], output_dir: Path) -> None:
    write_csv(output_dir / "selected_variable_values.csv", selected, SELECTED_FIELDS)
    write_jsonl(output_dir / "selected_variable_values.jsonl", selected)
    audit_rows = [{"company": row["company"], "year": row["year"], "variable_name": row["variable_name"], "status": row["selected_status"], "reason": row["selection_reason"]} for row in selected]
    write_jsonl(output_dir / "variable_selection_audit.jsonl", audit_rows)
    counts: dict[str, int] = {}
    for row in selected:
        counts[row["selected_status"]] = counts.get(row["selected_status"], 0) + 1
    write_json(output_dir / "variable_selection_summary.json", {"selected_variables_count": len(selected), "status_counts": counts})

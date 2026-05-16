from __future__ import annotations

import re


UNIT_PATTERNS = [
    ("tCO2e", re.compile(r"\b(?:tco2e|tonnes?\s+co2e)\b", re.I)),
    ("ktCO2e", re.compile(r"\bktco2e\b", re.I)),
    ("MtCO2e", re.compile(r"\bmtco2e\b", re.I)),
    ("GWh", re.compile(r"\bgwh\b", re.I)),
    ("MWh", re.compile(r"\bmwh\b", re.I)),
    ("kWh", re.compile(r"\bkwh\b", re.I)),
    ("m3", re.compile(r"\bm3\b|\bm³\b", re.I)),
    ("%", re.compile(r"%")),
    ("tonnes", re.compile(r"\btonnes?\b", re.I)),
    ("employees", re.compile(r"\bemployees?\b|\bheadcount\b", re.I)),
    ("hours", re.compile(r"\bhours?\b", re.I)),
    ("accident rate", re.compile(r"\baccident rate\b|\binjury rate\b", re.I)),
]


def normalize_candidate(row: dict[str, str]) -> dict[str, str]:
    text = " ".join([row.get("raw_unit", ""), row.get("label", ""), row.get("quote", "")])
    value = _normalize_value(row.get("raw_value", ""))
    unit, unit_source = _detect_unit(row, text)
    year, year_source, inferred = _detect_year(row)
    notes = []
    if not value and row.get("information_type") in {"observed_metric", "table_metric_candidate", "visual_metric_candidate", "target"}:
        notes.append("missing_numeric_value")
    if not unit:
        notes.append("missing_unit")
    if not year:
        notes.append("missing_year")
    status = "complete" if value and unit and year else "partial"
    if not value and not unit and not year:
        status = "not_normalized"
    return {
        "normalized_value": value,
        "normalized_unit": unit,
        "normalized_year": year,
        "year_inferred": "True" if inferred else "False",
        "normalization_status": status,
        "normalization_notes": "|".join(notes),
        "unit_detection_source": unit_source,
        "year_detection_source": year_source,
    }


def _normalize_value(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    match = re.search(r"-?\d[\d,\s]*(?:\.\d+)?", raw)
    if not match:
        return ""
    return match.group(0).replace(",", "").replace(" ", "")


def _detect_unit(row: dict[str, str], text: str) -> tuple[str, str]:
    raw_unit = (row.get("raw_unit") or "").strip()
    if raw_unit:
        for canonical, pattern in UNIT_PATTERNS:
            if pattern.search(raw_unit):
                return canonical, "raw_unit"
        return raw_unit, "raw_unit"
    for canonical, pattern in UNIT_PATTERNS:
        if pattern.search(text):
            return canonical, "quote_or_label"
    return "", ""


def _detect_year(row: dict[str, str]) -> tuple[str, str, bool]:
    for field in ("year", "fiscal_year"):
        match = re.search(r"\b(20\d{2}|19\d{2})\b", row.get(field, "") or "")
        if match:
            return match.group(1), field, False
    years_in_quote = re.findall(r"\b(20\d{2}|19\d{2})\b", row.get("quote", "") or "")
    if years_in_quote:
        return max(years_in_quote), "quote", True
    fiscal = row.get("fiscal_year", "")
    if fiscal:
        return fiscal, "fiscal_year_fallback", True
    return "", "", False

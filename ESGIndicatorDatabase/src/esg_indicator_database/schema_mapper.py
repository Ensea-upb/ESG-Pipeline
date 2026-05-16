from __future__ import annotations


DOMAIN_BY_FAMILY = {
    "ghg_emissions": "environmental",
    "energy": "environmental",
    "water": "environmental",
    "waste": "environmental",
    "workforce": "social",
    "diversity": "social",
    "health_safety": "social",
    "governance": "governance",
    "board_governance": "governance",
    "policy": "transversal",
    "risk": "transversal",
    "methodology": "transversal",
    "boundary": "transversal",
}


def map_schema(row: dict[str, str]) -> dict[str, str]:
    family = row.get("indicator_family") or row.get("corrected_indicator_family") or "unknown"
    text = " ".join([row.get("quote", ""), row.get("label", ""), row.get("indicator_key_candidate", "")]).lower()
    standard = ""
    for candidate in ["ESRS", "GRI", "GHG Protocol"]:
        if candidate.lower() in text:
            standard = candidate
            break
    unit = row.get("corrected_unit") or row.get("normalized_unit") or row.get("raw_unit", "")
    return {
        "indicator_domain": DOMAIN_BY_FAMILY.get(family, "unknown"),
        "indicator_topic": family if family else "unknown",
        "indicator_metric_name": row.get("label") or row.get("indicator_key_candidate") or "unknown",
        "indicator_unit_category": _unit_category(unit),
        "indicator_period_type": "annual" if (row.get("corrected_year") or row.get("normalized_year") or row.get("fiscal_year")) else "unknown",
        "indicator_scope": "candidate_scope",
        "indicator_geography": _geo(text),
        "indicator_methodology": "candidate_methodology" if standard else "",
        "indicator_standard_reference": standard,
        "indicator_schema_confidence": "0.50" if family != "unknown" else "0.20",
        "schema_mapping_notes": "preparation mapping only; not regulatory validation",
    }


def _unit_category(unit: str) -> str:
    u = (unit or "").lower()
    if "%" in u:
        return "percentage"
    if "co2" in u:
        return "emissions"
    if "wh" in u:
        return "energy"
    if "m3" in u:
        return "volume"
    if "employee" in u or "headcount" in u:
        return "people"
    return "unknown"


def _geo(text: str) -> str:
    for geo in ["france", "europe", "group"]:
        if geo in text:
            return geo
    return ""

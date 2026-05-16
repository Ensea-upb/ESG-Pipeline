from __future__ import annotations

from collections import Counter
from typing import Any


CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "climate": [
        "emissions", "greenhouse gas", "ghg", "scope 1", "scope 2", "scope 3",
        "co2e", "tco2e", "mtco2e", "ktco2e", "carbon", "co2", "biogenic",
        "climate", "carbone", "gaz a effet de serre",
    ],
    "energy": [
        "energy", "electricity", "fuel", "gas", "gwh", "mwh", "kwh", "gj", "mj",
        "renewable", "fossil", "natural gas", "heat", "steam", "energetique",
        "consommation energetique", "energie renouvelable",
    ],
    "water": [
        "water", "withdrawal", "discharge", "m3", "litre", "liter",
        "sewage", "wastewater", "recycled water", "rainfall", "hm3",
        "eau", "prelevement", "rejets",
    ],
    "waste": [
        "waste", "recycled", "hazardous waste", "landfill", "incinerated",
        "diverted", "valorised", "dechets", "recyclage",
    ],
    "workforce": [
        "employees", "headcount", "workforce", "staff", "fte",
        "part-time", "contractor", "effectif", "salaries", "collaborateurs",
    ],
    "diversity": [
        "women", "female", "gender", "diversity", "parity",
        "inclusion", "femmes", "parite", "mixite",
    ],
    "health_safety": [
        "injury", "accident", "frequency rate", "lost time", "fatality",
        "near miss", "recordable", "trir", "ltir", "taux de frequence",
        "accidents du travail",
    ],
    "governance": [
        "board", "directors", "independence", "committee",
        "administrateurs", "independants", "conseil d administration",
    ],
    "target": [
        "target", "objective", "goal", "commitment", "by 2030", "by 2035",
        "by 2040", "by 2050", "reduction target", "net zero", "objectif",
        "cible", "engagement", "trajectoire",
    ],
    "biodiversity": [
        "biodiversity", "ecosystem", "habitat", "species", "land use",
        "hectares", "ha", "deforestation", "biodiversite",
    ],
    "supply_chain": [
        "suppliers", "supply chain", "procurement", "value chain",
        "fournisseurs", "chaine d approvisionnement", "scope 3",
    ],
    "methodology": [
        "ghg protocol", "esrs", "gri", "market-based", "location-based",
        "methodologie", "protocole", "protocol",
    ],
    "boundary": [
        "group", "france", "europe", "excluding", "including", "subsidiaries",
        "groupe", "perimetre", "consolidation",
    ],
}

FAMILY_MAP: dict[str, str] = {
    "climate": "ghg_emissions",
    "energy": "energy",
    "water": "water",
    "waste": "waste",
    "workforce": "workforce",
    "diversity": "diversity",
    "health_safety": "health_safety",
    "governance": "governance",
    "target": "target",
    "biodiversity": "biodiversity",
    "supply_chain": "supply_chain",
}


def classify_text(text: str) -> tuple[str, list[str], float]:
    """Return (category, matched_keywords, confidence).

    Primary: semantic classification via sentence-transformers (multilingual,
    no keyword lists needed). Falls back to best-match keyword classification
    if the model is unavailable or the semantic score is too low.
    """
    # ── Semantic pass (sentence-transformers) ────────────────────────────
    try:
        from .semantic_classifier import classify_text_semantic
        sem_category, sem_confidence = classify_text_semantic(text, threshold=0.30)
        if sem_category != "unknown" and sem_confidence > 0.0:
            return sem_category, [], sem_confidence
    except Exception:
        pass

    # ── Keyword fallback ─────────────────────────────────────────────────
    lower = text.lower()
    best_category = "unknown"
    best_matched: list[str] = []
    best_count = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in lower]
        if len(matched) > best_count:
            best_category = category
            best_matched = matched
            best_count = len(matched)

    if best_category == "unknown":
        return "unknown", [], 0.2

    confidence = min(0.6, 0.35 + 0.05 * best_count)
    return best_category, best_matched, confidence


def family_for_category(category: str) -> str:
    return FAMILY_MAP.get(category, "unknown")


def classify_rows(reconstructed: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table in reconstructed:
        for idx, row in enumerate(table.get("matrix") or []):
            row_text = " ".join(str(cell) for cell in row if str(cell).strip())
            category, matched, confidence = classify_text(row_text)
            rows.append({
                "schema_version": "0.4.0",
                "document_id": table.get("document_id", ""),
                "table_id": table.get("table_id", ""),
                "page_number": table.get("page_number"),
                "row_index": idx,
                "row_text": row_text,
                "row_category": category,
                "matched_keywords": matched,
                "classification_confidence": confidence,
                "review_required": True,
            })
    return rows, {
        "schema_version": "0.4.0",
        "row_classifications_count": len(rows),
        "row_category_distribution": dict(Counter(row["row_category"] for row in rows)),
    }

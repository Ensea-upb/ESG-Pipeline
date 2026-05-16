from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Descriptions sémantiques par famille (même logique que semantic_classifier.py
# dans ESGTableExtraction — descriptions bilingues FR/EN pour la robustesse).
_FAMILY_DESCRIPTIONS: dict[str, str] = {
    "ghg_emissions": (
        "GHG greenhouse gas emissions CO2 scope 1 scope 2 scope 3 tCO2e carbon "
        "émissions gaz effet serre carbone bilan carbone empreinte carbone"
    ),
    "energy": (
        "energy electricity renewable fossil GWh MWh kWh fuel consumption "
        "énergie électricité renouvelable combustible consommation énergétique"
    ),
    "water": (
        "water withdrawal discharge cubic meters m3 wastewater consumption "
        "eau prélèvement rejet mètres cubes consommation eau stress hydrique"
    ),
    "waste": (
        "waste recycling landfill hazardous valorisation diverted "
        "déchets recyclage enfouissement valorisation dangereux"
    ),
    "workforce": (
        "employees headcount FTE workforce staff permanent temporary "
        "effectif salariés collaborateurs personnel temps plein"
    ),
    "diversity": (
        "women gender diversity parity inclusion representation "
        "femmes parité genre mixité représentation inclusion"
    ),
    "health_safety": (
        "injury accident safety frequency rate lost time fatality TRIR LTIR "
        "accidents sécurité taux fréquence accidents travail blessures"
    ),
    "governance": (
        "board directors independence committee governance audit remuneration "
        "conseil administrateurs indépendants gouvernance comité rémunération"
    ),
    "policy": (
        "policy commitment code of conduct human rights due diligence engagement "
        "politique engagement code conduite droits humains vigilance"
    ),
    "risk": (
        "risk exposure uncertainty climate risk transition risk litigation "
        "risque exposition incertitude risque climatique risque transition"
    ),
    "methodology": (
        "GHG protocol ESRS GRI methodology assurance market-based location-based "
        "protocole référentiel méthodologie vérification tiers assurance"
    ),
    "boundary": (
        "boundary perimeter consolidation scope excluding including subsidiaries "
        "périmètre groupe consolidation inclus exclus filiales couverture"
    ),
}

_encoder_cache: object = None


def _load_encoder():
    global _encoder_cache
    if _encoder_cache is not None:
        return _encoder_cache
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        families = list(_FAMILY_DESCRIPTIONS.keys())
        descriptions = [_FAMILY_DESCRIPTIONS[f] for f in families]
        embeddings = model.encode(descriptions, normalize_embeddings=True)
        _encoder_cache = (model, families, embeddings, np)
        return _encoder_cache
    except Exception:
        return None


def _classify_semantic(text: str) -> tuple[str, float]:
    enc = _load_encoder()
    if enc is None or not text.strip():
        return "unknown", 0.0
    model, families, fam_embeddings, np = enc
    try:
        emb = model.encode([text.strip()], normalize_embeddings=True)
        scores = np.dot(emb, fam_embeddings.T)[0]
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        if best_score < 0.28:
            return "unknown", best_score
        return families[best_idx], round(min(0.6, 0.35 + best_score * 0.4), 3)
    except Exception:
        return "unknown", 0.0


FAMILIES = {
    "ghg_emissions": ["scope 1", "scope 2", "scope 3", "ghg", "co2", "emission", "carbon", "tco2e"],
    "energy": ["energy", "electricity", "gwh", "mwh", "kwh"],
    "water": ["water", "withdrawal", "consumption", "m3"],
    "waste": ["waste", "recycled", "hazardous"],
    "workforce": ["employee", "workforce", "headcount", "staff"],
    "diversity": ["women", "female", "gender", "diversity"],
    "health_safety": ["injury", "accident", "lost time", "safety"],
    "governance": ["board", "independence", "committee", "director", "governance"],
    "policy": ["policy", "commitment", "committed"],
    "risk": ["risk", "exposure"],
    "methodology": ["ghg protocol", "esrs", "gri", "market-based", "location-based", "assurance"],
    "boundary": ["group", "france", "europe", "excluding", "including", "scope of consolidation"],
}


def map_indicator_family(row: dict[str, str], normalized: dict[str, str]) -> dict[str, object]:
    text = " ".join([
        row.get("information_type", ""), row.get("esg_category", ""), row.get("label", ""),
        row.get("quote", ""), normalized.get("normalized_unit", ""),
    ]).lower()
    if row.get("information_type") == "risk_statement":
        return _payload("risk", row, 0.55, "information_type risk_statement")
    if row.get("information_type") == "policy_or_commitment":
        return _payload("policy", row, 0.55, "information_type policy_or_commitment")
    if row.get("information_type") == "methodology_context":
        return _payload("methodology", row, 0.55, "information_type methodology_context")
    if row.get("information_type") == "boundary_context":
        return _payload("boundary", row, 0.55, "information_type boundary_context")
    best_family = "unknown"
    best_matched: list[str] = []
    for family, keywords in FAMILIES.items():
        matched = [kw for kw in keywords if kw in text]
        if len(matched) > len(best_matched):
            best_family = family
            best_matched = matched
    if best_matched:
        return _payload(best_family, row, min(0.6, 0.4 + 0.05 * len(best_matched)), "matched: " + ", ".join(best_matched[:5]))

    # Aucun mot-clé correspondant → fallback sémantique
    sem_family, sem_confidence = _classify_semantic(text)
    if sem_family != "unknown":
        return _payload(sem_family, row, sem_confidence, "semantic_embedding_fallback")

    return _payload("unknown", row, 0.2, "no reliable family keyword matched")


def _payload(family: str, row: dict[str, str], confidence: float, reason: str) -> dict[str, object]:
    label = row.get("label") or f"{family} candidate"
    return {
        "indicator_family": family,
        "indicator_key_candidate": f"{family}:{_slug(label)}",
        "indicator_label_candidate": label[:180],
        "indicator_mapping_confidence": confidence,
        "indicator_mapping_reason": reason,
    }


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    return "_".join(part for part in cleaned.split("_") if part)[:80] or "candidate"

"""Semantic ESG category classification for visual OCR and caption text.

Uses paraphrase-multilingual-MiniLM-L12-v2 to classify noisy OCR text
into ESG categories without brittle keyword lists. Mirrors the same module
in ESGTableExtraction but scoped to visual content (shorter, noisier text).
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

_CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "climate": (
        "GHG greenhouse gas emissions CO2 carbon scope 1 scope 2 scope 3 tCO2e climate change "
        "émissions gaz effet serre carbone empreinte carbone bilan carbone"
    ),
    "energy": (
        "energy consumption electricity fuel renewable fossil GWh MWh kWh energy intensity "
        "consommation énergie électricité énergies renouvelables combustibles"
    ),
    "water": (
        "water withdrawal consumption discharge m3 cubic meters wastewater "
        "prélèvement eau consommation eau rejets stress hydrique"
    ),
    "waste": (
        "waste recycling landfill hazardous valorisation diverted tonnes "
        "déchets recyclage valorisation enfouissement dangereux"
    ),
    "workforce": (
        "employees headcount FTE workforce staff contractors permanent temporary "
        "effectif salariés collaborateurs personnel temps plein"
    ),
    "diversity": (
        "women female gender diversity parity inclusion representation board "
        "femmes parité genre mixité représentation"
    ),
    "health_safety": (
        "injury accident frequency rate lost time TRIR LTIR fatality recordable "
        "accidents taux fréquence sécurité blessures"
    ),
    "governance": (
        "board directors independence committee governance ethics audit remuneration "
        "conseil administrateurs indépendants gouvernance comité"
    ),
    "target": (
        "target objective goal commitment net zero by 2030 by 2040 by 2050 science-based reduction "
        "objectif cible engagement net zéro trajectoire réduction"
    ),
    "biodiversity": (
        "biodiversity ecosystem habitat species land use hectares deforestation "
        "biodiversité écosystème espèces déforestation"
    ),
}

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_encoder_cache: Any = None


def _load_encoder():
    global _encoder_cache
    if _encoder_cache is not None:
        return _encoder_cache
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        model = SentenceTransformer(_MODEL_NAME)
        categories = list(_CATEGORY_DESCRIPTIONS.keys())
        descriptions = [_CATEGORY_DESCRIPTIONS[c] for c in categories]
        embeddings = model.encode(descriptions, normalize_embeddings=True)
        _encoder_cache = (model, categories, embeddings, np)
        return _encoder_cache
    except ImportError:
        log.debug("sentence-transformers not installed — semantic visual classification disabled.")
        return None
    except Exception as exc:
        log.warning("Could not load semantic model: %s", exc)
        return None


def classify_esg_category(text: str, threshold: float = 0.28) -> tuple[str, float]:
    """Return (esg_category, confidence) for the given text.

    Falls back to ("general", 0.0) when the model is unavailable or the
    best score is below threshold.
    """
    enc = _load_encoder()
    if enc is None or not text.strip():
        return "general", 0.0
    model, categories, cat_embeddings, np = enc
    try:
        emb = model.encode([text.strip()[:400]], normalize_embeddings=True)
        scores = np.dot(emb, cat_embeddings.T)[0]
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        if best_score < threshold:
            return "general", best_score
        confidence = round(min(0.6, 0.35 + best_score * 0.4), 3)
        return categories[best_idx], confidence
    except Exception as exc:
        log.debug("classify_esg_category failed: %s", exc)
        return "general", 0.0

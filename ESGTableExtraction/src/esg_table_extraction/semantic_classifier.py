"""
semantic_classifier.py
======================
Classification sémantique des lignes de tableau ESG via sentence-transformers.

Remplace la classification par sac de mots-clés de metric_classifier.py.
Au lieu de chercher des tokens exacts, ce module encode le texte et les
descriptions de catégories dans un espace vectoriel commun — la catégorie
dont la description est la plus proche (cosine) est retournée.

Avantage : "empreinte carbone" = "carbon footprint" = "GHG emissions" sans
maintenir de listes de mots-clés multilingues.

Modèle : paraphrase-multilingual-MiniLM-L12-v2 (~470 MB, CPU-compatible)
Fallback : keyword classifier si sentence-transformers non installé.

Source : https://www.sbert.net/
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

# Descriptions sémantiques des catégories ESG — en anglais et en français
# pour maximiser la couverture multilingue.
_CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "climate": (
        "GHG greenhouse gas emissions CO2 carbon scope 1 scope 2 scope 3 tCO2e climate change "
        "émissions gaz effet serre carbone empreinte carbone bilan carbone neutralité carbone"
    ),
    "energy": (
        "energy consumption electricity fuel renewable fossil GWh MWh kWh energy intensity "
        "consommation énergie électricité énergies renouvelables combustibles fossiles"
    ),
    "water": (
        "water withdrawal consumption discharge m3 cubic meters water stress wastewater "
        "prélèvement eau consommation eau rejets eau stress hydrique"
    ),
    "waste": (
        "waste recycling landfill hazardous valorisation diverted tonnes "
        "déchets recyclage valorisation enfouissement déchets dangereux"
    ),
    "workforce": (
        "employees headcount FTE workforce staff contractors permanent temporary "
        "effectif salariés collaborateurs personnel temps plein"
    ),
    "diversity": (
        "women female gender diversity parity inclusion DEI representation board "
        "femmes parité genre mixité représentation conseil administration"
    ),
    "health_safety": (
        "injury accident frequency rate lost time TRIR LTIR fatality near miss recordable "
        "accidents taux fréquence accidents travail sécurité blessures"
    ),
    "governance": (
        "board directors independence committee governance ethics audit remuneration "
        "conseil administrateurs indépendants gouvernance éthique comité audit"
    ),
    "target": (
        "target objective goal commitment net zero by 2030 by 2040 by 2050 science-based reduction "
        "objectif cible engagement net zéro trajectoire réduction d'ici 2030"
    ),
    "biodiversity": (
        "biodiversity ecosystem habitat species land use hectares deforestation "
        "biodiversité écosystème habitat espèces utilisation terres déforestation"
    ),
    "supply_chain": (
        "suppliers supply chain procurement value chain scope 3 upstream "
        "fournisseurs chaîne approvisionnement achats responsables"
    ),
    "methodology": (
        "GHG protocol ESRS GRI market-based location-based assurance methodology "
        "protocole référentiel méthode marché localisation vérification tiers"
    ),
    "boundary": (
        "group boundary perimeter consolidation scope excluding including subsidiaries "
        "périmètre groupe consolidation inclus exclus filiales couverture"
    ),
}

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_encoder_cache: Any = None
_embeddings_cache: dict[str, Any] | None = None


def _load_encoder():
    global _encoder_cache, _embeddings_cache
    if _encoder_cache is not None:
        return _encoder_cache, _embeddings_cache

    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        log.info("Chargement du modèle sémantique (%s)…", _MODEL_NAME)
        model = SentenceTransformer(_MODEL_NAME)
        # Pré-calculer les embeddings des descriptions de catégories
        categories = list(_CATEGORY_DESCRIPTIONS.keys())
        descriptions = [_CATEGORY_DESCRIPTIONS[c] for c in categories]
        embeddings = model.encode(descriptions, normalize_embeddings=True)
        _encoder_cache = (model, categories, embeddings, np)
        _embeddings_cache = {"categories": categories, "embeddings": embeddings}
        log.info("Modèle sémantique chargé (%d catégories).", len(categories))
        return _encoder_cache, _embeddings_cache
    except ImportError:
        log.debug("sentence-transformers non installé — classification sémantique désactivée.")
        return None, None
    except Exception as exc:
        log.warning("Impossible de charger le modèle sémantique (%s).", exc)
        return None, None


def classify_text_semantic(text: str, threshold: float = 0.30) -> tuple[str, float]:
    """Classifie un texte dans une catégorie ESG via similarité sémantique.

    Retourne (category, confidence).
    Si le score est sous threshold ou si le modèle n'est pas disponible,
    retourne ("unknown", 0.0) pour que le fallback keyword soit utilisé.

    Args:
        text: texte à classifier (ligne de tableau, libellé, passage).
        threshold: score cosine minimum pour accepter la classification.
    """
    encoder_tuple, _ = _load_encoder()
    if encoder_tuple is None:
        return "unknown", 0.0

    model, categories, cat_embeddings, np = encoder_tuple
    if not text or not text.strip():
        return "unknown", 0.0

    try:
        text_embedding = model.encode([text.strip()], normalize_embeddings=True)
        scores = np.dot(text_embedding, cat_embeddings.T)[0]
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        if best_score < threshold:
            return "unknown", best_score
        category = categories[best_idx]
        confidence = round(min(0.6, 0.35 + best_score * 0.4), 3)
        return category, confidence
    except Exception as exc:
        log.debug("classify_text_semantic a échoué : %s", exc)
        return "unknown", 0.0

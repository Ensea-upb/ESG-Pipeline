"""
gliner_extractor.py
===================
Extraction de métriques ESG par NER zero-shot avec GLiNER.

GLiNER (Zaratiana et al., 2023-2025) utilise DeBERTa-v3 comme encodeur
bidirectionnel et prédit des spans d'entités pour des labels arbitraires
sans fine-tuning. GLiNER2 (2025, EMNLP) unifie NER et extraction structurée.

Source : https://arxiv.org/abs/2311.08526
Modèle : urchade/gliner_medium-v2.1 (HuggingFace, ~400MB, CPU-compatible)

Ce module COMPLÈTE metric_candidate_extractor.py — il ne le remplace pas.
Les deux résultats sont fusionnés par merge_candidates().

Si GLiNER n'est pas installé, retourne une liste vide (pas de crash).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Labels ESG pour GLiNER — libellés en langage naturel, pas des codes.
# GLiNER encode ces labels et les compare aux spans du texte.
_GLINER_LABELS = [
    "metric value",           # valeur numérique mesurée (12 450, 3.2, 18%)
    "measurement unit",       # unité de mesure (tCO2e, MWh, m3, %)
    "reporting year",         # année de reporting (2023, 2022)
    "ghg scope",              # portée GHG (scope 1, scope 2, scope 3)
    "esg indicator name",     # nom de l'indicateur (GHG emissions, water withdrawal)
]

_MODEL_NAME = "urchade/gliner_medium-v2.1"
_model_cache: Any = None

# Generic metric IDs that are noise — filter them out at merge time
_GENERIC_METRIC_IDS: frozenset[str] = frozenset({"esg_metric", "gliner_metric", "metric", "esg", "indicator", "kpi", "value"})


_LOCAL_MODEL_DIR = Path(__file__).resolve().parents[1] / ".model_cache" / "gliner_medium_v2"


def _load_gliner_model():
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    try:
        from gliner import GLiNER
    except ImportError:
        log.warning("gliner non installé. Installez : pip install gliner")
        return None

    # Essai 1 : modèle déjà téléchargé localement
    if _LOCAL_MODEL_DIR.exists():
        try:
            log.info("Chargement de GLiNER depuis le cache local %s…", _LOCAL_MODEL_DIR)
            _model_cache = GLiNER.from_pretrained(str(_LOCAL_MODEL_DIR), local_files_only=True)
            log.info("GLiNER chargé (cache local).")
            return _model_cache
        except Exception as exc:
            log.debug("Cache local GLiNER invalide (%s), re-téléchargement…", exc)

    # Essai 2 : téléchargement HuggingFace avec local_dir pour éviter les symlinks Windows
    try:
        import os
        _LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        log.info("Téléchargement de GLiNER (%s)…", _MODEL_NAME)
        _model_cache = GLiNER.from_pretrained(
            _MODEL_NAME,
            local_dir=str(_LOCAL_MODEL_DIR),
            local_dir_use_symlinks=False,
        )
        log.info("GLiNER chargé.")
        return _model_cache
    except TypeError:
        # Ancienne version de huggingface_hub : local_dir_use_symlinks non supporté
        pass
    except Exception as exc:
        log.warning("Impossible de charger GLiNER (%s) — extraction NER désactivée.", exc)
        return None

    # Essai 3 : téléchargement sans options avancées
    try:
        import os
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        _model_cache = GLiNER.from_pretrained(_MODEL_NAME, cache_dir=str(_LOCAL_MODEL_DIR.parent))
        log.info("GLiNER chargé.")
        return _model_cache
    except Exception as exc:
        log.warning(
            "GLiNER non disponible (%s). Sur Windows, activez le Developer Mode "
            "ou lancez Python en tant qu'administrateur pour autoriser les symlinks.", exc
        )
        return None


def extract_with_gliner(
    pages: list[dict[str, Any]],
    threshold: float = 0.45,
) -> list[dict[str, Any]]:
    """Extrait des candidats métriques via GLiNER NER zero-shot.

    Args:
        pages: liste de pages au format parse_pdf_pages() ou parse_pdf_docling().
        threshold: score de confiance GLiNER minimum (0.0–1.0).

    Retourne une liste de candidats :
    {
        "metric_id":       str,   # construit depuis les entités détectées
        "metric_label":    str,   # nom de l'indicateur extrait
        "raw_value":       str,
        "raw_unit":        str,
        "page_number":     int,
        "context_snippet": str,
        "confidence":      float, # score GLiNER normalisé
        "gliner_spans":    list,  # spans bruts pour auditabilité
        "extraction_method": "gliner",
    }
    """
    model = _load_gliner_model()
    if model is None:
        return []

    candidates: list[dict[str, Any]] = []

    for page in pages:
        page_number = page.get("page_number", 0)
        text = page.get("text", "")
        if not text.strip():
            continue

        # GLiNER a une limite de tokens : on traite par segment de ~512 tokens
        segments = _split_into_segments(text, max_chars=1500)

        for segment in segments:
            try:
                entities = model.predict_entities(segment, _GLINER_LABELS, threshold=threshold)
            except Exception as exc:
                log.debug("GLiNER predict_entities a échoué sur segment : %s", exc)
                continue

            for candidate in _entities_to_candidates(entities, segment, page_number):
                if candidate.get("metric_id") not in _GENERIC_METRIC_IDS:
                    candidates.append(candidate)

    return candidates


def _split_into_segments(text: str, max_chars: int = 1500) -> list[str]:
    """Découpe le texte en segments de taille raisonnable pour GLiNER."""
    lines = text.splitlines()
    segments: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        if current_len + len(line) > max_chars and current:
            segments.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line)

    if current:
        segments.append("\n".join(current))

    return segments


def _entities_to_candidates(
    entities: list[dict],
    segment: str,
    page_number: int,
) -> list[dict[str, Any]]:
    """Convertit les entités GLiNER en candidats structurés.

    Crée un candidat par valeur numérique détectée, en associant chaque
    valeur à l'unité et à l'indicateur les plus proches (par position de span).
    """
    values = [e for e in entities if e.get("label") == "metric value"]
    units = [e for e in entities if e.get("label") == "measurement unit"]
    years = [e for e in entities if e.get("label") == "reporting year"]
    scopes = [e for e in entities if e.get("label") == "ghg scope"]
    indicators = [e for e in entities if e.get("label") == "esg indicator name"]

    # Si pas de valeurs, créer un candidat qualitatif depuis les indicateurs
    if not values:
        if not indicators and not scopes:
            return []
        indicator_name = _best_entity_text(indicators) or _best_entity_text(scopes)
        if not indicator_name:
            return []
        return [_build_candidate("", "", _best_entity_text(years), indicator_name, [], segment, page_number)]

    candidates = []
    for val_ent in values:
        val_start = val_ent.get("start", 0)
        val_end = val_ent.get("end", 0)

        # Unité la plus proche (en distance de span)
        nearest_unit = _nearest_entity(val_end, units, max_distance=80)
        raw_unit = nearest_unit.get("text", "") if nearest_unit else ""

        # Année la plus proche
        nearest_year = _nearest_entity(val_start, years, max_distance=200)
        raw_year = nearest_year.get("text", "") if nearest_year else ""

        # Indicateur le plus proche (avant la valeur, dans une fenêtre plus large)
        nearest_indicator = _nearest_entity(val_start, indicators + scopes, max_distance=300)
        if nearest_indicator is None:
            # No indicator found near this value → discard to avoid "esg_metric" false positives
            continue
        indicator_name = nearest_indicator.get("text", "")

        span_entities = [val_ent] + ([nearest_unit] if nearest_unit else []) + [nearest_indicator]
        candidates.append(_build_candidate(
            val_ent.get("text", ""), raw_unit, raw_year, indicator_name,
            span_entities, segment, page_number,
        ))

    return candidates


def _build_candidate(
    raw_value: str,
    raw_unit: str,
    raw_year: str,
    indicator_name: str,
    span_entities: list[dict],
    segment: str,
    page_number: int,
) -> dict[str, Any]:
    confidence = round(
        sum(e.get("score", 0.5) for e in span_entities) / max(len(span_entities), 1),
        3,
    ) if span_entities else 0.35
    confidence = min(confidence, 0.50)
    metric_id = re.sub(r"[^a-z0-9]+", "_", indicator_name.lower()).strip("_")[:60] or "gliner_metric"
    return {
        "metric_id": metric_id,
        "metric_label": indicator_name[:200],
        "raw_value": raw_value,
        "raw_unit": raw_unit,
        "year_detected": raw_year,
        "page_number": page_number,
        "context_snippet": segment.strip()[:300],
        "confidence": confidence,
        "gliner_spans": [
            {"label": e["label"], "text": e["text"], "score": round(e.get("score", 0), 3)}
            for e in span_entities
        ],
        "extraction_method": "gliner",
    }


def _nearest_entity(ref_pos: int, candidates: list[dict], max_distance: int) -> dict | None:
    """Retourne l'entité la plus proche de ref_pos dans la limite max_distance."""
    best: dict | None = None
    best_dist = max_distance + 1
    for ent in candidates:
        start = ent.get("start", 0)
        end = ent.get("end", 0)
        dist = min(abs(start - ref_pos), abs(end - ref_pos))
        if dist < best_dist:
            best_dist = dist
            best = ent
    return best


def _entities_to_candidate(
    entities: list[dict],
    segment: str,
    page_number: int,
) -> dict[str, Any] | None:
    """Compat shim — retourne le premier candidat de _entities_to_candidates."""
    result = _entities_to_candidates(entities, segment, page_number)
    return result[0] if result else None


def _best_entity_text(entities: list[dict]) -> str:
    """Retourne le texte de l'entité avec le meilleur score."""
    if not entities:
        return ""
    best = max(entities, key=lambda e: e.get("score", 0))
    return best.get("text", "").strip()


def merge_candidates(
    regex_candidates: list[dict[str, Any]],
    gliner_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fusionne les candidats regex et GLiNER en dédupliquant par page+valeur.

    - Les candidats regex gardent leur champ extraction_method="regex".
    - Les candidats GLiNER enrichissent les résultats pour les métriques
      que le regex n'a pas détectées (indicateurs sans valeur numérique explicite,
      libellés multilingues, structures atypiques).
    - En cas de doublon (même page, même valeur), on garde celui avec
      la confidence la plus haute.
    """
    all_candidates = [
        {**c, "extraction_method": c.get("extraction_method", "regex")}
        for c in regex_candidates
    ]

    # Index des candidats regex par (page, valeur normalisée)
    regex_keys: set[tuple] = set()
    for c in regex_candidates:
        key = (c.get("page_number"), _norm_value(c.get("raw_value", "")))
        regex_keys.add(key)

    for gc in gliner_candidates:
        key = (gc.get("page_number"), _norm_value(gc.get("raw_value", "")))
        if key not in regex_keys:
            all_candidates.append(gc)
        else:
            # Si GLiNER a détecté un meilleur score sur le même candidat, mettre à jour
            for existing in all_candidates:
                ex_key = (existing.get("page_number"), _norm_value(existing.get("raw_value", "")))
                if ex_key == key and gc.get("confidence", 0) > existing.get("confidence", 0):
                    existing["gliner_spans"] = gc.get("gliner_spans", [])
                    existing["gliner_confidence"] = gc.get("confidence")
                    break

    return all_candidates


def _norm_value(v: str) -> str:
    return re.sub(r"[\s,.]", "", str(v)).lower()

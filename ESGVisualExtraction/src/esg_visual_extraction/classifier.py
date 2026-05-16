from __future__ import annotations

import logging
from collections import Counter
from typing import Any

log = logging.getLogger(__name__)

ALLOWED_VISUAL_TYPES = {
    "logo_or_cover",
    "illustrative_photo",
    "chart",
    "scanned_table",
    "diagram",
    "org_chart",
    "map",
    "unknown_visual",
}

_CHART_TOKENS = [
    "chart", "graph", "evolution", "trend", "progression",
    "emission", "target", "objective", "scope", "intensity",
    "reduction", "performance", "indicator", "kpi",
    "energy consumption", "ghg", "co2", "water withdrawal",
    "%", "gwh", "mwh", "tco2e",
]
_TABLE_TOKENS = ["table", "rows", "columns", "gri", "esrs", "dpef", "indicator table"]
_ORG_TOKENS = ["holding", "company", "companies", "org chart", "subsidiary", "structure"]

# Semantic descriptions for visual type classification.
_VISUAL_TYPE_DESCRIPTIONS: dict[str, str] = {
    "chart": (
        "bar chart line graph pie chart evolution trend performance KPI indicator "
        "greenhouse gas emissions energy consumption reduction target percentage %"
    ),
    "scanned_table": (
        "table rows columns GRI ESRS DPEF indicator table data matrix figures values "
        "annual report data tabular structured"
    ),
    "org_chart": (
        "organizational chart company structure holding subsidiary corporate governance "
        "hierarchy divisions business units"
    ),
    "map": (
        "geographic map territory regions countries presence sites operations "
        "world map Europe France global footprint"
    ),
    "diagram": (
        "process diagram flow chart schematic value chain supply chain lifecycle "
        "circular economy methodology framework"
    ),
    "logo_or_cover": (
        "company logo cover page title brand name illustration photo decorative image"
    ),
}

_visual_encoder_cache: object = None


def _load_visual_encoder():
    global _visual_encoder_cache
    if _visual_encoder_cache is not None:
        return _visual_encoder_cache
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        types = list(_VISUAL_TYPE_DESCRIPTIONS.keys())
        descs = [_VISUAL_TYPE_DESCRIPTIONS[t] for t in types]
        embeddings = model.encode(descs, normalize_embeddings=True)
        _visual_encoder_cache = (model, types, embeddings, np)
        return _visual_encoder_cache
    except Exception as exc:
        log.debug("Visual semantic encoder unavailable: %s", exc)
        return None


def _classify_visual_type_semantic(text: str) -> tuple[str, float]:
    enc = _load_visual_encoder()
    if enc is None or not text.strip():
        return "unknown_visual", 0.0
    model, types, type_embeddings, np = enc
    try:
        emb = model.encode([text.strip()[:300]], normalize_embeddings=True)
        scores = np.dot(emb, type_embeddings.T)[0]
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        if best_score < 0.30:
            return "unknown_visual", best_score
        return types[best_idx], round(min(0.9, 0.5 + best_score * 0.5), 3)
    except Exception:
        return "unknown_visual", 0.0


def classify_visuals(visual_items: list[dict[str, Any]], ocr_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ocr_by_figure = {row.get("figure_id"): row for row in ocr_rows}
    rows: list[dict[str, Any]] = []
    for item in visual_items:
        text = " ".join([
            str(item.get("nearby_caption_text") or ""),
            str(ocr_by_figure.get(item.get("figure_id"), {}).get("ocr_text") or ""),
            " ".join(item.get("figure_quality_flags") or []),
        ]).lower()

        # Hard rules that take priority (page 1 or "cover" keyword → logo/cover).
        if "cover" in text or int(item.get("page_number") or 0) == 1:
            visual_type, reason, confidence = "logo_or_cover", "cover_or_page_one_signal", 0.85
        else:
            # Keyword pass — fast and deterministic for clear signals.
            kw_type = "unknown_visual"
            kw_reason = "default_unknown_visual"
            if any(token in text for token in _CHART_TOKENS):
                kw_type, kw_reason = "chart", "chart_keywords"
            elif any(token in text for token in _TABLE_TOKENS):
                kw_type, kw_reason = "scanned_table", "table_keywords"
            elif any(token in text for token in _ORG_TOKENS):
                kw_type, kw_reason = "org_chart", "org_chart_keywords"
            elif "map" in text:
                kw_type, kw_reason = "map", "map_keyword"
            elif "diagram" in text or "process" in text or "flow" in text:
                kw_type, kw_reason = "diagram", "diagram_keyword"

            if kw_type != "unknown_visual":
                visual_type, reason, confidence = kw_type, kw_reason, 0.55
            else:
                # Semantic fallback for ambiguous or short captions.
                sem_type, sem_conf = _classify_visual_type_semantic(text)
                visual_type = sem_type
                reason = "semantic_embedding_fallback" if sem_type != "unknown_visual" else "default_unknown_visual"
                confidence = sem_conf if sem_type != "unknown_visual" else 0.25

        relevant = visual_type in {"chart", "scanned_table", "diagram", "org_chart", "map"}
        rows.append({
            "schema_version": "0.4.0",
            "document_id": item.get("document_id", ""),
            "figure_id": item.get("figure_id", ""),
            "page_number": item.get("page_number"),
            "visual_type": visual_type,
            "visual_type_confidence": confidence,
            "classification_reason": reason,
            "is_potentially_esg_relevant": relevant,
            "review_required": True,
        })
    summary = {
        "visual_classifications_count": len(rows),
        "visual_type_distribution": dict(Counter(row["visual_type"] for row in rows)),
        "potentially_esg_relevant_count": sum(1 for row in rows if row["is_potentially_esg_relevant"]),
    }
    return rows, summary


__all__ = ["ALLOWED_VISUAL_TYPES", "classify_visuals"]

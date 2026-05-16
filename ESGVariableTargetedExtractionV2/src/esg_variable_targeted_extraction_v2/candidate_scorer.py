"""
candidate_scorer.py — Score and rank extracted candidates.
Score is fully explainable: components are stored with each candidate.

Modern improvements (2026):
- Cross-encoder re-ranking: cross-encoder/ms-marco-mMiniLMv2-L12-H384-v1
  (multilingual, CPU-compatible) for quote-to-variable relevance scoring.
- quantulum3 unit normalization for canonical unit comparison.
Both are optional — transparent fallback to prior heuristics if unavailable.
"""
from __future__ import annotations

import logging
from typing import Any

from .semantic_catalog import SemanticCatalog

log = logging.getLogger(__name__)

_cross_encoder_cache: object = None


def _load_cross_encoder():
    global _cross_encoder_cache
    if _cross_encoder_cache is not None:
        return _cross_encoder_cache
    try:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1", max_length=512)
        _cross_encoder_cache = model
        log.info("Cross-encoder loaded for candidate re-ranking.")
        return model
    except Exception as exc:
        log.debug("Cross-encoder unavailable (%s) — falling back to keyword context score.", exc)
        _cross_encoder_cache = False
        return None


def _cross_encoder_score(query: str, passage: str) -> float | None:
    """Return a 0-1 relevance score using the cross-encoder, or None if unavailable."""
    model = _load_cross_encoder()
    if not model:
        return None
    if not passage.strip():
        return None
    try:
        import math
        logit = float(model.predict([[query, passage[:500]]])[0])
        return round(max(0.0, min(1.0, 1.0 / (1.0 + math.exp(-logit)))), 4)
    except Exception as exc:
        log.debug("Cross-encoder predict failed: %s", exc)
        return None


def _normalize_unit_quantulum3(raw_unit: str) -> str | None:
    """Return a canonical unit string using quantulum3, or None if unavailable/unknown."""
    if not raw_unit:
        return None
    try:
        from quantulum3 import parser as qp
        results = qp.parse(f"1 {raw_unit}")
        if results and results[0].unit and results[0].unit.name not in ("dimensionless", "unknown"):
            return results[0].unit.name.lower()
    except Exception:
        pass
    return None


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


class CandidateScorer:
    def __init__(self, catalog: SemanticCatalog) -> None:
        self.catalog = catalog

    def score_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        """Add candidate_score, extraction_score, score_components, score_reason."""
        target_variable = candidate.get("target_variable", "")
        raw_value = candidate.get("raw_value", "")
        raw_unit = candidate.get("raw_unit", "")
        quote = candidate.get("quote", "")
        status = candidate.get("candidate_status", "")
        retrieval_score = float(candidate.get("retrieval_score", 0.0))
        source_type = candidate.get("source_type", "")

        # Pre-rejected candidates get score 0
        if status.startswith("rejected_"):
            candidate["extraction_score"] = 0.0
            candidate["candidate_score"] = 0.0
            candidate["score_components"] = {}
            candidate["score_reason"] = f"rejected: {candidate.get('rejection_reason', '')}"
            return candidate

        # Component 1: retrieval score (already computed)
        ret_score = _clamp(retrieval_score)

        # Component 2: value/unit coherence
        vu_score = self._value_unit_coherence(raw_value, raw_unit, target_variable)

        # Component 3: evidence quality
        ev_score = self._evidence_quality(quote, source_type, raw_value)

        # Component 4: variable context alignment
        ctx_score = self._variable_context_score(quote, target_variable)

        # Penalties
        structural_penalty = self._structural_penalty(candidate)
        unit_mismatch_penalty = 0.2 if not raw_unit and raw_value else 0.0

        extraction_score = _clamp(
            0.35 * vu_score + 0.35 * ev_score + 0.30 * ctx_score
        )

        candidate_score = _clamp(
            0.40 * ret_score
            + 0.35 * extraction_score
            + 0.25 * ctx_score
            - structural_penalty
            - unit_mismatch_penalty
        )

        reasons: list[str] = []
        reasons.append(f"retrieval={ret_score:.2f}")
        reasons.append(f"value_unit={vu_score:.2f}")
        reasons.append(f"evidence={ev_score:.2f}")
        reasons.append(f"context={ctx_score:.2f}")
        if structural_penalty:
            reasons.append(f"structural_penalty={structural_penalty:.2f}")
        if unit_mismatch_penalty:
            reasons.append("unit_missing_penalty")

        ce_available = _load_cross_encoder() is not None
        candidate["extraction_score"] = round(extraction_score, 4)
        candidate["candidate_score"] = round(candidate_score, 4)
        candidate["score_components"] = {
            "retrieval_score": round(ret_score, 4),
            "value_unit_coherence": round(vu_score, 4),
            "evidence_quality": round(ev_score, 4),
            "variable_context": round(ctx_score, 4),
            "structural_penalty": round(structural_penalty, 4),
            "unit_mismatch_penalty": round(unit_mismatch_penalty, 4),
            "context_backend": "cross_encoder" if ce_available else "keyword_count",
        }
        candidate["score_reason"] = " | ".join(reasons)
        return candidate

    def score_all(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored = [self.score_candidate(dict(c)) for c in candidates]
        scored.sort(key=lambda c: float(c.get("candidate_score", 0)), reverse=True)
        return scored

    def _value_unit_coherence(self, raw_value: str, raw_unit: str, variable: str) -> float:
        if not raw_value:
            return 0.1
        expected_units = self.catalog.get_expected_units(variable)
        if raw_unit and expected_units:
            unit_lower = raw_unit.lower()
            # Primary: substring match (fast, handles "MtCO2e" ⊇ "tco2e").
            matched = [u for u in expected_units if u.lower() in unit_lower or unit_lower in u.lower()]
            if matched:
                return 1.0
            # Secondary: quantulum3 canonical form comparison.
            canonical = _normalize_unit_quantulum3(raw_unit)
            if canonical:
                matched_q = [u for u in expected_units if canonical in u.lower() or u.lower() in canonical]
                if matched_q:
                    return 0.9
            return 0.3
        if raw_unit:
            return 0.6
        return 0.4

    def _evidence_quality(self, quote: str, source_type: str, raw_value: str) -> float:
        score = 0.0
        if not quote:
            return 0.0
        score += 0.3
        if raw_value and raw_value in quote:
            score += 0.3
        if source_type in ("paragraph", "evidence"):
            score += 0.2
        elif source_type in ("table_cell_context",):
            score += 0.3
        elif source_type in ("section",):
            score += 0.1
        if len(quote) >= 30:
            score += 0.1
        return _clamp(score)

    def _variable_context_score(self, quote: str, variable: str) -> float:
        if not quote:
            return 0.0

        # Primary: cross-encoder relevance score (query = key EN terms for variable).
        query_terms = self.catalog.get_all_query_terms(variable)
        query = variable.replace("_", " ")
        if query_terms:
            query = " ".join(query_terms[:6])
        ce_score = _cross_encoder_score(query, quote)
        if ce_score is not None:
            return _clamp(ce_score)

        # Fallback: keyword count.
        pos_terms = self.catalog.get_positive_patterns(variable)
        all_terms = [t.lower() for t in pos_terms + query_terms]
        quote_lower = quote.lower()
        matched = sum(1 for t in all_terms if t and t in quote_lower)
        return _clamp(min(1.0, matched * 0.12))

    def _structural_penalty(self, candidate: dict[str, Any]) -> float:
        flags = candidate.get("warning_flags", "")
        penalty = 0.0
        if "iso_standard" in flags.lower():
            penalty += 0.30
        if "section_number" in flags.lower():
            penalty += 0.20
        if "probable_footnote" in flags.lower():
            penalty += 0.25
        return _clamp(penalty, 0.0, 0.60)

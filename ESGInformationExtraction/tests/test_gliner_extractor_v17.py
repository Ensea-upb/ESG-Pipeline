"""
test_gliner_extractor_v17.py
============================
Unit tests for gliner_extractor.py:
- Generic metric ID filter (_GENERIC_METRIC_IDS)
- merge_candidates deduplication
- _entities_to_candidates with no indicator → skip
- _build_candidate field structure
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extraction.gliner_extractor import (
    _GENERIC_METRIC_IDS,
    _build_candidate,
    _entities_to_candidates,
    merge_candidates,
    _norm_value,
)


class TestGenericMetricFilter:
    def test_esg_metric_in_generic_ids(self):
        assert "esg_metric" in _GENERIC_METRIC_IDS

    def test_gliner_metric_in_generic_ids(self):
        assert "gliner_metric" in _GENERIC_METRIC_IDS

    def test_known_catalog_ids_not_in_generic(self):
        for mid in ("ghg_scope_1", "total_employees", "training_coverage"):
            assert mid not in _GENERIC_METRIC_IDS

    def test_build_candidate_generic_id_from_empty_indicator(self):
        # When indicator_name = "" → metric_id = "gliner_metric" (falls back)
        cand = _build_candidate("100", "%", "2024", "", [], "text", 1)
        assert cand["metric_id"] == "gliner_metric"
        assert cand["metric_id"] in _GENERIC_METRIC_IDS

    def test_build_candidate_specific_id(self):
        cand = _build_candidate("100", "tCO2e", "2024", "GHG scope 1 emissions", [], "ctx", 5)
        assert cand["metric_id"] not in _GENERIC_METRIC_IDS
        assert "ghg" in cand["metric_id"] or "scope" in cand["metric_id"]


class TestEntitiesToCandidates:
    def test_no_indicator_found_returns_empty(self):
        # Value entity but no indicator → should skip (no esg_metric fallback)
        entities = [
            {"label": "metric value", "text": "12345", "start": 0, "end": 5, "score": 0.9}
        ]
        result = _entities_to_candidates(entities, "some text 12345", 1)
        assert result == []

    def test_no_entities_returns_empty(self):
        result = _entities_to_candidates([], "empty segment", 1)
        assert result == []

    def test_value_and_indicator_creates_candidate(self):
        entities = [
            {"label": "metric value", "text": "42", "start": 20, "end": 22, "score": 0.85},
            {"label": "esg indicator name", "text": "GHG scope 1", "start": 0, "end": 11, "score": 0.78},
        ]
        result = _entities_to_candidates(entities, "GHG scope 1 emissions: 42 tCO2e", 3)
        assert len(result) == 1
        assert result[0]["raw_value"] == "42"
        assert "ghg" in result[0]["metric_id"] or "scope" in result[0]["metric_id"]
        assert result[0]["page_number"] == 3

    def test_qualitative_candidate_from_indicator_only(self):
        entities = [
            {"label": "esg indicator name", "text": "water withdrawal", "start": 0, "end": 16, "score": 0.8}
        ]
        result = _entities_to_candidates(entities, "water withdrawal reporting", 2)
        assert len(result) == 1
        assert result[0]["raw_value"] == ""
        assert "water" in result[0]["metric_id"]

    def test_no_indicator_no_scope_returns_empty_when_no_values(self):
        result = _entities_to_candidates([], "no entities here", 1)
        assert result == []


class TestMergeCandidates:
    def test_merge_no_overlap(self):
        regex = [{"metric_id": "ghg_scope_1", "raw_value": "100", "page_number": 1, "confidence": 0.8}]
        gliner = [{"metric_id": "total_employees", "raw_value": "150000", "page_number": 2, "confidence": 0.6, "extraction_method": "gliner"}]
        merged = merge_candidates(regex, gliner)
        assert len(merged) == 2

    def test_merge_dedup_same_page_value(self):
        regex = [{"metric_id": "ghg_scope_1", "raw_value": "100", "page_number": 1, "confidence": 0.8}]
        gliner = [{"metric_id": "ghg_scope_1", "raw_value": "100", "page_number": 1, "confidence": 0.9, "extraction_method": "gliner"}]
        merged = merge_candidates(regex, gliner)
        # GLiNER has higher confidence → should enrich regex candidate, not add duplicate
        assert len(merged) == 1

    def test_merge_preserves_regex_method(self):
        regex = [{"metric_id": "ghg_scope_1", "raw_value": "100", "page_number": 1, "confidence": 0.8}]
        merged = merge_candidates(regex, [])
        assert merged[0]["extraction_method"] == "regex"

    def test_norm_value_strips_whitespace_and_punctuation(self):
        assert _norm_value("1 234,56") == _norm_value("1234.56")

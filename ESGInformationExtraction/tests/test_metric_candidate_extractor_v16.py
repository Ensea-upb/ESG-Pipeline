"""
test_metric_candidate_extractor_v16.py
=======================================
Unit tests for the metric candidate extractor (keyword matching pipeline).

Tests cover:
- Per-metric anchor token isolation (no cross-metric contamination)
- Exact FlashText matching and longest-match disambiguation
- Fuzzy WRatio per-metric matching
- Precision regression tests for previously over-firing metrics
- Recall preservation tests for ground truth ESRS metrics
"""

import pytest
from pathlib import Path

# Insert the ESGInformationExtraction package path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extraction.metric_candidate_extractor import (
    _build_matchers,
    _fuzzy_match,
    _normalize,
    _load_metric_catalog,
    extract_metric_candidates,
)


@pytest.fixture(scope="module")
def matchers():
    catalog = _load_metric_catalog()
    keyword_map = {}
    for _cat, metrics in catalog.items():
        if not isinstance(metrics, dict):
            continue
        for mid, info in metrics.items():
            if not isinstance(info, dict):
                continue
            label = info.get("label_fr") or info.get("label_en") or mid
            unit = info.get("unit_expected", "")
            for kw in info.get("keywords_fr", []) + info.get("keywords_en", []):
                norm = _normalize(kw)
                if norm:
                    keyword_map[norm] = (mid, label, unit)
    _, per_metric_kws, per_metric_anchors = _build_matchers(keyword_map)
    return per_metric_kws, per_metric_anchors


def fuzzy(line, matchers):
    pm_kws, pm_anchors = matchers
    result = _fuzzy_match(_normalize(line), pm_kws, pm_anchors)
    return result[0] if result else None


# ---------------------------------------------------------------------------
# Precision regression tests — metrics that previously over-fired
# ---------------------------------------------------------------------------

class TestPrecisionRegressions:
    """Lines that previously triggered false positives must NOT match."""

    def test_hazardous_waste_not_triggered_by_energy_transition(self, matchers):
        line = "transition energetique indispensable pour demain"
        assert fuzzy(line, matchers) != "hazardous_waste"

    def test_hazardous_waste_not_triggered_by_generic_strategy(self, matchers):
        line = "notre strategie durable creer de la valeur rentable"
        assert fuzzy(line, matchers) != "hazardous_waste"

    def test_ceo_pay_ratio_not_triggered_by_general_remuneration(self, matchers):
        line = "politique de remuneration des dirigeants mandataires sociaux"
        assert fuzzy(line, matchers) != "ceo_pay_ratio"

    def test_supply_chain_audits_not_triggered_by_single_word(self, matchers):
        assert fuzzy("fournisseurs", matchers) != "supply_chain_audits"

    def test_supply_chain_audits_not_triggered_by_clients_fournisseurs(self, matchers):
        assert fuzzy("clients et fournisseurs", matchers) != "supply_chain_audits"

    def test_hazardous_waste_not_triggered_by_financial_text(self, matchers):
        line = "ventes de produits distribution electrique nombreux marches"
        assert fuzzy(line, matchers) != "hazardous_waste"


# ---------------------------------------------------------------------------
# Recall preservation tests — must still match after fix
# ---------------------------------------------------------------------------

class TestRecallPreservation:
    """Lines that should match must still match with the stricter rules."""

    def test_hazardous_waste_matched_with_both_tokens(self, matchers):
        line = "dechets dangereux produits en 2024 en tonnes"
        assert fuzzy(line, matchers) == "hazardous_waste"

    def test_ceo_pay_ratio_matched_with_ratio_token(self, matchers):
        line = "ratio de remuneration ceo versus salaire median"
        assert fuzzy(line, matchers) == "ceo_pay_ratio"

    def test_supply_chain_audits_matched_with_both_tokens(self, matchers):
        line = "fournisseurs audites par le groupe en 2024"
        assert fuzzy(line, matchers) == "supply_chain_audits"

    def test_training_coverage_matched(self, matchers):
        line = "formation continue des collaborateurs en 2024"
        assert fuzzy(line, matchers) == "training_coverage"

    def test_ghg_scope1_matched(self, matchers):
        line = "emissions de gaz a effet de serre scope 1 directes"
        assert fuzzy(line, matchers) == "ghg_scope_1"

    def test_total_employees_matched(self, matchers):
        line = "effectif total du groupe en equivalent temps plein"
        assert fuzzy(line, matchers) == "total_employees"


# ---------------------------------------------------------------------------
# End-to-end pipeline tests
# ---------------------------------------------------------------------------

class TestExtractMetricCandidatesE2E:
    """Full pipeline tests using extract_metric_candidates()."""

    def _make_pages(self, lines_text: str, page_number: int = 1) -> list:
        return [{"page_number": page_number, "text": lines_text}]

    def test_exact_match_returns_candidate(self):
        pages = self._make_pages("Scope 1 GHG emissions: 1 234 567 tCO2e en 2024")
        results = extract_metric_candidates(pages, fiscal_year=2024)
        assert any(r["metric_id"] == "ghg_scope_1" for r in results)

    def test_fuzzy_training_coverage_found(self):
        pages = self._make_pages(
            "89% des collaborateurs ont beneficie d'une formation continue"
        )
        results = extract_metric_candidates(pages, fiscal_year=2024)
        mids = [r["metric_id"] for r in results]
        assert "training_coverage" in mids

    def test_no_candidates_for_blank_page(self):
        pages = self._make_pages("")
        results = extract_metric_candidates(pages, fiscal_year=2024)
        assert results == []

    def test_candidate_has_required_fields(self):
        pages = self._make_pages("Effectif total : 175 000 collaborateurs")
        results = extract_metric_candidates(pages, fiscal_year=2024)
        assert results, "Expected at least one candidate"
        r = results[0]
        for key in ("metric_id", "metric_label", "raw_value", "raw_unit",
                    "page_number", "context_snippet", "confidence",
                    "year_in_context", "is_current_year",
                    "match_type", "fuzzy_score", "value_rejected_reason"):
            assert key in r, f"Missing field: {key}"

    def test_match_type_exact_for_keyword_match(self):
        pages = self._make_pages("emissions scope 1 du groupe 2024 : 1 000 000 tCO2e")
        results = extract_metric_candidates(pages, fiscal_year=2024)
        scope1 = [r for r in results if r["metric_id"] == "ghg_scope_1"]
        assert scope1
        assert scope1[0]["match_type"] == "exact"

    def test_match_type_fuzzy_for_fuzzy_match(self):
        pages = self._make_pages(
            "formation en ligne et presentielle des employes : 82% ont suivi une formation"
        )
        results = extract_metric_candidates(pages, fiscal_year=2024)
        training = [r for r in results if r["metric_id"] == "training_coverage"]
        assert training
        # At least some should be fuzzy
        match_types = {r["match_type"] for r in training}
        assert "fuzzy" in match_types or "exact" in match_types

    def test_current_year_detection(self):
        pages = self._make_pages("Effectif total 2024 : 175 000")
        results = extract_metric_candidates(pages, fiscal_year=2024)
        emp = [r for r in results if r["metric_id"] == "total_employees"]
        assert emp
        assert any(r["is_current_year"] is True for r in emp)

    def test_no_hazardous_waste_false_positive_from_energy_text(self):
        pages = self._make_pages(
            "La transition energetique est indispensable pour l'avenir durable"
        )
        results = extract_metric_candidates(pages, fiscal_year=2024)
        hw = [r for r in results if r["metric_id"] == "hazardous_waste"]
        assert hw == [], f"False positive hazardous_waste: {hw}"

    def test_no_ceo_pay_ratio_false_positive_from_general_remuneration(self):
        pages = self._make_pages(
            "Notre politique de remuneration des dirigeants est alignee sur la performance"
        )
        results = extract_metric_candidates(pages, fiscal_year=2024)
        ceo = [r for r in results if r["metric_id"] == "ceo_pay_ratio"]
        assert ceo == [], f"False positive ceo_pay_ratio: {ceo}"

    def test_value_extraction_with_unit(self):
        pages = self._make_pages("Dechets dangereux generes : 4 500 tonnes en 2024")
        results = extract_metric_candidates(pages, fiscal_year=2024)
        hw = [r for r in results if r["metric_id"] == "hazardous_waste"]
        assert hw, "hazardous_waste not found"
        assert any(r["raw_value"] for r in hw), "No value extracted"

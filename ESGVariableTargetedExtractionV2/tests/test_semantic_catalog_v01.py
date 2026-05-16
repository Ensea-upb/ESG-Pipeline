"""Tests for SemanticCatalog — 31 variables, units, patterns."""
import pytest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.semantic_catalog import (
    SemanticCatalog, EXPECTED_VARIABLE_COUNT,
)

CATALOG_PATH = _ROOT / "ESGVariableTargetedExtractionV2" / "config" / "variable_semantic_catalog_v1.yaml"

ALL_31 = [
    "co2_emissions", "carbon_intensity", "energy_consumption", "water_consumption",
    "waste", "biodiversity", "fossil_exposure",
    "turnover", "diversity", "work_accidents", "human_capital", "supply_chain", "human_rights",
    "board_independence", "ceo_chairman_separation", "remuneration",
    "shareholder_rights", "transparency",
    "esg_scandals", "fraud", "corruption", "pollution", "lawsuits", "social_controversies",
    "market_cap", "volatility", "leverage", "roa", "roe", "liquidity", "stock_returns",
]


@pytest.fixture(scope="module")
def catalog():
    return SemanticCatalog(CATALOG_PATH)


def test_catalog_contains_31_variables(catalog):
    variables = catalog.list_variables()
    assert len(variables) == EXPECTED_VARIABLE_COUNT, (
        f"Expected {EXPECTED_VARIABLE_COUNT} variables, got {len(variables)}: {variables}"
    )


def test_catalog_all_named_variables_present(catalog):
    missing = [v for v in ALL_31 if v not in catalog]
    assert not missing, f"Missing variables from catalog: {missing}"


def test_catalog_units_for_core_variables(catalog):
    assert catalog.get_expected_units("co2_emissions"), "co2_emissions must have expected_units"
    assert catalog.get_expected_units("water_consumption"), "water_consumption must have expected_units"
    assert catalog.get_expected_units("human_capital"), "human_capital must have expected_units"
    assert catalog.get_expected_units("energy_consumption"), "energy_consumption must have expected_units"


def test_catalog_water_units_include_m3(catalog):
    units = [u.lower() for u in catalog.get_expected_units("water_consumption")]
    assert any("m3" in u or "mm3" in u or "ml" in u for u in units), (
        f"water_consumption expected_units should include m3/Mm3/ML, got: {units}"
    )


def test_catalog_co2_units_include_tco2e(catalog):
    units = [u.lower() for u in catalog.get_expected_units("co2_emissions")]
    assert any("tco2e" in u or "co2e" in u for u in units), (
        f"co2_emissions expected_units should include tCO2e variants, got: {units}"
    )


def test_catalog_domains_are_correct(catalog):
    assert catalog.get_domain("co2_emissions") == "environmental"
    assert catalog.get_domain("human_capital") == "social"
    assert catalog.get_domain("board_independence") == "governance"
    assert catalog.get_domain("fraud") == "controversy"
    assert catalog.get_domain("market_cap") == "financial"


def test_catalog_query_terms_not_empty(catalog):
    for var in ALL_31:
        terms = catalog.get_all_query_terms(var)
        assert len(terms) >= 2, f"{var}: must have at least 2 query terms"


def test_catalog_forbidden_units_prevent_co2_in_water(catalog):
    forbidden = [u.lower() for u in catalog.get_forbidden_units("water_consumption")]
    assert any("co2" in f or "tco2" in f for f in forbidden), (
        "water_consumption must forbid CO2 units"
    )


def test_catalog_indicator_family_mapping(catalog):
    assert catalog.get_indicator_family("co2_emissions") == "environmental"
    assert catalog.get_indicator_family("human_capital") == "social"
    assert catalog.get_indicator_family("board_independence") == "governance"


def test_catalog_min_relevance_scores_positive(catalog):
    for var in ALL_31:
        score = catalog.get_min_relevance_score(var)
        assert 0.0 < score <= 1.0, f"{var}: min_relevance_score must be in (0, 1], got {score}"


def test_catalog_preferred_doc_types_not_empty_for_core(catalog):
    core = ["co2_emissions", "water_consumption", "energy_consumption", "human_capital"]
    for var in core:
        dtypes = catalog.get_preferred_doc_types(var)
        assert dtypes, f"{var}: preferred_doc_types must not be empty"

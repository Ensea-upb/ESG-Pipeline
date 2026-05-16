"""Tests for ConstrainedExtractor — extraction, FP rejection, variable mapping."""
import pytest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.tests.helpers import make_sample_chunks
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.semantic_catalog import SemanticCatalog
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.constrained_extractor import (
    ConstrainedExtractor, _is_iso_standard_value, _is_section_number,
    _is_page_number, _is_footnote_marker, _extract_numeric_values, _extract_year,
)

CATALOG_PATH = _ROOT / "ESGVariableTargetedExtractionV2" / "config" / "variable_semantic_catalog_v1.yaml"


@pytest.fixture(scope="module")
def catalog():
    return SemanticCatalog(CATALOG_PATH)


@pytest.fixture(scope="module")
def extractor(catalog):
    return ConstrainedExtractor(catalog=catalog)


def test_extractor_rejects_iso_50001(extractor, catalog):
    retrieval = [{
        "retrieval_id": "ret_001",
        "target_variable": "energy_consumption",
        "chunk_id": "chunk_iso",
        "document_id": "doc1",
        "company": "test",
        "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report",
        "page_number": "4",
        "source_type": "paragraph",
        "retrieval_score": 0.45,
        "text_snippet": "ISO 50001",
    }]
    chunk = {
        "chunk_id": "chunk_iso",
        "document_id": "doc1", "company": "test", "company_name": "Test",
        "company_slug": "test", "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report", "final_path": "",
        "text": "ISO 50001",
        "source_type": "paragraph", "page_number": "4",
        "evidence_id": "", "table_id": "", "figure_id": "", "crop_id": "",
    }
    candidates = extractor.extract_from_retrieval(retrieval, {"chunk_iso": chunk})
    found = [c for c in candidates if c.get("candidate_status") == "candidate_found"]
    # ISO 50001 should never produce a candidate_found
    for c in found:
        assert c.get("raw_value", "") not in ("50001", "14001", "ISO 50001"), (
            "ISO standard number must not appear as raw_value in candidate_found"
        )


def test_extractor_rejects_section_number(extractor, catalog):
    chunk = {
        "chunk_id": "chunk_sec", "document_id": "doc1", "company": "test",
        "company_name": "Test", "company_slug": "test", "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report", "final_path": "",
        "text": "Section 2.1 describes our governance approach.",
        "source_type": "paragraph", "page_number": "5",
        "evidence_id": "", "table_id": "", "figure_id": "", "crop_id": "",
    }
    retrieval = [{
        "retrieval_id": "ret_sec",
        "target_variable": "board_independence",
        "chunk_id": "chunk_sec",
        "document_id": "doc1", "company": "test", "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report",
        "page_number": "5", "source_type": "paragraph",
        "retrieval_score": 0.30, "text_snippet": "Section 2.1 describes governance.",
    }]
    candidates = extractor.extract_from_retrieval(retrieval, {"chunk_sec": chunk})
    found = [c for c in candidates if c.get("candidate_status") == "candidate_found"]
    for c in found:
        assert c.get("raw_value", "") != "2.1", "Section number 2.1 must not become raw_value"


def test_extractor_maps_scope3_mtco2e_to_ghg(extractor, catalog):
    chunk = {
        "chunk_id": "chunk_ghg", "document_id": "doc1", "company": "test",
        "company_name": "Test", "company_slug": "test", "fiscal_year": "2024",
        "official_doc_type": "03_climate_report_tcfd_transition_plan", "final_path": "",
        "text": "Scope 3 upstream supply chain GHG emissions: 4.7 MtCO2e in 2024.",
        "source_type": "paragraph", "page_number": "17",
        "evidence_id": "", "table_id": "", "figure_id": "", "crop_id": "",
    }
    retrieval = [{
        "retrieval_id": "ret_ghg",
        "target_variable": "co2_emissions",
        "chunk_id": "chunk_ghg",
        "document_id": "doc1", "company": "test", "fiscal_year": "2024",
        "official_doc_type": "03_climate_report_tcfd_transition_plan",
        "page_number": "17", "source_type": "paragraph",
        "retrieval_score": 0.75, "text_snippet": "Scope 3 upstream GHG 4.7 MtCO2e",
    }]
    candidates = extractor.extract_from_retrieval(retrieval, {"chunk_ghg": chunk})
    found = [c for c in candidates if c.get("candidate_status") == "candidate_found"]
    assert len(found) > 0, "Scope 3 MtCO2e should produce a candidate_found for co2_emissions"
    assert found[0]["target_variable"] == "co2_emissions"


def test_extractor_maps_water_mm3_to_water_consumption(extractor, catalog):
    chunk = {
        "chunk_id": "chunk_water", "document_id": "doc1", "company": "test",
        "company_name": "Test", "company_slug": "test", "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report", "final_path": "",
        "text": "Total fresh water withdrawal was 4.2 Mm3 in 2024.",
        "source_type": "paragraph", "page_number": "10",
        "evidence_id": "", "table_id": "", "figure_id": "", "crop_id": "",
    }
    retrieval = [{
        "retrieval_id": "ret_water",
        "target_variable": "water_consumption",
        "chunk_id": "chunk_water",
        "document_id": "doc1", "company": "test", "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report",
        "page_number": "10", "source_type": "paragraph",
        "retrieval_score": 0.72, "text_snippet": "water withdrawal 4.2 Mm3",
    }]
    candidates = extractor.extract_from_retrieval(retrieval, {"chunk_water": chunk})
    found = [c for c in candidates if c.get("candidate_status") == "candidate_found"]
    assert len(found) > 0, "Water Mm3 should produce candidate_found for water_consumption"
    assert found[0]["target_variable"] == "water_consumption"
    assert "Mm3" in found[0].get("raw_unit", "") or "mm3" in found[0].get("raw_unit", "").lower()


def test_extractor_maps_employees_to_human_capital(extractor, catalog):
    chunk = {
        "chunk_id": "chunk_emp", "document_id": "doc1", "company": "test",
        "company_name": "Test", "company_slug": "test", "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report", "final_path": "",
        "text": "The group employed 52,000 employees at December 2024.",
        "source_type": "paragraph", "page_number": "20",
        "evidence_id": "", "table_id": "", "figure_id": "", "crop_id": "",
    }
    retrieval = [{
        "retrieval_id": "ret_emp",
        "target_variable": "human_capital",
        "chunk_id": "chunk_emp",
        "document_id": "doc1", "company": "test", "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report",
        "page_number": "20", "source_type": "paragraph",
        "retrieval_score": 0.68, "text_snippet": "52,000 employees 2024",
    }]
    candidates = extractor.extract_from_retrieval(retrieval, {"chunk_emp": chunk})
    found = [c for c in candidates if c.get("candidate_status") == "candidate_found"]
    assert len(found) > 0, "employees should produce candidate_found for human_capital"
    assert found[0]["target_variable"] == "human_capital"


def test_is_iso_standard_value():
    assert _is_iso_standard_value("50001") is True
    assert _is_iso_standard_value("14001") is True
    assert _is_iso_standard_value("ISO 50001") is True
    assert _is_iso_standard_value("457") is False
    assert _is_iso_standard_value("4.2") is False


def test_is_section_number():
    assert _is_section_number("2.1") is True
    assert _is_section_number("12.3") is True
    assert _is_section_number("457") is False


def test_extract_year():
    assert _extract_year("total 457 ktCO2e in 2024") == "2024"
    assert _extract_year("reduction vs 2017") == "2017"
    assert _extract_year("no year here") == ""


def test_candidate_has_required_fields(extractor, catalog):
    chunk = {
        "chunk_id": "chunk_full", "document_id": "doc_full", "company": "comp",
        "company_name": "Comp SA", "company_slug": "comp", "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report", "final_path": "/path/doc.pdf",
        "text": "GHG Scope 1 emissions: 100 ktCO2e in 2024.",
        "source_type": "paragraph", "page_number": "5",
        "evidence_id": "ev_001", "table_id": "", "figure_id": "", "crop_id": "",
    }
    retrieval = [{
        "retrieval_id": "ret_full", "target_variable": "co2_emissions",
        "chunk_id": "chunk_full", "document_id": "doc_full", "company": "comp",
        "fiscal_year": "2024", "official_doc_type": "01_urd_annual_report",
        "page_number": "5", "source_type": "paragraph", "retrieval_score": 0.80,
        "text_snippet": "GHG 100 ktCO2e",
    }]
    candidates = extractor.extract_from_retrieval(retrieval, {"chunk_full": chunk})
    required = [
        "candidate_id", "schema_version", "engine", "target_variable",
        "document_id", "company", "fiscal_year", "quote", "candidate_status",
    ]
    for c in candidates:
        for field in required:
            assert field in c, f"Missing '{field}' in candidate"
        assert c["document_id"] == "doc_full"
        assert c["company"] == "comp"
        assert c["fiscal_year"] == "2024"
        assert c["quote"], f"quote must not be empty, got: {c['quote']!r}"

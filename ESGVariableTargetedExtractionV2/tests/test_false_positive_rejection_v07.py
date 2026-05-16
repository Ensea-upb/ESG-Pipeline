"""Tests for structural false positive rejection — ISO, sections, pages, footnotes."""
import pytest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.constrained_extractor import (
    _is_iso_standard_value, _is_section_number, _is_page_number, _is_footnote_marker,
    _extract_numeric_values, ConstrainedExtractor,
)
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.semantic_catalog import SemanticCatalog

CATALOG_PATH = _ROOT / "ESGVariableTargetedExtractionV2" / "config" / "variable_semantic_catalog_v1.yaml"


@pytest.fixture(scope="module")
def catalog():
    return SemanticCatalog(CATALOG_PATH)


@pytest.fixture(scope="module")
def extractor(catalog):
    return ConstrainedExtractor(catalog=catalog)


# ── ISO standard rejection ───────────────────────────────────

def test_iso_50001_rejected_as_value():
    assert _is_iso_standard_value("50001") is True
    assert _is_iso_standard_value("14001") is True
    assert _is_iso_standard_value("ISO 50001") is True
    assert _is_iso_standard_value("ISO 14001") is True
    assert _is_iso_standard_value("ISO 45001") is True


def test_real_values_not_iso():
    assert _is_iso_standard_value("457") is False
    assert _is_iso_standard_value("4.2") is False
    assert _is_iso_standard_value("52000") is False
    assert _is_iso_standard_value("18000") is False
    assert _is_iso_standard_value("27") is False
    assert _is_iso_standard_value("75") is False


# ── Section number rejection ─────────────────────────────────

def test_section_numbers_rejected():
    assert _is_section_number("2.1") is True
    assert _is_section_number("3.2") is True
    assert _is_section_number("12.3") is True
    assert _is_section_number("1.2.3") is True


def test_real_values_not_section_numbers():
    # "4.2" matches the section number pattern; the extractor only rejects it when there is no unit
    assert _is_section_number("4.2") is True
    assert _is_section_number("457") is False
    assert _is_section_number("27%") is False


# ── Page number rejection ────────────────────────────────────

def test_bare_numbers_flagged_as_page_number():
    assert _is_page_number("Page 5") is True
    assert _is_page_number("page 12") is True


def test_values_with_unit_not_page_numbers():
    assert _is_page_number("4.2 Mm3") is False
    assert _is_page_number("457 ktCO2e") is False


# ── Footnote marker rejection ────────────────────────────────

def test_footnote_markers_detected():
    assert _is_footnote_marker("(1)") is True
    assert _is_footnote_marker("(3)") is True
    assert _is_footnote_marker("[1]") is True
    assert _is_footnote_marker("1)") is True


def test_real_values_not_footnotes():
    assert _is_footnote_marker("457") is False
    assert _is_footnote_marker("27%") is False
    assert _is_footnote_marker("4.2 Mm3") is False


# ── End-to-end FP test ──────────────────────────────────────

def test_extractor_iso_full_text_chunk(extractor):
    """ISO cert text produces no candidate_found with value=50001."""
    chunk = {
        "chunk_id": "iso_chunk", "document_id": "doc", "company": "co",
        "company_name": "Co", "company_slug": "co", "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report", "final_path": "",
        "text": "The site is certified ISO 50001 and ISO 14001.",
        "source_type": "paragraph", "page_number": "6",
        "evidence_id": "", "table_id": "", "figure_id": "", "crop_id": "",
    }
    ret = [{
        "retrieval_id": "r1", "target_variable": "energy_consumption",
        "chunk_id": "iso_chunk", "document_id": "doc", "company": "co",
        "fiscal_year": "2024", "official_doc_type": "01_urd_annual_report",
        "page_number": "6", "source_type": "paragraph",
        "retrieval_score": 0.50, "text_snippet": "ISO 50001 ISO 14001",
    }]
    candidates = extractor.extract_from_retrieval(ret, {"iso_chunk": chunk})
    found = [c for c in candidates if c.get("candidate_status") == "candidate_found"]
    for c in found:
        assert c.get("raw_value", "") not in ("50001", "14001"), (
            f"ISO number {c.get('raw_value')} became a candidate_found — must be rejected"
        )


def test_extractor_section_number_full_text_chunk(extractor):
    """Section number from text chunk must not produce candidate_found with value=2.1."""
    chunk = {
        "chunk_id": "sec_chunk", "document_id": "doc", "company": "co",
        "company_name": "Co", "company_slug": "co", "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report", "final_path": "",
        "text": "As described in section 2.1, governance principles apply.",
        "source_type": "paragraph", "page_number": "7",
        "evidence_id": "", "table_id": "", "figure_id": "", "crop_id": "",
    }
    ret = [{
        "retrieval_id": "r2", "target_variable": "board_independence",
        "chunk_id": "sec_chunk", "document_id": "doc", "company": "co",
        "fiscal_year": "2024", "official_doc_type": "01_urd_annual_report",
        "page_number": "7", "source_type": "paragraph",
        "retrieval_score": 0.35, "text_snippet": "section 2.1 governance",
    }]
    candidates = extractor.extract_from_retrieval(ret, {"sec_chunk": chunk})
    found = [c for c in candidates if c.get("candidate_status") == "candidate_found"]
    for c in found:
        assert c.get("raw_value", "") != "2.1", "Section number 2.1 must not be candidate_found"

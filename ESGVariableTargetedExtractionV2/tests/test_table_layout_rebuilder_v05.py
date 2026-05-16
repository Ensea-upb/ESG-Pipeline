"""Tests for TableLayoutRebuilder — unit preservation, unit conflict detection."""
import pytest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.tests.helpers import make_input_dir
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.input_adapter import load_document_input
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.table_layout_rebuilder import (
    TableLayoutRebuilder, TableContextChunk, _is_probable_footnote, _is_iso_standard, _is_section_number,
)


@pytest.fixture
def input_dir(tmp_path):
    return make_input_dir(tmp_path)


@pytest.fixture
def doc_input(input_dir):
    return load_document_input(input_dir)


def test_table_layout_rebuilder_basic(doc_input):
    rebuilder = TableLayoutRebuilder()
    chunks = rebuilder.rebuild(doc_input)
    # Should produce some table context chunks from sample data
    assert isinstance(chunks, list)


def test_table_layout_rebuilder_keeps_percent_unit():
    """The value '27' in a '(%)' column must NOT become '27 tonnes'."""
    ctx = TableContextChunk(
        table_id="tbl_001",
        cell_id="tbl_001_r1_c1",
        cell_text="27",
        row_header="Women in management",
        col_header="Value (%)",
        table_title="Diversity indicators",
        page_number="10",
        section_context="",
        document_id="test_doc",
        company="test",
        fiscal_year="2024",
        official_doc_type="01_urd_annual_report",
    )
    # nearby_unit should reflect the % from column header, NOT an externally assigned unit
    assert "%" in ctx.nearby_unit or "percent" in ctx.nearby_unit.lower() or ctx.nearby_unit in ("", "(%)", "%"), (
        f"Unit from '(%)' column should be '%', got: '{ctx.nearby_unit}'"
    )
    assert not ctx.iso_standard_detected
    assert not ctx.section_number_detected


def test_table_layout_rebuilder_detects_unit_conflict():
    """Column says tCO2e but row says 'sites' — conflict should be flagged."""
    ctx = TableContextChunk(
        table_id="tbl_002",
        cell_id="tbl_002_r1_c0",
        cell_text="101",
        row_header="101 sites",
        col_header="Indicator (tCO2e)",
        table_title="",
        page_number="11",
        section_context="",
        document_id="test_doc",
        company="test",
        fiscal_year="2024",
        official_doc_type="01_urd_annual_report",
    )
    assert ctx.unit_conflict, "tCO2e in column vs sites in row should trigger unit_conflict"


def test_probable_footnote_detection():
    assert _is_probable_footnote("1") is True, "Single digit '1' is a probable footnote"
    assert _is_probable_footnote("(1)") is True, "'(1)' is a probable footnote marker"
    assert _is_probable_footnote("457") is False, "'457' is not a probable footnote"
    assert _is_probable_footnote("4.2 Mm3") is False, "A value with unit is not a footnote"


def test_iso_standard_detection():
    assert _is_iso_standard("ISO 50001") is True
    assert _is_iso_standard("ISO 14001") is True
    assert _is_iso_standard("ISO 45001") is True
    assert _is_iso_standard("457 ktCO2e") is False
    assert _is_iso_standard("4.2 Mm3") is False


def test_section_number_detection():
    assert _is_section_number("2.1") is True
    assert _is_section_number("12.3") is True
    assert _is_section_number("457") is False
    assert _is_section_number("4.2 Mm3") is False
    assert _is_section_number("27%") is False


def test_iso_in_cell_marks_iso_detected():
    ctx = TableContextChunk(
        table_id="tbl_003",
        cell_id="tbl_003_r1_c0",
        cell_text="ISO 50001",
        row_header="Certification",
        col_header="Standard",
        table_title="",
        page_number="5",
        section_context="",
        document_id="test_doc",
        company="test",
        fiscal_year="2024",
        official_doc_type="01_urd_annual_report",
    )
    assert ctx.iso_standard_detected, "ISO 50001 in cell should mark iso_standard_detected"


def test_table_context_to_dict_has_required_keys():
    ctx = TableContextChunk(
        table_id="t1", cell_id="c1", cell_text="42", row_header="GHG",
        col_header="ktCO2e", table_title="", page_number="7",
        section_context="", document_id="d1", company="co", fiscal_year="2024",
        official_doc_type="01_urd_annual_report",
    )
    d = ctx.to_dict()
    for key in ["table_id", "cell_id", "cell_text", "nearby_unit", "unit_conflict",
                "unit_source", "probable_footnote", "iso_standard_detected"]:
        assert key in d, f"Missing key '{key}' in TableContextChunk.to_dict()"

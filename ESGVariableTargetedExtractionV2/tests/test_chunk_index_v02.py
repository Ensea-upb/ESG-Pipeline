"""Tests for DocumentChunkIndex — metadata preservation, numeric detection."""
import pytest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.tests.helpers import make_input_dir, DOCUMENT_ID, COMPANY, FISCAL_YEAR
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.input_adapter import load_document_input
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.document_chunk_index import (
    build_all_chunks, build_text_block_chunks, build_table_cell_chunks,
)


@pytest.fixture
def input_dir(tmp_path):
    return make_input_dir(tmp_path)


@pytest.fixture
def doc_input(input_dir):
    return load_document_input(input_dir)


def test_chunk_index_loads_without_error(doc_input):
    assert doc_input.document_id == DOCUMENT_ID


def test_chunk_index_preserves_metadata(doc_input):
    chunks = build_all_chunks(doc_input)
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk["document_id"] == DOCUMENT_ID, "document_id must be preserved in all chunks"
        assert chunk["company"] == COMPANY, "company must be preserved in all chunks"
        assert chunk["fiscal_year"] == FISCAL_YEAR, "fiscal_year must be preserved in all chunks"


def test_chunk_index_no_empty_document_id(doc_input):
    chunks = build_all_chunks(doc_input)
    assert all(c["document_id"] for c in chunks), "No chunk should have empty document_id"


def test_chunk_index_page_number_present(doc_input):
    chunks = build_text_block_chunks(doc_input)
    # Most text block chunks should have page_number
    with_page = [c for c in chunks if c.get("page_number")]
    assert len(with_page) > 0, "At least some chunks must have page_number"


def test_chunk_index_detects_numeric_values(doc_input):
    chunks = build_text_block_chunks(doc_input)
    numeric_chunks = [c for c in chunks if c.get("has_numeric_value")]
    assert len(numeric_chunks) > 0, "Must detect numeric values in at least one chunk"


def test_chunk_index_detects_unit_candidates(doc_input):
    chunks = build_text_block_chunks(doc_input)
    unit_chunks = [c for c in chunks if c.get("has_unit_candidate")]
    assert len(unit_chunks) > 0, "Must detect unit candidates (Mm3, ktCO2e, FTE, etc.)"


def test_chunk_index_flags_iso_noise(doc_input):
    chunks = build_text_block_chunks(doc_input)
    noise_chunks = [c for c in chunks if c.get("structural_noise_flags")]
    assert len(noise_chunks) > 0, "ISO 14001 / ISO 50001 text must produce structural_noise_flags"


def test_chunk_index_table_cell_chunks(doc_input):
    chunks = build_table_cell_chunks(doc_input)
    assert len(chunks) > 0, "Should produce table cell chunks from sample data"


def test_chunk_ids_are_unique(doc_input):
    chunks = build_all_chunks(doc_input)
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids)), "All chunk_ids must be unique"


def test_chunk_has_source_type(doc_input):
    chunks = build_all_chunks(doc_input)
    valid_source_types = {
        "paragraph", "section", "page_context", "table_cell_context",
        "figure_caption", "visual_crop_context", "multimodal_context", "evidence"
    }
    for c in chunks:
        assert c["source_type"] in valid_source_types, (
            f"Invalid source_type: {c['source_type']}"
        )

"""Tests for output contract validation."""
import pytest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.tests.helpers import make_sample_candidate, DOCUMENT_ID, COMPANY, FISCAL_YEAR
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.validators import (
    validate_candidates_against_contract, validate_output_dir, _is_iso_standard_value,
)
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.output_adapter import OutputAdapter

CONTRACT_PATH = _ROOT / "ESGVariableTargetedExtractionV2" / "contracts" / "targeted_candidates_v2_contract.json"


def test_targeted_candidates_contract_file_exists():
    assert CONTRACT_PATH.exists(), f"Contract file not found: {CONTRACT_PATH}"


def test_targeted_candidates_contract_valid_json():
    import json
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert "required_columns" in data
    assert "allowed_candidate_statuses" in data


def test_valid_candidate_passes_contract():
    cand = make_sample_candidate()
    result = validate_candidates_against_contract([cand], CONTRACT_PATH)
    assert result["invalid_candidates"] == 0, (
        f"Valid candidate should pass contract. Errors: {result['errors']}"
    )


def test_candidate_missing_company_fails(capfd):
    cand = make_sample_candidate()
    cand["company"] = ""
    result = validate_candidates_against_contract([cand], CONTRACT_PATH)
    assert result["invalid_candidates"] > 0, "Candidate with empty company must fail"


def test_candidate_missing_quote_fails_for_found():
    cand = make_sample_candidate(status="candidate_found")
    cand["quote"] = ""
    result = validate_candidates_against_contract([cand], CONTRACT_PATH)
    assert result["invalid_candidates"] > 0, "candidate_found with empty quote must fail"


def test_candidate_invalid_status_fails():
    cand = make_sample_candidate()
    cand["candidate_status"] = "invalid_status_xyz"
    result = validate_candidates_against_contract([cand], CONTRACT_PATH)
    assert result["invalid_candidates"] > 0


def test_candidate_iso_value_fails_contract():
    cand = make_sample_candidate(raw_value="50001", raw_unit="")
    cand["candidate_status"] = "candidate_found"
    result = validate_candidates_against_contract([cand], CONTRACT_PATH)
    assert result["invalid_candidates"] > 0, "ISO standard as raw_value must fail contract"


def test_empty_candidates_returns_warning():
    result = validate_candidates_against_contract([], CONTRACT_PATH)
    assert result["status"] in ("warning", "ok")
    assert result["total_candidates"] == 0


def test_output_adapter_writes_all_files(tmp_path):
    adapter = OutputAdapter(tmp_path / "v2_output")
    chunks = [{"chunk_id": "c1", "document_id": DOCUMENT_ID, "company": COMPANY,
               "company_name": "Test", "company_slug": COMPANY, "fiscal_year": FISCAL_YEAR,
               "official_doc_type": "01_urd_annual_report", "final_path": "",
               "page_number": "1", "section_id": "", "evidence_id": "", "table_id": "",
               "figure_id": "", "crop_id": "", "source_type": "paragraph",
               "text": "test", "text_length": 4, "has_numeric_value": False,
               "has_unit_candidate": False, "numeric_values_detected": "",
               "units_detected": "", "structural_noise_flags": ""}]

    class FakeDoc:
        document_id = DOCUMENT_ID
        company = COMPANY
        company_name = "Test"
        company_slug = COMPANY
        fiscal_year = FISCAL_YEAR
        official_doc_type = "01_urd_annual_report"
        final_path = ""
        load_warnings: list = []

    candidates = [make_sample_candidate()]
    adapter.write_all(
        doc_input=FakeDoc(),
        chunks=chunks,
        retrieval_results=[],
        candidates=candidates,
        embedding_backend_status="lexical_fallback",
        variables_requested=["water_consumption"],
        elapsed_seconds=0.5,
    )
    assert (adapter.output_dir / "targeted_candidates_v2.csv").exists()
    assert (adapter.output_dir / "document_chunks_v2.csv").exists()
    assert (adapter.output_dir / "extraction_v2_summary.json").exists()
    assert (adapter.output_dir / "extraction_v2_quality_report.md").exists()


def test_validate_output_dir(tmp_path):
    # Create minimal valid output
    adapter = OutputAdapter(tmp_path / "v2_test_out")
    candidates = [make_sample_candidate()]

    class FakeDoc:
        document_id = DOCUMENT_ID
        company = COMPANY
        company_name = "Test"
        company_slug = COMPANY
        fiscal_year = FISCAL_YEAR
        official_doc_type = "01_urd_annual_report"
        final_path = ""
        load_warnings: list = []

    adapter.write_all(
        doc_input=FakeDoc(),
        chunks=[],
        retrieval_results=[],
        candidates=candidates,
        embedding_backend_status="lexical",
        variables_requested=["water_consumption"],
    )

    result = validate_output_dir(adapter.output_dir, CONTRACT_PATH)
    assert result["status"] in ("ok", "warning"), f"Validation failed: {result}"

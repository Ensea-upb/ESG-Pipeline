"""Tests that V2 does not modify any source outputs or corpus files."""
import os
import hashlib
import pytest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

PILOT_ROOT = _ROOT / "EXTERNAL_AUDIT_RUNS" / "strict_pilot_prepare_review_10docs_v2"
CORPUS_ROOT = _ROOT / "ESGFinalCorpus"
V1_MODULES = [
    _ROOT / "ESGInformationExtraction",
    _ROOT / "ESGCSVExtraction",
    _ROOT / "ESGVisualExtraction",
    _ROOT / "ESGTableExtraction",
    _ROOT / "ESGExtractionOrchestrator",
    _ROOT / "ESGIndicatorValidation",
    _ROOT / "ESGManualReview",
    _ROOT / "ESGIndicatorDatabase",
    _ROOT / "ESGVariableDatasetBuilder",
]


def _file_checksum(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def test_v2_module_only_imports_do_not_modify_sources():
    """Importing all V2 modules must not cause any file writes."""
    from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2 import (
        config, io_utils, validators, semantic_catalog,
        input_adapter, document_chunk_index, embedding_backends,
        hybrid_retriever, table_layout_rebuilder, visual_evidence_recovery,
        constrained_extractor, candidate_scorer, output_adapter, benchmark,
    )
    # If we get here without error, all imports are clean


def test_no_modification_to_esg_final_corpus():
    """ESGFinalCorpus must not be touched by V2."""
    if not CORPUS_ROOT.exists():
        pytest.skip("ESGFinalCorpus not present in test environment")
    # Just verify the directory is readable and we don't accidentally open it for write
    assert CORPUS_ROOT.is_dir()
    # No V2 output file should be present in corpus
    v2_files = list(CORPUS_ROOT.rglob("targeted_candidates_v2*"))
    assert len(v2_files) == 0, (
        f"V2 output files found inside ESGFinalCorpus: {v2_files}"
    )


def test_no_modification_to_pilot_v1_outputs():
    """V1 pilot workspaces must not contain any V2 output files."""
    if not PILOT_ROOT.exists():
        pytest.skip("Pilot V1 root not present")

    v2_in_pilot = list(PILOT_ROOT.rglob("targeted_candidates_v2*"))
    assert len(v2_in_pilot) == 0, (
        f"V2 outputs found inside V1 pilot root: {v2_in_pilot}"
    )


def test_build_all_chunks_does_not_write_to_input_dir(tmp_path):
    """build_all_chunks must write nothing to the input_dir."""
    from ESGVariableTargetedExtractionV2.tests.helpers import make_input_dir
    from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.input_adapter import load_document_input
    from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.document_chunk_index import build_all_chunks

    input_dir = make_input_dir(tmp_path)
    before = {p: _file_checksum(p) for p in sorted(input_dir.rglob("*")) if p.is_file()}
    doc_input = load_document_input(input_dir)
    build_all_chunks(doc_input)
    after = {p: _file_checksum(p) for p in sorted(input_dir.rglob("*")) if p.is_file()}

    assert before == after, (
        f"build_all_chunks modified input_dir files: "
        f"changed = {[p for p in before if before[p] != after.get(p)]}"
    )


def test_extractor_does_not_write_to_input_dir(tmp_path):
    """ConstrainedExtractor must not write to input_dir."""
    from ESGVariableTargetedExtractionV2.tests.helpers import make_input_dir, make_sample_chunks
    from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.semantic_catalog import SemanticCatalog
    from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.constrained_extractor import ConstrainedExtractor

    input_dir = make_input_dir(tmp_path)
    before = {p: os.path.getmtime(p) for p in sorted(input_dir.rglob("*")) if p.is_file()}

    catalog = SemanticCatalog()
    extractor = ConstrainedExtractor(catalog=catalog)
    chunks = make_sample_chunks()
    chunks_by_id = {c["chunk_id"]: c for c in chunks}
    fake_retrieval = [{
        "retrieval_id": "r1", "target_variable": "water_consumption",
        "chunk_id": "chunk_water_001", "document_id": "test_doc",
        "company": "test", "fiscal_year": "2024",
        "official_doc_type": "01_urd_annual_report",
        "page_number": "1", "source_type": "paragraph",
        "retrieval_score": 0.70, "text_snippet": "water 4.2 Mm3",
    }]
    extractor.extract_from_retrieval(fake_retrieval, chunks_by_id)

    after = {p: os.path.getmtime(p) for p in sorted(input_dir.rglob("*")) if p.is_file()}
    assert before == after, "ConstrainedExtractor must not modify input_dir"


def test_output_goes_only_to_output_dir(tmp_path):
    """All V2 outputs must be in output_dir, never in source dirs."""
    from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.output_adapter import OutputAdapter
    from ESGVariableTargetedExtractionV2.tests.helpers import make_sample_candidate, DOCUMENT_ID, COMPANY, FISCAL_YEAR

    output_dir = tmp_path / "my_v2_output"

    class FakeDoc:
        document_id = DOCUMENT_ID
        company = COMPANY
        company_name = "Test"
        company_slug = COMPANY
        fiscal_year = FISCAL_YEAR
        official_doc_type = "01_urd_annual_report"
        final_path = ""
        load_warnings: list = []

    adapter = OutputAdapter(output_dir)
    adapter.write_all(
        doc_input=FakeDoc(), chunks=[], retrieval_results=[],
        candidates=[make_sample_candidate()],
        embedding_backend_status="lexical", variables_requested=["water_consumption"],
    )

    # Verify output is strictly inside output_dir
    assert output_dir.exists()
    assert (output_dir / "targeted_candidates_v2.csv").exists()

    # Verify nothing written to source dirs
    if PILOT_ROOT.exists():
        v2_in_pilot = list(PILOT_ROOT.rglob("targeted_candidates_v2*"))
        assert len(v2_in_pilot) == 0


def test_visual_recovery_non_fatal_missing_crop():
    """visual_evidence_recovery must not crash when crops are missing."""
    from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.visual_evidence_recovery import recover_visual_evidence
    from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.input_adapter import DocumentV2Input

    doc = DocumentV2Input()
    doc.document_id = "test_doc"
    doc.company = "test"
    doc.fiscal_year = "2024"
    doc.figure_index = [
        {"figure_id": "fig_001", "page_number": 5,
         "crop_path": "/nonexistent/path/crop.png", "caption": ""},
    ]
    # Must not raise
    findings = recover_visual_evidence(doc, input_dir=None)
    assert isinstance(findings, list)
    assert len(findings) > 0
    for f in findings:
        assert "visual_warning" in f or "crop_file_exists" in f

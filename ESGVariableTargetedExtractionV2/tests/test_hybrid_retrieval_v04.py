"""Tests for HybridRetriever — variable ranking, ISO penalty, unit matching."""
import pytest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.tests.helpers import make_sample_chunks
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.semantic_catalog import SemanticCatalog
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.embedding_backends import FakeEmbeddingBackend
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.hybrid_retriever import HybridRetriever

CATALOG_PATH = _ROOT / "ESGVariableTargetedExtractionV2" / "config" / "variable_semantic_catalog_v1.yaml"


@pytest.fixture(scope="module")
def catalog():
    return SemanticCatalog(CATALOG_PATH)


@pytest.fixture(scope="module")
def backend():
    return FakeEmbeddingBackend()


@pytest.fixture(scope="module")
def retriever(catalog, backend):
    return HybridRetriever(
        catalog=catalog,
        backend=backend,
        top_k=10,
        min_score=0.0,  # Low threshold so all chunks can be ranked
    )


@pytest.fixture(scope="module")
def sample_chunks():
    return make_sample_chunks()


def test_retrieval_ranks_water_chunk_for_water_consumption(retriever, catalog, sample_chunks):
    results = retriever.retrieve_for_variable(sample_chunks, "water_consumption")
    assert len(results) > 0, "Should retrieve at least one result for water_consumption"
    top_result = results[0]
    # Water chunk should be top ranked
    assert top_result["chunk_id"] == "chunk_water_001", (
        f"Water chunk should be top for water_consumption, got: {top_result['chunk_id']}"
    )


def test_retrieval_ranks_employees_chunk_for_human_capital(retriever, catalog, sample_chunks):
    results = retriever.retrieve_for_variable(sample_chunks, "human_capital")
    assert len(results) > 0
    top_ids = [r["chunk_id"] for r in results[:3]]
    assert "chunk_employees_001" in top_ids, (
        f"Employee chunk should be in top 3 for human_capital, top: {top_ids}"
    )


def test_retrieval_ranks_ghg_chunk_for_co2_emissions(retriever, catalog, sample_chunks):
    results = retriever.retrieve_for_variable(sample_chunks, "co2_emissions")
    assert len(results) > 0
    top_ids = [r["chunk_id"] for r in results[:3]]
    assert "chunk_ghg_001" in top_ids, (
        f"GHG chunk should be in top 3 for co2_emissions, top: {top_ids}"
    )


def test_retrieval_penalizes_iso_standard_noise(retriever, catalog, sample_chunks):
    results_water = retriever.retrieve_for_variable(sample_chunks, "water_consumption")
    results_by_id = {r["chunk_id"]: r for r in results_water}
    # ISO noise chunk should have a penalty applied
    if "chunk_iso_noise_001" in results_by_id:
        iso_result = results_by_id["chunk_iso_noise_001"]
        water_result = results_by_id.get("chunk_water_001")
        if water_result:
            assert iso_result["retrieval_score"] < water_result["retrieval_score"], (
                "ISO noise chunk should score lower than water chunk for water_consumption"
            )
        assert iso_result["structural_penalty"] > 0, "ISO noise chunk must have structural penalty"


def test_retrieval_results_have_required_fields(retriever, catalog, sample_chunks):
    results = retriever.retrieve_for_variable(sample_chunks, "co2_emissions")
    required = [
        "retrieval_id", "target_variable", "chunk_id", "document_id",
        "retrieval_score", "embedding_score", "keyword_score",
    ]
    for res in results:
        for field in required:
            assert field in res, f"Missing field '{field}' in retrieval result"


def test_retrieval_top_k_respected(catalog, backend, sample_chunks):
    retriever = HybridRetriever(catalog=catalog, backend=backend, top_k=2, min_score=0.0)
    results = retriever.retrieve_for_variable(sample_chunks, "water_consumption")
    assert len(results) <= 2, f"top_k=2 must be respected, got {len(results)}"


def test_retrieve_all_variables_returns_multi_variable_results(retriever, catalog, sample_chunks):
    results = retriever.retrieve_all_variables(sample_chunks, ["water_consumption", "human_capital"])
    variables_found = set(r["target_variable"] for r in results)
    assert "water_consumption" in variables_found
    assert "human_capital" in variables_found


def test_retrieval_score_in_range(retriever, catalog, sample_chunks):
    results = retriever.retrieve_all_variables(sample_chunks, ["co2_emissions", "water_consumption"])
    for res in results:
        score = res["retrieval_score"]
        assert 0.0 <= score <= 1.0, f"retrieval_score must be in [0,1], got {score}"

"""Tests for embedding backends — FakeBackend determinism, LexicalFallback no external deps."""
import pytest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.embedding_backends import (
    FakeEmbeddingBackend, LexicalFallbackBackend, get_backend,
)


def test_fake_embedding_backend_is_deterministic():
    backend = FakeEmbeddingBackend()
    texts = ["water consumption m3", "CO2 emissions scope 1"]
    v1 = backend.encode_texts(texts)
    v2 = backend.encode_texts(texts)
    assert v1 == v2, "FakeEmbeddingBackend must be deterministic"


def test_fake_embedding_backend_produces_correct_dim():
    backend = FakeEmbeddingBackend()
    vecs = backend.encode_texts(["test text"])
    assert len(vecs) == 1
    assert len(vecs[0]) == FakeEmbeddingBackend.DIM


def test_fake_embedding_backend_different_texts_different_vectors():
    backend = FakeEmbeddingBackend()
    v1 = backend.encode_texts(["water consumption"])
    v2 = backend.encode_texts(["carbon emissions"])
    assert v1[0] != v2[0], "Different texts should produce different vectors"


def test_fake_embedding_backend_normalized():
    import math
    backend = FakeEmbeddingBackend()
    vec = backend.encode_texts(["normalized vector test"])[0]
    norm = math.sqrt(sum(v * v for v in vec))
    assert abs(norm - 1.0) < 1e-6, "FakeBackend should produce normalized vectors"


def test_lexical_fallback_backend_no_external_dependency():
    """LexicalFallbackBackend must work without any external package."""
    backend = LexicalFallbackBackend()
    texts = ["water consumption in m3", "total employees FTE", "GHG emissions CO2e"]
    backend.fit(texts)
    vecs = backend.encode_texts(texts)
    assert len(vecs) == len(texts)
    assert all(len(v) == LexicalFallbackBackend.DIM for v in vecs)


def test_lexical_fallback_encodes_without_prior_fit():
    backend = LexicalFallbackBackend()
    texts = ["energy consumption kWh"]
    vecs = backend.encode_texts(texts)
    assert len(vecs) == 1
    assert len(vecs[0]) > 0


def test_lexical_fallback_different_texts_different_vectors():
    backend = LexicalFallbackBackend()
    corpus = ["water withdrawal Mm3", "employee headcount FTE", "carbon emissions ktCO2e"]
    backend.fit(corpus)
    v1 = backend.encode_texts(["water withdrawal"])
    v2 = backend.encode_texts(["employee headcount"])
    assert v1[0] != v2[0], "Different texts should produce different lexical vectors"


def test_get_backend_returns_lexical_on_request():
    backend, status = get_backend(backend_name="lexical")
    assert isinstance(backend, LexicalFallbackBackend)
    assert status == "lexical_fallback"


def test_get_backend_returns_fake_on_request():
    backend, status = get_backend(backend_name="fake")
    assert isinstance(backend, FakeEmbeddingBackend)
    assert status == "fake"


def test_get_backend_auto_falls_back_when_hf_unavailable():
    """When HF model not present, auto should fall back to lexical."""
    backend, status = get_backend(
        backend_name="auto",
        model_name="nonexistent-model-xyz-12345",
        offline_mode=True,
        fallback_backend="lexical",
    )
    assert isinstance(backend, LexicalFallbackBackend)
    assert "lexical" in status or "fallback" in status


def test_huggingface_backend_not_downloaded_in_test():
    """HuggingFace backend should not download during tests."""
    from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.embedding_backends import (
        HuggingFaceEmbeddingBackend,
    )
    hf = HuggingFaceEmbeddingBackend(
        model_name="nonexistent-xyz-model",
        offline_mode=True,
    )
    # Should report unavailable, not raise or download
    available = hf.is_available
    assert available is False

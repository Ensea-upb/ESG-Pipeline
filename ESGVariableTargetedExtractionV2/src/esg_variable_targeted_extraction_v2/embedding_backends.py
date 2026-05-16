"""
embedding_backends.py — Pluggable embedding backends for hybrid retrieval.
No HF model download during tests. FakeEmbeddingBackend for unit tests.
"""
from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from typing import Any


class EmbeddingBackend(ABC):
    """Base interface for all embedding backends."""

    @abstractmethod
    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def is_available(self) -> bool:
        return True


# ──────────────────────────────────────────────────────────────────
# FakeEmbeddingBackend — deterministic, tests only
# ──────────────────────────────────────────────────────────────────

class FakeEmbeddingBackend(EmbeddingBackend):
    """
    Deterministic embedding backend for unit tests.
    Produces fixed-length vectors based on text hash — no external deps.
    """

    DIM = 64

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._text_to_vec(t) for t in texts]

    def _text_to_vec(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vals: list[float] = []
        for i in range(0, min(len(h), self.DIM), 1):
            vals.append((h[i % len(h)] / 127.5) - 1.0)
        while len(vals) < self.DIM:
            vals.append(0.0)
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]

    @property
    def name(self) -> str:
        return "fake"


# ──────────────────────────────────────────────────────────────────
# LexicalFallbackBackend — TF-IDF-like, no external deps
# ──────────────────────────────────────────────────────────────────

class LexicalFallbackBackend(EmbeddingBackend):
    """
    TF-IDF-inspired embedding backend. No external dependencies.
    Used when HuggingFace model is unavailable.

    Vocabulary selection: most discriminative tokens (high IDF = low document frequency).
    Excludes stopwords (appearing in > 50% of docs) and hapax (appearing once).
    DIM=512 for adequate ESG vocabulary coverage.
    """

    DIM = 512

    def __init__(self) -> None:
        self._vocab: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._fitted = False

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9À-ÿ]+", text.lower())

    def fit(self, corpus: list[str]) -> None:
        n_docs = len(corpus)
        if n_docs == 0:
            return
        df: Counter = Counter()
        for doc in corpus:
            tokens = set(self._tokenize(doc))
            df.update(tokens)

        # Select most DISCRIMINATIVE tokens:
        # - Exclude tokens appearing in > 50% of docs (stopwords, structure markers)
        # - Exclude hapax (df == 1) — noise
        # - Sort by ascending df (= descending IDF) → most discriminative first
        # min_df: adaptive — skip hapax in large corpora (noise, OCR errors, page numbers)
        # For 3-doc test corpus min_df=1, for 17k-chunk corpus min_df≈17 (0.1%)
        min_df = max(1, int(n_docs * 0.001))
        max_df_threshold = max(2, int(n_docs * 0.50))
        candidates = sorted(
            ((t, cnt) for t, cnt in df.items() if min_df <= cnt <= max_df_threshold),
            key=lambda x: x[1],  # ascending df = descending IDF
        )
        top_tokens = [t for t, _ in candidates[: self.DIM]]

        # If not enough candidates, fill with high-df tokens (at least cover common ESG terms)
        if len(top_tokens) < self.DIM:
            seen = set(top_tokens)
            extras = sorted(
                ((t, cnt) for t, cnt in df.items() if t not in seen and cnt > max_df_threshold),
                key=lambda x: x[1],
            )
            top_tokens.extend(t for t, _ in extras[: self.DIM - len(top_tokens)])

        self._vocab = {t: i for i, t in enumerate(top_tokens)}
        self._idf = {
            t: math.log((1 + n_docs) / (1 + cnt)) + 1.0
            for t, cnt in df.items()
            if t in self._vocab
        }
        self._fitted = True

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        if not self._fitted and texts:
            self.fit(texts)
        return [self._encode_one(t) for t in texts]

    def _encode_one(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        tf: Counter = Counter(tokens)
        n_tokens = len(tokens) or 1
        vec = [0.0] * self.DIM
        for token, count in tf.items():
            if token in self._vocab:
                idx = self._vocab[token]  # direct index, no modulo — no collision
                tfidf = (count / n_tokens) * self._idf.get(token, 1.0)
                vec[idx] += tfidf
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    @property
    def name(self) -> str:
        return "lexical"


# ──────────────────────────────────────────────────────────────────
# HuggingFaceEmbeddingBackend — optional, local/offline only
# ──────────────────────────────────────────────────────────────────

class HuggingFaceEmbeddingBackend(EmbeddingBackend):
    """
    sentence-transformers backend. Requires model to be already downloaded locally.
    If model is unavailable, raises RuntimeError — caller must handle fallback.
    Never downloads during tests (offline_mode=True).
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        local_model_path: str | None = None,
        device: str = "auto",
        batch_size: int = 16,
        normalize_embeddings: bool = True,
        offline_mode: bool = True,
    ) -> None:
        self.model_name = model_name
        self.local_model_path = local_model_path
        self.device = device
        self.batch_size = batch_size
        self.normalize_embeddings = normalize_embeddings
        self.offline_mode = offline_mode
        self._model: Any = None
        self._available: bool | None = None

    def _load_model(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            from sentence_transformers import SentenceTransformer
            import os
            if self.offline_mode:
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
                os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
            model_id = self.local_model_path or self.model_name
            dev = None if self.device == "auto" else self.device
            self._model = SentenceTransformer(model_id, device=dev)
            self._available = True
        except Exception:
            self._available = False
        return self._available

    @property
    def is_available(self) -> bool:
        return self._load_model()

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        if not self._load_model() or self._model is None:
            raise RuntimeError(
                f"HuggingFace model '{self.model_name}' is not available locally. "
                "Set embedding_backend: lexical or fake in config, or download the model first."
            )
        vecs = self._model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vecs]

    @property
    def name(self) -> str:
        return "huggingface"


# ──────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────

def get_backend(
    backend_name: str = "auto",
    model_name: str = "BAAI/bge-m3",
    local_model_path: str | None = None,
    device: str = "auto",
    batch_size: int = 16,
    normalize_embeddings: bool = True,
    offline_mode: bool = True,
    fallback_backend: str = "lexical",
) -> tuple[EmbeddingBackend, str]:
    """
    Return (backend, backend_status) where status is one of:
    - 'huggingface_local'
    - 'lexical_fallback'
    - 'unavailable_fallback_lexical'
    - 'fake'
    """
    if backend_name == "fake":
        return FakeEmbeddingBackend(), "fake"

    if backend_name == "lexical":
        return LexicalFallbackBackend(), "lexical_fallback"

    if backend_name in ("huggingface", "huggingface_local", "auto"):
        hf = HuggingFaceEmbeddingBackend(
            model_name=model_name,
            local_model_path=local_model_path,
            device=device,
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
            offline_mode=offline_mode,
        )
        if hf.is_available:
            return hf, "huggingface_local"
        # Fall back
        fallback = LexicalFallbackBackend() if fallback_backend == "lexical" else FakeEmbeddingBackend()
        return fallback, "unavailable_fallback_lexical"

    # Default
    return LexicalFallbackBackend(), "lexical_fallback"

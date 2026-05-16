"""
hybrid_retriever.py — Variable-targeted hybrid retrieval over document chunks.
Score = embedding_weight * emb + keyword_weight * kw + unit_weight * unit + section_weight * sec
        - structural_penalty
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from .embedding_backends import EmbeddingBackend, LexicalFallbackBackend
from .semantic_catalog import SemanticCatalog

_RETRIEVAL_COLUMNS = [
    "retrieval_id", "target_variable", "chunk_id", "document_id", "company",
    "fiscal_year", "official_doc_type", "page_number", "source_type",
    "retrieval_score", "embedding_score", "keyword_score", "unit_score",
    "section_score", "structural_penalty", "matched_terms", "matched_units",
    "text_snippet",
]

_SECTION_TYPE_BOOST = {
    "environmental": 0.15,
    "social": 0.10,
    "governance": 0.10,
    "sustainability": 0.12,
    "climate": 0.15,
    "financial": 0.08,
    "unknown": 0.0,
}

_STRUCTURAL_NOISE_PATTERNS = [
    re.compile(r"\bISO\s*\d{4,5}\b", re.IGNORECASE),
    re.compile(r"^\d{1,2}\.\d{1,2}$", re.MULTILINE),
    re.compile(r"\bpage\s+\d+\b", re.IGNORECASE),
    re.compile(r"^\d{1}$", re.MULTILINE),
]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


def _keyword_score(text: str, terms: list[str], positive: list[str]) -> tuple[float, list[str]]:
    text_lower = text.lower()
    matched: list[str] = []
    score = 0.0
    all_terms = [t.lower() for t in terms + positive]
    for term in all_terms:
        if term and term in text_lower:
            matched.append(term)
            # Longer/more specific terms score higher
            score += min(0.15, 0.05 + len(term) * 0.005)
    return min(1.0, score), matched


def _unit_score(text: str, expected_units: list[str]) -> tuple[float, list[str]]:
    text_lower = text.lower()
    matched: list[str] = []
    for unit in expected_units:
        if unit.lower() in text_lower:
            matched.append(unit)
    score = min(1.0, len(matched) * 0.35)
    return score, matched


def _section_score(chunk: dict[str, Any], variable: str, catalog: SemanticCatalog) -> float:
    sec_id = chunk.get("section_id", "")
    source_type = chunk.get("source_type", "")
    domain = catalog.get_domain(variable)

    boost = 0.0
    if "table" in source_type:
        boost += 0.08
    if sec_id:
        boost += _SECTION_TYPE_BOOST.get(domain, 0.0) * 0.5

    preferred = catalog.get_preferred_doc_types(variable)
    doc_type = chunk.get("official_doc_type", "")
    if preferred and doc_type in preferred:
        boost += 0.10

    return min(1.0, boost)


def _structural_penalty(text: str, chunk: dict[str, Any]) -> float:
    noise_flags = chunk.get("structural_noise_flags", "")
    penalty = 0.0
    for pat in _STRUCTURAL_NOISE_PATTERNS:
        if pat.search(text):
            penalty += 0.20
    if noise_flags:
        penalty += 0.10
    return min(0.50, penalty)


def _retrieval_id(target_variable: str, chunk_id: str) -> str:
    raw = f"{target_variable}|{chunk_id}"
    return "ret_" + hashlib.md5(raw.encode()).hexdigest()[:20]


class HybridRetriever:
    def __init__(
        self,
        catalog: SemanticCatalog,
        backend: EmbeddingBackend,
        embedding_weight: float = 0.60,
        keyword_weight: float = 0.25,
        unit_weight: float = 0.10,
        section_weight: float = 0.05,
        top_k: int = 20,
        min_score: float = 0.25,
    ) -> None:
        self.catalog = catalog
        self.backend = backend
        self.embedding_weight = embedding_weight
        self.keyword_weight = keyword_weight
        self.unit_weight = unit_weight
        self.section_weight = section_weight
        self.top_k = top_k
        self.min_score = min_score

        # LexicalFallbackBackend needs to be fitted on the corpus
        self._fitted = False

    def _fit_backend_if_needed(self, chunks: list[dict[str, Any]]) -> None:
        if self._fitted:
            return
        if isinstance(self.backend, LexicalFallbackBackend) and not self.backend._fitted:
            texts = [c.get("text", "") for c in chunks]
            self.backend.fit(texts)
        self._fitted = True

    def retrieve_for_variable(
        self,
        chunks: list[dict[str, Any]],
        variable: str,
        chunk_embeddings: list[list[float]] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve and rank chunks for a single target variable."""
        if not chunks:
            return []

        cfg = self.catalog.get_variable_config(variable)
        if not cfg:
            return []

        self._fit_backend_if_needed(chunks)

        query_terms = self.catalog.get_all_query_terms(variable)
        positive_patterns = self.catalog.get_positive_patterns(variable)
        expected_units = self.catalog.get_expected_units(variable)

        # Encode query as single string
        query_text = " ".join(query_terms[:8])
        try:
            query_vec = self.backend.encode_texts([query_text])[0]
        except Exception:
            query_vec = []

        # Get or compute chunk embeddings
        if chunk_embeddings is None:
            texts = [c.get("text", "") for c in chunks]
            try:
                chunk_embeddings = self.backend.encode_texts(texts)
            except Exception:
                chunk_embeddings = [[] for _ in chunks]

        results: list[dict[str, Any]] = []
        for chunk, emb in zip(chunks, chunk_embeddings):
            text = chunk.get("text", "")
            if not text:
                continue

            # Embedding similarity
            if query_vec and emb:
                emb_score = _cosine(query_vec, emb)
            else:
                emb_score = 0.0

            # Keyword score
            kw_score, matched_terms = _keyword_score(text, query_terms, positive_patterns)

            # Unit score
            u_score, matched_units = _unit_score(text, expected_units)

            # Section boost
            s_score = _section_score(chunk, variable, self.catalog)

            # Structural noise penalty
            penalty = _structural_penalty(text, chunk)

            # Final weighted score
            final_score = (
                self.embedding_weight * emb_score
                + self.keyword_weight * kw_score
                + self.unit_weight * u_score
                + self.section_weight * s_score
                - penalty
            )
            final_score = max(0.0, min(1.0, final_score))

            if final_score < self.min_score and not matched_terms:
                continue

            results.append({
                "retrieval_id": _retrieval_id(variable, chunk["chunk_id"]),
                "target_variable": variable,
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk.get("document_id", ""),
                "company": chunk.get("company", ""),
                "fiscal_year": chunk.get("fiscal_year", ""),
                "official_doc_type": chunk.get("official_doc_type", ""),
                "page_number": chunk.get("page_number", ""),
                "source_type": chunk.get("source_type", ""),
                "retrieval_score": round(final_score, 4),
                "embedding_score": round(emb_score, 4),
                "keyword_score": round(kw_score, 4),
                "unit_score": round(u_score, 4),
                "section_score": round(s_score, 4),
                "structural_penalty": round(penalty, 4),
                "matched_terms": ",".join(matched_terms[:6]),
                "matched_units": ",".join(matched_units[:4]),
                "text_snippet": text[:300],
            })

        # Sort by score descending, keep top_k
        results.sort(key=lambda x: x["retrieval_score"], reverse=True)
        return results[: self.top_k]

    def retrieve_all_variables(
        self,
        chunks: list[dict[str, Any]],
        variables: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve top-k chunks for each variable. Encodes chunks once."""
        if not chunks:
            return []

        vars_to_run = variables or self.catalog.list_variables()
        self._fit_backend_if_needed(chunks)

        # Encode all chunks once
        texts = [c.get("text", "") for c in chunks]
        try:
            chunk_embeddings = self.backend.encode_texts(texts)
        except Exception:
            chunk_embeddings = [[] for _ in chunks]

        all_results: list[dict[str, Any]] = []
        for var in vars_to_run:
            var_results = self.retrieve_for_variable(chunks, var, chunk_embeddings)
            all_results.extend(var_results)

        return all_results

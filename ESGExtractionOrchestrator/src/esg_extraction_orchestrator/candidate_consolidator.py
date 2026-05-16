from __future__ import annotations

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .io_utils import write_csv, write_jsonl

log = logging.getLogger(__name__)


CONSOLIDATED_FIELDS = [
    "document_id", "company", "fiscal_year", "source_engine", "information_type", "esg_category", "label",
    "raw_value", "raw_unit", "year", "source_modality", "page_number", "section_id",
    "evidence_id", "table_id", "cell_id", "figure_id", "quote", "confidence",
    "review_required", "extraction_status", "source_information_type",
    "normalized_candidate_key", "deduplication_group_id", "deduplication_status",
    "canonical_candidate_id", "duplicate_reason",
]


DEDUPLICATION_GROUP_FIELDS = [
    "deduplication_group_id", "canonical_candidate_id", "group_size", "duplicate_reason",
    "document_id", "information_type", "page_number", "normalized_quote",
    "source_engines",
]


def consolidate_candidates(collected: dict[str, Any], output_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in collected["csv"]["rows"]:
        rows.append({
            "document_id": row.get("document_id", ""),
            "company": row.get("company", ""),
            "fiscal_year": row.get("fiscal_year", ""),
            "source_engine": "csv",
            "information_type": row.get("information_type", ""),
            "esg_category": row.get("esg_category", ""),
            "label": row.get("label", ""),
            "raw_value": row.get("raw_value", ""),
            "raw_unit": row.get("raw_unit", ""),
            "year": row.get("year", ""),
            "source_modality": row.get("source_modality", "text"),
            "page_number": row.get("page_number", ""),
            "section_id": row.get("section_id", ""),
            "evidence_id": row.get("evidence_id", ""),
            "table_id": "",
            "cell_id": "",
            "figure_id": "",
            "quote": row.get("quote", ""),
            "confidence": row.get("confidence", ""),
            "review_required": row.get("review_required", ""),
            "extraction_status": row.get("extraction_status", ""),
            "source_information_type": row.get("information_type", ""),
        })
    for row in collected["visual"]["rows"]:
        rows.append({
            "document_id": row.get("document_id", ""),
            "company": row.get("company", ""),
            "fiscal_year": row.get("fiscal_year", ""),
            "source_engine": "visual",
            "information_type": row.get("information_type", ""),
            "esg_category": row.get("esg_category", ""),
            "label": row.get("label", ""),
            "raw_value": row.get("raw_value", ""),
            "raw_unit": row.get("raw_unit", ""),
            "year": row.get("year", ""),
            "source_modality": "figure",
            "page_number": row.get("page_number", ""),
            "section_id": row.get("section_id", ""),
            "evidence_id": "",
            "table_id": "",
            "cell_id": "",
            "figure_id": row.get("figure_id", ""),
            "quote": row.get("ocr_text") or row.get("caption", ""),
            "confidence": row.get("confidence", ""),
            "review_required": row.get("review_required", ""),
            "extraction_status": row.get("extraction_status", ""),
            "source_information_type": row.get("information_type", ""),
        })
    for row in collected["table"]["rows"]:
        # Preserve the original information_type from the table engine (target,
        # policy, metric, etc.) instead of blindly overwriting with a generic tag.
        original_table_type = row.get("information_type", "") or "table_metric_candidate"
        rows.append({
            "document_id": row.get("document_id", ""),
            "company": row.get("company", ""),
            "fiscal_year": row.get("fiscal_year", ""),
            "source_engine": "table",
            "information_type": original_table_type,
            "esg_category": row.get("esg_category", ""),
            "label": row.get("metric_label", ""),
            "raw_value": row.get("raw_value", ""),
            "raw_unit": row.get("raw_unit", ""),
            "year": row.get("reported_year", ""),
            "source_modality": "table",
            "page_number": row.get("page_number", ""),
            "section_id": row.get("section_id", ""),
            "evidence_id": "",
            "table_id": row.get("table_id", ""),
            "cell_id": row.get("cell_id", ""),
            "figure_id": "",
            "quote": row.get("source_row_text", ""),
            "confidence": row.get("confidence", ""),
            "review_required": row.get("review_required", ""),
            "extraction_status": row.get("extraction_status", ""),
            "source_information_type": original_table_type,
        })

    # Backfill company/fiscal_year for rows that lack them (visual candidates
    # in particular often omit metadata). We prefer structured engines (table,
    # csv) over visual as metadata sources; within an engine we take the first
    # complete record found.
    ENGINE_META_PRIORITY = {"table": 0, "csv": 1, "visual": 2}
    doc_meta: dict[str, dict[str, str]] = {}
    for row in sorted(rows, key=lambda r: ENGINE_META_PRIORITY.get(r.get("source_engine", ""), 9)):
        doc_id = row.get("document_id", "")
        if doc_id and row.get("company") and row.get("fiscal_year") and doc_id not in doc_meta:
            doc_meta[doc_id] = {
                "company": str(row["company"]),
                "fiscal_year": str(row["fiscal_year"]),
            }
    for row in rows:
        doc_id = row.get("document_id", "")
        if doc_id in doc_meta and not row.get("company"):
            row["company"] = doc_meta[doc_id]["company"]
            row["fiscal_year"] = doc_meta[doc_id]["fiscal_year"]

    _apply_deduplication_audit(rows, output_dir)
    write_csv(output_dir / "consolidated_candidates.csv", rows, CONSOLIDATED_FIELDS)
    write_jsonl(output_dir / "consolidated_candidates.jsonl", rows)
    unique_rows = [row for row in rows if row.get("deduplication_status") != "duplicate_candidate"]
    write_csv(output_dir / "consolidated_unique_candidates.csv", unique_rows, CONSOLIDATED_FIELDS)
    write_jsonl(output_dir / "consolidated_unique_candidates.jsonl", unique_rows)
    return rows


def _apply_deduplication_audit(rows: list[dict[str, Any]], output_dir: Path) -> None:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = _candidate_key(row)
        row["normalized_candidate_key"] = key
        groups[key].append(row)

    duplicate_group_rows: list[dict[str, Any]] = []
    duplicate_group_index = 1
    for key, group in groups.items():
        group_id = f"dedup_group_{duplicate_group_index:04d}"
        canonical = _select_canonical(group)
        canonical_id = _candidate_id(canonical)
        reason = _duplicate_reason(group)
        if len(group) == 1:
            row = group[0]
            row["deduplication_group_id"] = ""
            row["deduplication_status"] = "unique_candidate"
            row["canonical_candidate_id"] = _candidate_id(row)
            row["duplicate_reason"] = ""
            continue
        duplicate_group_index += 1
        for row in group:
            row["deduplication_group_id"] = group_id
            row["canonical_candidate_id"] = canonical_id
            row["duplicate_reason"] = reason
            row["deduplication_status"] = "canonical_candidate" if row is canonical else "duplicate_candidate"
        # When multiple engines agree on the same candidate, boost canonical
        # confidence to reflect multi-source consensus (capped at engine max).
        engine_max = {"table": 0.6, "csv": 0.6, "visual": 0.5}
        canonical_engine = canonical.get("source_engine", "csv")
        if reason == "same_candidate_across_engines":
            boosted = _safe_float(canonical.get("confidence", "")) + 0.05 * (len(group) - 1)
            canonical["confidence"] = round(min(boosted, engine_max.get(canonical_engine, 0.6)), 3)

        # Use the same truncation length as the dedup key to avoid confusion.
        QUOTE_TRUNC = 160
        duplicate_group_rows.append({
            "deduplication_group_id": group_id,
            "canonical_candidate_id": canonical_id,
            "group_size": len(group),
            "duplicate_reason": reason,
            "document_id": canonical.get("document_id", ""),
            "information_type": canonical.get("information_type", ""),
            "page_number": canonical.get("page_number", ""),
            "normalized_quote": _normalize_text(canonical.get("quote", ""))[:QUOTE_TRUNC],
            "source_engines": "|".join(sorted(set(row.get("source_engine", "") for row in group))),
        })

    duplicate_group_index = _semantic_dedup_pass(rows, duplicate_group_rows, duplicate_group_index)

    write_jsonl(output_dir / "consolidated_duplicate_groups.jsonl", duplicate_group_rows)
    write_csv(output_dir / "consolidated_duplicate_groups.csv", duplicate_group_rows, DEDUPLICATION_GROUP_FIELDS)


def _uf_find(parent: list[int], x: int) -> int:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _semantic_dedup_pass(
    rows: list[dict[str, Any]],
    duplicate_group_rows: list[dict[str, Any]],
    duplicate_group_index: int,
) -> int:
    """Detect soft duplicates whose quotes are semantically identical but differ in phrasing/language.

    Operates only on rows already tagged unique_candidate. Groups candidates by
    (document_id, information_type, year, raw_value) before computing embeddings so
    that candidates from different data points (same metric, different year) are
    never mistakenly merged.
    """
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        log.debug("sentence-transformers not available — semantic dedup skipped.")
        return duplicate_group_index

    unique_rows = [
        row for row in rows
        if row.get("deduplication_status") in ("unique_candidate", None, "")
    ]

    scope_groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in unique_rows:
        key = (
            _normalize_text(row.get("document_id", "")),
            _normalize_text(row.get("information_type", "")),
            _normalize_text(str(row.get("year", ""))),
            _normalize_text(str(row.get("raw_value", ""))),
        )
        scope_groups[key].append(row)

    candidate_groups = [(k, v) for k, v in scope_groups.items() if len(v) >= 2]
    if not candidate_groups:
        return duplicate_group_index

    try:
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    except Exception as exc:
        log.warning("Could not load sentence-transformers model for semantic dedup: %s", exc)
        return duplicate_group_index

    THRESHOLD = 0.90
    QUOTE_TRUNC = 160

    for _scope_key, group_rows in candidate_groups:
        texts = [
            (row.get("quote") or row.get("label") or "")[:300]
            for row in group_rows
        ]
        if not any(t.strip() for t in texts):
            continue

        try:
            embeddings = model.encode(texts, normalize_embeddings=True)
        except Exception as exc:
            log.debug("Embedding failed for scope group: %s", exc)
            continue

        sim_matrix = np.dot(embeddings, embeddings.T)
        n = len(group_rows)
        parent = list(range(n))

        for i in range(n):
            for j in range(i + 1, n):
                if float(sim_matrix[i, j]) >= THRESHOLD:
                    pi, pj = _uf_find(parent, i), _uf_find(parent, j)
                    if pi != pj:
                        parent[pj] = pi

        cluster_map: dict[int, list[int]] = defaultdict(list)
        for i in range(n):
            cluster_map[_uf_find(parent, i)].append(i)

        for indices in cluster_map.values():
            if len(indices) < 2:
                continue
            cluster = [group_rows[i] for i in indices]
            canonical = _select_canonical(cluster)
            canonical_id = _candidate_id(canonical)
            group_id = f"dedup_group_{duplicate_group_index:04d}"
            duplicate_group_index += 1

            for row in cluster:
                row["deduplication_group_id"] = group_id
                row["canonical_candidate_id"] = canonical_id
                row["duplicate_reason"] = "semantic_duplicate"
                row["deduplication_status"] = (
                    "canonical_candidate" if row is canonical else "duplicate_candidate"
                )

            duplicate_group_rows.append({
                "deduplication_group_id": group_id,
                "canonical_candidate_id": canonical_id,
                "group_size": len(cluster),
                "duplicate_reason": "semantic_duplicate",
                "document_id": canonical.get("document_id", ""),
                "information_type": canonical.get("information_type", ""),
                "page_number": canonical.get("page_number", ""),
                "normalized_quote": _normalize_text(canonical.get("quote", ""))[:QUOTE_TRUNC],
                "source_engines": "|".join(
                    sorted(set(row.get("source_engine", "") for row in cluster))
                ),
            })

    return duplicate_group_index


def _candidate_key(row: dict[str, Any]) -> str:
    quote = _normalize_text(row.get("quote", ""))
    value = _normalize_text(row.get("raw_value", ""))
    label = _normalize_text(row.get("label", ""))
    return "|".join([
        _normalize_text(row.get("document_id", "")),
        _normalize_text(row.get("information_type", "")),
        _normalize_text(row.get("page_number", "")),
        value,
        quote[:160] or label[:160],
    ])


def _candidate_id(row: dict[str, Any]) -> str:
    for field in ("evidence_id", "cell_id", "figure_id"):
        value = row.get(field)
        if value:
            return f"{row.get('source_engine', '')}:{value}:{row.get('information_type', '')}"
    return f"{row.get('source_engine', '')}:{row.get('normalized_candidate_key', '')}"


def _select_canonical(group: list[dict[str, Any]]) -> dict[str, Any]:
    source_priority = {"table": 0, "csv": 1, "visual": 2}
    return sorted(
        group,
        key=lambda row: (
            source_priority.get(row.get("source_engine", ""), 9),
            -_safe_float(row.get("confidence", "")),
            len(row.get("quote", "")),
        ),
    )[0]


def _duplicate_reason(group: list[dict[str, Any]]) -> str:
    source_counts = Counter(row.get("source_engine", "") for row in group)
    if len(source_counts) > 1:
        return "same_candidate_across_engines"
    return "same_candidate_same_engine"


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0

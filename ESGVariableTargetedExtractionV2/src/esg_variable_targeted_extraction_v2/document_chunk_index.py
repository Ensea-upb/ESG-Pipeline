"""
document_chunk_index.py — Build document_chunks_v2 from DocumentV2Input.
Chunks preserve full lineage: document_id, company, fiscal_year, page_number.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from .input_adapter import DocumentV2Input
from .io_utils import write_csv, write_jsonl

_NUMERIC_PAT = re.compile(r"\b\d+(?:[.,]\d+)*\s*%?\b")
_UNIT_CANDIDATES = re.compile(
    r"\b(tCO2e?|ktCO2e?|MtCO2e?|kWh|MWh|GWh|TWh|GJ|TJ|PJ|m3|Mm3|km3|ML|"
    r"hectares?|ha|km2|tonnes?|kt|employees?|FTE|people|percent|EUR|USD|M€|B€|"
    r"MEUR|BEUR|million|billion|sites?|years?|hours?|days?)\b",
    re.IGNORECASE,
)

_STRUCTURAL_NOISE = re.compile(
    r"\bISO\s*\d{4,5}\b"          # ISO 14001, ISO 50001
    r"|\b\d{1,2}\.\d{1,2}\b"      # section numbers like 2.1
    r"|\bpage\s+\d+\b"            # page 12
    r"|\bfootnote\s*\d\b"         # footnote 1
    r"|\b^\d{1,2}$",              # bare footnote markers
    re.IGNORECASE | re.MULTILINE,
)

_CHUNK_COLUMNS = [
    "chunk_id", "document_id", "company", "company_name", "company_slug",
    "fiscal_year", "official_doc_type", "final_path", "page_number",
    "section_id", "evidence_id", "table_id", "figure_id", "crop_id",
    "source_type", "text", "text_length", "has_numeric_value",
    "has_unit_candidate", "numeric_values_detected", "units_detected",
    "structural_noise_flags",
]


def _make_chunk_id(document_id: str, source_type: str, source_id: str) -> str:
    raw = f"{document_id}|{source_type}|{source_id}"
    return "chunk_" + hashlib.md5(raw.encode()).hexdigest()[:20]


def _detect_numerics(text: str) -> list[str]:
    return _NUMERIC_PAT.findall(text)


def _detect_units(text: str) -> list[str]:
    return list({m.group() for m in _UNIT_CANDIDATES.finditer(text)})


def _detect_structural_noise(text: str) -> list[str]:
    return [m.group() for m in _STRUCTURAL_NOISE.finditer(text)]


def _base_fields(doc: DocumentV2Input) -> dict[str, Any]:
    return {
        "document_id": doc.document_id,
        "company": doc.company,
        "company_name": doc.company_name,
        "company_slug": doc.company_slug,
        "fiscal_year": doc.fiscal_year,
        "official_doc_type": doc.official_doc_type,
        "final_path": doc.final_path,
    }


def _enrich_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    text = chunk.get("text", "")
    nums = _detect_numerics(text)
    units = _detect_units(text)
    noise = _detect_structural_noise(text)
    chunk["text_length"] = len(text)
    chunk["has_numeric_value"] = bool(nums)
    chunk["has_unit_candidate"] = bool(units)
    chunk["numeric_values_detected"] = ",".join(nums[:10])
    chunk["units_detected"] = ",".join(units[:8])
    chunk["structural_noise_flags"] = ",".join(noise[:5])
    return chunk


def build_text_block_chunks(doc: DocumentV2Input) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    base = _base_fields(doc)
    for block in doc.text_blocks:
        text = block.get("text", "").strip()
        if not text:
            continue
        block_id = block.get("text_block_id", "")
        page_number = block.get("page_number", "")
        section_id = block.get("section_id", "")
        block_type = block.get("block_type", "paragraph")

        if block.get("is_header") or block.get("is_footer"):
            source_type = "page_context"
        elif block.get("is_footnote"):
            source_type = "page_context"
        elif block_type == "table_caption":
            source_type = "figure_caption"
        else:
            source_type = "paragraph"

        chunk: dict[str, Any] = {
            **base,
            "chunk_id": _make_chunk_id(doc.document_id, source_type, block_id),
            "page_number": str(page_number),
            "section_id": str(section_id),
            "evidence_id": "",
            "table_id": "",
            "figure_id": "",
            "crop_id": "",
            "source_type": source_type,
            "text": text,
        }
        chunks.append(_enrich_chunk(chunk))
    return chunks


def build_section_chunks(doc: DocumentV2Input) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    base = _base_fields(doc)
    for sec in doc.section_index:
        title = sec.get("section_title", "").strip()
        if not title:
            continue
        sec_id = sec.get("section_id", "")
        page_start = sec.get("page_start", "")
        sec_type = sec.get("section_type", "unknown")
        text = f"[SECTION: {sec_type}] {title}"
        chunk: dict[str, Any] = {
            **base,
            "chunk_id": _make_chunk_id(doc.document_id, "section", sec_id),
            "page_number": str(page_start),
            "section_id": str(sec_id),
            "evidence_id": "",
            "table_id": "",
            "figure_id": "",
            "crop_id": "",
            "source_type": "section",
            "text": text,
        }
        chunks.append(_enrich_chunk(chunk))
    return chunks


def build_evidence_chunks(doc: DocumentV2Input) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    base = _base_fields(doc)
    for ev in doc.evidence_store:
        quote = ev.get("quote", "").strip()
        if not quote:
            continue
        ev_id = ev.get("evidence_id", "")
        page_number = ev.get("page_number", "")
        section_id = ev.get("section_id", "")
        ev_type = ev.get("evidence_type", "text")
        source_type = "paragraph" if "text" in ev_type else "page_context"
        chunk: dict[str, Any] = {
            **base,
            "chunk_id": _make_chunk_id(doc.document_id, "evidence", ev_id),
            "page_number": str(page_number),
            "section_id": str(section_id),
            "evidence_id": str(ev_id),
            "table_id": "",
            "figure_id": "",
            "crop_id": "",
            "source_type": source_type,
            "text": quote,
        }
        chunks.append(_enrich_chunk(chunk))
    return chunks


def _col_dominant_unit(col_texts: list[str]) -> str:
    """Return the most common unit found across all cells in a column."""
    counts: dict[str, int] = {}
    for t in col_texts:
        for m in _UNIT_CANDIDATES.finditer(t):
            u = m.group().lower()
            counts[u] = counts.get(u, 0) + 1
    if not counts:
        return ""
    return max(counts, key=counts.__getitem__)


def build_table_cell_chunks(doc: DocumentV2Input, max_cells_per_table: int = 200) -> list[dict[str, Any]]:
    """Build context-aware table row chunks: cell_value + row_header + col_header + column unit."""
    chunks: list[dict[str, Any]] = []
    base = _base_fields(doc)

    # Group cells by table_id
    tables: dict[str, list[dict[str, Any]]] = {}
    for cell in doc.table_cells:
        tid = cell.get("table_id", "")
        if tid:
            tables.setdefault(tid, []).append(cell)

    # Build table_id -> page_number from table_index
    table_pages: dict[str, str] = {
        t.get("table_id", ""): str(t.get("page_number", ""))
        for t in doc.table_index
    }

    for table_id, cells in tables.items():
        page_number = table_pages.get(table_id, "")
        if len(cells) > max_cells_per_table:
            cells = cells[:max_cells_per_table]

        # Identify header cells (row_index == 0 or is_header_cell)
        headers_by_col: dict[int, str] = {}
        row_headers: dict[int, str] = {}
        for cell in cells:
            if cell.get("is_header_cell") or cell.get("row_index", 99) == 0:
                col_idx = int(cell.get("column_index", 0))
                headers_by_col[col_idx] = cell.get("text", "").strip()
            if int(cell.get("column_index", 0)) == 0 and not cell.get("is_header_cell"):
                row_idx = int(cell.get("row_index", 0))
                row_headers[row_idx] = cell.get("text", "").strip()

        # Build per-column text lists for unit detection
        col_texts_all: dict[int, list[str]] = {}
        for cell in cells:
            col_idx = int(cell.get("column_index", 0))
            col_texts_all.setdefault(col_idx, []).append(cell.get("text", ""))

        # Per-column dominant unit (covers tables where unit is in a data cell, not header)
        col_unit: dict[int, str] = {
            col_idx: _col_dominant_unit(texts)
            for col_idx, texts in col_texts_all.items()
        }

        # Build one chunk per data cell (non-header with text)
        for cell in cells:
            if cell.get("is_header_cell"):
                continue
            cell_text = cell.get("text", "").strip()
            if not cell_text:
                continue
            row_idx = int(cell.get("row_index", 0))
            col_idx = int(cell.get("column_index", 0))
            col_header = headers_by_col.get(col_idx, "")
            row_header = row_headers.get(row_idx, "")
            cell_id = cell.get("cell_id", f"{table_id}_r{row_idx}_c{col_idx}")

            context_parts = []
            if row_header and row_header != cell_text:
                context_parts.append(f"row: {row_header[:60]}")
            if col_header and col_header != cell_text:
                context_parts.append(f"col: {col_header[:40]}")

            # Inject column-level unit when the cell itself has no unit
            detected_in_cell = _detect_units(cell_text)
            dominant = col_unit.get(col_idx, "")
            if dominant and not detected_in_cell and dominant not in cell_text.lower():
                context_parts.append(f"unit: {dominant}")

            context = " | ".join(context_parts)
            text = f"{cell_text} [{context}]" if context else cell_text

            chunk: dict[str, Any] = {
                **base,
                "chunk_id": _make_chunk_id(doc.document_id, "table_cell_context", cell_id),
                "page_number": str(page_number),
                "section_id": "",
                "evidence_id": "",
                "table_id": str(table_id),
                "figure_id": "",
                "crop_id": "",
                "source_type": "table_cell_context",
                "text": text,
            }
            chunks.append(_enrich_chunk(chunk))

    return chunks


def build_figure_caption_chunks(doc: DocumentV2Input) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    base = _base_fields(doc)
    for fig in doc.figure_index:
        caption = fig.get("caption", fig.get("figure_caption", "")).strip()
        if not caption:
            continue
        fig_id = fig.get("figure_id", "")
        page_number = fig.get("page_number", "")
        chunk: dict[str, Any] = {
            **base,
            "chunk_id": _make_chunk_id(doc.document_id, "figure_caption", fig_id),
            "page_number": str(page_number),
            "section_id": "",
            "evidence_id": "",
            "table_id": "",
            "figure_id": str(fig_id),
            "crop_id": "",
            "source_type": "figure_caption",
            "text": caption,
        }
        chunks.append(_enrich_chunk(chunk))
    return chunks


def build_all_chunks(doc: DocumentV2Input) -> list[dict[str, Any]]:
    """Build complete chunk index from all sources."""
    all_chunks: list[dict[str, Any]] = []
    all_chunks.extend(build_text_block_chunks(doc))
    all_chunks.extend(build_section_chunks(doc))
    all_chunks.extend(build_table_cell_chunks(doc))
    all_chunks.extend(build_figure_caption_chunks(doc))
    # Evidence chunks add additional coverage (evidence often has better quotes)
    all_chunks.extend(build_evidence_chunks(doc))
    # Deduplicate by chunk_id
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for c in all_chunks:
        cid = c["chunk_id"]
        if cid not in seen:
            seen.add(cid)
            unique.append(c)
    return unique


def write_chunk_index(
    chunks: list[dict[str, Any]],
    output_dir,
) -> None:
    from pathlib import Path
    output_dir = Path(output_dir)
    write_csv(output_dir / "document_chunks_v2.csv", chunks, _CHUNK_COLUMNS)
    write_jsonl(output_dir / "document_chunks_v2.jsonl", chunks)

"""
input_adapter.py — Reads ESGInformationExtraction outputs into DocumentV2Input.
Read-only. Never modifies source directories.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .io_utils import read_json, read_jsonl


@dataclass
class DocumentV2Input:
    # Core metadata (mandatory)
    document_id: str = ""
    company: str = ""
    company_name: str = ""
    company_slug: str = ""
    fiscal_year: str = ""
    official_doc_type: str = ""
    final_path: str = ""
    corpus_run_id: str = ""

    # Document stats
    page_count: int = 0
    loading_status: str = ""

    # Loaded data
    text_blocks: list[dict[str, Any]] = field(default_factory=list)
    section_index: list[dict[str, Any]] = field(default_factory=list)
    evidence_store: list[dict[str, Any]] = field(default_factory=list)
    table_cells: list[dict[str, Any]] = field(default_factory=list)
    table_index: list[dict[str, Any]] = field(default_factory=list)
    figure_index: list[dict[str, Any]] = field(default_factory=list)
    page_index: list[dict[str, Any]] = field(default_factory=list)
    multimodal_evidence: list[dict[str, Any]] = field(default_factory=list)

    # Warnings collected during loading
    load_warnings: list[str] = field(default_factory=list)

    @property
    def has_valid_metadata(self) -> bool:
        return bool(self.document_id and self.company and self.fiscal_year)

    @property
    def text_block_count(self) -> int:
        return len(self.text_blocks)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence_store)

    @property
    def table_cell_count(self) -> int:
        return len(self.table_cells)


def load_document_input(input_dir: str | Path) -> DocumentV2Input:
    """
    Read all ESGInformationExtraction outputs from input_dir.
    Returns a DocumentV2Input. Never raises — warnings are collected.
    """
    input_dir = Path(input_dir)
    result = DocumentV2Input()

    if not input_dir.exists():
        result.load_warnings.append(f"input_dir does not exist: {input_dir}")
        return result

    # 1. Load document_record.json (primary metadata)
    doc_record = read_json(input_dir / "document_record.json")
    if not doc_record:
        doc_record = read_json(input_dir / "document_inventory.json")

    if doc_record:
        result.document_id = doc_record.get("document_id", "")
        slug = doc_record.get("company_slug", "")
        result.company = doc_record.get("company", "") or slug
        result.company_name = doc_record.get("company_name", "") or result.company
        result.company_slug = slug or result.company
        result.fiscal_year = str(doc_record.get("fiscal_year", ""))
        result.official_doc_type = doc_record.get("official_doc_type", "")
        result.final_path = doc_record.get("final_path", doc_record.get("document_path", doc_record.get("pdf_path", "")))
        result.corpus_run_id = doc_record.get("corpus_run_id", "")
        result.page_count = int(doc_record.get("page_count", 0))
        result.loading_status = doc_record.get("loading_status", "")
    else:
        result.load_warnings.append("metadata_missing: document_record.json and document_inventory.json not found")

    # 2. Also load document_inventory for additional stats if needed
    if not doc_record:
        pass  # already warned above
    elif not result.company and not result.fiscal_year:
        result.load_warnings.append("metadata_missing: company and fiscal_year absent from document record")

    # Validate mandatory fields
    if not result.document_id:
        result.load_warnings.append("metadata_missing: document_id is empty")
    if not result.company:
        result.load_warnings.append("metadata_missing: company is empty — do not invent value")
    if not result.fiscal_year:
        result.load_warnings.append("metadata_missing: fiscal_year is empty — do not invent value")

    # 3. Load text blocks
    result.text_blocks = read_jsonl(input_dir / "text_blocks.jsonl")

    # 4. Load section index
    result.section_index = read_jsonl(input_dir / "section_index.jsonl")

    # 5. Load evidence store
    result.evidence_store = read_jsonl(input_dir / "evidence_store.jsonl")

    # 6. Load table cells and table index
    result.table_cells = read_jsonl(input_dir / "table_cells.jsonl")
    result.table_index = read_jsonl(input_dir / "table_index.jsonl")

    # 7. Load figure index
    result.figure_index = read_jsonl(input_dir / "figure_index.jsonl")

    # 8. Load page index
    result.page_index = read_jsonl(input_dir / "page_index.jsonl")

    # 9. Load multimodal evidence index
    result.multimodal_evidence = read_jsonl(input_dir / "multimodal_evidence_index.jsonl")

    return result

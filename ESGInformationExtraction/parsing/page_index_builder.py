"""
page_index_builder.py
=====================
Transforme les pages brutes (issues de pdf_text_parser) en PageRecord.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from ..schemas.document_record import DocumentRecord
from ..schemas.page_record import PageRecord


def build_page_records(
    document: DocumentRecord,
    raw_pages: list[dict],
    parser_name: str = "pdfplumber",
    parser_version: str = "unknown",
) -> list[PageRecord]:
    """
    Convertit une liste de pages brutes en PageRecord.

    raw_pages : sortie de pdf_text_parser.parse_pdf_pages()
    Ne modifie pas le document source.
    """
    records = []
    for page in raw_pages:
        page_number = page["page_number"]
        text = page.get("text", "")
        char_count = page.get("char_count", len(text))
        has_tables = page.get("has_tables", False)

        status = "ok"
        if char_count < 50:
            status = "empty"

        records.append(PageRecord(
            page_id=str(uuid.uuid4()),
            document_id=document.document_id,
            company_slug=document.company_slug,
            fiscal_year=document.fiscal_year,
            official_doc_type=document.official_doc_type,
            page_number=page_number,
            text=text,
            char_count=char_count,
            extraction_status=status,
            has_tables=has_tables,
            parser_name=parser_name,
            parser_version=parser_version,
        ))
    return records


def write_page_index(
    records: list[PageRecord],
    output_dir: Path,
    filename: str = "page_index.jsonl",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    with output_path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")
    return output_path

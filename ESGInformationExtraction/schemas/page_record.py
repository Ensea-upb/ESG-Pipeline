from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class PageRecord(BaseModel):
    """PDF page schema aligned with current page_index.jsonl and legacy drafts."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0.0"
    page_id: str
    document_id: str
    page_number: int
    company_slug: Optional[str] = None
    fiscal_year: Optional[int] = None
    official_doc_type: Optional[str] = None
    text: str = ""
    char_count: int = 0
    width: Optional[float] = None
    height: Optional[float] = None
    rotation: Optional[int] = None
    text_char_count: Optional[int] = None
    has_text: Optional[bool] = None
    language: Optional[str] = None
    extraction_status: Literal["ok", "empty", "error", "skipped"] = "ok"
    has_tables: bool = False
    has_images: bool = False
    parser_name: str = "pdfplumber"
    parser_version: str = "unknown"

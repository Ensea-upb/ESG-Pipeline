from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentRecord(BaseModel):
    """Document metadata schema aligned with current and legacy outputs."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0.0"
    document_id: str
    canonical_document_id: Optional[str] = None
    sha256: str
    document_path: str
    file_name: Optional[str] = None
    page_count: Optional[int] = None
    loading_status: Optional[str] = None
    company_name: Optional[str] = None
    company_slug: Optional[str] = None
    fiscal_year: Optional[int] = None
    official_doc_type: Optional[str] = None
    official_doc_type_label: Optional[str] = None
    manifest_path: Optional[str] = None
    references_path: Optional[str] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    selection_status: Literal["selected", "candidate", "unknown"] = "unknown"
    validation_status: Literal["validated", "pending", "rejected", "unknown"] = "unknown"
    extraction_ready: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

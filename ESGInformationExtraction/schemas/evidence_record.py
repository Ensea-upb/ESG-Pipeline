from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class EvidenceRecord(BaseModel):
    """
    Evidence documentaire produite par le moteur PDF actif.

    v1.5 hygiene note:
    The production source of truth is run_pdf_extraction.py and the real
    `evidence_store.jsonl` output. Legacy corpus fields from early drafts are
    optional and are not required by current outputs.
    """

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0.0"
    evidence_id: str
    document_id: str
    page_id: Optional[str] = None
    page_number: int
    evidence_type: str = "unknown"
    quote: str
    bbox: Optional[Dict[str, Any]] = None
    section_id: Optional[str] = None
    text_block_id: Optional[str] = None
    table_id: Optional[str] = None
    figure_id: Optional[str] = None
    source_element_type: Optional[str] = None
    source_element_id: Optional[str] = None
    source_text_block_ids: List[str] = []
    merged_blocks_count: int = 1
    was_merged_evidence: bool = False
    merge_method: Optional[str] = None
    evidence_confidence: float = 0.0
    localization_confidence: float = 0.0
    extraction_method: str = "keyword_regex"
    review_required: bool = True
    section_quality_score: Optional[float] = None
    section_is_suspicious: Optional[bool] = None
    section_suspicion_reasons: List[str] = []
    evidence_policy: Optional[str] = None
    is_quarantined_evidence: bool = False
    review_required_due_to_section: Optional[bool] = None

    # Optional legacy fields kept for backward compatibility with early drafts.
    company_slug: Optional[str] = None
    fiscal_year: Optional[int] = None
    official_doc_type: Optional[str] = None
    source_url: Optional[str] = None
    confidence: float = 0.0

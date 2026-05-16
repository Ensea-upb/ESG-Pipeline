from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


SECTION_TYPES = Literal[
    "climate", "emissions", "energy", "water", "waste", "biodiversity",
    "workforce", "health_safety", "diversity", "human_rights", "vigilance",
    "governance", "remuneration", "ethics", "anti_corruption",
    "risk_management", "assurance", "other", "unknown",
]


class SectionRecord(BaseModel):
    """Section schema aligned with current section_index.jsonl and legacy drafts."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0.0"
    section_id: str
    document_id: str
    section_title: str
    section_type: str = "unknown"
    page_start: int
    page_end: Optional[int] = None
    company_slug: Optional[str] = None
    fiscal_year: Optional[int] = None
    official_doc_type: Optional[str] = None
    confidence: float = 0.0
    detection_method: str = "rule_based"
    parent_section_id: Optional[str] = None
    section_quality_score: Optional[float] = None
    is_suspicious_section: Optional[bool] = None
    suspicion_reasons: list[str] = []
    evidence_policy: Optional[str] = None

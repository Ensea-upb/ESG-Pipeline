from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class MetricRecord(BaseModel):
    """
    Représente un indicateur ESG extrait (candidat).
    Produit par extraction/metric_candidate_extractor.py.
    Ne constitue pas un indicateur validé tant que review_required=True.
    """

    schema_version: str = "1.0.0"
    metric_id: str
    company_slug: str
    fiscal_year: int
    metric_name: str
    metric_category: Literal["environment", "social", "governance", "other"] = "other"
    value_raw: Optional[str] = None
    value_normalized: Optional[float] = None
    unit_raw: Optional[str] = None
    unit_normalized: Optional[str] = None
    period: Optional[str] = None
    scope: Optional[str] = None
    source_document_id: str
    evidence_id: Optional[str] = None
    confidence: float = 0.0
    extraction_method: str = "keyword_regex"
    review_required: bool = True

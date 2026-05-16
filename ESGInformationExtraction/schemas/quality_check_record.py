from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class QualityCheckRecord(BaseModel):
    """Quality check schema aligned with current quality_report.jsonl."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0.0"
    quality_check_id: str
    target_type: str
    target_id: str
    check_name: str
    status: str = "skipped"
    severity: str = "info"
    message: str = ""
    review_required: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

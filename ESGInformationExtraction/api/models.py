"""Pydantic models for the ESG extraction API."""
from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class ExtractionRequest(BaseModel):
    pdf_path: str = Field(..., description="Absolute path to the PDF file on the server")
    document_id: str = Field(..., description="Unique document identifier (used as output folder name)")
    output_dir: str = Field(..., description="Directory where extraction outputs will be written")
    company: Optional[str] = None
    company_slug: Optional[str] = None
    fiscal_year: Optional[int] = None
    official_doc_type: Optional[str] = None
    document_family: Optional[str] = None
    max_pages: Optional[int] = None
    overwrite: bool = False


class JobStatus(BaseModel):
    job_id: str
    document_id: str
    status: Literal["queued", "running", "success", "failed", "timeout"]
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    elapsed_s: Optional[float] = None
    pages_processed: Optional[int] = None
    text_blocks_count: Optional[int] = None
    errors_count: Optional[int] = None
    output_dir: Optional[str] = None
    error_message: Optional[str] = None


class RecallReport(BaseModel):
    ground_truth_count: int
    total_candidates: int
    recall_metric_level: float
    recall_value_level: float
    recall_current_year_level: float
    precision_proxy_carry_value: Optional[float] = None
    precision_proxy_noise_ratio: Optional[float] = None
    found_metric_ids: list[str] = []
    missed_metric_ids: list[str] = []


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    pipeline: str = "ESGInformationExtraction"

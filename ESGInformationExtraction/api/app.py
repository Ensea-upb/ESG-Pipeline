"""
ESG Extraction API — FastAPI application.

Endpoints:
  GET  /health                        — health check
  POST /api/v1/extract                — submit a document for extraction
  GET  /api/v1/jobs                   — list all jobs
  GET  /api/v1/jobs/{job_id}          — get job status
  GET  /api/v1/recall/{output_dir:path} — get recall/precision report

Run with:
  pip install fastapi uvicorn
  uvicorn ESGInformationExtraction.api.app:app --host 0.0.0.0 --port 8080

Or directly:
  python -m ESGInformationExtraction.api.app
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ESGInformationExtraction.api.models import (
    ExtractionRequest, JobStatus, RecallReport, HealthResponse,
)
from ESGInformationExtraction.api.runner import submit_job, get_job, list_jobs

app = FastAPI(
    title="ESG Extraction API",
    description="Trigger ESG metric extraction and monitor job status.",
    version="1.0.0",
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/api/v1/extract", tags=["Extraction"])
def submit_extraction(req: ExtractionRequest) -> dict:
    """Submit a PDF for ESG metric extraction.

    The job runs asynchronously. Poll /api/v1/jobs/{job_id} for status.
    """
    pdf = Path(req.pdf_path)
    if not pdf.exists():
        raise HTTPException(status_code=400, detail=f"PDF not found: {req.pdf_path}")
    if not req.document_id.strip():
        raise HTTPException(status_code=400, detail="document_id must not be empty")

    job_id = submit_job(req)
    return {"job_id": job_id, "status": "queued", "document_id": req.document_id}


@app.get("/api/v1/jobs", tags=["Extraction"])
def list_all_jobs() -> list[dict]:
    """List all submitted jobs (most recent first)."""
    return list_jobs()


@app.get("/api/v1/jobs/{job_id}", tags=["Extraction"])
def get_job_status(job_id: str) -> dict:
    """Get the status and result of a job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@app.get("/api/v1/recall/{output_dir:path}", tags=["Analytics"])
def get_recall_report(output_dir: str) -> dict:
    """Return the recall/precision report for a completed extraction run.

    output_dir: absolute path to the extraction output directory.
    The recall_report.json must exist (run compute_recall.py first).
    """
    report_path = Path(output_dir) / "recall_report.json"
    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"recall_report.json not found in {output_dir}. "
                   f"Run: python recall_eval/compute_recall.py {output_dir}",
        )
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report: {e}") from e


@app.get("/api/v1/stats/{output_dir:path}", tags=["Analytics"])
def get_extraction_stats(output_dir: str) -> dict:
    """Return the metric statistics from a completed extraction run."""
    stats_path = Path(output_dir) / "metric_statistics.json"
    if not stats_path.exists():
        raise HTTPException(status_code=404, detail=f"metric_statistics.json not found in {output_dir}")
    try:
        return json.loads(stats_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ESGInformationExtraction.api.app:app", host="0.0.0.0", port=8080, reload=True)

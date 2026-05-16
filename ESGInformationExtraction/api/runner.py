"""Job manager for async extraction runs."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ExtractionRequest, JobStatus

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_EXTRACTION_SCRIPT = _PROJECT_ROOT / "ESGInformationExtraction" / "run_pdf_extraction.py"

# In-memory job store (replace with Redis/DB for production)
_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _build_cli(req: ExtractionRequest) -> list[str]:
    cli = [
        sys.executable, "-X", "utf8",
        str(_EXTRACTION_SCRIPT),
        "--pdf-path",    req.pdf_path,
        "--document-id", req.document_id,
        "--output-dir",  req.output_dir,
    ]
    if req.company:
        cli.extend(["--company", req.company])
    if req.company_slug:
        cli.extend(["--company-slug", req.company_slug])
    if req.fiscal_year:
        cli.extend(["--fiscal-year", str(req.fiscal_year)])
    if req.official_doc_type:
        cli.extend(["--official-doc-type", req.official_doc_type])
    if req.document_family:
        cli.extend(["--document-family", req.document_family])
    if req.max_pages:
        cli.extend(["--max-pages", str(req.max_pages)])
    if req.overwrite:
        cli.append("--overwrite")
    return cli


def _run_job(job_id: str, req: ExtractionRequest) -> None:
    with _lock:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["started_at"] = datetime.now(tz=timezone.utc).isoformat()

    t0 = time.monotonic()
    cli = _build_cli(req)
    try:
        result = subprocess.run(
            cli,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=7200,
        )
        elapsed = time.monotonic() - t0

        if result.returncode == 0:
            try:
                last_line = result.stdout.strip().splitlines()[-1]
                out_json = json.loads(last_line)
            except Exception:
                out_json = {}

            with _lock:
                _jobs[job_id].update({
                    "status": "success",
                    "elapsed_s": round(elapsed, 1),
                    "pages_processed": out_json.get("pages_processed"),
                    "text_blocks_count": out_json.get("text_blocks_count"),
                    "errors_count": out_json.get("errors_count"),
                    "output_dir": req.output_dir,
                    "completed_at": datetime.now(tz=timezone.utc).isoformat(),
                })
        else:
            with _lock:
                _jobs[job_id].update({
                    "status": "failed",
                    "elapsed_s": round(elapsed, 1),
                    "error_message": result.stderr[-2000:] if result.stderr else result.stdout[-1000:],
                    "completed_at": datetime.now(tz=timezone.utc).isoformat(),
                })
    except subprocess.TimeoutExpired:
        with _lock:
            _jobs[job_id].update({
                "status": "timeout",
                "elapsed_s": 7200,
                "error_message": "Job timed out after 2 hours.",
                "completed_at": datetime.now(tz=timezone.utc).isoformat(),
            })
    except Exception as e:
        with _lock:
            _jobs[job_id].update({
                "status": "failed",
                "elapsed_s": time.monotonic() - t0,
                "error_message": str(e),
                "completed_at": datetime.now(tz=timezone.utc).isoformat(),
            })


def submit_job(req: ExtractionRequest) -> str:
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "job_id":       job_id,
            "document_id":  req.document_id,
            "status":       "queued",
            "submitted_at": datetime.now(tz=timezone.utc).isoformat(),
        }
    thread = threading.Thread(target=_run_job, args=(job_id, req), daemon=True)
    thread.start()
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        return _jobs.get(job_id)


def list_jobs() -> list[dict[str, Any]]:
    with _lock:
        return sorted(_jobs.values(), key=lambda j: j.get("submitted_at", ""), reverse=True)

"""
test_api_v17.py
===============
Unit tests for the ESG Extraction FastAPI layer.
Uses httpx TestClient — no network or real extraction needed.
"""
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from fastapi.testclient import TestClient
    from ESGInformationExtraction.api.app import app
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not _HAS_FASTAPI, reason="fastapi not installed")


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_health_has_version(self, client):
        r = client.get("/health")
        assert "version" in r.json()


class TestExtractEndpoint:
    def test_missing_pdf_returns_400(self, client):
        payload = {
            "pdf_path": "/nonexistent/path/document.pdf",
            "document_id": "test_doc",
            "output_dir": "/tmp/test_output",
        }
        r = client.post("/api/v1/extract", json=payload)
        assert r.status_code == 400
        assert "not found" in r.json()["detail"].lower()

    def test_empty_document_id_returns_400(self, client, tmp_path):
        pdf = tmp_path / "fake.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        payload = {
            "pdf_path": str(pdf),
            "document_id": "   ",  # whitespace only
            "output_dir": str(tmp_path),
        }
        r = client.post("/api/v1/extract", json=payload)
        assert r.status_code == 400

    def test_valid_submission_returns_job_id(self, client, tmp_path):
        pdf = tmp_path / "fake.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        payload = {
            "pdf_path": str(pdf),
            "document_id": "test_doc_api",
            "output_dir": str(tmp_path),
        }
        r = client.post("/api/v1/extract", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["document_id"] == "test_doc_api"


class TestJobsEndpoint:
    def test_list_jobs_returns_list(self, client):
        r = client.get("/api/v1/jobs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_unknown_job_id_returns_404(self, client):
        r = client.get("/api/v1/jobs/nonexistent-uuid")
        assert r.status_code == 404

    def test_submitted_job_appears_in_list(self, client, tmp_path):
        pdf = tmp_path / "fake2.pdf"
        pdf.write_bytes(b"%PDF fake")
        r = client.post("/api/v1/extract", json={
            "pdf_path": str(pdf),
            "document_id": "test_list_doc",
            "output_dir": str(tmp_path),
        })
        assert r.status_code == 200
        job_id = r.json()["job_id"]

        r2 = client.get(f"/api/v1/jobs/{job_id}")
        assert r2.status_code == 200
        assert r2.json()["job_id"] == job_id
        assert r2.json()["status"] in ("queued", "running", "success", "failed")


class TestRecallEndpoint:
    def test_missing_recall_report_returns_404(self, client, tmp_path):
        r = client.get(f"/api/v1/recall/{tmp_path}")
        assert r.status_code == 404

    def test_valid_recall_report_returned(self, client, tmp_path):
        report = {
            "recall_metric_level": 1.0,
            "recall_value_level": 1.0,
            "recall_current_year_level": 1.0,
            "ground_truth_count": 20,
            "total_candidates": 5852,
            "found_metric_ids": [],
            "missed_metric_ids": [],
        }
        (tmp_path / "recall_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
        r = client.get(f"/api/v1/recall/{tmp_path}")
        assert r.status_code == 200
        data = r.json()
        assert data["recall_metric_level"] == 1.0
        assert data["ground_truth_count"] == 20

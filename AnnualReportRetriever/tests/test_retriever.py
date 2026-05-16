from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from annual_report_retriever.downloader import PDFDownloader
from annual_report_retriever.models import Company, ScoredCandidate, SearchCandidate
from annual_report_retriever.retriever import AnnualReportRetriever
from annual_report_retriever.storage import AnnualReportStorage


def test_retriever_deduplicates_scored_candidates_by_url() -> None:
    candidates = [
        ScoredCandidate(title="A", url="https://example.com/report.pdf", score=90),
        ScoredCandidate(title="B", url="https://example.com/report.pdf", score=80),
        ScoredCandidate(title="C", url="https://example.com/other.pdf", score=70),
    ]

    unique = AnnualReportRetriever._deduplicate_scored_candidates(candidates)

    assert [candidate.title for candidate in unique] == ["A", "C"]


def test_retriever_returns_no_candidate_without_network() -> None:
    result = AnnualReportRetriever().download_annual_report_from_candidates(
        company=Company(name="No Result SA"),
        fiscal_year=2024,
        candidates=[],
    )

    assert result.status == "no_candidate"


def test_downloader_rejects_non_pdf_response(monkeypatch, tmp_path: Path) -> None:
    class FakeResponse:
        status_code = 200
        content = b"<html>not a pdf</html>"
        headers = {"Content-Type": "text/html"}

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("annual_report_retriever.downloader.requests.Session", lambda: FakeSession())

    response = PDFDownloader(max_retries=0).download_pdf(
        "https://example.com/report.pdf",
        tmp_path / "report.pdf",
    )

    assert response.status == "not_a_pdf"
    assert response.output_path is None
    assert not (tmp_path / "report.pdf").exists()


def test_storage_writes_manifest_and_registry(tmp_path: Path) -> None:
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF- fake")
    candidate = ScoredCandidate(
        title="LVMH Annual Report 2024",
        url="https://www.lvmh.com/report.pdf",
        score=92,
        decision="auto_download",
    )

    manifest = AnnualReportStorage(root_dir=tmp_path / "ingestion").store_annual_report(
        temp_pdf_path=pdf,
        company=Company(name="LVMH"),
        fiscal_year=2024,
        candidate=candidate,
    )

    assert Path(manifest["file"]["local_path"]).exists()
    assert Path(manifest["file"]["manifest_path"]).exists()
    assert (tmp_path / "ingestion" / "registry" / "annual_reports_registry.jsonl").exists()

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from annual_report_retriever.models import AnnualReportRequest, Company, SearchCandidate
from annual_report_retriever.scorer import AnnualReportScorer


def test_scorer_auto_downloads_official_annual_report_pdf() -> None:
    request = AnnualReportRequest(
        company=Company(name="LVMH", official_domain="lvmh.com"),
        fiscal_year=2024,
    )
    candidate = SearchCandidate(
        title="LVMH Annual Report 2024",
        url="https://www.lvmh.com/investors/lvmh-annual-report-2024.pdf",
        snippet="LVMH group annual financial report 2024",
    )

    scored = AnnualReportScorer().score_candidate(request, candidate)

    assert scored.decision == "auto_download"
    assert scored.score >= 80
    assert scored.positive_signals


def test_scorer_rejects_wrong_year_press_release() -> None:
    request = AnnualReportRequest(
        company=Company(name="LVMH", official_domain="lvmh.com"),
        fiscal_year=2024,
    )
    candidate = SearchCandidate(
        title="LVMH press release Q1 2023",
        url="https://live.euronext.com/company-press-releases/lvmh-q1-2023",
        snippet="Quarterly press release",
    )

    scored = AnnualReportScorer().score_candidate(request, candidate)

    assert scored.decision == "reject"
    assert scored.score < 60
    assert scored.negative_signals

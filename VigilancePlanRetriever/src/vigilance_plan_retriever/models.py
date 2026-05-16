from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Company:
    name: str
    official_domain: Optional[str] = None
    ticker: Optional[str] = None
    isin: Optional[str] = None
    jurisdiction: Optional[str] = None


@dataclass
class VigilancePlanRequest:
    """
    Demande documentaire pour un plan de vigilance / devoir de vigilance.
    """
    company: Company
    fiscal_year: int


@dataclass
class SearchCandidate:
    title: str
    url: str
    snippet: str = ""
    source_name: str = "unknown"


@dataclass
class ScoredCandidate:
    title: str
    url: str
    snippet: str = ""
    source_name: str = "unknown"
    score: float = 0.0
    decision: str = "not_scored"
    positive_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)


@dataclass
class DownloadResult:
    status: str
    message: str
    company_name: str
    fiscal_year: int
    downloaded_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    downloaded: list[dict] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)

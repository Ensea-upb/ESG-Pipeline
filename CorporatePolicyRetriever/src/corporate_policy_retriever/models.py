from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class PolicyType(str, Enum):
    CODE_OF_CONDUCT = "code_of_conduct"
    ANTICORRUPTION = "anticorruption"
    HUMAN_RIGHTS = "human_rights"
    DEI = "dei"
    ENVIRONMENTAL = "environmental"
    SUPPLIER_CODE = "supplier_code"


@dataclass
class Company:
    name: str
    official_domain: Optional[str] = None
    ticker: Optional[str] = None
    isin: Optional[str] = None
    jurisdiction: Optional[str] = None


@dataclass
class CorporatePolicyRequest:
    """
    Demande documentaire pour une politique corporate (document pérenne).
    reference_year : année de référence pour évaluer la fraîcheur du document.
    policy_type    : type de politique recherchée.
    """
    company: Company
    reference_year: int
    policy_type: PolicyType


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
    reference_year: int
    policy_type: str
    downloaded_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    downloaded: list[dict] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)

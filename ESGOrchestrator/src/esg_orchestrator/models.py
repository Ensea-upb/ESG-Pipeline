from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


TASK_STATUSES = {
    "pending",
    "running",
    "success",
    "failed",
    "skipped_existing",
    "skipped_not_applicable",
    "no_candidate_found",
    "partial_success",
}


@dataclass
class Company:
    name: str
    company_slug: str
    official_domain: Optional[str] = None
    ticker: Optional[str] = None
    isin: Optional[str] = None
    jurisdiction: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Company":
        return cls(
            name=payload["name"],
            company_slug=payload.get("company_slug") or slugify(payload["name"]),
            official_domain=payload.get("official_domain"),
            ticker=payload.get("ticker"),
            isin=payload.get("isin"),
            jurisdiction=payload.get("jurisdiction"),
        )


@dataclass
class DocumentType:
    official_doc_type: str
    label: str
    retriever: Optional[str] = None
    enabled: bool = True
    policy_type: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DocumentType":
        return cls(
            official_doc_type=payload["official_doc_type"],
            label=payload["label"],
            retriever=payload.get("retriever"),
            enabled=bool(payload.get("enabled", True)),
            policy_type=payload.get("policy_type"),
        )


@dataclass
class PipelineTask:
    task_id: str
    company_name: str
    company_slug: str
    fiscal_year: int
    official_doc_type: str
    official_doc_type_label: str
    retriever: Optional[str]
    policy_type: Optional[str] = None
    status: str = "pending"
    command: list[str] = field(default_factory=list)
    message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunConfig:
    profile: str
    run_id: str
    dry_run: bool
    resume: bool
    skip_existing_downloads: bool
    max_workers: int
    years: list[int]
    companies: list[str]


def slugify(value: str) -> str:
    chars = []
    previous_dash = False
    for char in str(value).lower().strip():
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-") or "unknown"

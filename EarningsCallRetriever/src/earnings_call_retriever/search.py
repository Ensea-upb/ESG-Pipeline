from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate

class EarningsCallSearch:
    """Recherche des transcripts et présentations d'earnings calls."""

    def search_candidates(self, company: Company, fiscal_year: int) -> list[SearchCandidate]:
        queries = self._build_queries(company=company, fiscal_year=fiscal_year)
        seen_urls: set[str] = set()
        candidates: list[SearchCandidate] = []
        with DDGS() as ddgs:
            for query in queries:
                try:
                    results = list(ddgs.text(query, max_results=5)) or []
                except Exception:
                    results = []
                for item in results:
                    url = item.get("href", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        candidates.append(SearchCandidate(
                            title=item.get("title", ""),
                            url=url,
                            snippet=item.get("body", ""),
                            source_name="ddgs",
                        ))
        return candidates

    def _build_queries(self, company: Company, fiscal_year: int) -> list[str]:
        name = company.name
        queries = [
            f"{name} {fiscal_year} earnings call transcript",
            f"{name} {fiscal_year} Q4 earnings call transcript",
            f"{name} {fiscal_year} Q1 earnings call transcript",
            f"{name} {fiscal_year} Q2 earnings call transcript",
            f"{name} {fiscal_year} Q3 earnings call transcript",
            f"{name} {fiscal_year} full year earnings call transcript",
            f"{name} {fiscal_year} annual earnings call transcript",
            f"{name} {fiscal_year} results call transcript",
            f"{name} {fiscal_year} conference call transcript",
            f"{name} {fiscal_year} analyst call transcript",
            f"site:seekingalpha.com {name} {fiscal_year} earnings call transcript",
            f"site:fool.com {name} {fiscal_year} earnings call transcript",
        ]
        return queries

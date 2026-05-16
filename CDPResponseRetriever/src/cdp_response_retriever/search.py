from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate

class CDPResponseSearch:
    """Recherche des réponses CDP publiées (Climate Change, Water Security, Forests)."""

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
            f"{name} {fiscal_year} CDP response PDF",
            f"{name} {fiscal_year} CDP climate change response PDF",
            f"{name} {fiscal_year} CDP water security response PDF",
            f"{name} {fiscal_year} CDP forests response PDF",
            f"{name} CDP score {fiscal_year}",
            f"{name} {fiscal_year} carbon disclosure project response PDF",
            f"site:cdp.net {name} {fiscal_year}",
            f"{name} {fiscal_year} CDP questionnaire response",
            f"{name} {fiscal_year} CDP disclosure climate",
            f"{name} {fiscal_year} réponse CDP changement climatique PDF",
        ]
        return queries

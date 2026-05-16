from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate

class SBTiSearch:
    """Recherche des validations SBTi : lettres d'engagement, targets validés, Net-Zero Standard."""

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
            f"{name} SBTi validated targets",
            f"{name} science based targets validated",
            f"{name} SBTi commitment letter PDF",
            f"{name} SBTi net zero standard",
            f"{name} science based targets net zero",
            f"{name} 1.5 degree aligned science based targets",
            f"site:sciencebasedtargets.org {name}",
            f"{name} SBTi target validation {fiscal_year}",
            f"{name} objectifs science based targets PDF",
            f"{name} engagement SBTi PDF",
        ]
        return queries

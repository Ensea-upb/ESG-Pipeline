from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate

class InvestorPresentationSearch:
    """Recherche des présentations investisseurs : CMD, ESG Day, roadshows, slides résultats."""

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
            f"{name} {fiscal_year} capital markets day PDF",
            f"{name} {fiscal_year} investor day presentation PDF",
            f"{name} {fiscal_year} CMD presentation PDF",
            f"{name} {fiscal_year} ESG day presentation PDF",
            f"{name} {fiscal_year} investor presentation PDF",
            f"{name} {fiscal_year} roadshow presentation PDF",
            f"{name} {fiscal_year} results presentation slides PDF",
            f"{name} {fiscal_year} annual results presentation PDF",
            f"{name} {fiscal_year} full year results presentation PDF",
            f"{name} {fiscal_year} investor relations presentation PDF",
            f"{name} {fiscal_year} journée investisseurs PDF",
            f"{name} {fiscal_year} présentation investisseurs PDF",
        ]
        if company.official_domain:
            domain = (
                company.official_domain
                .replace("https://", "").replace("http://", "").strip("/")
            )
            queries.extend([
                f'site:{domain} "{name}" {fiscal_year} "investor" "presentation" filetype:pdf',
                f'site:{domain} "{name}" {fiscal_year} "capital markets day" filetype:pdf',
            ])
        return queries

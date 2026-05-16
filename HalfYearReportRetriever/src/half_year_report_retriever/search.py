from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate

class HalfYearReportSearch:
    """
    Recherche multi-requêtes des rapports financiers semestriels (H1).
    Cible : rapport semestriel, half year report, interim report, résultats H1.
    """

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
            f"{name} {fiscal_year} half year report PDF",
            f"{name} {fiscal_year} semi-annual report PDF",
            f"{name} {fiscal_year} interim report PDF",
            f"{name} {fiscal_year} H1 results PDF",
            f"{name} {fiscal_year} first half results PDF",
            f"{name} {fiscal_year} rapport semestriel PDF",
            f"{name} {fiscal_year} résultats H1 PDF",
            f"{name} {fiscal_year} résultats premier semestre PDF",
            f"{name} {fiscal_year} rapport financier semestriel PDF",
            f"{name} {fiscal_year} half year financial report PDF",
            f"{name} {fiscal_year} six months results PDF",
            f"{name} {fiscal_year} six months report PDF",
        ]
        if company.official_domain:
            domain = (
                company.official_domain
                .replace("https://", "").replace("http://", "").strip("/")
            )
            queries.extend([
                f'site:{domain} "{name}" {fiscal_year} "half year" filetype:pdf',
                f'site:{domain} "{name}" {fiscal_year} "rapport semestriel" filetype:pdf',
                f'site:{domain} "{name}" {fiscal_year} "interim report" filetype:pdf',
                f'site:{domain} "{name}" {fiscal_year} "H1" filetype:pdf',
            ])
        return queries

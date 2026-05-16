from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate

class AssuranceReportSearch:
    """Recherche des rapports d'assurance tiers sur les données de durabilité ESG."""

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
            f"{name} {fiscal_year} assurance report ESG PDF",
            f"{name} {fiscal_year} third party assurance sustainability PDF",
            f"{name} {fiscal_year} ISAE 3000 assurance PDF",
            f"{name} {fiscal_year} ISAE 3410 assurance PDF",
            f"{name} {fiscal_year} AA1000 assurance PDF",
            f"{name} {fiscal_year} limited assurance sustainability report PDF",
            f"{name} {fiscal_year} reasonable assurance sustainability PDF",
            f"{name} {fiscal_year} independent assurance statement ESG PDF",
            f"{name} {fiscal_year} rapport assurance extra-financière PDF",
            f"{name} {fiscal_year} commissaire aux comptes durabilité PDF",
            f"{name} {fiscal_year} CSRD assurance PDF",
            f"{name} {fiscal_year} vérification données ESG PDF",
        ]
        if company.official_domain:
            domain = (
                company.official_domain
                .replace("https://", "").replace("http://", "").strip("/")
            )
            queries.extend([
                f'site:{domain} "{name}" {fiscal_year} "assurance" filetype:pdf',
                f'site:{domain} "{name}" {fiscal_year} "ISAE" filetype:pdf',
            ])
        return queries

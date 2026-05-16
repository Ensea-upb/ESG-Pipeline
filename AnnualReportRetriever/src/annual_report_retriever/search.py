from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate


class AnnualReportSearch:
    """
    Recherche multi-requêtes des rapports annuels / URD / DEU / integrated reports.
    """

    def search_candidates(self, company: Company, fiscal_year: int) -> list[SearchCandidate]:
        queries = self.build_queries(company=company, fiscal_year=fiscal_year)
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

    def build_queries(self, company: Company, fiscal_year: int) -> list[str]:
        name = company.name
        queries = [
            f"{name} {fiscal_year} annual report PDF",
            f"{name} {fiscal_year} rapport annuel PDF",
            f"{name} {fiscal_year} universal registration document PDF",
            f"{name} {fiscal_year} document d'enregistrement universel PDF",
            f"{name} {fiscal_year} URD PDF",
            f"{name} {fiscal_year} DEU PDF",
            f"{name} {fiscal_year} integrated report PDF",
        ]
        if company.official_domain:
            domain = (
                company.official_domain
                .replace("https://", "")
                .replace("http://", "")
                .strip("/")
            )
            queries.extend([
                f"site:{domain} {name} {fiscal_year} annual report PDF",
                f"site:{domain} {name} {fiscal_year} rapport annuel PDF",
                f"site:{domain} {name} {fiscal_year} universal registration document PDF",
                f"site:{domain} {name} {fiscal_year} document d'enregistrement universel PDF",
                f"site:{domain} {name} {fiscal_year} URD PDF",
                f"site:{domain} {name} {fiscal_year} DEU PDF",
            ])
        return queries

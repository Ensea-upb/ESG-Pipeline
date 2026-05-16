from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate


class RemunerationReportSearch:
    """
    Recherche des rapports de rémunération :
    - Remuneration Report / Directors' Remuneration Report ;
    - Executive Compensation Report ;
    - Pay Report / Say on Pay ;
    - Rapport de rémunération / Politique de rémunération.
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
            f"{name} {fiscal_year} remuneration report PDF",
            f"{name} {fiscal_year} directors remuneration report PDF",
            f"{name} {fiscal_year} executive remuneration report PDF",
            f"{name} {fiscal_year} compensation report PDF",
            f"{name} {fiscal_year} executive compensation report PDF",
            f"{name} {fiscal_year} pay report PDF",
            f"{name} {fiscal_year} say on pay report PDF",
            f"{name} {fiscal_year} remuneration policy report PDF",
            f"{name} {fiscal_year} rapport rémunération PDF",
            f"{name} {fiscal_year} rapport sur les rémunérations PDF",
            f"{name} {fiscal_year} politique de rémunération PDF",
            f"{name} {fiscal_year} rapport rémunération dirigeants PDF",
            f"{name} {fiscal_year} rémunération mandataires sociaux PDF",
        ]

        if company.official_domain:
            domain = (
                company.official_domain
                .replace("https://", "")
                .replace("http://", "")
                .strip("/")
            )
            queries.extend([
                f"site:{domain} {name} {fiscal_year} remuneration report PDF",
                f"site:{domain} {name} {fiscal_year} compensation report PDF",
                f"site:{domain} {name} {fiscal_year} pay report PDF",
                f"site:{domain} {name} {fiscal_year} rapport rémunération PDF",
                f"site:{domain} {name} {fiscal_year} politique de rémunération PDF",
            ])

        return queries

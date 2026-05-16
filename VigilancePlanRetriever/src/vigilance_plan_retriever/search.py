from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate


class VigilancePlanSearch:
    """
    Recherche des plans de vigilance et documents connexes :
    - Plan de vigilance / Devoir de vigilance (loi française de 2017) ;
    - Modern Slavery Statement / Modern Slavery Act ;
    - Human Rights Due Diligence Report ;
    - Supply Chain Transparency Report ;
    - Forced Labour Report.
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
            f"{name} {fiscal_year} plan de vigilance PDF",
            f"{name} {fiscal_year} devoir de vigilance PDF",
            f"{name} {fiscal_year} vigilance plan PDF",
            f"{name} {fiscal_year} duty of vigilance PDF",
            f"{name} {fiscal_year} modern slavery statement PDF",
            f"{name} {fiscal_year} modern slavery act report PDF",
            f"{name} {fiscal_year} human rights due diligence report PDF",
            f"{name} {fiscal_year} supply chain transparency report PDF",
            f"{name} {fiscal_year} forced labour report PDF",
            f"{name} {fiscal_year} rapport diligence raisonnée PDF",
            f"{name} {fiscal_year} rapport droits humains chaîne approvisionnement PDF",
            f"{name} {fiscal_year} rapport vigilance droits humains PDF",
            f"{name} {fiscal_year} human rights report PDF",
        ]

        if company.official_domain:
            domain = (
                company.official_domain
                .replace("https://", "")
                .replace("http://", "")
                .strip("/")
            )
            queries.extend([
                f"site:{domain} {name} {fiscal_year} plan de vigilance PDF",
                f"site:{domain} {name} {fiscal_year} vigilance plan PDF",
                f"site:{domain} {name} {fiscal_year} modern slavery statement PDF",
                f"site:{domain} {name} {fiscal_year} human rights due diligence PDF",
                f"site:{domain} {name} {fiscal_year} rapport droits humains PDF",
            ])

        return queries

from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate


class SustainabilityReportSearch:
    """
    Recherche multi-requêtes des rapports de durabilité / ESG / RSE / CSRD.
    Cible : Sustainability Report, ESG Report, DPEF, CSRD Statement, rapport RSE.
    """

    def build_queries(
        self,
        company: Company,
        fiscal_year: int,
    ) -> list[str]:
        """
        Génère les requêtes de recherche adaptées aux rapports ESG / durabilité.

        On couvre les terminologies françaises et anglaises.
        """

        company_name = company.name

        queries = [
            f"{company_name} {fiscal_year} sustainability report PDF",
            f"{company_name} {fiscal_year} ESG report PDF",
            f"{company_name} {fiscal_year} corporate responsibility report PDF",
            f"{company_name} {fiscal_year} CSR report PDF",
            f"{company_name} {fiscal_year} social environmental responsibility report PDF",
            f"{company_name} {fiscal_year} non-financial statement PDF",
            f"{company_name} {fiscal_year} CSRD statement PDF",
            f"{company_name} {fiscal_year} ESRS statement PDF",
            f"{company_name} {fiscal_year} sustainability statement PDF",
            f"{company_name} {fiscal_year} rapport RSE PDF",
            f"{company_name} {fiscal_year} rapport ESG PDF",
            f"{company_name} {fiscal_year} rapport de durabilité PDF",
            f"{company_name} {fiscal_year} déclaration de performance extra-financière PDF",
            f"{company_name} {fiscal_year} DPEF PDF",
        ]

        if company.official_domain:
            domain = (
                company.official_domain
                .replace("https://", "")
                .replace("http://", "")
                .strip("/")
            )

            queries.extend(
                [
                    f"site:{domain} {company_name} {fiscal_year} sustainability report PDF",
                    f"site:{domain} {company_name} {fiscal_year} ESG report PDF",
                    f"site:{domain} {company_name} {fiscal_year} sustainability statement PDF",
                    f"site:{domain} {company_name} {fiscal_year} CSRD statement PDF",
                    f"site:{domain} {company_name} {fiscal_year} ESRS statement PDF",
                    f"site:{domain} {company_name} {fiscal_year} rapport RSE PDF",
                    f"site:{domain} {company_name} {fiscal_year} rapport ESG PDF",
                    f"site:{domain} {company_name} {fiscal_year} rapport de durabilité PDF",
                    f"site:{domain} {company_name} {fiscal_year} DPEF PDF",
                ]
            )

        return queries

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

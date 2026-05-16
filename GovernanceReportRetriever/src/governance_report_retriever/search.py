from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate


class GovernanceReportSearch:
    """
    Source de recherche pour trouver des candidats de type :
    - Corporate Governance Report ;
    - Governance Statement / Corporate Governance Statement ;
    - Corporate Governance Charter / Governance Charter ;
    - Corporate Governance Code ;
    - Governance Framework ;
    - Rapport de gouvernance / Gouvernance d'entreprise ;
    - Déclaration de gouvernance / Charte de gouvernance.

    Cette classe ne télécharge rien.
    Elle retourne seulement des SearchCandidate.
    """

    def __init__(
        self,
        max_results_per_query: int = 5,
    ) -> None:
        self.max_results_per_query = max_results_per_query

    def build_queries(
        self,
        company: Company,
        fiscal_year: int,
    ) -> list[str]:
        """
        Génère les requêtes de recherche adaptées aux rapports de gouvernance.

        On couvre les terminologies françaises et anglaises ainsi que les
        référentiels de gouvernance (AFEP-MEDEF, UK Corporate Governance Code, etc.)
        """

        company_name = company.name

        queries = [
            f"{company_name} {fiscal_year} corporate governance report PDF",
            f"{company_name} {fiscal_year} governance report PDF",
            f"{company_name} {fiscal_year} corporate governance statement PDF",
            f"{company_name} {fiscal_year} governance statement PDF",
            f"{company_name} {fiscal_year} corporate governance charter PDF",
            f"{company_name} {fiscal_year} governance framework PDF",
            f"{company_name} {fiscal_year} corporate governance code PDF",
            f"{company_name} {fiscal_year} corporate governance disclosure PDF",
            f"{company_name} {fiscal_year} board governance report PDF",
            f"{company_name} {fiscal_year} rapport de gouvernance PDF",
            f"{company_name} {fiscal_year} rapport gouvernance entreprise PDF",
            f"{company_name} {fiscal_year} déclaration de gouvernance PDF",
            f"{company_name} {fiscal_year} charte de gouvernance PDF",
            f"{company_name} {fiscal_year} code de gouvernance PDF",
            f"{company_name} {fiscal_year} gouvernance d entreprise PDF",
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
                    f"site:{domain} {company_name} {fiscal_year} corporate governance report PDF",
                    f"site:{domain} {company_name} {fiscal_year} governance statement PDF",
                    f"site:{domain} {company_name} {fiscal_year} governance charter PDF",
                    f"site:{domain} {company_name} {fiscal_year} governance framework PDF",
                    f"site:{domain} {company_name} {fiscal_year} rapport de gouvernance PDF",
                    f"site:{domain} {company_name} {fiscal_year} charte de gouvernance PDF",
                ]
            )

        return queries

    def search_candidates(
        self,
        company: Company,
        fiscal_year: int,
    ) -> list[SearchCandidate]:
        """
        Cherche des candidats et retourne une liste dédupliquée.
        """

        queries = self.build_queries(company=company, fiscal_year=fiscal_year)
        all_candidates: list[SearchCandidate] = []

        with DDGS() as ddgs:
            for query in queries:
                results = self._ddgs_search(ddgs=ddgs, query=query)
                for item in results:
                    candidate = SearchCandidate(
                        title=item.get("title", ""),
                        url=item.get("href", ""),
                        snippet=item.get("body", ""),
                        source_name="ddgs",
                    )
                    if candidate.url:
                        all_candidates.append(candidate)

        return self._deduplicate_candidates(all_candidates)

    def _ddgs_search(self, ddgs: DDGS, query: str) -> list[dict]:
        """
        Appelle DuckDuckGo Search via DDGS.
        """
        try:
            return list(ddgs.text(query, max_results=self.max_results_per_query)) or []
        except Exception:
            return []

    @staticmethod
    def _deduplicate_candidates(
        candidates: list[SearchCandidate],
    ) -> list[SearchCandidate]:
        """
        Supprime les doublons d'URL.
        """

        seen_urls = set()
        unique_candidates = []

        for candidate in candidates:
            normalized_url = candidate.url.strip()

            if not normalized_url:
                continue

            if normalized_url in seen_urls:
                continue

            seen_urls.add(normalized_url)
            unique_candidates.append(candidate)

        return unique_candidates

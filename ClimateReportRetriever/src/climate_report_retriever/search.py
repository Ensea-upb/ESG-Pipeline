from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate


class ClimateReportSearch:
    """
    Source de recherche pour trouver des candidats de type :
    - Climate Report ;
    - TCFD Report / TCFD Index ;
    - Climate Transition Plan / Transition Plan ;
    - Net Zero Report / Net Zero Transition Plan ;
    - Carbon Report / GHG Emissions Report ;
    - CDP Climate Response ;
    - Rapport climat / Plan de transition / Bilan carbone ;
    - Rapport TCFD / Stratégie climat / Rapport émissions carbone.

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
        Génère les requêtes de recherche adaptées aux rapports climat.

        On couvre les terminologies françaises et anglaises ainsi que
        les référentiels TCFD, CDP, GHG Protocol.
        """

        company_name = company.name

        queries = [
            f"{company_name} {fiscal_year} climate report PDF",
            f"{company_name} {fiscal_year} TCFD report PDF",
            f"{company_name} {fiscal_year} climate transition plan PDF",
            f"{company_name} {fiscal_year} transition plan PDF",
            f"{company_name} {fiscal_year} net zero report PDF",
            f"{company_name} {fiscal_year} net zero transition plan PDF",
            f"{company_name} {fiscal_year} carbon report PDF",
            f"{company_name} {fiscal_year} climate strategy PDF",
            f"{company_name} {fiscal_year} CDP climate response PDF",
            f"{company_name} {fiscal_year} GHG emissions report PDF",
            f"{company_name} {fiscal_year} greenhouse gas report PDF",
            f"{company_name} {fiscal_year} rapport climat PDF",
            f"{company_name} {fiscal_year} plan de transition PDF",
            f"{company_name} {fiscal_year} rapport TCFD PDF",
            f"{company_name} {fiscal_year} stratégie climat PDF",
            f"{company_name} {fiscal_year} bilan carbone PDF",
            f"{company_name} {fiscal_year} rapport émissions carbone PDF",
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
                    f"site:{domain} {company_name} {fiscal_year} climate report PDF",
                    f"site:{domain} {company_name} {fiscal_year} TCFD report PDF",
                    f"site:{domain} {company_name} {fiscal_year} transition plan PDF",
                    f"site:{domain} {company_name} {fiscal_year} net zero PDF",
                    f"site:{domain} {company_name} {fiscal_year} carbon report PDF",
                    f"site:{domain} {company_name} {fiscal_year} rapport climat PDF",
                    f"site:{domain} {company_name} {fiscal_year} plan de transition PDF",
                    f"site:{domain} {company_name} {fiscal_year} bilan carbone PDF",
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

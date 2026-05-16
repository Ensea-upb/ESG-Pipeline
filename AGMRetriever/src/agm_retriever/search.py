from __future__ import annotations

from ddgs import DDGS

from .models import Company, SearchCandidate

class AGMSearch:
    """Recherche des documents AGM : convocation, résolutions, résultats de vote, PV."""

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
            f"{name} {fiscal_year} AGM resolutions PDF",
            f"{name} {fiscal_year} annual general meeting resolutions PDF",
            f"{name} {fiscal_year} proxy statement PDF",
            f"{name} {fiscal_year} notice of annual general meeting PDF",
            f"{name} {fiscal_year} AGM voting results PDF",
            f"{name} {fiscal_year} say on climate vote PDF",
            f"{name} {fiscal_year} shareholders meeting resolutions PDF",
            f"{name} {fiscal_year} convocation assemblée générale PDF",
            f"{name} {fiscal_year} résolutions assemblée générale PDF",
            f"{name} {fiscal_year} avis de convocation AG PDF",
            f"{name} {fiscal_year} résultats votes assemblée générale PDF",
            f"{name} {fiscal_year} procès-verbal assemblée générale PDF",
        ]
        if company.official_domain:
            domain = (
                company.official_domain
                .replace("https://", "").replace("http://", "").strip("/")
            )
            queries.extend([
                f'site:{domain} "{name}" {fiscal_year} "AGM" filetype:pdf',
                f'site:{domain} "{name}" {fiscal_year} "assemblée générale" filetype:pdf',
            ])
        return queries

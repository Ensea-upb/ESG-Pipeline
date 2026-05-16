from __future__ import annotations

from ddgs import DDGS



from .models import Company, PolicyType, SearchCandidate


# Requêtes spécifiques par type de politique
POLICY_QUERIES: dict[PolicyType, list[str]] = {
    PolicyType.CODE_OF_CONDUCT: [
        "{name} code of conduct PDF",
        "{name} code éthique PDF",
        "{name} code of ethics PDF",
        "{name} business conduct policy PDF",
        "{name} charte éthique PDF",
        "{name} business ethics code PDF",
    ],
    PolicyType.ANTICORRUPTION: [
        "{name} anti-corruption policy PDF",
        "{name} anticorruption policy PDF",
        "{name} anti-bribery policy PDF",
        "{name} politique anticorruption PDF",
        "{name} anti-corruption compliance program PDF",
        "{name} FCPA compliance policy PDF",
    ],
    PolicyType.HUMAN_RIGHTS: [
        "{name} human rights policy PDF",
        "{name} politique droits humains PDF",
        "{name} human rights commitment PDF",
        "{name} human rights statement PDF",
        "{name} droits de l'homme politique PDF",
        "{name} human rights due diligence policy PDF",
    ],
    PolicyType.DEI: [
        "{name} diversity equity inclusion policy PDF",
        "{name} DEI policy PDF",
        "{name} politique diversité équité inclusion PDF",
        "{name} diversity and inclusion policy PDF",
        "{name} equal opportunity policy PDF",
        "{name} politique égalité professionnelle PDF",
    ],
    PolicyType.ENVIRONMENTAL: [
        "{name} environmental policy PDF",
        "{name} politique environnementale PDF",
        "{name} environmental commitment PDF",
        "{name} climate policy PDF",
        "{name} politique climat environnement PDF",
        "{name} sustainability policy PDF",
    ],
    PolicyType.SUPPLIER_CODE: [
        "{name} supplier code of conduct PDF",
        "{name} code fournisseurs PDF",
        "{name} supplier ethics code PDF",
        "{name} responsible sourcing policy PDF",
        "{name} politique achats responsables PDF",
        "{name} vendor code of conduct PDF",
    ],
}

POLICY_SITE_QUERIES: dict[PolicyType, list[str]] = {
    PolicyType.CODE_OF_CONDUCT: [
        'site:{domain} "code of conduct" filetype:pdf',
        'site:{domain} "code éthique" filetype:pdf',
    ],
    PolicyType.ANTICORRUPTION: [
        'site:{domain} "anti-corruption" filetype:pdf',
        'site:{domain} "anticorruption" filetype:pdf',
    ],
    PolicyType.HUMAN_RIGHTS: [
        'site:{domain} "human rights policy" filetype:pdf',
        'site:{domain} "droits humains" filetype:pdf',
    ],
    PolicyType.DEI: [
        'site:{domain} "diversity" "inclusion" policy filetype:pdf',
        'site:{domain} "diversité" "inclusion" filetype:pdf',
    ],
    PolicyType.ENVIRONMENTAL: [
        'site:{domain} "environmental policy" filetype:pdf',
        'site:{domain} "politique environnementale" filetype:pdf',
    ],
    PolicyType.SUPPLIER_CODE: [
        'site:{domain} "supplier code" filetype:pdf',
        'site:{domain} "code fournisseurs" filetype:pdf',
    ],
}


class CorporatePolicySearch:
    """
    Recherche multi-requêtes des politiques corporate.
    Supporte 6 types : code_of_conduct, anticorruption, human_rights,
    dei, environmental, supplier_code.
    """

    def search_candidates(
        self, company: Company, policy_type: PolicyType, reference_year: int
    ) -> list[SearchCandidate]:
        queries = self._build_queries(
            company=company, policy_type=policy_type, reference_year=reference_year
        )
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

    def _build_queries(
        self, company: Company, policy_type: PolicyType, reference_year: int
    ) -> list[str]:
        name = company.name
        base_queries = POLICY_QUERIES.get(policy_type, [])
        queries = [q.format(name=name, year=reference_year) for q in base_queries]

        if company.official_domain:
            domain = company.official_domain
            site_queries = POLICY_SITE_QUERIES.get(policy_type, [])
            queries += [q.format(domain=domain, name=name) for q in site_queries]

        return queries


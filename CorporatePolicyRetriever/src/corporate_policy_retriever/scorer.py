from __future__ import annotations

import re
import unicodedata

from .models import Company, CorporatePolicyRequest, PolicyType, SearchCandidate, ScoredCandidate

# ---------------------------------------------------------------------------
# Mots-clés par type de politique
# ---------------------------------------------------------------------------

POLICY_STRONG_KEYWORDS: dict[PolicyType, list[str]] = {
    PolicyType.CODE_OF_CONDUCT: [
        "code of conduct", "code of ethics", "business conduct policy",
        "code éthique", "charte éthique", "charte de déontologie",
        "business ethics code", "code of business ethics",
        "code de conduite", "code de déontologie",
        "ethics and compliance code", "standards of business conduct",
        "règles de conduite", "global code of conduct",
    ],
    PolicyType.ANTICORRUPTION: [
        "anti-corruption policy", "anticorruption policy",
        "anti-bribery policy", "anti-bribery and corruption policy",
        "politique anticorruption", "politique anti-corruption",
        "corruption prevention policy", "bribery prevention policy",
        "fcpa compliance", "uk bribery act compliance",
        "anti-corruption compliance program", "lutte contre la corruption",
        "sapin ii compliance", "anti-facilitation of tax evasion",
    ],
    PolicyType.HUMAN_RIGHTS: [
        "human rights policy", "human rights commitment",
        "human rights statement", "politique droits humains",
        "droits de l'homme politique", "human rights framework",
        "human rights principles", "un guiding principles",
        "respect for human rights", "human rights due diligence policy",
        "charte droits humains", "engagements droits humains",
        "modern slavery and human trafficking policy",
    ],
    PolicyType.DEI: [
        "diversity equity inclusion policy", "dei policy",
        "diversity and inclusion policy", "diversity policy",
        "politique diversité équité inclusion", "politique diversité inclusion",
        "equal opportunity policy", "politique égalité professionnelle",
        "inclusion policy", "diversity commitment",
        "gender equality policy", "politique parité",
        "charte diversité", "disability inclusion policy",
    ],
    PolicyType.ENVIRONMENTAL: [
        "environmental policy", "politique environnementale",
        "environmental commitment", "climate policy",
        "politique climat", "environmental management policy",
        "environmental principles", "sustainability policy",
        "politique développement durable", "biodiversity policy",
        "net zero policy", "climate change policy",
        "politique eau", "water policy",
    ],
    PolicyType.SUPPLIER_CODE: [
        "supplier code of conduct", "supplier code",
        "vendor code of conduct", "code fournisseurs",
        "responsible sourcing policy", "politique achats responsables",
        "supply chain code of conduct", "supplier ethics code",
        "supplier sustainability requirements", "supplier standards",
        "charte fournisseurs", "code achats",
        "supplier expectations", "responsible procurement policy",
    ],
}

POLICY_SECONDARY_KEYWORDS: dict[PolicyType, list[str]] = {
    PolicyType.CODE_OF_CONDUCT: [
        "compliance", "integrity", "whistleblowing", "intégrité",
        "speak up", "alert mechanism", "alerte éthique", "deontology",
    ],
    PolicyType.ANTICORRUPTION: [
        "gifts and hospitality", "conflict of interest", "facilitation payment",
        "third party due diligence", "cadeaux et invitations", "conflits d'intérêts",
    ],
    PolicyType.HUMAN_RIGHTS: [
        "forced labor", "child labor", "travail forcé", "travail des enfants",
        "freedom of association", "right to organize", "supply chain",
    ],
    PolicyType.DEI: [
        "gender", "race", "ethnicity", "disability", "lgbtq",
        "inclusion", "belonging", "representation", "pay equity",
    ],
    PolicyType.ENVIRONMENTAL: [
        "carbon", "ghg", "emissions", "waste", "water", "biodiversity",
        "circular economy", "climate change", "energie", "ressources",
    ],
    PolicyType.SUPPLIER_CODE: [
        "audit", "assessment", "screening", "corrective action",
        "supplier audit", "évaluation fournisseurs", "diligence",
    ],
}

POLICY_FILENAME_KEYWORDS: dict[PolicyType, list[str]] = {
    PolicyType.CODE_OF_CONDUCT: [
        "code-of-conduct", "codeofconduct", "code_of_conduct",
        "code-ethique", "codeethique", "charte-ethique",
        "business-conduct", "ethics-code",
    ],
    PolicyType.ANTICORRUPTION: [
        "anti-corruption", "anticorruption", "anti_corruption",
        "anti-bribery", "antibribery", "corruption-policy",
    ],
    PolicyType.HUMAN_RIGHTS: [
        "human-rights", "humanrights", "human_rights",
        "droits-humains", "droitshumains", "rights-policy",
    ],
    PolicyType.DEI: [
        "diversity", "dei-policy", "deipolicy", "inclusion-policy",
        "equal-opportunity", "diversite", "egalite",
    ],
    PolicyType.ENVIRONMENTAL: [
        "environmental-policy", "environmentalpolicy", "politique-environnementale",
        "climate-policy", "sustainability-policy", "eco-policy",
    ],
    PolicyType.SUPPLIER_CODE: [
        "supplier-code", "suppliercode", "supplier_code",
        "code-fournisseurs", "vendor-code", "achats-responsables",
    ],
}

WEAK_POLICY_KEYWORDS = [
    "policy", "politique", "commitment", "engagements", "charter",
    "charte", "principles", "principes", "guidelines", "framework",
    "standards", "normes",
]

LOW_TRUST_DOMAINS = [
    "scribd.com", "slideshare.net", "issuu.com", "calameo.com",
]

PRESS_RELEASE_DOMAINS = [
    "businesswire.com", "prnewswire.com", "globenewswire.com",
    "accesswire.com", "actusnews.com", "cision.com",
]

CDN_OR_ASSET_DOMAIN_PATTERNS = [
    r"akamaized\.net", r"cloudfront\.net", r"fastly\.net",
    r"storage\.googleapis\.com", r"blob\.core\.windows\.net",
    r"s3\.amazonaws\.com", r"cdn\.",
]


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def find_keywords(text_norm: str, keywords: list[str]) -> list[str]:
    found = []
    for kw in keywords:
        kw_norm = normalize_text(kw)
        if len(kw_norm) <= 3:
            if f" {kw_norm} " in f" {text_norm} ":
                found.append(kw)
        else:
            if kw_norm in text_norm:
                found.append(kw)
    return found


def domain_of(url: str) -> str:
    url = url.lower()
    for prefix in ("https://", "http://", "//"):
        if url.startswith(prefix):
            url = url[len(prefix):]
    return url.split("/")[0]


class CorporatePolicyScorer:

    def __init__(
        self,
        auto_download_threshold: float = 80.0,
        human_review_threshold: float = 60.0,
    ) -> None:
        self.auto_download_threshold = auto_download_threshold
        self.human_review_threshold = human_review_threshold

    def rank_candidates(
        self,
        request: CorporatePolicyRequest,
        candidates: list[SearchCandidate],
    ) -> list[ScoredCandidate]:
        scored = [self._score(request=request, candidate=c) for c in candidates]
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored

    def _score(
        self,
        request: CorporatePolicyRequest,
        candidate: SearchCandidate,
    ) -> ScoredCandidate:
        company = request.company
        reference_year = request.reference_year
        policy_type = request.policy_type

        title = candidate.title or ""
        url = candidate.url or ""
        snippet = candidate.snippet or ""
        full_text = f"{title} {url} {snippet}"
        text_norm = normalize_text(full_text)
        url_norm = normalize_text(url)
        filename = url.split("/")[-1].lower()
        filename_norm = normalize_text(filename)
        doc_domain = domain_of(url)

        score = 0.0
        positive: list[str] = []
        negative: list[str] = []

        strong_kws_list = POLICY_STRONG_KEYWORDS.get(policy_type, [])
        secondary_kws_list = POLICY_SECONDARY_KEYWORDS.get(policy_type, [])
        filename_kws_list = POLICY_FILENAME_KEYWORDS.get(policy_type, [])

        # --- Signaux positifs ---
        strong_kws = find_keywords(text_norm, strong_kws_list)
        if strong_kws:
            score += 40
            positive.append(f"mots-clés forts politique : {strong_kws[:3]}")

        secondary_kws = find_keywords(text_norm, secondary_kws_list)
        if secondary_kws:
            score += 20
            positive.append(f"mots-clés secondaires : {secondary_kws[:3]}")

        weak_kws = find_keywords(text_norm, WEAK_POLICY_KEYWORDS)
        if weak_kws and not strong_kws:
            score += 10
            positive.append(f"mots-clés faibles : {weak_kws[:3]}")

        # Fraîcheur — tolérance large pour documents pérennes (5 ans)
        years_found = {int(m) for m in re.findall(r"\b(20\d{2})\b", full_text)}
        recent_years = set(range(reference_year - 4, reference_year + 1))
        matching_years = years_found & recent_years
        if matching_years:
            score += 15
            positive.append(f"année récente détectée : {max(matching_years)}")

        # Nom entreprise
        name_norm = normalize_text(company.name)
        if name_norm in text_norm:
            score += 20
            positive.append("nom de l'entreprise détecté")

        # Domaine officiel
        if company.official_domain and company.official_domain.lower() in doc_domain:
            score += 25
            positive.append(f"domaine officiel détecté : {company.official_domain}")

        # URL PDF
        if url_norm.endswith("pdf") or ".pdf" in url_norm:
            score += 10
            positive.append("URL PDF directe")

        # Nom de fichier
        fn_kws = find_keywords(filename_norm, filename_kws_list)
        if fn_kws:
            score += 15
            positive.append(f"nom de fichier politique : {fn_kws[:2]}")

        # CDN
        if any(re.search(p, doc_domain) for p in CDN_OR_ASSET_DOMAIN_PATTERNS):
            score += 5
            positive.append("CDN / asset domain")

        # --- Pénalités ---
        if any(d in doc_domain for d in PRESS_RELEASE_DOMAINS):
            score -= 30
            negative.append(f"domaine presse : {doc_domain}")

        if any(d in doc_domain for d in LOW_TRUST_DOMAINS):
            score -= 45
            negative.append(f"domaine faible confiance : {doc_domain}")

        # Document trop ancien
        if years_found and not matching_years:
            oldest = max(years_found) if years_found else 0
            if oldest < reference_year - 4:
                score -= 20
                negative.append(f"document potentiellement obsolète : {oldest}")

        score = max(0.0, min(100.0, score))

        # --- Classification ---
        if not strong_kws:
            document_class = "generic_policy_document"
        else:
            document_class = f"standalone_{policy_type.value}"
        positive.append(f"classe documentaire : {document_class}")

        if score >= self.auto_download_threshold:
            decision = "auto_download"
        elif score >= self.human_review_threshold:
            decision = "human_review_required"
        else:
            decision = "reject"

        if not strong_kws and not secondary_kws:
            decision = "reject"

        # HTML → PDF resolution
        if score >= self.human_review_threshold and not (
            url_norm.endswith("pdf") or ".pdf" in url_norm
        ):
            decision = "pdf_resolution_required"

        return ScoredCandidate(
            title=candidate.title,
            url=candidate.url,
            snippet=candidate.snippet,
            source_name=candidate.source_name,
            score=score,
            decision=decision,
            positive_signals=positive,
            negative_signals=negative,
        )

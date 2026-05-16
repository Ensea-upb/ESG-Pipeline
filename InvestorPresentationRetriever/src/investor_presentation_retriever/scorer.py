from __future__ import annotations

import re
import unicodedata

from .models import Company, InvestorPresentationRequest, SearchCandidate, ScoredCandidate

STRONG_PRESENTATION_KEYWORDS = [
    "capital markets day", "investor day", "esg day", "sustainability day",
    "investor presentation", "investor relations presentation",
    "roadshow presentation", "results presentation", "annual results presentation",
    "full year results presentation", "half year results presentation",
    "strategy presentation", "strategic update presentation",
    "journée investisseurs", "présentation investisseurs",
    "présentation résultats", "présentation stratégique",
    "cmd presentation", "cmd slides", "investor briefing",
    "earnings presentation", "financial results presentation",
]

SECONDARY_PRESENTATION_KEYWORDS = [
    "slides", "slide deck", "webcast", "investor relations",
    "financial calendar", "ir presentation", "equity story",
    "pitch deck", "strategy day", "investor update",
]

WEAK_PRESENTATION_KEYWORDS = [
    "presentation", "présentation", "investor", "investisseur",
    "results", "résultats", "strategy", "stratégie",
]

STRONG_FILENAME_KEYWORDS = [
    "investor-day", "investorday", "capital-markets-day", "cmd",
    "investor-presentation", "results-presentation", "esg-day",
    "full-year-presentation", "fy-presentation", "strategy-presentation",
    "roadshow", "investor-briefing",
]

ANNUAL_REPORT_KEYWORDS = [
    "annual report", "rapport annuel", "urd", "deu",
    "universal registration document", "integrated report",
]

PRESS_RELEASE_KEYWORDS = [
    "press release", "communiqué de presse", "news release",
    "profit warning", "trading update",
]

LOW_TRUST_DOMAINS = ["scribd.com", "slideshare.net", "issuu.com", "calameo.com"]
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


class InvestorPresentationScorer:

    def __init__(self, auto_download_threshold: float = 80.0, human_review_threshold: float = 60.0):
        self.auto_download_threshold = auto_download_threshold
        self.human_review_threshold = human_review_threshold

    def rank_candidates(self, request: InvestorPresentationRequest, candidates: list[SearchCandidate]) -> list[ScoredCandidate]:
        scored = [self._score(request=request, candidate=c) for c in candidates]
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored

    def _score(self, request: InvestorPresentationRequest, candidate: SearchCandidate) -> ScoredCandidate:
        company = request.company
        fiscal_year = request.fiscal_year
        full_text = f"{candidate.title} {candidate.url} {candidate.snippet}"
        text_norm = normalize_text(full_text)
        url_norm = normalize_text(candidate.url)
        filename_norm = normalize_text(candidate.url.split("/")[-1])
        doc_domain = domain_of(candidate.url)

        score = 0.0
        positive: list[str] = []
        negative: list[str] = []

        strong_kws = find_keywords(text_norm, STRONG_PRESENTATION_KEYWORDS)
        if strong_kws:
            score += 40
            positive.append(f"mots-clés forts présentation : {strong_kws[:3]}")

        secondary_kws = find_keywords(text_norm, SECONDARY_PRESENTATION_KEYWORDS)
        if secondary_kws:
            score += 20
            positive.append(f"mots-clés secondaires : {secondary_kws[:3]}")

        weak_kws = find_keywords(text_norm, WEAK_PRESENTATION_KEYWORDS)
        if weak_kws and not strong_kws:
            score += 8
            positive.append(f"mots-clés faibles : {weak_kws[:3]}")

        years_found = {m for m in re.findall(r"\b(20\d{2})\b", full_text)}
        if years_found & {str(fiscal_year), str(fiscal_year - 1)}:
            score += 20
            positive.append(f"année trouvée : {fiscal_year}")

        company_name_found = normalize_text(company.name) in text_norm
        if company_name_found:
            score += 20
            positive.append("nom de l'entreprise détecté")
        else:
            score -= 40
            negative.append("nom de l'entreprise absent")

        if company.official_domain and company.official_domain.lower() in doc_domain:
            score += 20
            positive.append(f"domaine officiel : {company.official_domain}")

        if url_norm.endswith("pdf") or ".pdf" in url_norm:
            score += 10
            positive.append("URL PDF directe")

        fn_kws = find_keywords(filename_norm, STRONG_FILENAME_KEYWORDS)
        if fn_kws:
            score += 15
            positive.append(f"nom de fichier présentation : {fn_kws[:2]}")

        if any(re.search(p, doc_domain) for p in CDN_OR_ASSET_DOMAIN_PATTERNS):
            score += 5
            positive.append("CDN / asset domain")

        # Pénalités
        annual_kws = find_keywords(text_norm, ANNUAL_REPORT_KEYWORDS)
        if annual_kws and not strong_kws:
            score -= 30
            negative.append(f"rapport annuel détecté : {annual_kws[:2]}")

        press_kws = find_keywords(text_norm, PRESS_RELEASE_KEYWORDS)
        if press_kws and not strong_kws:
            score -= 30
            negative.append(f"communiqué de presse : {press_kws[:2]}")

        if any(d in doc_domain for d in PRESS_RELEASE_DOMAINS):
            score -= 25
            negative.append(f"domaine presse : {doc_domain}")

        if any(d in doc_domain for d in LOW_TRUST_DOMAINS):
            score -= 45
            negative.append(f"domaine faible confiance : {doc_domain}")

        score = max(0.0, min(100.0, score))

        if not strong_kws and not secondary_kws:
            document_class = "unclassified"
            decision = "reject"
        else:
            document_class = "investor_presentation"
            if score >= self.auto_download_threshold:
                decision = "auto_download"
            elif score >= self.human_review_threshold:
                decision = "human_review_required"
            else:
                decision = "reject"
            if decision != "reject" and not (url_norm.endswith("pdf") or ".pdf" in url_norm):
                decision = "pdf_resolution_required"

        positive.append(f"classe documentaire : {document_class}")

        return ScoredCandidate(
            title=candidate.title, url=candidate.url, snippet=candidate.snippet,
            source_name=candidate.source_name, score=score, decision=decision,
            positive_signals=positive, negative_signals=negative,
        )

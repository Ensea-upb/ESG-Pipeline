from __future__ import annotations

import re
import unicodedata

from .models import Company, EarningsCallRequest, SearchCandidate, ScoredCandidate

STRONG_EARNINGS_KEYWORDS = [
    "earnings call transcript", "earnings transcript", "call transcript",
    "conference call transcript", "results call transcript",
    "quarterly earnings transcript", "annual earnings transcript",
    "q1 earnings transcript", "q2 earnings transcript",
    "q3 earnings transcript", "q4 earnings transcript",
    "full year results transcript", "transcription résultats",
    "transcript conférence analystes", "verbatim earnings call",
    "earnings call verbatim", "investor call transcript",
]

SECONDARY_EARNINGS_KEYWORDS = [
    "earnings call", "conference call", "analyst call",
    "results call", "q&a transcript", "management commentary",
    "conférence analystes", "appel investisseurs",
    "seeking alpha transcript", "motley fool transcript",
]

WEAK_EARNINGS_KEYWORDS = [
    "earnings", "transcript", "call recording", "webcast transcript",
    "résultats", "conférence", "analystes",
]

STRONG_FILENAME_KEYWORDS = [
    "earnings-transcript", "call-transcript", "earnings-call",
    "transcript", "q1-transcript", "q2-transcript", "q3-transcript", "q4-transcript",
]

TRANSCRIPT_SOURCE_DOMAINS = [
    "seekingalpha.com", "motleyfool.com", "fool.com",
    "wsj.com", "businesswire.com",
]

PRESS_RELEASE_KEYWORDS = [
    "press release", "communiqué de presse", "news release",
]

LOW_TRUST_DOMAINS = ["scribd.com", "slideshare.net", "issuu.com"]
PRESS_RELEASE_DOMAINS = [
    "prnewswire.com", "globenewswire.com", "accesswire.com", "actusnews.com",
]
CDN_OR_ASSET_DOMAIN_PATTERNS = [
    r"akamaized\.net", r"cloudfront\.net", r"s3\.amazonaws\.com", r"cdn\.",
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


def domain_matches_any(domain: str, domains: list[str]) -> bool:
    """Exact suffix match to avoid 'apple.com' matching 'pineapple.com'."""
    domain = domain.lower().replace("www.", "")
    for ref in domains:
        ref = ref.lower().replace("www.", "")
        if domain == ref or domain.endswith("." + ref):
            return True
    return False


class EarningsCallScorer:

    def __init__(self, auto_download_threshold: float = 80.0, human_review_threshold: float = 60.0):
        self.auto_download_threshold = auto_download_threshold
        self.human_review_threshold = human_review_threshold

    def rank_candidates(self, request: EarningsCallRequest, candidates: list[SearchCandidate]) -> list[ScoredCandidate]:
        scored = [self._score(request=request, candidate=c) for c in candidates]
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored

    def _score(self, request: EarningsCallRequest, candidate: SearchCandidate) -> ScoredCandidate:
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

        strong_kws = find_keywords(text_norm, STRONG_EARNINGS_KEYWORDS)
        if strong_kws:
            score += 45
            positive.append(f"mots-clés forts earnings call : {strong_kws[:3]}")

        secondary_kws = find_keywords(text_norm, SECONDARY_EARNINGS_KEYWORDS)
        if secondary_kws:
            score += 20
            positive.append(f"mots-clés secondaires : {secondary_kws[:3]}")

        weak_kws = find_keywords(text_norm, WEAK_EARNINGS_KEYWORDS)
        if weak_kws and not strong_kws:
            score += 8
            positive.append(f"mots-clés faibles : {weak_kws[:3]}")

        years_found = {m for m in re.findall(r"\b(20\d{2})\b", full_text)}
        if str(fiscal_year) in years_found:
            score += 20
            positive.append(f"année trouvée : {fiscal_year}")
        elif years_found:
            score -= 10
            negative.append(f"année demandée absente, années détectées : {sorted(years_found)}")

        company_name_found = normalize_text(company.name) in text_norm
        if company_name_found:
            score += 15
            positive.append("nom de l'entreprise détecté")
        else:
            score -= 40
            negative.append("nom de l'entreprise absent")

        if company.official_domain and domain_matches_any(doc_domain, [company.official_domain]):
            score += 15
            positive.append(f"domaine officiel : {company.official_domain}")

        # Sources spécialisées en transcripts
        if any(d in doc_domain for d in TRANSCRIPT_SOURCE_DOMAINS):
            score += 10
            positive.append(f"source spécialisée transcripts : {doc_domain}")

        if url_norm.endswith("pdf") or ".pdf" in url_norm:
            score += 5
            positive.append("URL PDF directe")

        fn_kws = find_keywords(filename_norm, STRONG_FILENAME_KEYWORDS)
        if fn_kws:
            score += 10
            positive.append(f"nom de fichier transcript : {fn_kws[:2]}")

        # Pénalités
        press_kws = find_keywords(text_norm, PRESS_RELEASE_KEYWORDS)
        if press_kws and not strong_kws:
            score -= 25
            negative.append(f"communiqué de presse : {press_kws[:2]}")

        if any(d in doc_domain for d in PRESS_RELEASE_DOMAINS):
            score -= 20
            negative.append(f"domaine presse : {doc_domain}")

        if any(d in doc_domain for d in LOW_TRUST_DOMAINS):
            score -= 45
            negative.append(f"domaine faible confiance : {doc_domain}")

        # Safety caps : un signal fort manquant plafonne le score
        # pour éviter qu'un document soit accepté sur des signaux
        # indirects seuls (domaine + année sans mots-clés transcript).
        if not company_name_found:
            score = min(score, 50.0)
        if not strong_kws and not secondary_kws:
            score = min(score, 45.0)

        score = max(0.0, min(100.0, score))

        if not strong_kws and not secondary_kws:
            document_class = "unclassified"
            decision = "reject"
        else:
            document_class = "earnings_call_transcript"
            if score >= self.auto_download_threshold:
                decision = "auto_download"
            elif score >= self.human_review_threshold:
                decision = "human_review_required"
            else:
                decision = "reject"
            # Transcripts peuvent être HTML (seekingalpha) → résolution PDF
            if decision != "reject" and not (url_norm.endswith("pdf") or ".pdf" in url_norm):
                decision = "pdf_resolution_required"

        positive.append(f"classe documentaire : {document_class}")

        return ScoredCandidate(
            title=candidate.title, url=candidate.url, snippet=candidate.snippet,
            source_name=candidate.source_name, score=score, decision=decision,
            positive_signals=positive, negative_signals=negative,
        )

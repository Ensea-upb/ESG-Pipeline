from __future__ import annotations

import re
import unicodedata

from .models import Company, HalfYearReportRequest, SearchCandidate, ScoredCandidate

# ---------------------------------------------------------------------------
# Mots-clés
# ---------------------------------------------------------------------------

STRONG_HALF_YEAR_KEYWORDS = [
    "half year report", "half-year report", "half year financial report",
    "semi-annual report", "semi annual report", "interim report",
    "half year results", "half-year results", "first half results",
    "six months results", "six-month results", "six months financial report",
    "rapport semestriel", "rapport financier semestriel",
    "résultats semestriels", "résultats du premier semestre",
    "résultats du deuxième semestre", "résultats premier semestre",
    "résultats s1", "comptes semestriels", "half year accounts",
    "interim financial statements", "rapport financier intermédiaire",
]

HALF_YEAR_PERIOD_KEYWORDS = [
    "premier semestre", "deuxième semestre", "first semester", "second semester",
    "first half", "second half", "six months", "6 months",
]

WEAK_HALF_YEAR_KEYWORDS = [
    "semestriel", "semestrial", "interim", "midyear", "mid-year",
    "half year", "half-year", "semi annual", "semi-annual",
]

STRONG_FILENAME_KEYWORDS = [
    "half-year", "half_year", "halfyear", "semi-annual", "semestrial",
    "semestriel", "h1-report", "h1report", "interim-report", "interimreport",
    "6months", "sixmonths", "rapport-semestriel", "comptes-semestriels",
]

# Exclusions — documents à rejeter
ANNUAL_REPORT_KEYWORDS = [
    "annual report", "rapport annuel", "universal registration document",
    "document d'enregistrement universel", "integrated report", "urd", "deu",
    "20-f", "10-k",
]

PRESS_RELEASE_KEYWORDS = [
    "press release", "communiqué de presse", "news release",
    "earnings release", "profit warning", "trading update",
]

PRESENTATION_KEYWORDS = [
    "investor presentation", "investor day", "capital markets day",
    "roadshow", "slide deck", "webcast slides",
]

FINANCIAL_ONLY_KEYWORDS = [
    "financial statements only", "statutory accounts", "standalone financial",
]

PERIODIC_KEYWORDS = ["q1", "q3", "quarterly report", "rapport trimestriel"]

LOW_TRUST_DOMAINS = [
    "scribd.com", "slideshare.net", "issuu.com", "calameo.com",
]

PRESS_RELEASE_DOMAINS = [
    "businesswire.com", "prnewswire.com", "globenewswire.com",
    "accesswire.com", "businesswire.fr", "actusnews.com",
    "newswire.ca", "cision.com", "lesechos.fr", "lefigaro.fr",
]

CDN_OR_ASSET_DOMAIN_PATTERNS = [
    r"akamaized\.net", r"cloudfront\.net", r"fastly\.net",
    r"storage\.googleapis\.com", r"blob\.core\.windows\.net",
    r"s3\.amazonaws\.com", r"cdn\.",
]

THIRD_PARTY_ARCHIVE_DOMAINS = [
    "annualreports.com", "wsj.com", "macrotrends.net",
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


class HalfYearReportScorer:

    def __init__(
        self,
        auto_download_threshold: float = 80.0,
        human_review_threshold: float = 60.0,
    ) -> None:
        self.auto_download_threshold = auto_download_threshold
        self.human_review_threshold = human_review_threshold

    def rank_candidates(
        self,
        request: HalfYearReportRequest,
        candidates: list[SearchCandidate],
    ) -> list[ScoredCandidate]:
        scored = [self._score(request=request, candidate=c) for c in candidates]
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored

    def _score(
        self,
        request: HalfYearReportRequest,
        candidate: SearchCandidate,
    ) -> ScoredCandidate:
        company = request.company
        fiscal_year = request.fiscal_year

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

        # --- Signaux positifs ---
        strong_kws = find_keywords(text_norm, STRONG_HALF_YEAR_KEYWORDS)
        if strong_kws:
            score += 35
            positive.append(f"mots-clés forts semestriel : {strong_kws[:3]}")

        period_kws = find_keywords(text_norm, HALF_YEAR_PERIOD_KEYWORDS)
        if period_kws:
            score += 20
            positive.append(f"période semestrielle détectée : {period_kws[:2]}")

        # Détection H1/H2 avec word boundary
        if f" h1 " in f" {text_norm} " or f" h2 " in f" {text_norm} ":
            score += 20
            positive.append("marqueur semestriel H1/H2 détecté")

        weak_kws = find_keywords(text_norm, WEAK_HALF_YEAR_KEYWORDS)
        if weak_kws and not strong_kws:
            score += 10
            positive.append(f"mots-clés faibles semestriel : {weak_kws[:3]}")

        # Année
        years_found = {m for m in re.findall(r"\b(20\d{2})\b", full_text)}
        target_years = {str(fiscal_year), str(fiscal_year - 1)}
        if years_found & target_years:
            score += 25
            positive.append(f"année trouvée : {years_found & target_years}")

        # Nom entreprise
        name_norm = normalize_text(company.name)
        if name_norm in text_norm:
            score += 20
            positive.append("nom de l'entreprise détecté")

        # Domaine officiel
        if company.official_domain and company.official_domain.lower() in doc_domain:
            score += 20
            positive.append(f"domaine officiel détecté : {company.official_domain}")

        # URL PDF
        if url_norm.endswith("pdf") or ".pdf" in url_norm:
            score += 10
            positive.append("URL PDF directe")

        # Nom de fichier
        fn_kws = find_keywords(filename_norm, STRONG_FILENAME_KEYWORDS)
        if fn_kws:
            score += 15
            positive.append(f"nom de fichier semestriel : {fn_kws[:2]}")

        # CDN
        if any(re.search(p, doc_domain) for p in CDN_OR_ASSET_DOMAIN_PATTERNS):
            score += 5
            positive.append("CDN / asset domain")

        # Archive tierce
        if any(d in doc_domain for d in THIRD_PARTY_ARCHIVE_DOMAINS):
            score += 3
            positive.append("archive tierce reconnue")

        # --- Pénalités ---
        annual_kws = find_keywords(text_norm, ANNUAL_REPORT_KEYWORDS)
        if annual_kws:
            score -= 35
            negative.append(f"rapport annuel détecté : {annual_kws[:2]}")

        press_kws = find_keywords(text_norm, PRESS_RELEASE_KEYWORDS)
        if press_kws:
            score -= 35
            negative.append(f"communiqué de presse : {press_kws[:2]}")

        pres_kws = find_keywords(text_norm, PRESENTATION_KEYWORDS)
        if pres_kws:
            score -= 30
            negative.append(f"présentation investisseurs : {pres_kws[:2]}")

        periodic_kws = find_keywords(text_norm, PERIODIC_KEYWORDS)
        if periodic_kws:
            score -= 20
            negative.append(f"rapport périodique trimestriel : {periodic_kws[:2]}")

        if any(d in doc_domain for d in PRESS_RELEASE_DOMAINS):
            score -= 30
            negative.append(f"domaine presse : {doc_domain}")

        if any(d in doc_domain for d in LOW_TRUST_DOMAINS):
            score -= 45
            negative.append(f"domaine faible confiance : {doc_domain}")

        fin_kws = find_keywords(text_norm, FINANCIAL_ONLY_KEYWORDS)
        if fin_kws:
            score -= 20
            negative.append(f"document exclusivement financier : {fin_kws[:2]}")

        score = max(0.0, min(100.0, score))

        # --- Classification ---
        document_class, decision = self._classify(
            score=score,
            strong_kws=strong_kws,
            period_kws=period_kws,
            annual_kws=annual_kws,
            press_kws=press_kws,
        )
        positive.append(f"classe documentaire : {document_class}")

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

    def _classify(
        self,
        score: float,
        strong_kws: list,
        period_kws: list,
        annual_kws: list,
        press_kws: list,
    ) -> tuple[str, str]:
        if press_kws and not strong_kws:
            document_class = "press_release_results"
            score = min(score, 35)
            return document_class, "reject"

        if annual_kws and not strong_kws and not period_kws:
            document_class = "annual_report"
            score = min(score, 60)
            decision = "human_review_required" if score >= self.human_review_threshold else "reject"
            return document_class, decision

        if strong_kws or period_kws:
            document_class = "standalone_half_year_report"
            if score >= self.auto_download_threshold:
                return document_class, "auto_download"
            if score >= self.human_review_threshold:
                return document_class, "human_review_required"
            return document_class, "reject"

        document_class = "unclassified_financial"
        if score >= self.auto_download_threshold:
            return document_class, "human_review_required"
        return document_class, "reject"

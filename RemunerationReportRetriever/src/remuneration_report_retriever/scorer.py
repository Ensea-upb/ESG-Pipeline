from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from .models import RemunerationReportRequest, SearchCandidate, ScoredCandidate
from .utils import (
    company_name_matches,
    extract_domain,
    extract_years,
    is_pdf_url,
    normalize_text,
    official_domain_matches,
)


# ============================================================
# 1. Mots-clés centraux : rapports de rémunération
# ============================================================

STRONG_REMUNERATION_KEYWORDS = [
    # Anglais
    "remuneration report",
    "directors remuneration report",
    "directors' remuneration report",
    "executive remuneration report",
    "compensation report",
    "executive compensation report",
    "pay report",
    "remuneration policy report",
    "directors pay report",
    "say on pay report",
    "remuneration committee report",
    "annual remuneration report",
    "executive pay report",
    "board remuneration report",
    "compensation and benefits report",
    "total compensation report",

    # Français
    "rapport de rémunération",
    "rapport sur les rémunérations",
    "rapport sur les remunerations",
    "rapport rémunération dirigeants",
    "rapport remuneration dirigeants",
    "politique de rémunération",
    "politique de remuneration",
    "rapport sur la politique de rémunération",
    "rapport sur la politique de remuneration",
    "rémunération des mandataires sociaux",
    "remuneration des mandataires sociaux",
    "rapport du comité des rémunérations",
    "rapport du comite des remunerations",
    "éléments de rémunération",
    "elements de remuneration",
]

REMUNERATION_DISCLOSURE_KEYWORDS = [
    # Anglais — mécanismes
    "long-term incentive plan",
    "long term incentive",
    "short-term incentive",
    "ltip",
    "stip",
    "long term incentive plan",
    "equity compensation",
    "share-based payment",
    "share based payment",
    "deferred compensation",
    "golden parachute",
    "clawback policy",
    "pay ratio",
    "ceo pay ratio",
    "median employee pay",

    # Français
    "plan d incitation à long terme",
    "plan d incitation a long terme",
    "rémunération variable",
    "remuneration variable",
    "rémunération fixe",
    "remuneration fixe",
    "intéressement long terme",
    "interessement long terme",
    "stock options",
    "actions de performance",
    "ratio de rémunération",
    "ratio de remuneration",
    "vote say on pay",
]

WEAK_REMUNERATION_KEYWORDS = [
    "remuneration",
    "rémunération",
    "remuneration",
    "compensation",
    "executive pay",
    "pay policy",
    "salary",
    "bonus",
    "incentive",
    "mandataires sociaux",
    "dirigeants",
    "directors pay",
    "board pay",
]

ANNUAL_REPORT_CONTEXT_KEYWORDS = [
    "annual report",
    "universal registration document",
    "document d'enregistrement universel",
    "document d enregistrement universel",
    "integrated report",
    "rapport annuel",
    "urd",
    "deu",
]

STRONG_FILENAME_KEYWORDS = [
    "remunerationreport",
    "remuneration-report",
    "remuneration_report",
    "compensationreport",
    "compensation-report",
    "compensation_report",
    "payreport",
    "pay-report",
    "pay_report",
    "directorsremunerationreport",
    "directors-remuneration-report",
    "executiveremunerationreport",
    "executive-remuneration-report",
    "rapportremuneration",
    "rapport-remuneration",
    "rapport_remuneration",
    "politiqueremuneration",
    "politique-remuneration",
    "remunerationpolicy",
    "remuneration-policy",
    "remuneration_policy",
    "sayonpay",
    "say-on-pay",
]


# ============================================================
# 2. Mots-clés d'exclusion ou de bruit
# ============================================================

FINANCIAL_ONLY_KEYWORDS = [
    "financial statements",
    "consolidated financial statements",
    "documents financiers",
    "financial results",
    "résultats financiers",
    "resultats financiers",
    "earnings",
    "annual financial report",
]

PRESENTATION_KEYWORDS = [
    "presentation",
    "powerpoint",
    "slides",
    "investor presentation",
    "results presentation",
    "webcast",
    "transcript",
]

PERIODIC_KEYWORDS = [
    "quarterly",
    "half year",
    "half-year",
    "first half",
    "interim",
    "semestriel",
    "premier semestre",
]

PRESS_RELEASE_KEYWORDS = [
    "press release",
    "communiqué",
    "communique",
    "now available",
    "availability of",
    "announces the availability",
    "publication of",
    "mise à disposition",
    "mise a disposition",
]

AGM_CONVOCATION_KEYWORDS = [
    "brochure d'avis de convocation",
    "avis de convocation",
    "convocation ag",
    "notice of annual general meeting",
    "notice of meeting",
    "proxy form",
    "formulaire de vote",
    "vote par correspondance",
]

LOW_TRUST_DOMAINS = [
    "scribd.com",
    "fr.scribd.com",
    "slideshare.net",
    "docplayer.fr",
    "docplayer.net",
]

THIRD_PARTY_ARCHIVE_DOMAINS = [
    "annualreports.com",
    "publicnow.com",
    "ddd.uab.cat",
    "bnains.org",
]

PRESS_RELEASE_DOMAINS = [
    "live.euronext.com",
    "globenewswire.com",
    "businesswire.com",
    "prnewswire.com",
    "actusnews.com",
    "eqs-news.com",
]

CDN_OR_ASSET_DOMAIN_PATTERNS = [
    "cdn.", ".cdn.", "cloudfront.net", "ctfassets.net",
    "prismic.io", "akamai", "azureedge.net",
]


# ============================================================
# 3. Classes documentaires
# ============================================================

AUTO_DOWNLOAD_ALLOWED_CLASSES = {
    "standalone_remuneration_report",
    "remuneration_disclosure",
    "annual_report_with_remuneration_section",
}

BLOCKED_AUTO_DOWNLOAD_CLASSES = {
    "financial_only_document",
    "presentation",
    "periodic_report",
    "press_release",
    "low_trust_copy",
    "unknown",
    "agm_convocation_document",
}


# ============================================================
# 4. Structures internes
# ============================================================

@dataclass
class CandidateFeatures:
    requested_year_found: bool
    years_found: set[int]
    company_name_found: bool
    strong_remuneration_keywords: list[str]
    remuneration_disclosure_keywords: list[str]
    weak_remuneration_keywords: list[str]
    annual_report_context_keywords: list[str]
    strong_filename_keywords: list[str]
    financial_only_keywords: list[str]
    agm_convocation_keywords: list[str]
    presentation_keywords: list[str]
    periodic_keywords: list[str]
    press_release_keywords: list[str]
    domain: str
    is_pdf: bool
    is_official_domain: bool
    is_asset_cdn: bool
    is_low_trust_domain: bool
    is_third_party_archive: bool
    is_press_release_domain: bool


# ============================================================
# 5. Fonctions utilitaires
# ============================================================

def find_keywords(text: str, keywords: list[str]) -> list[str]:
    text_norm = normalize_text(text)
    padded = f" {text_norm} "
    found = []
    for keyword in keywords:
        keyword_norm = normalize_text(keyword)
        if len(keyword_norm) <= 3:
            if f" {keyword_norm} " in padded:
                found.append(keyword)
        else:
            if keyword_norm in text_norm:
                found.append(keyword)
    return found


def compact(text: str) -> str:
    return normalize_text(text).replace(" ", "")


def url_path_and_query(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.path} {parsed.query}"


def domain_matches_any(domain: str, domains: list[str]) -> bool:
    domain = domain.lower().replace("www.", "")
    for ref in domains:
        ref = ref.lower().replace("www.", "")
        if domain == ref or domain.endswith("." + ref):
            return True
    return False


def domain_contains_any(domain: str, patterns: list[str]) -> bool:
    domain = domain.lower()
    return any(pattern in domain for pattern in patterns)


# ============================================================
# 6. Scorer principal
# ============================================================

class RemunerationReportScorer:
    """
    Scorer pour les rapports de rémunération des dirigeants.

    Distinctions clés :
    - Un rapport de rémunération décrit la politique et les éléments de
      rémunération des dirigeants (fixe, variable, LTI, stock-options...).
    - Il ne doit pas être confondu avec un avis de convocation d'AG
      ni avec un rapport financier pur.
    """

    def __init__(
        self,
        auto_download_threshold: float = 80.0,
        human_review_threshold: float = 60.0,
    ) -> None:
        self.auto_download_threshold = auto_download_threshold
        self.human_review_threshold = human_review_threshold

    def score_candidate(
        self,
        request: RemunerationReportRequest,
        candidate: SearchCandidate,
    ) -> ScoredCandidate:
        combined_text = " ".join([
            candidate.title or "",
            candidate.url or "",
            candidate.snippet or "",
        ])

        features = self.extract_features(
            request=request, candidate=candidate, combined_text=combined_text
        )
        candidate_class = self.classify_candidate(features)

        score = 0.0
        positive_signals: list[str] = []
        negative_signals: list[str] = []

        # A. Signaux positifs
        if features.requested_year_found:
            score += 25
            positive_signals.append(f"année trouvée : {request.fiscal_year}")
        elif features.years_found:
            score -= 15
            negative_signals.append(
                f"année demandée absente, années détectées : {sorted(features.years_found)}"
            )
        else:
            negative_signals.append("aucune année détectée")

        if features.strong_remuneration_keywords:
            score += 35
            positive_signals.append(
                f"mots-clés forts rémunération : {features.strong_remuneration_keywords}"
            )
        elif features.remuneration_disclosure_keywords:
            score += 35
            positive_signals.append(
                f"mots-clés divulgation rémunération : {features.remuneration_disclosure_keywords}"
            )
        elif features.weak_remuneration_keywords:
            score += 18
            positive_signals.append(
                f"mots-clés faibles rémunération : {features.weak_remuneration_keywords}"
            )
        else:
            score -= 25
            negative_signals.append("aucun signal rémunération fort")

        if features.company_name_found:
            score += 20
            positive_signals.append("nom de l'entreprise détecté")
        else:
            score -= 25
            negative_signals.append("nom de l'entreprise non détecté")

        if features.is_official_domain:
            score += 20
            positive_signals.append(f"domaine officiel détecté : {features.domain}")
        elif request.company.official_domain:
            negative_signals.append(f"domaine non officiel : {features.domain}")

        if features.is_pdf:
            score += 10
            positive_signals.append("URL PDF directe")
        else:
            score -= 8
            negative_signals.append("URL non PDF directe")

        if features.strong_filename_keywords and features.is_pdf:
            score += 15
            positive_signals.append(
                f"nom de fichier compatible rémunération : {features.strong_filename_keywords}"
            )

        if features.annual_report_context_keywords and (
            features.strong_remuneration_keywords
            or features.remuneration_disclosure_keywords
            or features.weak_remuneration_keywords
        ):
            score += 8
            positive_signals.append(
                f"rapport annuel/URD contenant signaux rémunération : {features.annual_report_context_keywords}"
            )

        if (
            features.is_asset_cdn and features.is_pdf
            and features.strong_filename_keywords and features.company_name_found
        ):
            score += 5
            positive_signals.append(f"CDN/asset host plausible : {features.domain}")

        if features.is_third_party_archive:
            score += 3
            positive_signals.append(f"archive ou agrégateur documentaire : {features.domain}")

        # B. Pénalités
        if features.financial_only_keywords and not (
            features.strong_remuneration_keywords
            or features.remuneration_disclosure_keywords
            or features.weak_remuneration_keywords
        ):
            score -= 45
            negative_signals.append(
                f"document financier sans signal rémunération fort : {features.financial_only_keywords}"
            )

        if features.agm_convocation_keywords:
            score -= 60
            negative_signals.append(
                f"avis de convocation / vote détecté : {features.agm_convocation_keywords}"
            )

        if candidate_class == "agm_convocation_document":
            score = min(score, 40)

        if features.presentation_keywords:
            score -= 40
            negative_signals.append(
                f"présentation ou support slides détecté : {features.presentation_keywords}"
            )

        if features.periodic_keywords:
            score -= 30
            negative_signals.append(
                f"document périodique non annuel détecté : {features.periodic_keywords}"
            )

        if features.press_release_keywords:
            score -= 35
            negative_signals.append(
                f"communiqué / avis de publication détecté : {features.press_release_keywords}"
            )

        if features.is_press_release_domain:
            score -= 30
            negative_signals.append(f"domaine typique de communiqué : {features.domain}")

        if features.is_low_trust_domain:
            score -= 45
            negative_signals.append(f"domaine de faible confiance : {features.domain}")

        # C. Plafonds de sécurité
        if candidate_class == "financial_only_document":
            score = min(score, 50)
        if candidate_class == "presentation":
            score = min(score, 50)
        if candidate_class == "periodic_report":
            score = min(score, 55)
        if candidate_class == "press_release":
            score = min(score, 55)
        if candidate_class == "low_trust_copy":
            score = min(score, 59)
        if candidate_class == "unknown":
            score = min(score, 59)

        # D. Score final
        score = max(0.0, min(100.0, score))

        decision = self._decision(
            score=score, is_pdf=features.is_pdf, candidate_class=candidate_class
        )

        if candidate_class in AUTO_DOWNLOAD_ALLOWED_CLASSES:
            positive_signals.append(f"classe documentaire : {candidate_class}")
        else:
            negative_signals.append(f"classe documentaire : {candidate_class}")

        return ScoredCandidate(
            title=candidate.title,
            url=candidate.url,
            snippet=candidate.snippet,
            source_name=candidate.source_name,
            score=score,
            decision=decision,
            positive_signals=positive_signals,
            negative_signals=negative_signals,
        )

    def extract_features(
        self,
        request: RemunerationReportRequest,
        candidate: SearchCandidate,
        combined_text: str,
    ) -> CandidateFeatures:
        url = candidate.url or ""
        domain = extract_domain(url)
        years_found = extract_years(combined_text)
        url_compact = compact(url_path_and_query(url))

        return CandidateFeatures(
            requested_year_found=request.fiscal_year in years_found,
            years_found=years_found,
            company_name_found=company_name_matches(request.company.name, combined_text),
            strong_remuneration_keywords=find_keywords(combined_text, STRONG_REMUNERATION_KEYWORDS),
            remuneration_disclosure_keywords=find_keywords(combined_text, REMUNERATION_DISCLOSURE_KEYWORDS),
            weak_remuneration_keywords=find_keywords(combined_text, WEAK_REMUNERATION_KEYWORDS),
            annual_report_context_keywords=find_keywords(combined_text, ANNUAL_REPORT_CONTEXT_KEYWORDS),
            strong_filename_keywords=[kw for kw in STRONG_FILENAME_KEYWORDS if kw in url_compact],
            financial_only_keywords=find_keywords(combined_text, FINANCIAL_ONLY_KEYWORDS),
            agm_convocation_keywords=find_keywords(combined_text, AGM_CONVOCATION_KEYWORDS),
            presentation_keywords=find_keywords(combined_text, PRESENTATION_KEYWORDS),
            periodic_keywords=find_keywords(combined_text, PERIODIC_KEYWORDS),
            press_release_keywords=find_keywords(combined_text, PRESS_RELEASE_KEYWORDS),
            domain=domain,
            is_pdf=is_pdf_url(url),
            is_official_domain=official_domain_matches(domain, request.company.official_domain),
            is_asset_cdn=domain_contains_any(domain, CDN_OR_ASSET_DOMAIN_PATTERNS),
            is_low_trust_domain=domain_matches_any(domain, LOW_TRUST_DOMAINS),
            is_third_party_archive=domain_matches_any(domain, THIRD_PARTY_ARCHIVE_DOMAINS),
            is_press_release_domain=domain_matches_any(domain, PRESS_RELEASE_DOMAINS),
        )

    def classify_candidate(self, features: CandidateFeatures) -> str:
        if features.is_low_trust_domain:
            return "low_trust_copy"
        if features.presentation_keywords:
            return "presentation"
        if features.press_release_keywords or features.is_press_release_domain:
            return "press_release"
        if features.periodic_keywords:
            return "periodic_report"
        if features.agm_convocation_keywords and not features.strong_remuneration_keywords:
            return "agm_convocation_document"
        if features.financial_only_keywords and not (
            features.strong_remuneration_keywords
            or features.remuneration_disclosure_keywords
            or features.weak_remuneration_keywords
        ):
            return "financial_only_document"
        if features.remuneration_disclosure_keywords:
            return "remuneration_disclosure"
        if features.strong_remuneration_keywords:
            return "standalone_remuneration_report"
        if features.annual_report_context_keywords and features.weak_remuneration_keywords:
            return "annual_report_with_remuneration_section"
        if not features.is_pdf and (
            features.strong_remuneration_keywords
            or features.remuneration_disclosure_keywords
            or features.weak_remuneration_keywords
        ):
            return "html_landing_page"
        return "unknown"

    def rank_candidates(
        self,
        request: RemunerationReportRequest,
        candidates: list[SearchCandidate],
    ) -> list[ScoredCandidate]:
        scored = [
            self.score_candidate(request=request, candidate=c) for c in candidates
        ]
        return sorted(scored, key=lambda c: c.score, reverse=True)

    def _decision(self, score: float, is_pdf: bool, candidate_class: str) -> str:
        if candidate_class in BLOCKED_AUTO_DOWNLOAD_CLASSES:
            if score >= self.human_review_threshold:
                return "human_review_required"
            return "reject"
        if candidate_class == "html_landing_page":
            if score >= self.auto_download_threshold:
                return "pdf_resolution_required"
            if score >= self.human_review_threshold:
                return "human_review_required"
            return "reject"
        if candidate_class in AUTO_DOWNLOAD_ALLOWED_CLASSES:
            if score >= self.auto_download_threshold and is_pdf:
                return "auto_download"
            if score >= self.auto_download_threshold and not is_pdf:
                return "pdf_resolution_required"
            if score >= self.human_review_threshold:
                return "human_review_required"
            return "reject"
        if score >= self.human_review_threshold:
            return "human_review_required"
        return "reject"

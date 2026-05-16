from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from .models import SustainabilityReportRequest, SearchCandidate, ScoredCandidate
from .utils import (
    company_name_matches,
    extract_domain,
    extract_years,
    is_pdf_url,
    normalize_text,
    official_domain_matches,
)


# ============================================================
# 1. Mots-clés centraux : rapports ESG / Sustainability / RSE
# ============================================================

STRONG_SUSTAINABILITY_KEYWORDS = [
    "sustainability report",
    "esg report",
    "environmental social governance report",
    "corporate responsibility report",
    "corporate social responsibility report",
    "csr report",
    "social and environmental responsibility report",
    "environmental responsibility report",
    "responsibility report",
    "sustainable development report",
    "positive impact report",

    "rapport rse",
    "rapport esg",
    "rapport de durabilité",
    "rapport de durabilite",
    "rapport développement durable",
    "rapport developpement durable",
    "rapport de responsabilité sociale",
    "rapport de responsabilite sociale",
    "rapport responsabilité sociale et environnementale",
    "rapport responsabilite sociale et environnementale",
]

CSRD_ESRS_KEYWORDS = [
    "sustainability statement",
    "csrd statement",
    "esrs statement",
    "csrd report",
    "esrs report",
    "non-financial statement",
    "non financial statement",
    "nonfinancial statement",
    "déclaration de performance extra-financière",
    "declaration de performance extra financiere",
    "dpef",
    "déclaration de durabilité",
    "declaration de durabilite",
]

WEAK_SUSTAINABILITY_KEYWORDS = [
    "sustainability",
    "sustainable",
    "esg",
    "csr",
    "rse",
    "csrd",
    "esrs",
    "climate",
    "environment",
    "environmental",
    "social responsibility",
    "responsible business",
    "durability",
    "durabilité",
    "durabilite",
    "développement durable",
    "developpement durable",
]

# Rapports annuels / URD : utiles si la durabilité y est intégrée,
# mais ce ne sont pas les signaux principaux du moteur.
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
    "sustainabilityreport",
    "sustainability-report",
    "sustainability_report",
    "esgreport",
    "esg-report",
    "esg_report",
    "csrreport",
    "csr-report",
    "csr_report",
    "corporateresponsibilityreport",
    "corporate-responsibility-report",
    "socialandenvironmentalresponsibilityreport",
    "social-environmental-responsibility-report",
    "responsibilityreport",
    "responsibility-report",
    "rapportrse",
    "rapport-rse",
    "rapport_rse",
    "rapportesg",
    "rapport-esg",
    "rapport_esg",
    "rapportdedurabilite",
    "rapport-de-durabilite",
    "dpef",
    "csrd",
    "esrs",
    "sustainabilitystatement",
    "sustainability-statement",
    "sustainability_statement",
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

GOVERNANCE_MEETING_KEYWORDS = [
    "brochure d'avis de convocation",
    "avis de convocation",
    "convocation ag",
    "assemblée générale",
    "assemblee generale",
    "general meeting",
    "annual general meeting",
    "agm",
    "proxy statement",
    "shareholder meeting",
    "notice of meeting",
]

PRESENTATION_KEYWORDS = [
    "presentation",
    "powerpoint",
    "slides",
    "investor presentation",
    "results presentation",
    "team presentation",
    "webcast",
    "transcript",
]

PERIODIC_KEYWORDS = [
    "quarterly",
    "q1",
    "q2",
    "q3",
    "q4",
    "half year",
    "half-year",
    "h1",
    "first half",
    "interim",
    "semestriel",
    "premier semestre",
    "t1",
    "t2",
    "t3",
    "t4",
    "quatrième trimestre",
    "quatrieme trimestre",
    "troisième trimestre",
    "troisieme trimestre",
    "résultats extra-financiers",
    "resultats extra financiers",
    "extra-financial results",
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

LOW_TRUST_DOMAINS = [
    "scribd.com",
    "fr.scribd.com",
    "slideshare.net",
    "docplayer.fr",
    "docplayer.net",
]

THIRD_PARTY_ARCHIVE_DOMAINS = [
    "annualreports.com",
    "sustainabilityreports.com",
    "cdp.net",
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
    "cdn.",
    ".cdn.",
    "cloudfront.net",
    "ctfassets.net",
    "prismic.io",
    "akamai",
    "azureedge.net",
]


# ============================================================
# 3. Classes documentaires
# ============================================================

AUTO_DOWNLOAD_ALLOWED_CLASSES = {
    "standalone_sustainability_report",
    "csrd_esrs_statement",
    "sustainability_statement",
    "annual_report_with_sustainability_content",
}

BLOCKED_AUTO_DOWNLOAD_CLASSES = {
    "financial_only_document",
    "presentation",
    "periodic_report",
    "press_release",
    "low_trust_copy",
    "unknown",
    "governance_meeting_document",
}


# ============================================================
# 4. Structures internes
# ============================================================

@dataclass
class CandidateFeatures:
    requested_year_found: bool
    years_found: set[int]

    company_name_found: bool

    strong_sustainability_keywords: list[str]
    csrd_esrs_keywords: list[str]
    weak_sustainability_keywords: list[str]
    annual_report_context_keywords: list[str]
    strong_filename_keywords: list[str]

    financial_only_keywords: list[str]
    presentation_keywords: list[str]
    periodic_keywords: list[str]
    press_release_keywords: list[str]
    governance_meeting_keywords: list[str]

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
        # Word-boundary padding for short tokens (q1, h1, t2 …) to avoid false
        # positives on URL fragments or compound words (e.g. "unique" matching "q").
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

class SustainabilityReportScorer:
    """
    Scorer généraliste pour les rapports ESG / Sustainability / RSE.

    Il ne valide pas définitivement un document.
    Il sert uniquement à décider quels candidats méritent d'être ingérés.
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
        request: SustainabilityReportRequest,
        candidate: SearchCandidate,
    ) -> ScoredCandidate:
        combined_text = " ".join(
            [
                candidate.title or "",
                candidate.url or "",
                candidate.snippet or "",
            ]
        )

        features = self.extract_features(
            request=request,
            candidate=candidate,
            combined_text=combined_text,
        )

        candidate_class = self.classify_candidate(features)

        score = 0.0
        positive_signals: list[str] = []
        negative_signals: list[str] = []

        # ----------------------------------------------------
        # A. Signaux positifs
        # ----------------------------------------------------

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

        if features.strong_sustainability_keywords:
            score += 35
            positive_signals.append(
                f"mots-clés forts durabilité : {features.strong_sustainability_keywords}"
            )
        elif features.csrd_esrs_keywords:
            score += 35
            positive_signals.append(
                f"mots-clés CSRD/ESRS/DPEF : {features.csrd_esrs_keywords}"
            )
        elif features.weak_sustainability_keywords:
            score += 18
            positive_signals.append(
                f"mots-clés faibles durabilité : {features.weak_sustainability_keywords}"
            )
        else:
            score -= 25
            negative_signals.append("aucun signal ESG/RSE/durabilité fort")

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
                f"nom de fichier compatible durabilité : {features.strong_filename_keywords}"
            )

        if features.annual_report_context_keywords and (
            features.strong_sustainability_keywords
            or features.csrd_esrs_keywords
            or features.weak_sustainability_keywords
        ):
            score += 8
            positive_signals.append(
                f"rapport annuel/URD contenant signaux durabilité : {features.annual_report_context_keywords}"
            )

        if (
            features.is_asset_cdn
            and features.is_pdf
            and features.strong_filename_keywords
            and features.company_name_found
        ):
            score += 5
            positive_signals.append(
                f"CDN/asset host plausible : {features.domain}"
            )

        if features.is_third_party_archive:
            score += 3
            positive_signals.append(
                f"archive ou agrégateur documentaire : {features.domain}"
            )

        # ----------------------------------------------------
        # B. Pénalités
        # ----------------------------------------------------

        if features.financial_only_keywords and not (
            features.strong_sustainability_keywords
            or features.csrd_esrs_keywords
            or features.weak_sustainability_keywords
        ):
            score -= 45
            negative_signals.append(
                f"document financier sans signal ESG fort : {features.financial_only_keywords}"
            )

        if features.presentation_keywords:
            score -= 40
            negative_signals.append(
                f"présentation ou support slides détecté : {features.presentation_keywords}"
            )

        if features.governance_meeting_keywords:
            score -= 60
            negative_signals.append(
                f"document de gouvernance / assemblée détecté : {features.governance_meeting_keywords}"
            )

        if candidate_class == "governance_meeting_document":
            score = min(score, 40)

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
            negative_signals.append(
                f"domaine typique de communiqué financier : {features.domain}"
            )

        if features.is_low_trust_domain:
            score -= 45
            negative_signals.append(
                f"domaine de faible confiance : {features.domain}"
            )

        # ----------------------------------------------------
        # C. Plafonds de sécurité par classe
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # D. Score final et décision
        # ----------------------------------------------------

        score = max(0.0, min(100.0, score))

        decision = self._decision(
            score=score,
            is_pdf=features.is_pdf,
            candidate_class=candidate_class,
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
        request: SustainabilityReportRequest,
        candidate: SearchCandidate,
        combined_text: str,
    ) -> CandidateFeatures:
        url = candidate.url or ""
        domain = extract_domain(url)
        years_found = extract_years(combined_text)

        url_text = url_path_and_query(url)
        url_compact = compact(url_text)

        return CandidateFeatures(
            requested_year_found=request.fiscal_year in years_found,
            years_found=years_found,

            company_name_found=company_name_matches(
                request.company.name,
                combined_text,
            ),

            strong_sustainability_keywords=find_keywords(
                combined_text,
                STRONG_SUSTAINABILITY_KEYWORDS,
            ),
            csrd_esrs_keywords=find_keywords(
                combined_text,
                CSRD_ESRS_KEYWORDS,
            ),
            weak_sustainability_keywords=find_keywords(
                combined_text,
                WEAK_SUSTAINABILITY_KEYWORDS,
            ),
            annual_report_context_keywords=find_keywords(
                combined_text,
                ANNUAL_REPORT_CONTEXT_KEYWORDS,
            ),
            strong_filename_keywords=[
                keyword
                for keyword in STRONG_FILENAME_KEYWORDS
                if keyword in url_compact
            ],

            financial_only_keywords=find_keywords(
                combined_text,
                FINANCIAL_ONLY_KEYWORDS,
            ),
            presentation_keywords=find_keywords(
                combined_text,
                PRESENTATION_KEYWORDS,
            ),
            periodic_keywords=find_keywords(
                combined_text,
                PERIODIC_KEYWORDS,
            ),
            press_release_keywords=find_keywords(
                combined_text,
                PRESS_RELEASE_KEYWORDS,
            ),

            domain=domain,
            is_pdf=is_pdf_url(url),
            is_official_domain=official_domain_matches(
                domain,
                request.company.official_domain,
            ),
            is_asset_cdn=domain_contains_any(
                domain,
                CDN_OR_ASSET_DOMAIN_PATTERNS,
            ),
            is_low_trust_domain=domain_matches_any(
                domain,
                LOW_TRUST_DOMAINS,
            ),
            is_third_party_archive=domain_matches_any(
                domain,
                THIRD_PARTY_ARCHIVE_DOMAINS,
            ),
            is_press_release_domain=domain_matches_any(
                domain,
                PRESS_RELEASE_DOMAINS,
            ),
            governance_meeting_keywords=find_keywords(
                combined_text,
                GOVERNANCE_MEETING_KEYWORDS,
            ),
        )

    def classify_candidate(self, features: CandidateFeatures) -> str:
        """
        Classe documentaire du candidat.
        """

        if features.is_low_trust_domain:
            return "low_trust_copy"

        if features.presentation_keywords:
            return "presentation"

        if features.press_release_keywords or features.is_press_release_domain:
            return "press_release"

        if features.periodic_keywords:
            return "periodic_report"

        if features.financial_only_keywords and not (
            features.strong_sustainability_keywords
            or features.csrd_esrs_keywords
            or features.weak_sustainability_keywords
        ):
            return "financial_only_document"

        if features.csrd_esrs_keywords:
            return "csrd_esrs_statement"

        if features.strong_sustainability_keywords:
            return "standalone_sustainability_report"

        if (
            features.annual_report_context_keywords
            and features.weak_sustainability_keywords
        ):
            return "annual_report_with_sustainability_content"

        if not features.is_pdf and (
            features.strong_sustainability_keywords
            or features.csrd_esrs_keywords
            or features.weak_sustainability_keywords
        ):
            return "html_landing_page"
        
        if features.governance_meeting_keywords:
            return "governance_meeting_document"

        return "unknown"

    def rank_candidates(
        self,
        request: SustainabilityReportRequest,
        candidates: list[SearchCandidate],
    ) -> list[ScoredCandidate]:
        scored_candidates = [
            self.score_candidate(request=request, candidate=candidate)
            for candidate in candidates
        ]

        return sorted(
            scored_candidates,
            key=lambda candidate: candidate.score,
            reverse=True,
        )

    def _decision(
        self,
        score: float,
        is_pdf: bool,
        candidate_class: str,
    ) -> str:
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
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from .models import AnnualReportRequest, SearchCandidate, ScoredCandidate
from .utils import (
    company_name_matches,
    extract_domain,
    extract_years,
    is_pdf_url,
    normalize_text,
    official_domain_matches,
)


# ============================================================
# 1. Vocabulaires documentaires généraux
# ============================================================

STRONG_ANNUAL_REPORT_KEYWORDS = [
    "annual report",
    "annual financial report",
    "rapport annuel",
    "universal registration document",
    "document d'enregistrement universel",
    "document d enregistrement universel",
    "integrated report",
    "rapport intégré",
    "rapport integre",
]

WEAK_ANNUAL_REPORT_KEYWORDS = [
    "urd",
    "deu",
]

GROUP_LEVEL_KEYWORDS = [
    "group",
    "groupe",
    "consolidated",
    "consolide",
    "consolidé",
    "annual financial report",
    "rapport financier annuel",
    "universal registration document",
    "document d'enregistrement universel",
    "document d enregistrement universel",
]

STRONG_PDF_FILENAME_KEYWORDS = [
    "universalregistrationdocument",
    "universal-registration-document",
    "universal_registration_document",
    "documentdenregistrementuniversel",
    "document-d-enregistrement-universel",
    "document_d_enregistrement_universel",
    "annualreport",
    "annual-report",
    "annual_report",
    "annualfinancialreport",
    "annual-financial-report",
    "annual_financial_report",
    "integratedreport",
    "integrated-report",
    "integrated_report",
    "rapportannuel",
    "rapport-annuel",
    "rapport_annuel",
    "urd",
    "deu",
]


# ============================================================
# 2. Vocabulaires d'exclusion documentaire
# ============================================================

AVAILABILITY_NOTICE_KEYWORDS = [
    "availability of the",
    "availability of",
    "announces the availability",
    "announces the publication",
    "now available",
    "is now available",
    "available online",
    "available on",
    "available at",
    "has filed",
    "filed with",
    "registration document now",
    "urd now available",
    "document now available",
    "release of the english version",
    "release of the french version",
    "publication of the english version",
    "publication of the french version",
    "avis de mise à disposition",
    "avis de mise a disposition",
    "mise à disposition",
    "mise a disposition",
    "disponibilité",
    "disponibilite",
]

AMENDMENT_KEYWORDS = [
    "amendment",
    "amended",
    "1st amendment",
    "2nd amendment",
    "3rd amendment",
    "first amendment",
    "second amendment",
    "third amendment",
    "supplement",
    "supplementary",
    "amendement",
    "actualisation",
    "mise à jour",
    "mise a jour",
]

INTERIM_OR_PERIODIC_KEYWORDS = [
    "quarterly",
    "q1",
    "q2",
    "q3",
    "q4",
    "half year",
    "half-year",
    "h1",
    "interim report",
    "first half",
    "first half of the year",
    "premier semestre",
    "résultats semestriels",
    "resultats semestriels",
    "semestriel",
    "semestrielle",
    "half-year results",
    "half year results",
]

COMMUNICATION_KEYWORDS = [
    "press release",
    "communiqué",
    "communique",
    "webcast",
    "transcript",
    "factsheet",
    "results presentation",
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

SUBSIDIARY_OR_PRODUCT_CONTEXT_KEYWORDS = [
    "issuer",
    "other legal",
    "other-legal",
    "warrant",
    "warrants",
    "structured products",
    "produits de bourse",
    "derivative",
    "derivatives",
    "subsidiary",
    "filiale",
    "vehicle",
    "special purpose vehicle",
    "spv",
    "legal entity",
    "entity report",
]


# ============================================================
# 3. Domaines et patterns généraux
# ============================================================

LOW_TRUST_DOMAINS = [
    "scribd.com",
    "fr.scribd.com",
    "slideshare.net",
    "docplayer.fr",
    "docplayer.net",
]

SECONDARY_BUT_USEFUL_DOMAINS = [
    "annualreports.com",
]

PRESS_RELEASE_DOMAINS = [
    "live.euronext.com",
    "globenewswire.com",
    "businesswire.com",
    "prnewswire.com",
    "actusnews.com",
    "eqs-news.com",
]

PRESS_RELEASE_URL_PATTERNS = [
    "company_press_releases",
    "company-press-releases",
    "press_release",
    "press-release",
    "pressreleases",
    "press-releases",
    "communique",
    "communiques",
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
# 4. Classes documentaires reconnues
# ============================================================

AUTO_DOWNLOAD_ALLOWED_CLASSES = {
    "main_annual_report",
    "universal_registration_document",
    "annual_financial_report",
    "integrated_report",
}

BLOCKED_AUTO_DOWNLOAD_CLASSES = {
    "availability_notice",
    "amendment_or_supplement",
    "interim_or_quarterly_report",
    "press_release",
    "governance_meeting_document",
    "subsidiary_or_entity_report",
    "third_party_copy",
    "unknown",
}


# ============================================================
# 5. Structures internes
# ============================================================

@dataclass
class CandidateFeatures:
    requested_year_found: bool
    other_years_found: bool
    years_found: set[int]

    company_name_found: bool

    strong_annual_keywords: list[str]
    weak_annual_keywords: list[str]
    group_level_keywords: list[str]
    strong_filename_keywords: list[str]

    availability_notice_keywords: list[str]
    amendment_keywords: list[str]
    interim_keywords: list[str]
    communication_keywords: list[str]
    governance_meeting_keywords: list[str]
    subsidiary_or_product_keywords: list[str]

    domain: str
    is_pdf: bool
    is_official_domain: bool
    is_asset_cdn: bool
    is_low_trust_domain: bool
    is_secondary_source: bool
    is_press_release_domain: bool
    has_press_release_url_pattern: bool


# ============================================================
# 6. Fonctions utilitaires
# ============================================================

def find_keywords(text: str, keywords: list[str]) -> list[str]:
    text_norm = normalize_text(text)
    found = []

    for keyword in keywords:
        keyword_norm = normalize_text(keyword)
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


def url_contains_any(url: str, patterns: list[str]) -> bool:
    url = url.lower()
    return any(pattern in url for pattern in patterns)


# ============================================================
# 7. Scorer principal
# ============================================================

class AnnualReportScorer:
    """
    Scorer généraliste du moteur AnnualReportRetriever.

    Logique :
    1. Extraire les signaux du candidat.
    2. Classifier le type de candidat.
    3. Calculer un score.
    4. Appliquer des plafonds de sécurité.
    5. Décider à la fin.
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
        request: AnnualReportRequest,
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
        # A. Signaux positifs fondamentaux
        # ----------------------------------------------------

        if features.requested_year_found:
            score += 30
            positive_signals.append(f"année fiscale trouvée : {request.fiscal_year}")
        elif features.years_found:
            score -= 35
            negative_signals.append(
                f"année demandée absente, années détectées : {sorted(features.years_found)}"
            )
        else:
            score -= 5
            negative_signals.append("aucune année détectée")

        if features.strong_annual_keywords:
            score += 30
            positive_signals.append(
                f"mots-clés forts rapport annuel : {features.strong_annual_keywords}"
            )
        elif features.weak_annual_keywords:
            score += 15
            positive_signals.append(
                f"mots-clés faibles rapport annuel : {features.weak_annual_keywords}"
            )
        else:
            score -= 20
            negative_signals.append("aucun mot-clé de rapport annuel détecté")

        if features.company_name_found:
            score += 20
            positive_signals.append("nom de l'entreprise détecté")
        else:
            score -= 30
            negative_signals.append("nom de l'entreprise non détecté")

        if features.is_official_domain:
            score += 20
            positive_signals.append(f"domaine officiel détecté : {features.domain}")
        elif request.company.official_domain:
            negative_signals.append(f"domaine non officiel : {features.domain}")

        if features.is_pdf:
            score += 12
            positive_signals.append("URL PDF directe")
        else:
            score -= 8
            negative_signals.append("URL non PDF directe")

        if features.strong_filename_keywords and features.is_pdf:
            score += 15
            positive_signals.append(
                f"nom de fichier PDF compatible : {features.strong_filename_keywords}"
            )

        if features.group_level_keywords:
            score += 8
            positive_signals.append(
                f"signaux de périmètre groupe : {features.group_level_keywords}"
            )

        if (
            features.is_asset_cdn
            and features.is_pdf
            and features.strong_filename_keywords
            and features.company_name_found
        ):
            score += 5
            positive_signals.append(
                f"CDN/asset host plausible pour PDF officiel : {features.domain}"
            )

        if features.is_secondary_source:
            score += 5
            positive_signals.append(
                f"source secondaire spécialisée : {features.domain}"
            )

        # ----------------------------------------------------
        # B. Pénalités générales
        # ----------------------------------------------------

        if features.availability_notice_keywords:
            score -= 50
            negative_signals.append(
                f"avis de disponibilité détecté : {features.availability_notice_keywords}"
            )

        if features.amendment_keywords:
            score -= 45
            negative_signals.append(
                f"amendement / supplément détecté : {features.amendment_keywords}"
            )

        if features.interim_keywords:
            score -= 45
            negative_signals.append(
                f"document périodique non annuel détecté : {features.interim_keywords}"
            )

        if features.communication_keywords:
            score -= min(25, 8 * len(features.communication_keywords))
            negative_signals.append(
                f"signaux de communication détectés : {features.communication_keywords}"
            )

        if features.governance_meeting_keywords:
            score -= 60
            negative_signals.append(
                f"document de gouvernance / assemblée détecté : {features.governance_meeting_keywords}"
            )

        if candidate_class == "governance_meeting_document":
            score = min(score, 40)

        if features.is_press_release_domain:
            score -= 35
            negative_signals.append(
                f"domaine typique de communiqué financier : {features.domain}"
            )

        if features.has_press_release_url_pattern:
            score -= 35
            negative_signals.append("URL typique de communiqué de presse")

        if features.is_low_trust_domain:
            score -= 45
            negative_signals.append(
                f"domaine de faible confiance : {features.domain}"
            )

        if features.subsidiary_or_product_keywords:
            score -= 35
            negative_signals.append(
                "contexte filiale / produit / émetteur spécifique : "
                f"{features.subsidiary_or_product_keywords}"
            )

        # ----------------------------------------------------
        # C. Plafonds de sécurité par classe
        # ----------------------------------------------------

        if not features.requested_year_found:
            score = min(score, 50)

        if not features.company_name_found:
            score = min(score, 55)

        if candidate_class == "availability_notice":
            score = min(score, 55)

        if candidate_class == "amendment_or_supplement":
            score = min(score, 59)

        if candidate_class == "interim_or_quarterly_report":
            score = min(score, 50)

        if candidate_class == "press_release":
            score = min(score, 55)

        if candidate_class == "subsidiary_or_entity_report":
            score = min(score, 59)

        if candidate_class == "third_party_copy":
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
        request: AnnualReportRequest,
        candidate: SearchCandidate,
        combined_text: str,
    ) -> CandidateFeatures:
        url = candidate.url or ""
        title = candidate.title or ""
        snippet = candidate.snippet or ""

        domain = extract_domain(url)
        years_found = extract_years(combined_text)
        is_pdf = is_pdf_url(url)

        url_text = url_path_and_query(url)
        url_compact = compact(url_text)

        return CandidateFeatures(
            requested_year_found=request.fiscal_year in years_found,
            other_years_found=bool(years_found - {request.fiscal_year}),
            years_found=years_found,

            company_name_found=company_name_matches(
                request.company.name,
                combined_text,
            ),

            strong_annual_keywords=find_keywords(
                combined_text,
                STRONG_ANNUAL_REPORT_KEYWORDS,
            ),
            weak_annual_keywords=find_keywords(
                combined_text,
                WEAK_ANNUAL_REPORT_KEYWORDS,
            ),
            group_level_keywords=find_keywords(
                combined_text,
                GROUP_LEVEL_KEYWORDS,
            ),
            strong_filename_keywords=[
                keyword
                for keyword in STRONG_PDF_FILENAME_KEYWORDS
                if keyword in url_compact
            ],

            availability_notice_keywords=find_keywords(
                " ".join([title, snippet, url]),
                AVAILABILITY_NOTICE_KEYWORDS,
            ),
            amendment_keywords=find_keywords(
                combined_text,
                AMENDMENT_KEYWORDS,
            ),
            interim_keywords=find_keywords(
                combined_text,
                INTERIM_OR_PERIODIC_KEYWORDS,
            ),
            communication_keywords=find_keywords(
                combined_text,
                COMMUNICATION_KEYWORDS,
            ),
            governance_meeting_keywords=find_keywords(
                combined_text,
                GOVERNANCE_MEETING_KEYWORDS,
            ),
            subsidiary_or_product_keywords=find_keywords(
                combined_text,
                SUBSIDIARY_OR_PRODUCT_CONTEXT_KEYWORDS,
            ),

            domain=domain,
            is_pdf=is_pdf,
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
            is_secondary_source=domain_matches_any(
                domain,
                SECONDARY_BUT_USEFUL_DOMAINS,
            ),
            is_press_release_domain=domain_matches_any(
                domain,
                PRESS_RELEASE_DOMAINS,
            ),
            has_press_release_url_pattern=url_contains_any(
                url,
                PRESS_RELEASE_URL_PATTERNS,
            ),
        )

    def classify_candidate(self, features: CandidateFeatures) -> str:
        """
        Classe le candidat dans une catégorie documentaire générale.
        """

        if features.availability_notice_keywords:
            return "availability_notice"

        if features.amendment_keywords:
            return "amendment_or_supplement"

        if features.interim_keywords:
            return "interim_or_quarterly_report"

        if features.governance_meeting_keywords:
            return "governance_meeting_document"

        if features.is_press_release_domain or features.has_press_release_url_pattern:
            return "press_release"

        if features.is_low_trust_domain:
            return "third_party_copy"

        if (
            features.subsidiary_or_product_keywords
            and not features.group_level_keywords
        ):
            return "subsidiary_or_entity_report"

        if not features.is_pdf and (
            features.strong_annual_keywords or features.weak_annual_keywords
        ):
            return "html_landing_page"

        strong_text = " ".join(features.strong_annual_keywords).lower()

        if "universal registration document" in strong_text:
            return "universal_registration_document"

        if "document d'enregistrement universel" in strong_text:
            return "universal_registration_document"

        if "document d enregistrement universel" in strong_text:
            return "universal_registration_document"

        if "annual financial report" in strong_text:
            return "annual_financial_report"

        if "integrated report" in strong_text or "rapport integre" in strong_text:
            return "integrated_report"

        if features.strong_annual_keywords:
            return "main_annual_report"

        return "unknown"

    def rank_candidates(
        self,
        request: AnnualReportRequest,
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
        """
        Décision finale.

        Un score élevé ne suffit pas.
        La classe documentaire doit aussi autoriser l'auto-download.
        """

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
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from .models import VigilancePlanRequest, SearchCandidate, ScoredCandidate
from .utils import (
    company_name_matches,
    extract_domain,
    extract_years,
    is_pdf_url,
    normalize_text,
    official_domain_matches,
)


# ============================================================
# 1. Mots-clés centraux : plans de vigilance / devoir de vigilance
# ============================================================

STRONG_VIGILANCE_KEYWORDS = [
    # Français — loi du 27 mars 2017
    "plan de vigilance",
    "devoir de vigilance",
    "rapport de vigilance",
    "plan vigilance",
    "loi de vigilance",
    "rapport sur le plan de vigilance",
    "vigilance raisonnée",
    "diligence raisonnée droits humains",
    "diligence raisonnable droits humains",
    "rapport diligence raisonnée",
    "rapport droits humains chaine d approvisionnement",
    "rapport droits humains chaîne d approvisionnement",

    # Anglais — Modern Slavery
    "modern slavery statement",
    "modern slavery act",
    "modern slavery report",
    "anti-slavery statement",
    "anti slavery statement",
    "forced labour report",
    "forced labor report",
    "forced labour statement",
    "human trafficking statement",

    # Anglais — Due Diligence
    "human rights due diligence report",
    "human rights due diligence statement",
    "duty of vigilance report",
    "duty of vigilance plan",
    "vigilance plan",
    "supply chain transparency report",
    "supply chain human rights report",
    "supply chain due diligence",
    "human rights report",
    "responsible sourcing report",
]

VIGILANCE_DISCLOSURE_KEYWORDS = [
    # Référentiels et mécanismes
    "un guiding principles",
    "ungp",
    "oecd guidelines",
    "ocde guidelines",
    "national action plan on business and human rights",
    "plan d action national entreprises droits humains",
    "csddd",
    "corporate sustainability due diligence",
    "child labour",
    "travail des enfants",
    "travail forcé",
    "forced labour",
    "conflict minerals",
    "minerais de conflit",
    "responsible minerals",
    "responsible minerals initiative",
    "supplier code of conduct",
    "code conduite fournisseurs",
    "audit fournisseurs",
    "supplier audit",
    "grievance mechanism",
    "mécanisme d alerte",
    "mecanisme d alerte",
]

WEAK_VIGILANCE_KEYWORDS = [
    "vigilance",
    "human rights",
    "droits humains",
    "supply chain",
    "chaine d approvisionnement",
    "chaîne d approvisionnement",
    "due diligence",
    "diligence raisonnée",
    "diligence raisonnable",
    "modern slavery",
    "esclavage moderne",
    "responsible sourcing",
    "approvisionnement responsable",
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
    "plandevigilance",
    "plan-de-vigilance",
    "plan_de_vigilance",
    "vigilanceplan",
    "vigilance-plan",
    "vigilance_plan",
    "devoirdevigilance",
    "devoir-de-vigilance",
    "devoir_de_vigilance",
    "modernslavery",
    "modern-slavery",
    "modern_slavery",
    "modernslaverystatement",
    "modern-slavery-statement",
    "humanrights",
    "human-rights",
    "human_rights",
    "humanrightsduediligence",
    "human-rights-due-diligence",
    "duediligence",
    "due-diligence",
    "due_diligence",
    "forcedlabour",
    "forced-labour",
    "forcedlabor",
    "supplychaintransparency",
    "supply-chain-transparency",
    "responsiblesourcing",
    "responsible-sourcing",
    "vigilance",
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
    "modernslaveryscrutiny.org",
    "modernslaveryregistry.org",
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
    "standalone_vigilance_plan",
    "vigilance_disclosure",
    "annual_report_with_vigilance_section",
}

BLOCKED_AUTO_DOWNLOAD_CLASSES = {
    "financial_only_document",
    "presentation",
    "periodic_report",
    "press_release",
    "low_trust_copy",
    "unknown",
}


# ============================================================
# 4. Structures internes
# ============================================================

@dataclass
class CandidateFeatures:
    requested_year_found: bool
    years_found: set[int]
    company_name_found: bool
    strong_vigilance_keywords: list[str]
    vigilance_disclosure_keywords: list[str]
    weak_vigilance_keywords: list[str]
    annual_report_context_keywords: list[str]
    strong_filename_keywords: list[str]
    financial_only_keywords: list[str]
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

class VigilancePlanScorer:
    """
    Scorer pour les plans de vigilance et rapports de devoir de vigilance.

    Couvre :
    - Plan de vigilance (loi française du 27 mars 2017) ;
    - Modern Slavery Statement (UK Modern Slavery Act 2015, Australie) ;
    - Human Rights Due Diligence (OCDE, CSDDD) ;
    - Supply Chain Transparency.

    Note : les tiers-registres spécialisés (modernslaveryregistry.org) sont
    traités comme des agrégateurs documentaires (+3 pts).
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
        request: VigilancePlanRequest,
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

        if features.strong_vigilance_keywords:
            score += 35
            positive_signals.append(
                f"mots-clés forts vigilance : {features.strong_vigilance_keywords}"
            )
        elif features.vigilance_disclosure_keywords:
            score += 35
            positive_signals.append(
                f"mots-clés divulgation vigilance : {features.vigilance_disclosure_keywords}"
            )
        elif features.weak_vigilance_keywords:
            score += 18
            positive_signals.append(
                f"mots-clés faibles vigilance : {features.weak_vigilance_keywords}"
            )
        else:
            score -= 25
            negative_signals.append("aucun signal vigilance fort")

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
                f"nom de fichier compatible vigilance : {features.strong_filename_keywords}"
            )

        if features.annual_report_context_keywords and (
            features.strong_vigilance_keywords
            or features.vigilance_disclosure_keywords
            or features.weak_vigilance_keywords
        ):
            score += 8
            positive_signals.append(
                f"rapport annuel/URD contenant signaux vigilance : {features.annual_report_context_keywords}"
            )

        if (
            features.is_asset_cdn and features.is_pdf
            and features.strong_filename_keywords and features.company_name_found
        ):
            score += 5
            positive_signals.append(f"CDN/asset host plausible : {features.domain}")

        if features.is_third_party_archive:
            score += 3
            positive_signals.append(f"archive ou registre spécialisé : {features.domain}")

        # B. Pénalités
        if features.financial_only_keywords and not (
            features.strong_vigilance_keywords
            or features.vigilance_disclosure_keywords
            or features.weak_vigilance_keywords
        ):
            score -= 45
            negative_signals.append(
                f"document financier sans signal vigilance fort : {features.financial_only_keywords}"
            )

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
        request: VigilancePlanRequest,
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
            strong_vigilance_keywords=find_keywords(combined_text, STRONG_VIGILANCE_KEYWORDS),
            vigilance_disclosure_keywords=find_keywords(combined_text, VIGILANCE_DISCLOSURE_KEYWORDS),
            weak_vigilance_keywords=find_keywords(combined_text, WEAK_VIGILANCE_KEYWORDS),
            annual_report_context_keywords=find_keywords(combined_text, ANNUAL_REPORT_CONTEXT_KEYWORDS),
            strong_filename_keywords=[kw for kw in STRONG_FILENAME_KEYWORDS if kw in url_compact],
            financial_only_keywords=find_keywords(combined_text, FINANCIAL_ONLY_KEYWORDS),
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
        if features.financial_only_keywords and not (
            features.strong_vigilance_keywords
            or features.vigilance_disclosure_keywords
            or features.weak_vigilance_keywords
        ):
            return "financial_only_document"
        if features.vigilance_disclosure_keywords:
            return "vigilance_disclosure"
        if features.strong_vigilance_keywords:
            return "standalone_vigilance_plan"
        if features.annual_report_context_keywords and features.weak_vigilance_keywords:
            return "annual_report_with_vigilance_section"
        if not features.is_pdf and (
            features.strong_vigilance_keywords
            or features.vigilance_disclosure_keywords
            or features.weak_vigilance_keywords
        ):
            return "html_landing_page"
        return "unknown"

    def rank_candidates(
        self,
        request: VigilancePlanRequest,
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

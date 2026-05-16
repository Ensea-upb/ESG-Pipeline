from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Company:
    """
    Représente l'entreprise cible.

    Exemple :
        Company(
            name="LVMH",
            official_domain="lvmh.com",
            ticker="MC",
            isin="FR0000121014",
            jurisdiction="France"
        )
    """

    name: str
    official_domain: Optional[str] = None
    ticker: Optional[str] = None
    isin: Optional[str] = None
    jurisdiction: Optional[str] = None


@dataclass
class SustainabilityReportRequest:
    """
    Représente la demande documentaire.

    Ici, l'année peut désigner soit :
    - l'année de publication ;
    - soit l'exercice couvert.

    Pour l'instant, on garde fiscal_year par cohérence avec le premier moteur.
    La distinction publication_year / reporting_year sera traitée plus tard.
    """

    company: Company
    fiscal_year: int


@dataclass
class SearchCandidate:
    """
    Représente un lien candidat trouvé par la recherche web.

    À ce stade, ce lien n'est pas encore validé.
    Il peut être :
    - un vrai rapport ESG / Sustainability ;
    - un rapport annuel contenant une section durabilité ;
    - une page HTML ;
    - un communiqué ;
    - un document non pertinent.
    """

    title: str
    url: str
    snippet: str = ""
    source_name: str = "unknown"


@dataclass
class ScoredCandidate:
    """
    Représente un candidat après scoring.

    Le score sert uniquement à décider si le candidat mérite d'être téléchargé
    dans le dossier d'ingestion.

    Il ne valide pas définitivement le document.
    """

    title: str
    url: str
    snippet: str = ""
    source_name: str = "unknown"

    score: float = 0.0
    decision: str = "not_scored"

    positive_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)


@dataclass
class DownloadResult:
    """
    Résultat final d'une opération d'ingestion.

    Ce résultat résume :
    - combien de candidats ont été trouvés ;
    - combien ont été téléchargés ;
    - combien ont échoué ;
    - combien ont été ignorés.
    """

    status: str
    message: str

    company_name: str
    fiscal_year: int

    downloaded_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0

    downloaded: list[dict] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
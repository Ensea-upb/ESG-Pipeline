from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Company:
    """
    Représente l'entreprise pour laquelle on veut récupérer le rapport annuel.

    Exemple :
        Company(
            name="TotalEnergies",
            official_domain="totalenergies.com",
            ticker="TTE",
            isin="FR0000120271"
        )
    """

    name: str
    official_domain: Optional[str] = None
    ticker: Optional[str] = None
    isin: Optional[str] = None
    jurisdiction: Optional[str] = None


@dataclass
class AnnualReportRequest:
    """
    Représente la demande documentaire.

    Exemple :
        AnnualReportRequest(
            company=company,
            fiscal_year=2024
        )
    """

    company: Company
    fiscal_year: int


@dataclass
class SearchCandidate:
    """
    Représente un lien candidat trouvé sur le web.

    À ce stade, un candidat n'est pas encore validé.
    Il peut être le bon rapport annuel ou non.
    """

    title: str
    url: str
    snippet: str = ""
    source_name: str = "unknown"


@dataclass
class ScoredCandidate:
    """
    Représente un candidat après scoring.

    Le score sert à décider si le document est probablement
    le bon rapport annuel de la bonne entreprise et de la bonne année.
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
    Résultat final du moteur.

    Ce résultat est retourné après tentative de récupération
    du rapport annuel.
    """

    status: str
    message: str

    company_name: str
    fiscal_year: int

    source_url: Optional[str] = None
    local_path: Optional[str] = None
    manifest_path: Optional[str] = None
    sha256: Optional[str] = None

    confidence_score: Optional[float] = None
    best_candidate: Optional[ScoredCandidate] = None
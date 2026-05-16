from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class IngestedDocument:
    """
    Représente un document candidat produit par un moteur d'ingestion.

    Ce modèle sert à normaliser les manifests issus de plusieurs retrievers :
    - AnnualReportRetriever
    - SustainabilityReportRetriever
    - ClimateReportRetriever
    - futurs moteurs ESG
    """

    document_id: str

    # Origine technique
    retriever_name: str
    document_family: str

    # Entreprise / année
    company_name: str
    company_slug: str
    fiscal_year: int

    # Source web
    source_url: Optional[str]
    source_title: Optional[str]
    source_snippet: Optional[str]
    source_name: Optional[str]

    # Scoring ingestion
    score: Optional[float]
    decision: Optional[str]
    positive_signals: list[str]
    negative_signals: list[str]

    # Fichier local
    local_path: Optional[str]
    manifest_path: Optional[str]
    sha256: Optional[str]
    file_size_mb: Optional[float]

    # Métadonnées stockage
    document_type: Optional[str]
    storage_role: Optional[str]
    candidate_rank: Optional[int]
    stored_at: Optional[str]

    # Chemin du manifest source lu par le registry builder
    source_manifest_path: str

    def to_dict(self) -> dict:
        """
        Convertit l'objet en dictionnaire.
        """

        return asdict(self)


@dataclass
class RegistryBuildResult:
    """
    Résultat de construction du registre central.
    """

    status: str
    message: str

    total_manifests_found: int
    total_documents_loaded: int
    total_errors: int

    output_json_path: Optional[str] = None
    output_csv_path: Optional[str] = None

    errors: list[dict] | None = None
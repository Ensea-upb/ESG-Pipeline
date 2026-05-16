from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import pandas as pd

from .scope import filter_dataframe_scope


@dataclass
class ExactDuplicateGroup:
    """
    Représente un groupe de documents strictement identiques.

    Deux documents sont strictement identiques s'ils ont le même SHA-256.
    """

    duplicate_group_id: str
    sha256: str
    duplicate_count: int
    companies: list[str]
    document_families: list[str]
    retrievers: list[str]
    documents: list[dict]


@dataclass
class DeduplicationResult:
    """
    Résultat global de la déduplication exacte.
    """

    status: str
    message: str

    total_documents: int
    total_documents_with_sha256: int
    total_unique_sha256: int
    total_duplicate_groups: int
    total_duplicate_documents: int

    output_json_path: Optional[str] = None
    output_csv_path: Optional[str] = None
    summary_path: Optional[str] = None


class DocumentDeduplicator:
    """
    Détecte les doublons exacts dans le registre central.

    Version actuelle :
    - déduplication exacte par sha256 ;
    - aucun fichier n'est supprimé ;
    - on produit seulement des rapports.
    """

    def __init__(
        self,
        registry_csv_path: str | Path = "data/central_registry/documents_registry.csv",
        output_dir: str | Path = "data/deduplication",
        company_slugs: set[str] | None = None,
        years: set[int] | None = None,
    ) -> None:
        self.registry_csv_path = Path(registry_csv_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.company_slugs = company_slugs
        self.years = years

    def run_exact_deduplication(self) -> DeduplicationResult:
        """
        Lance la déduplication exacte par SHA-256.
        """

        if not self.registry_csv_path.exists():
            raise FileNotFoundError(
                f"Registre central introuvable : {self.registry_csv_path}"
            )

        df = pd.read_csv(self.registry_csv_path)
        df = filter_dataframe_scope(df, self.company_slugs, self.years)

        if "sha256" not in df.columns:
            raise ValueError("La colonne 'sha256' est absente du registre central.")

        total_documents = len(df)

        df_with_sha = df[
            df["sha256"].notna()
            & (df["sha256"].astype(str).str.strip() != "")
        ].copy()

        total_documents_with_sha256 = len(df_with_sha)
        total_unique_sha256 = df_with_sha["sha256"].nunique()

        duplicate_groups = self.find_exact_duplicate_groups(df_with_sha)

        output_json_path = self.output_dir / "exact_duplicates.json"
        output_csv_path = self.output_dir / "exact_duplicates.csv"
        summary_path = self.output_dir / "deduplication_summary.json"

        self.save_duplicate_groups_json(
            duplicate_groups=duplicate_groups,
            output_path=output_json_path,
        )

        self.save_duplicate_groups_csv(
            duplicate_groups=duplicate_groups,
            output_path=output_csv_path,
        )

        total_duplicate_groups = len(duplicate_groups)
        total_duplicate_documents = sum(
            group.duplicate_count for group in duplicate_groups
        )

        result = DeduplicationResult(
            status="success",
            message=(
                f"Déduplication exacte terminée : "
                f"{total_duplicate_groups} groupe(s) de doublons exacts détecté(s)."
            ),
            total_documents=total_documents,
            total_documents_with_sha256=total_documents_with_sha256,
            total_unique_sha256=total_unique_sha256,
            total_duplicate_groups=total_duplicate_groups,
            total_duplicate_documents=total_duplicate_documents,
            output_json_path=str(output_json_path),
            output_csv_path=str(output_csv_path),
            summary_path=str(summary_path),
        )

        summary_path.write_text(
            json.dumps(asdict(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return result

    def find_exact_duplicate_groups(
        self,
        df_with_sha: pd.DataFrame,
    ) -> list[ExactDuplicateGroup]:
        """
        Regroupe les documents par SHA-256 et conserve uniquement
        les groupes de taille supérieure à 1.
        """

        duplicate_groups: list[ExactDuplicateGroup] = []

        grouped = df_with_sha.groupby("sha256", dropna=True)

        group_index = 1

        for sha256, group in grouped:
            if len(group) <= 1:
                continue

            group = group.copy()

            documents = []

            for _, row in group.iterrows():
                documents.append(
                    {
                        "document_id": self.safe_value(row.get("document_id")),
                        "retriever_name": self.safe_value(row.get("retriever_name")),
                        "document_family": self.safe_value(row.get("document_family")),
                        "company_name": self.safe_value(row.get("company_name")),
                        "company_slug": self.safe_value(row.get("company_slug")),
                        "fiscal_year": self.safe_value(row.get("fiscal_year")),
                        "source_title": self.safe_value(row.get("source_title")),
                        "source_url": self.safe_value(row.get("source_url")),
                        "local_path": self.safe_value(row.get("local_path")),
                        "manifest_path": self.safe_value(row.get("manifest_path")),
                        "file_size_mb": self.safe_value(row.get("file_size_mb")),
                        "score": self.safe_value(row.get("score")),
                        "decision": self.safe_value(row.get("decision")),
                    }
                )

            duplicate_groups.append(
                ExactDuplicateGroup(
                    duplicate_group_id=f"exact_dup_{group_index:04d}",
                    sha256=str(sha256),
                    duplicate_count=len(group),
                    companies=sorted(
                        {
                            str(x)
                            for x in group["company_name"].dropna().unique().tolist()
                        }
                    ),
                    document_families=sorted(
                        {
                            str(x)
                            for x in group["document_family"].dropna().unique().tolist()
                        }
                    ),
                    retrievers=sorted(
                        {
                            str(x)
                            for x in group["retriever_name"].dropna().unique().tolist()
                        }
                    ),
                    documents=documents,
                )
            )

            group_index += 1

        return duplicate_groups

    @staticmethod
    def save_duplicate_groups_json(
        duplicate_groups: list[ExactDuplicateGroup],
        output_path: Path,
    ) -> None:
        """
        Sauvegarde les groupes de doublons exacts en JSON.
        """

        payload = [asdict(group) for group in duplicate_groups]

        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def save_duplicate_groups_csv(
        duplicate_groups: list[ExactDuplicateGroup],
        output_path: Path,
    ) -> None:
        """
        Sauvegarde une version tabulaire des doublons exacts.
        Une ligne = un document appartenant à un groupe de doublons.
        """

        rows = []

        for group in duplicate_groups:
            for document in group.documents:
                row = {
                    "duplicate_group_id": group.duplicate_group_id,
                    "sha256": group.sha256,
                    "duplicate_count": group.duplicate_count,
                    "companies": json.dumps(group.companies, ensure_ascii=False),
                    "document_families": json.dumps(
                        group.document_families,
                        ensure_ascii=False,
                    ),
                    "retrievers": json.dumps(group.retrievers, ensure_ascii=False),
                }

                row.update(document)
                rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

    @staticmethod
    def safe_value(value):
        """
        Convertit les NaN pandas en None pour éviter des sorties sales.
        """

        if pd.isna(value):
            return None

        return value

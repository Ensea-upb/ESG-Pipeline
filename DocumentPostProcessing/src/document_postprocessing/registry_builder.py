from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from .models import IngestedDocument, RegistryBuildResult
from .scope import row_in_scope


class DocumentRegistryBuilder:
    """
    Construit un registre central de tous les documents ingérés.

    Cette classe lit les manifests produits par les retrievers :

    - AGMRetriever
    - AnnualReportRetriever
    - AssuranceReportRetriever
    - CDPResponseRetriever
    - SustainabilityReportRetriever
    - ClimateReportRetriever
    - CorporatePolicyRetriever
    - EarningsCallRetriever
    - GovernanceReportRetriever
    - HalfYearReportRetriever
    - InvestorPresentationRetriever
    - RemunerationReportRetriever
    - SBTiRetriever
    - VigilancePlanRetriever

    Elle ne fait pas de déduplication.
    Elle ne fait pas de validation documentaire.
    Elle centralise uniquement les métadonnées.
    """

    DEFAULT_RETRIEVER_CONFIGS = [
        {
            "retriever_name": "AGMRetriever",
            "document_family": "agm_document",
            "relative_root": "../AGMRetriever",
            "manifest_glob": "data/dossier_ingestion_0/agm_documents/**/*manifest.json",
        },
        {
            "retriever_name": "AnnualReportRetriever",
            "document_family": "annual_report",
            "relative_root": "../AnnualReportRetriever",
            "manifest_glob": "data/dossier_ingestion_0/annual_reports/**/*manifest.json",
        },
        {
            "retriever_name": "AssuranceReportRetriever",
            "document_family": "assurance_report",
            "relative_root": "../AssuranceReportRetriever",
            "manifest_glob": "data/dossier_ingestion_0/assurance_reports/**/*manifest.json",
        },
        {
            "retriever_name": "CDPResponseRetriever",
            "document_family": "cdp_response",
            "relative_root": "../CDPResponseRetriever",
            "manifest_glob": "data/dossier_ingestion_0/cdp_responses/**/*manifest.json",
        },
        {
            "retriever_name": "SustainabilityReportRetriever",
            "document_family": "sustainability_report",
            "relative_root": "../SustainabilityReportRetriever",
            "manifest_glob": "data/dossier_ingestion_0/sustainability_reports/**/*manifest.json",
        },
        {
            "retriever_name": "ClimateReportRetriever",
            "document_family": "climate_report",
            "relative_root": "../ClimateReportRetriever",
            "manifest_glob": "data/dossier_ingestion_0/climate_reports/**/*manifest.json",
        },
        {
            "retriever_name": "CorporatePolicyRetriever",
            "document_family": "corporate_policy",
            "relative_root": "../CorporatePolicyRetriever",
            "manifest_glob": "data/dossier_ingestion_0/corporate_policies/**/*manifest.json",
        },
        {
            "retriever_name": "EarningsCallRetriever",
            "document_family": "earnings_call",
            "relative_root": "../EarningsCallRetriever",
            "manifest_glob": "data/dossier_ingestion_0/earnings_calls/**/*manifest.json",
        },
        {
            "retriever_name": "GovernanceReportRetriever",
            "document_family": "governance_report",
            "relative_root": "../GovernanceReportRetriever",
            "manifest_glob": "data/dossier_ingestion_0/governance_reports/**/*manifest.json",
        },
        {
            "retriever_name": "HalfYearReportRetriever",
            "document_family": "half_year_report",
            "relative_root": "../HalfYearReportRetriever",
            "manifest_glob": "data/dossier_ingestion_0/half_year_reports/**/*manifest.json",
        },
        {
            "retriever_name": "InvestorPresentationRetriever",
            "document_family": "investor_presentation",
            "relative_root": "../InvestorPresentationRetriever",
            "manifest_glob": "data/dossier_ingestion_0/investor_presentations/**/*manifest.json",
        },
        {
            "retriever_name": "RemunerationReportRetriever",
            "document_family": "remuneration_report",
            "relative_root": "../RemunerationReportRetriever",
            "manifest_glob": "data/dossier_ingestion_0/remuneration_reports/**/*manifest.json",
        },
        {
            "retriever_name": "SBTiRetriever",
            "document_family": "sbti_commitment",
            "relative_root": "../SBTiRetriever",
            "manifest_glob": "data/dossier_ingestion_0/sbti_commitments/**/*manifest.json",
        },
        {
            "retriever_name": "VigilancePlanRetriever",
            "document_family": "vigilance_plan",
            "relative_root": "../VigilancePlanRetriever",
            "manifest_glob": "data/dossier_ingestion_0/vigilance_plans/**/*manifest.json",
        },
    ]

    def __init__(
        self,
        project_root: str | Path | None = None,
        output_dir: str | Path = "data/central_registry",
        company_slugs: set[str] | None = None,
        years: set[int] | None = None,
        input_root: str | Path | None = None,
    ) -> None:
        """
        Parameters
        ----------
        project_root:
            Racine de DocumentPostProcessing.
            Si None, on utilise le dossier courant.

        output_dir:
            Dossier de sortie du registre central.
        """

        self.project_root = Path(project_root or ".").resolve()
        self.output_dir = (self.project_root / output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.company_slugs = company_slugs
        self.years = years
        self.input_root = Path(input_root).resolve() if input_root else None

    def build_registry(self) -> RegistryBuildResult:
        """
        Construit le registre central et sauvegarde JSON + CSV.
        """

        manifest_paths = self.find_manifest_paths()

        documents: list[IngestedDocument] = []
        errors: list[dict] = []

        for manifest_info in manifest_paths:
            manifest_path = manifest_info["manifest_path"]
            retriever_name = manifest_info["retriever_name"]
            document_family = manifest_info["document_family"]
            retriever_root = manifest_info["retriever_root"]

            try:
                document = self.load_manifest_as_document(
                    manifest_path=manifest_path,
                    retriever_name=retriever_name,
                    document_family=document_family,
                    retriever_root=retriever_root,
                )
                if not row_in_scope(
                    company_slug=document.company_slug,
                    fiscal_year=document.fiscal_year,
                    company_slugs=self.company_slugs,
                    years=self.years,
                ):
                    continue
                documents.append(document)

            except Exception as exc:
                errors.append(
                    {
                        "manifest_path": str(manifest_path),
                        "retriever_name": retriever_name,
                        "document_family": document_family,
                        "error": str(exc),
                    }
                )

        output_json_path = self.output_dir / "documents_registry.json"
        output_csv_path = self.output_dir / "documents_registry.csv"

        self.save_json(
            documents=documents,
            output_path=output_json_path,
        )

        self.save_csv(
            documents=documents,
            output_path=output_csv_path,
        )

        status = "success" if not errors else "completed_with_errors"

        message = (
            f"Registre central construit : {len(documents)} document(s) chargé(s), "
            f"{len(errors)} erreur(s)."
        )

        return RegistryBuildResult(
            status=status,
            message=message,
            total_manifests_found=len(manifest_paths),
            total_documents_loaded=len(documents),
            total_errors=len(errors),
            output_json_path=str(output_json_path),
            output_csv_path=str(output_csv_path),
            errors=errors,
        )

    def find_manifest_paths(self) -> list[dict]:
        """
        Trouve tous les manifests candidats dans les retrievers connus.
        """

        results: list[dict] = []

        for config in self.DEFAULT_RETRIEVER_CONFIGS:
            if self.input_root is not None:
                if not self.input_root.exists():
                    continue
                retriever_root = self.input_root.parents[1]
                manifest_glob = config["manifest_glob"].replace(
                    "data/dossier_ingestion_0/",
                    "",
                    1,
                )
                manifest_paths = sorted(self.input_root.glob(manifest_glob))
            else:
                retriever_root = (self.project_root / config["relative_root"]).resolve()

                if not retriever_root.exists():
                    continue

                manifest_paths = sorted(
                    retriever_root.glob(config["manifest_glob"])
                )

            for manifest_path in manifest_paths:
                results.append(
                    {
                        "retriever_name": config["retriever_name"],
                        "document_family": config["document_family"],
                        "retriever_root": retriever_root,
                        "manifest_path": manifest_path.resolve(),
                    }
                )

        return results

    def load_manifest_as_document(
        self,
        manifest_path: Path,
        retriever_name: str,
        document_family: str,
        retriever_root: Path,
    ) -> IngestedDocument:
        """
        Charge un manifest JSON et le transforme en IngestedDocument.
        """

        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)

        company = manifest.get("company") or {}
        source = manifest.get("source") or {}
        scoring = manifest.get("scoring") or {}
        file_info = manifest.get("file") or {}
        ingestion = manifest.get("ingestion") or {}

        company_name = company.get("name") or "unknown"
        company_slug = manifest.get("company_slug") or self.slugify(company_name)
        fiscal_year = self.safe_int(
            manifest.get("fiscal_year", manifest.get("reference_year"))
        )

        source_url = source.get("url")
        source_title = source.get("title")
        source_snippet = source.get("snippet")
        source_name = source.get("source_name")

        local_path = self.resolve_path_from_retriever_root(
            path_value=file_info.get("local_path"),
            retriever_root=retriever_root,
        )

        manifest_path_from_file = self.resolve_path_from_retriever_root(
            path_value=file_info.get("manifest_path"),
            retriever_root=retriever_root,
        )

        source_manifest_path = str(manifest_path.resolve())
        if manifest_path_from_file is None:
            manifest_path_from_file = source_manifest_path

        sha256 = file_info.get("sha256")
        file_size_mb = self.safe_float(file_info.get("file_size_mb"))

        score = self.safe_float(scoring.get("score"))
        decision = scoring.get("decision")

        positive_signals = self.safe_list(scoring.get("positive_signals"))
        negative_signals = self.safe_list(scoring.get("negative_signals"))

        document_type = manifest.get("document_type")
        storage_role = manifest.get("storage_role")
        candidate_rank = self.safe_int(manifest.get("candidate_rank"))
        stored_at = ingestion.get("stored_at")

        document_id = self.build_document_id(
            retriever_name=retriever_name,
            document_family=document_family,
            company_slug=company_slug,
            fiscal_year=fiscal_year,
            sha256=sha256,
            local_path=local_path,
            source_url=source_url,
            source_manifest_path=source_manifest_path,
        )

        return IngestedDocument(
            document_id=document_id,
            retriever_name=retriever_name,
            document_family=document_family,
            company_name=company_name,
            company_slug=company_slug,
            fiscal_year=fiscal_year,
            source_url=source_url,
            source_title=source_title,
            source_snippet=source_snippet,
            source_name=source_name,
            score=score,
            decision=decision,
            positive_signals=positive_signals,
            negative_signals=negative_signals,
            local_path=local_path,
            manifest_path=manifest_path_from_file,
            sha256=sha256,
            file_size_mb=file_size_mb,
            document_type=document_type,
            storage_role=storage_role,
            candidate_rank=candidate_rank,
            stored_at=stored_at,
            source_manifest_path=source_manifest_path,
        )

    @staticmethod
    def build_document_id(
        retriever_name: str,
        document_family: str,
        company_slug: str,
        fiscal_year: int,
        sha256: Optional[str],
        local_path: Optional[str],
        source_url: Optional[str],
        source_manifest_path: str,
    ) -> str:
        """
        Construit un identifiant stable de document.

        On utilise plusieurs champs pour éviter les collisions.
        """

        raw = "|".join(
            [
                retriever_name or "",
                document_family or "",
                company_slug or "",
                str(fiscal_year or ""),
                sha256 or "",
                local_path or "",
                source_url or "",
                source_manifest_path or "",
            ]
        )

        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def resolve_path_from_retriever_root(
        path_value: Any,
        retriever_root: Path,
    ) -> Optional[str]:
        """
        Convertit les chemins relatifs des retrievers en chemins absolus.

        Les manifests des retrievers stockent souvent :
            data/dossier_ingestion_0/...

        On les résout depuis la racine du retriever.
        """

        if not path_value:
            return None

        path = Path(str(path_value))

        if path.is_absolute():
            return str(path.resolve())

        return str((retriever_root / path).resolve())

    @staticmethod
    def save_json(
        documents: list[IngestedDocument],
        output_path: Path,
    ) -> None:
        """
        Sauvegarde le registre central en JSON.
        """

        payload = [document.to_dict() for document in documents]

        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def save_csv(
        documents: list[IngestedDocument],
        output_path: Path,
    ) -> None:
        """
        Sauvegarde le registre central en CSV.

        Les listes sont converties en chaînes JSON pour rester lisibles.
        """

        rows = []

        for document in documents:
            row = document.to_dict()

            row["positive_signals"] = json.dumps(
                row.get("positive_signals") or [],
                ensure_ascii=False,
            )
            row["negative_signals"] = json.dumps(
                row.get("negative_signals") or [],
                ensure_ascii=False,
            )

            rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

    @staticmethod
    def safe_int(value: Any) -> int:
        """
        Convertit une valeur en int.
        """

        if value is None:
            return 0

        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def safe_float(value: Any) -> Optional[float]:
        """
        Convertit une valeur en float.
        """

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def safe_list(value: Any) -> list[str]:
        """
        Convertit une valeur de manifest en liste de chaines exploitable.
        """

        if value is None:
            return []

        if isinstance(value, list):
            return [str(item) for item in value]

        return [str(value)]

    @staticmethod
    def slugify(text: str) -> str:
        """
        Slug minimal sans dépendance externe.
        """

        text = str(text).lower().strip()
        chars = []

        for char in text:
            if char.isalnum():
                chars.append(char)
            elif char in {" ", "-", "_"}:
                chars.append("-")

        slug = "".join(chars)

        while "--" in slug:
            slug = slug.replace("--", "-")

        return slug.strip("-") or "unknown"

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from .models import Company, DocumentType, PipelineTask


class TaskBuilder:
    def __init__(
        self,
        document_types_config_path: str | Path,
        workspace_root: str | Path,
        min_score: float = 80.0,
    ) -> None:
        self.document_types_config_path = Path(document_types_config_path)
        self.workspace_root = Path(workspace_root).resolve()
        self.min_score = min_score

    def load_document_types(self) -> list[DocumentType]:
        payload = yaml.safe_load(
            self.document_types_config_path.read_text(encoding="utf-8")
        )
        return [
            DocumentType.from_dict(item)
            for item in payload.get("document_types", [])
            if item.get("enabled", True)
        ]

    def build_tasks(
        self,
        companies: list[Company],
        years: list[int],
    ) -> list[PipelineTask]:
        document_types = self.load_document_types()
        tasks = []

        for company in companies:
            for year in years:
                for document_type in document_types:
                    task = PipelineTask(
                        task_id=self.build_task_id(
                            company.company_slug,
                            year,
                            document_type.official_doc_type,
                        ),
                        company_name=company.name,
                        company_slug=company.company_slug,
                        fiscal_year=year,
                        official_doc_type=document_type.official_doc_type,
                        official_doc_type_label=document_type.label,
                        retriever=document_type.retriever,
                        policy_type=document_type.policy_type,
                    )
                    task.command = self.build_command(company, year, document_type)
                    if not document_type.retriever:
                        task.status = "skipped_not_applicable"
                        task.message = "No retriever configured for this official document type."
                    tasks.append(task)

        return tasks

    def build_command(
        self,
        company: Company,
        year: int,
        document_type: DocumentType,
    ) -> list[str]:
        if not document_type.retriever:
            return []

        retriever_dir = self.workspace_root / document_type.retriever
        script = retriever_dir / "scripts" / "run_download_all.py"
        command = [
            "python",
            str(script),
            "--company-name",
            company.name,
        ]

        if document_type.retriever == "CorporatePolicyRetriever":
            command.extend(["--reference-year", str(year)])
            command.extend(["--policy-type", str(document_type.policy_type)])
        else:
            command.extend(["--fiscal-year", str(year)])

        if company.official_domain:
            command.extend(["--official-domain", company.official_domain])
        if company.ticker:
            command.extend(["--ticker", company.ticker])
        if company.isin:
            command.extend(["--isin", company.isin])
        if company.jurisdiction:
            command.extend(["--jurisdiction", company.jurisdiction])

        command.extend(["--min-score", str(self.min_score)])
        command.extend(["--root-dir", "data/dossier_ingestion_0"])
        return command

    @staticmethod
    def build_task_id(company_slug: str, year: int, official_doc_type: str) -> str:
        raw = f"{company_slug}|{year}|{official_doc_type}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"task_{digest}"

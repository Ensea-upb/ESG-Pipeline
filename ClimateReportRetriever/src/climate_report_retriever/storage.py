from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import Company, ScoredCandidate
from .utils import compute_sha256, file_size_mb, slugify


class ClimateReportStorage:
    """
    Stockage des candidats rapports climat / TCFD / transition.

    Cette classe ne sélectionne pas le document final.
    Elle stocke les candidats téléchargés dans le dossier d'ingestion.
    """

    def __init__(self, root_dir: str | Path = "data/dossier_ingestion_0") -> None:
        self.root_dir = Path(root_dir)
        self.climate_reports_dir = self.root_dir / "climate_reports"
        self.registry_dir = self.root_dir / "registry"
        self.registry_path = self.registry_dir / "climate_reports_registry.jsonl"

        self._ensure_directories()

    def store_candidate_climate_report(
        self,
        temp_pdf_path: str | Path,
        company: Company,
        fiscal_year: int,
        candidate: ScoredCandidate,
        candidate_rank: int,
    ) -> dict:
        """
        Stocke un candidat rapport climat / TCFD / transition.

        Le fichier est placé dans :

        data/dossier_ingestion_0/climate_reports/<entreprise>/<année>/candidates/
        """

        temp_pdf_path = Path(temp_pdf_path)

        if not temp_pdf_path.exists():
            raise FileNotFoundError(f"PDF temporaire introuvable : {temp_pdf_path}")

        company_slug = slugify(company.name)

        candidate_dir = (
            self.climate_reports_dir
            / company_slug
            / str(fiscal_year)
            / "candidates"
        )
        candidate_dir.mkdir(parents=True, exist_ok=True)

        safe_score = str(round(candidate.score, 2)).replace(".", "_")

        final_pdf_path = (
            candidate_dir
            / f"candidate_{candidate_rank:03d}_score_{safe_score}.pdf"
        )

        shutil.copy2(temp_pdf_path, final_pdf_path)

        sha256 = compute_sha256(final_pdf_path)

        manifest_path = candidate_dir / f"candidate_{candidate_rank:03d}_manifest.json"

        manifest = {
            "document_type": "climate_report_candidate",
            "storage_role": "high_score_candidate",
            "candidate_rank": candidate_rank,
            "company": asdict(company),
            "company_slug": company_slug,
            "fiscal_year": fiscal_year,
            "source": {
                "url": candidate.url,
                "title": candidate.title,
                "snippet": candidate.snippet,
                "source_name": candidate.source_name,
            },
            "scoring": {
                "score": candidate.score,
                "decision": candidate.decision,
                "positive_signals": candidate.positive_signals,
                "negative_signals": candidate.negative_signals,
            },
            "file": {
                "local_path": str(final_pdf_path),
                "manifest_path": str(manifest_path),
                "sha256": sha256,
                "file_size_mb": file_size_mb(final_pdf_path),
                "original_temp_path": str(temp_pdf_path),
            },
            "ingestion": {
                "stored_at": self._utc_now(),
                "storage_version": "climate_report_candidate_storage_v0",
            },
        }

        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._append_registry(manifest)

        return manifest

    def _append_registry(self, manifest: dict) -> None:
        """
        Ajoute une ligne JSON dans le registre global.
        """

        self.registry_dir.mkdir(parents=True, exist_ok=True)

        with self.registry_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(manifest, ensure_ascii=False) + "\n")

    def _ensure_directories(self) -> None:
        """
        Crée les dossiers nécessaires.
        """

        self.climate_reports_dir.mkdir(parents=True, exist_ok=True)
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _utc_now() -> str:
        """
        Retourne la date UTC au format ISO.
        """

        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

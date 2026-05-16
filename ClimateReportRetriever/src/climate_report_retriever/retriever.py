from __future__ import annotations

from pathlib import Path

from .downloader import PDFDownloader
from .html_resolver import HTMLToPDFLinkResolver
from .models import (
    Company,
    DownloadResult,
    ScoredCandidate,
    ClimateReportRequest,
)
from .scorer import ClimateReportScorer
from .search import ClimateReportSearch
from .storage import ClimateReportStorage
from .utils import extract_years, safe_filename, slugify


class ClimateReportRetriever:
    """
    Moteur central d'ingestion des rapports climat / TCFD / transition.

    Rôle :
    - rechercher les candidats (Climate Report, TCFD, Transition Plan, Net Zero, CDP, GHG) ;
    - scorer les candidats ;
    - résoudre les pages HTML pertinentes vers des liens PDF ;
    - filtrer les candidats temporellement non pertinents ;
    - télécharger les candidats dont le score dépasse un seuil ;
    - stocker les PDF dans data/dossier_ingestion_0/climate_reports/ ;
    - créer les manifests.

    Important :
    Ce moteur ne valide pas définitivement le document.
    La validation documentaire se fait après l'ingestion.
    """

    def __init__(
        self,
        root_dir: str | Path = "data/dossier_ingestion_0",
        auto_download_threshold: float = 80.0,
        human_review_threshold: float = 60.0,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.tmp_dir = self.root_dir / "tmp"

        self.search = ClimateReportSearch()

        self.scorer = ClimateReportScorer(
            auto_download_threshold=auto_download_threshold,
            human_review_threshold=human_review_threshold,
        )

        self.downloader = PDFDownloader()
        self.storage = ClimateReportStorage(root_dir=self.root_dir)
        self.html_resolver = HTMLToPDFLinkResolver()

    def download_high_score_candidates(
        self,
        company: Company,
        fiscal_year: int,
        min_score: float = 80.0,
    ) -> DownloadResult:
        """
        Télécharge tous les candidats rapports climat / TCFD / transition
        dont le score est supérieur ou égal à min_score.

        Cette méthode gère aussi les pages HTML avec :
            decision = pdf_resolution_required

        Pipeline :
            recherche Tavily
                ↓
            scoring initial
                ↓
            sélection des candidats score >= min_score
                ↓
            si page HTML : extraction des liens PDF
                ↓
            filtrage temporel
                ↓
            téléchargement
                ↓
            stockage dans climate_reports/

        Règle temporelle :
            On accepte fiscal_year et fiscal_year - 1.

        Exemple :
            fiscal_year = 2024
            accepté : 2024, 2023
            rejeté  : 2022, 2021, 2020, ...
        """

        request = ClimateReportRequest(
            company=company,
            fiscal_year=fiscal_year,
        )

        raw_candidates = self.search.search_candidates(
            company=company,
            fiscal_year=fiscal_year,
        )

        ranked_candidates = self.scorer.rank_candidates(
            request=request,
            candidates=raw_candidates,
        )

        selected_candidates = [
            candidate
            for candidate in ranked_candidates
            if candidate.score >= min_score
        ]

        downloaded = []
        failed = []
        skipped = []

        seen_download_urls: set[str] = set()
        storage_rank = 1

        resolved_below_threshold_count = 0
        resolved_year_irrelevant_count = 0
        direct_year_irrelevant_count = 0

        for source_search_rank, candidate in enumerate(selected_candidates, start=1):
            # ====================================================
            # Cas 1 — Page HTML pertinente à résoudre en PDF
            # ====================================================
            if candidate.decision == "pdf_resolution_required":
                resolved = self.html_resolver.resolve(candidate)

                if resolved.status != "success" or not resolved.candidates:
                    skipped.append(
                        {
                            "rank": source_search_rank,
                            "source_search_rank": source_search_rank,
                            "title": candidate.title,
                            "url": candidate.url,
                            "score": candidate.score,
                            "decision": candidate.decision,
                            "reason": (
                                "Résolution HTML -> PDF échouée ou aucun PDF trouvé : "
                                f"{resolved.status} - {resolved.message}"
                            ),
                        }
                    )
                    continue

                resolved_scored_candidates = self.scorer.rank_candidates(
                    request=request,
                    candidates=resolved.candidates,
                )

                for resolved_candidate in resolved_scored_candidates:
                    # --------------------------------------------
                    # Filtre temporel des PDF extraits depuis HTML.
                    # --------------------------------------------
                    if not self._is_candidate_year_relevant(
                        candidate=resolved_candidate,
                        fiscal_year=fiscal_year,
                    ):
                        resolved_year_irrelevant_count += 1
                        continue

                    if resolved_candidate.url in seen_download_urls:
                        skipped.append(
                            {
                                "rank": source_search_rank,
                                "source_search_rank": source_search_rank,
                                "title": resolved_candidate.title,
                                "url": resolved_candidate.url,
                                "score": resolved_candidate.score,
                                "decision": resolved_candidate.decision,
                                "reason": "PDF extrait déjà traité.",
                                "resolved_from": candidate.url,
                            }
                        )
                        continue

                    if resolved_candidate.score < min_score:
                        resolved_below_threshold_count += 1
                        continue

                    if resolved_candidate.decision not in {
                        "auto_download",
                        "human_review_required",
                    }:
                        skipped.append(
                            {
                                "rank": source_search_rank,
                                "source_search_rank": source_search_rank,
                                "title": resolved_candidate.title,
                                "url": resolved_candidate.url,
                                "score": resolved_candidate.score,
                                "decision": resolved_candidate.decision,
                                "reason": (
                                    "PDF extrait de HTML mais décision "
                                    "non téléchargeable."
                                ),
                                "resolved_from": candidate.url,
                            }
                        )
                        continue

                    temp_pdf_path = self._build_temp_pdf_path(
                        company=company,
                        fiscal_year=fiscal_year,
                        source_url=resolved_candidate.url,
                    )

                    download_response = self.downloader.download_pdf(
                        url=resolved_candidate.url,
                        output_path=temp_pdf_path,
                    )

                    if download_response.status != "download_success":
                        failed.append(
                            {
                                "rank": storage_rank,
                                "candidate_rank": storage_rank,
                                "source_search_rank": source_search_rank,
                                "title": resolved_candidate.title,
                                "url": resolved_candidate.url,
                                "score": resolved_candidate.score,
                                "decision": resolved_candidate.decision,
                                "download_status": download_response.status,
                                "message": download_response.message,
                                "attempts": download_response.attempts,
                                "resolved_from": candidate.url,
                            }
                        )

                        seen_download_urls.add(resolved_candidate.url)
                        storage_rank += 1
                        continue

                    manifest = self.storage.store_candidate_climate_report(
                        temp_pdf_path=download_response.output_path,
                        company=company,
                        fiscal_year=fiscal_year,
                        candidate=resolved_candidate,
                        candidate_rank=storage_rank,
                    )

                    downloaded.append(
                        {
                            "rank": storage_rank,
                            "candidate_rank": storage_rank,
                            "source_search_rank": source_search_rank,
                            "title": resolved_candidate.title,
                            "url": resolved_candidate.url,
                            "score": resolved_candidate.score,
                            "decision": resolved_candidate.decision,
                            "local_path": manifest["file"]["local_path"],
                            "manifest_path": manifest["file"]["manifest_path"],
                            "sha256": manifest["file"]["sha256"],
                            "resolved_from": candidate.url,
                        }
                    )

                    seen_download_urls.add(resolved_candidate.url)
                    storage_rank += 1

                continue

            # ====================================================
            # Cas 2 — Candidat PDF direct ou téléchargeable
            # ====================================================

            if not self._is_candidate_year_relevant(
                candidate=candidate,
                fiscal_year=fiscal_year,
            ):
                direct_year_irrelevant_count += 1
                continue

            if candidate.decision not in {"auto_download", "human_review_required"}:
                skipped.append(
                    {
                        "rank": source_search_rank,
                        "source_search_rank": source_search_rank,
                        "title": candidate.title,
                        "url": candidate.url,
                        "score": candidate.score,
                        "decision": candidate.decision,
                        "reason": "Décision non téléchargeable automatiquement.",
                    }
                )
                continue

            if candidate.url in seen_download_urls:
                skipped.append(
                    {
                        "rank": source_search_rank,
                        "source_search_rank": source_search_rank,
                        "title": candidate.title,
                        "url": candidate.url,
                        "score": candidate.score,
                        "decision": candidate.decision,
                        "reason": "URL déjà traitée.",
                    }
                )
                continue

            temp_pdf_path = self._build_temp_pdf_path(
                company=company,
                fiscal_year=fiscal_year,
                source_url=candidate.url,
            )

            download_response = self.downloader.download_pdf(
                url=candidate.url,
                output_path=temp_pdf_path,
            )

            if download_response.status != "download_success":
                failed.append(
                    {
                        "rank": storage_rank,
                        "candidate_rank": storage_rank,
                        "source_search_rank": source_search_rank,
                        "title": candidate.title,
                        "url": candidate.url,
                        "score": candidate.score,
                        "decision": candidate.decision,
                        "download_status": download_response.status,
                        "message": download_response.message,
                        "attempts": download_response.attempts,
                    }
                )

                seen_download_urls.add(candidate.url)
                storage_rank += 1
                continue

            manifest = self.storage.store_candidate_climate_report(
                temp_pdf_path=download_response.output_path,
                company=company,
                fiscal_year=fiscal_year,
                candidate=candidate,
                candidate_rank=storage_rank,
            )

            downloaded.append(
                {
                    "rank": storage_rank,
                    "candidate_rank": storage_rank,
                    "source_search_rank": source_search_rank,
                    "title": candidate.title,
                    "url": candidate.url,
                    "score": candidate.score,
                    "decision": candidate.decision,
                    "local_path": manifest["file"]["local_path"],
                    "manifest_path": manifest["file"]["manifest_path"],
                    "sha256": manifest["file"]["sha256"],
                }
            )

            seen_download_urls.add(candidate.url)
            storage_rank += 1

        # ========================================================
        # Résumés des candidats ignorés
        # ========================================================

        if resolved_below_threshold_count > 0:
            skipped.append(
                {
                    "rank": "?",
                    "title": "PDFs extraits de pages HTML sous le seuil",
                    "url": None,
                    "score": None,
                    "decision": "reject",
                    "reason": (
                        f"{resolved_below_threshold_count} PDF(s) extraits "
                        f"de pages HTML ont été ignorés car leur score était "
                        f"inférieur à {min_score}."
                    ),
                }
            )

        if resolved_year_irrelevant_count > 0:
            skipped.append(
                {
                    "rank": "?",
                    "title": "PDFs extraits de pages HTML hors période cible",
                    "url": None,
                    "score": None,
                    "decision": "reject",
                    "reason": (
                        f"{resolved_year_irrelevant_count} PDF(s) extraits "
                        f"de pages HTML ont été ignorés car leur année était "
                        f"trop éloignée de l'année cible {fiscal_year}. "
                        f"Années acceptées : {fiscal_year} et {fiscal_year - 1}."
                    ),
                }
            )

        if direct_year_irrelevant_count > 0:
            skipped.append(
                {
                    "rank": "?",
                    "title": "Candidats directs hors période cible",
                    "url": None,
                    "score": None,
                    "decision": "reject",
                    "reason": (
                        f"{direct_year_irrelevant_count} candidat(s) directs "
                        f"ont été ignorés car leur année était trop éloignée "
                        f"de l'année cible {fiscal_year}. "
                        f"Années acceptées : {fiscal_year} et {fiscal_year - 1}."
                    ),
                }
            )

        return DownloadResult(
            status="completed",
            message="Ingestion des candidats rapports climat / TCFD / transition terminée.",
            company_name=company.name,
            fiscal_year=fiscal_year,
            downloaded_count=len(downloaded),
            failed_count=len(failed),
            skipped_count=len(skipped),
            downloaded=downloaded,
            failed=failed,
            skipped=skipped,
        )

    # ========================================================
    # Filtre temporel des candidats
    # ========================================================

    @staticmethod
    def _is_candidate_year_relevant(
        candidate: ScoredCandidate,
        fiscal_year: int,
    ) -> bool:
        """
        Vérifie si un candidat est temporellement pertinent.

        Règle :
        - si aucune année n'est détectée dans le titre ou l'URL, on conserve ;
        - si des années sont détectées, on accepte fiscal_year et fiscal_year - 1.

        Exemple :
            fiscal_year = 2024
            accepté : 2024, 2023
            rejeté  : 2022, 2021, 2020, ...
        """

        text = f"{candidate.title} {candidate.url}"
        years = extract_years(text)

        if not years:
            return True

        accepted_years = {
            fiscal_year,
            fiscal_year - 1,
        }

        return bool(years & accepted_years)

    # ========================================================
    # Utilitaire interne
    # ========================================================

    def _build_temp_pdf_path(
        self,
        company: Company,
        fiscal_year: int,
        source_url: str,
    ) -> Path:
        """
        Construit le chemin temporaire du PDF téléchargé.
        """

        self.tmp_dir.mkdir(parents=True, exist_ok=True)

        company_slug = slugify(company.name)
        filename = safe_filename(
            source_url.split("/")[-1] or "climate_report.pdf"
        )

        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"

        return self.tmp_dir / f"{company_slug}_{fiscal_year}_{filename}"

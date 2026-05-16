from __future__ import annotations

from pathlib import Path

from .downloader import PDFDownloader
from .html_resolver import HTMLToPDFLinkResolver
from .models import (
    AnnualReportRequest,
    Company,
    DownloadResult,
    SearchCandidate,
    ScoredCandidate,
)
from .scorer import AnnualReportScorer
from .search import AnnualReportSearch
from .storage import AnnualReportStorage
from .utils import safe_filename, slugify


class AnnualReportRetriever:
    """
    Moteur central pour récupérer les rapports annuels d'une entreprise.

    Deux modes principaux :

    1. download_annual_report()
       -> cherche, score, résout les pages HTML si nécessaire,
          télécharge et stocke le meilleur candidat final.

    2. download_high_score_candidates()
       -> cherche, score, résout les pages HTML si nécessaire,
          télécharge tous les candidats dont le score >= min_score.
    """

    def __init__(
        self,
        root_dir: str | Path = "data/dossier_ingestion_0",
        auto_download_threshold: float = 80.0,
        human_review_threshold: float = 60.0,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.tmp_dir = self.root_dir / "tmp"

        self.search = AnnualReportSearch()

        self.scorer = AnnualReportScorer(
            auto_download_threshold=auto_download_threshold,
            human_review_threshold=human_review_threshold,
        )

        self.downloader = PDFDownloader()
        self.storage = AnnualReportStorage(root_dir=self.root_dir)
        self.html_resolver = HTMLToPDFLinkResolver()

    # ========================================================
    # Mode 1 — télécharger le meilleur candidat final
    # ========================================================

    def download_annual_report(
        self,
        company: Company,
        fiscal_year: int,
    ) -> DownloadResult:
        """
        Cherche automatiquement les candidats, puis télécharge le meilleur.

        Cette méthode utilise :
        - les candidats PDF directs ;
        - les PDFs extraits depuis les pages HTML pertinentes.
        """

        candidates = self.search.search_candidates(
            company=company,
            fiscal_year=fiscal_year,
        )

        return self.download_annual_report_from_candidates(
            company=company,
            fiscal_year=fiscal_year,
            candidates=candidates,
        )

    def download_annual_report_from_candidates(
        self,
        company: Company,
        fiscal_year: int,
        candidates: list[SearchCandidate],
    ) -> DownloadResult:
        """
        Télécharge le meilleur rapport annuel à partir d'une liste de candidats.
        """

        request = AnnualReportRequest(
            company=company,
            fiscal_year=fiscal_year,
        )

        if not candidates:
            return DownloadResult(
                status="no_candidate",
                message="Aucun candidat fourni.",
                company_name=company.name,
                fiscal_year=fiscal_year,
            )

        ranked_candidates = self.scorer.rank_candidates(
            request=request,
            candidates=candidates,
        )

        first_candidate = ranked_candidates[0]

        # 1. Candidats PDF directs
        direct_auto_candidates = [
            candidate
            for candidate in ranked_candidates
            if candidate.decision == "auto_download"
        ]

        # 2. Candidats PDF extraits depuis les pages HTML pertinentes
        resolved_auto_candidates = self._resolve_html_candidates(
            request=request,
            ranked_candidates=ranked_candidates,
            min_score=self.scorer.auto_download_threshold,
            only_auto_download=True,
        )

        # 3. On essaie les directs d'abord, puis les résolus
        candidates_to_try = self._deduplicate_scored_candidates(
            direct_auto_candidates + resolved_auto_candidates
        )

        if not candidates_to_try:
            return DownloadResult(
                status="no_auto_download_candidate",
                message=(
                    "Aucun candidat téléchargeable automatiquement. "
                    "Les meilleurs candidats nécessitent une validation humaine "
                    "ou une résolution HTML sans PDF exploitable."
                ),
                company_name=company.name,
                fiscal_year=fiscal_year,
                confidence_score=first_candidate.score,
                best_candidate=first_candidate,
            )

        download_errors = []

        for candidate in candidates_to_try:
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
                download_errors.append(
                    {
                        "url": candidate.url,
                        "title": candidate.title,
                        "score": candidate.score,
                        "decision": candidate.decision,
                        "download_status": download_response.status,
                        "message": download_response.message,
                        "attempts": download_response.attempts,
                    }
                )
                continue

            manifest = self.storage.store_annual_report(
                temp_pdf_path=download_response.output_path,
                company=company,
                fiscal_year=fiscal_year,
                candidate=candidate,
            )

            return DownloadResult(
                status="success",
                message="Rapport annuel téléchargé et stocké avec succès.",
                company_name=company.name,
                fiscal_year=fiscal_year,
                source_url=candidate.url,
                local_path=manifest["file"]["local_path"],
                manifest_path=manifest["file"]["manifest_path"],
                sha256=manifest["file"]["sha256"],
                confidence_score=candidate.score,
                best_candidate=candidate,
            )

        return DownloadResult(
            status="all_downloads_failed",
            message=f"Tous les candidats téléchargeables ont échoué : {download_errors}",
            company_name=company.name,
            fiscal_year=fiscal_year,
            confidence_score=first_candidate.score,
            best_candidate=first_candidate,
        )

    # ========================================================
    # Mode 2 — télécharger tous les candidats score >= seuil
    # ========================================================

    def download_high_score_candidates(
        self,
        company: Company,
        fiscal_year: int,
        min_score: float = 80.0,
    ) -> dict:
        """
        Télécharge tous les candidats dont le score est supérieur ou égal à min_score.

        Cette méthode ne choisit pas un seul document final.
        Elle construit un dossier de candidats haute confiance.

        Elle gère aussi les pages HTML avec decision = pdf_resolution_required :
        - ouverture de la page ;
        - extraction des liens PDF ;
        - scoring des PDF extraits ;
        - téléchargement si score >= min_score.
        """

        request = AnnualReportRequest(
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

        storage_rank = 1
        seen_download_urls = set()

        for search_rank, candidate in enumerate(selected_candidates, start=1):
            # ------------------------------------------------
            # Cas 1 : page HTML pertinente à résoudre en PDFs
            # ------------------------------------------------
            if candidate.decision == "pdf_resolution_required":
                resolved = self.html_resolver.resolve(candidate)

                if resolved.status != "success" or not resolved.candidates:
                    skipped.append(
                        {
                            "source_search_rank": search_rank,
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
                    if resolved_candidate.url in seen_download_urls:
                        skipped.append(
                            {
                                "source_search_rank": search_rank,
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
                        # On ne log pas individuellement tous les PDFs faibles extraits
                        # depuis une page HTML, car certains agrégateurs comme AnnualReports
                        # peuvent exposer des dizaines d'anciens rapports.
                        continue

                    if resolved_candidate.decision not in {
                        "auto_download",
                        "human_review_required",
                    }:
                        skipped.append(
                            {
                                "source_search_rank": search_rank,
                                "title": resolved_candidate.title,
                                "url": resolved_candidate.url,
                                "score": resolved_candidate.score,
                                "decision": resolved_candidate.decision,
                                "reason": "PDF extrait de HTML mais décision non téléchargeable.",
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
                                "candidate_rank": storage_rank,
                                "source_search_rank": search_rank,
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

                    manifest = self.storage.store_candidate_annual_report(
                        temp_pdf_path=download_response.output_path,
                        company=company,
                        fiscal_year=fiscal_year,
                        candidate=resolved_candidate,
                        candidate_rank=storage_rank,
                    )

                    downloaded.append(
                        {
                            "candidate_rank": storage_rank,
                            "source_search_rank": search_rank,
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

            # ------------------------------------------------
            # Cas 2 : candidat PDF direct ou candidat téléchargeable
            # ------------------------------------------------
            if candidate.decision not in {"auto_download", "human_review_required"}:
                skipped.append(
                    {
                        "source_search_rank": search_rank,
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
                        "source_search_rank": search_rank,
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
                        "candidate_rank": storage_rank,
                        "source_search_rank": search_rank,
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

            manifest = self.storage.store_candidate_annual_report(
                temp_pdf_path=download_response.output_path,
                company=company,
                fiscal_year=fiscal_year,
                candidate=candidate,
                candidate_rank=storage_rank,
            )

            downloaded.append(
                {
                    "candidate_rank": storage_rank,
                    "source_search_rank": search_rank,
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

        return {
            "company_name": company.name,
            "fiscal_year": fiscal_year,
            "min_score": min_score,
            "total_raw_candidates": len(raw_candidates),
            "total_ranked_candidates": len(ranked_candidates),
            "total_selected_candidates": len(selected_candidates),
            "downloaded_count": len(downloaded),
            "failed_count": len(failed),
            "skipped_count": len(skipped),
            "downloaded": downloaded,
            "failed": failed,
            "skipped": skipped,
        }

    # ========================================================
    # Résolution HTML -> PDF
    # ========================================================

    def _resolve_html_candidates(
        self,
        request: AnnualReportRequest,
        ranked_candidates: list[ScoredCandidate],
        min_score: float,
        only_auto_download: bool = True,
    ) -> list[ScoredCandidate]:
        """
        Résout les candidats HTML en liens PDF puis les rescore.
        """

        resolved_candidates: list[ScoredCandidate] = []

        html_candidates = [
            candidate
            for candidate in ranked_candidates
            if candidate.decision == "pdf_resolution_required"
        ]

        for html_candidate in html_candidates:
            search_candidate = SearchCandidate(
                title=html_candidate.title,
                url=html_candidate.url,
                snippet=html_candidate.snippet,
                source_name=html_candidate.source_name,
            )

            resolved = self.html_resolver.resolve(search_candidate)

            if resolved.status != "success" or not resolved.candidates:
                continue

            scored_resolved = self.scorer.rank_candidates(
                request=request,
                candidates=resolved.candidates,
            )

            for candidate in scored_resolved:
                if candidate.score < min_score:
                    continue

                if only_auto_download and candidate.decision != "auto_download":
                    continue

                resolved_candidates.append(candidate)

        return resolved_candidates

    @staticmethod
    def _deduplicate_scored_candidates(
        candidates: list[ScoredCandidate],
    ) -> list[ScoredCandidate]:
        """
        Déduplique les candidats scorés par URL.
        """

        seen_urls = set()
        unique_candidates = []

        for candidate in candidates:
            url = candidate.url.strip()

            if not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)
            unique_candidates.append(candidate)

        return unique_candidates

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
        filename = safe_filename(source_url.split("/")[-1] or "annual_report.pdf")

        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"

        return self.tmp_dir / f"{company_slug}_{fiscal_year}_{filename}"
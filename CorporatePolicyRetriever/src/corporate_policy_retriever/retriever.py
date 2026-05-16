from __future__ import annotations

from pathlib import Path

from .downloader import PDFDownloader
from .html_resolver import HTMLToPDFLinkResolver
from .models import Company, CorporatePolicyRequest, DownloadResult, PolicyType, ScoredCandidate
from .scorer import CorporatePolicyScorer
from .search import CorporatePolicySearch
from .storage import CorporatePolicyStorage
from .utils import safe_filename, slugify


class CorporatePolicyRetriever:
    """
    Moteur central d'ingestion des politiques corporate (documents pérennes).

    Cible (via policy_type) :
    - code_of_conduct     : Code éthique / Code of Conduct ;
    - anticorruption      : Politique anticorruption / Anti-Bribery Policy ;
    - human_rights        : Politique droits humains / Human Rights Policy ;
    - dei                 : Politique diversité, équité, inclusion (DEI) ;
    - environmental       : Politique environnementale / Environmental Policy ;
    - supplier_code       : Supplier Code of Conduct / Politique achats responsables.

    Stocke dans : data/dossier_ingestion_0/corporate_policies/<policy_type>/
    """

    def __init__(
        self,
        root_dir: str | Path = "data/dossier_ingestion_0",
        auto_download_threshold: float = 80.0,
        human_review_threshold: float = 60.0,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.tmp_dir = self.root_dir / "tmp"
        self.search = CorporatePolicySearch()
        self.scorer = CorporatePolicyScorer(
            auto_download_threshold=auto_download_threshold,
            human_review_threshold=human_review_threshold,
        )
        self.downloader = PDFDownloader()
        self.storage = CorporatePolicyStorage(root_dir=self.root_dir)
        self.html_resolver = HTMLToPDFLinkResolver()

    def download_high_score_candidates(
        self,
        company: Company,
        policy_type: PolicyType,
        reference_year: int,
        min_score: float = 80.0,
    ) -> DownloadResult:
        """
        Télécharge tous les candidats politiques dont le score >= min_score.

        Les politiques corporate sont des documents pérennes — pas de filtre
        temporel strict. On accepte tout document émis dans les 5 dernières années.
        """
        request = CorporatePolicyRequest(
            company=company,
            reference_year=reference_year,
            policy_type=policy_type,
        )

        raw_candidates = self.search.search_candidates(
            company=company, policy_type=policy_type, reference_year=reference_year
        )
        ranked_candidates = self.scorer.rank_candidates(request=request, candidates=raw_candidates)
        selected_candidates = [c for c in ranked_candidates if c.score >= min_score]

        downloaded, failed, skipped = [], [], []
        seen_download_urls: set[str] = set()
        storage_rank = 1
        resolved_below_threshold_count = 0

        for source_search_rank, candidate in enumerate(selected_candidates, start=1):

            # --- Cas 1 : page HTML à résoudre ---
            if candidate.decision == "pdf_resolution_required":
                resolved = self.html_resolver.resolve(candidate)

                if resolved.status != "success" or not resolved.candidates:
                    skipped.append({
                        "rank": source_search_rank, "source_search_rank": source_search_rank,
                        "title": candidate.title, "url": candidate.url,
                        "score": candidate.score, "decision": candidate.decision,
                        "reason": f"Résolution HTML -> PDF échouée : {resolved.status} - {resolved.message}",
                    })
                    continue

                for resolved_candidate in self.scorer.rank_candidates(
                    request=request, candidates=resolved.candidates
                ):
                    if resolved_candidate.url in seen_download_urls:
                        skipped.append({
                            "rank": source_search_rank, "source_search_rank": source_search_rank,
                            "title": resolved_candidate.title, "url": resolved_candidate.url,
                            "score": resolved_candidate.score, "decision": resolved_candidate.decision,
                            "reason": "PDF extrait déjà traité.", "resolved_from": candidate.url,
                        })
                        continue
                    if resolved_candidate.score < min_score:
                        resolved_below_threshold_count += 1
                        continue
                    if resolved_candidate.decision not in {"auto_download", "human_review_required"}:
                        skipped.append({
                            "rank": source_search_rank, "source_search_rank": source_search_rank,
                            "title": resolved_candidate.title, "url": resolved_candidate.url,
                            "score": resolved_candidate.score, "decision": resolved_candidate.decision,
                            "reason": "PDF extrait mais décision non téléchargeable.",
                            "resolved_from": candidate.url,
                        })
                        continue

                    temp_pdf_path = self._build_temp_pdf_path(company, policy_type, resolved_candidate.url)
                    download_response = self.downloader.download_pdf(
                        url=resolved_candidate.url, output_path=temp_pdf_path
                    )

                    if download_response.status != "download_success":
                        failed.append({
                            "rank": storage_rank, "candidate_rank": storage_rank,
                            "source_search_rank": source_search_rank,
                            "title": resolved_candidate.title, "url": resolved_candidate.url,
                            "score": resolved_candidate.score, "decision": resolved_candidate.decision,
                            "download_status": download_response.status,
                            "message": download_response.message,
                            "attempts": download_response.attempts,
                            "resolved_from": candidate.url,
                        })
                        seen_download_urls.add(resolved_candidate.url)
                        storage_rank += 1
                        continue

                    manifest = self.storage.store_candidate_policy(
                        temp_pdf_path=download_response.output_path,
                        company=company, reference_year=reference_year,
                        policy_type=policy_type,
                        candidate=resolved_candidate, candidate_rank=storage_rank,
                    )
                    downloaded.append({
                        "rank": storage_rank, "candidate_rank": storage_rank,
                        "source_search_rank": source_search_rank,
                        "title": resolved_candidate.title, "url": resolved_candidate.url,
                        "score": resolved_candidate.score, "decision": resolved_candidate.decision,
                        "local_path": manifest["file"]["local_path"],
                        "manifest_path": manifest["file"]["manifest_path"],
                        "sha256": manifest["file"]["sha256"],
                        "resolved_from": candidate.url,
                    })
                    seen_download_urls.add(resolved_candidate.url)
                    storage_rank += 1
                continue

            # --- Cas 2 : candidat PDF direct ---
            if candidate.decision not in {"auto_download", "human_review_required"}:
                skipped.append({
                    "rank": source_search_rank, "source_search_rank": source_search_rank,
                    "title": candidate.title, "url": candidate.url,
                    "score": candidate.score, "decision": candidate.decision,
                    "reason": "Décision non téléchargeable automatiquement.",
                })
                continue

            if candidate.url in seen_download_urls:
                skipped.append({
                    "rank": source_search_rank, "source_search_rank": source_search_rank,
                    "title": candidate.title, "url": candidate.url,
                    "score": candidate.score, "decision": candidate.decision,
                    "reason": "URL déjà traitée.",
                })
                continue

            temp_pdf_path = self._build_temp_pdf_path(company, policy_type, candidate.url)
            download_response = self.downloader.download_pdf(
                url=candidate.url, output_path=temp_pdf_path
            )

            if download_response.status != "download_success":
                failed.append({
                    "rank": storage_rank, "candidate_rank": storage_rank,
                    "source_search_rank": source_search_rank,
                    "title": candidate.title, "url": candidate.url,
                    "score": candidate.score, "decision": candidate.decision,
                    "download_status": download_response.status,
                    "message": download_response.message,
                    "attempts": download_response.attempts,
                })
                seen_download_urls.add(candidate.url)
                storage_rank += 1
                continue

            manifest = self.storage.store_candidate_policy(
                temp_pdf_path=download_response.output_path,
                company=company, reference_year=reference_year,
                policy_type=policy_type,
                candidate=candidate, candidate_rank=storage_rank,
            )
            downloaded.append({
                "rank": storage_rank, "candidate_rank": storage_rank,
                "source_search_rank": source_search_rank,
                "title": candidate.title, "url": candidate.url,
                "score": candidate.score, "decision": candidate.decision,
                "local_path": manifest["file"]["local_path"],
                "manifest_path": manifest["file"]["manifest_path"],
                "sha256": manifest["file"]["sha256"],
            })
            seen_download_urls.add(candidate.url)
            storage_rank += 1

        if resolved_below_threshold_count > 0:
            skipped.append({"rank": "?", "title": "PDFs extraits HTML sous le seuil",
                "url": None, "score": None, "decision": "reject",
                "reason": f"{resolved_below_threshold_count} PDF(s) extraits de HTML ignorés (score < {min_score})."})

        return DownloadResult(
            status="completed",
            message=f"Ingestion des candidats politique {policy_type.value} terminée.",
            company_name=company.name,
            reference_year=reference_year,
            policy_type=policy_type.value,
            downloaded_count=len(downloaded),
            failed_count=len(failed),
            skipped_count=len(skipped),
            downloaded=downloaded,
            failed=failed,
            skipped=skipped,
        )

    def _build_temp_pdf_path(
        self, company: Company, policy_type: PolicyType, source_url: str
    ) -> Path:
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        company_slug = slugify(company.name)
        filename = safe_filename(source_url.split("/")[-1] or f"{policy_type.value}.pdf")
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"
        return self.tmp_dir / f"{company_slug}_{policy_type.value}_{filename}"

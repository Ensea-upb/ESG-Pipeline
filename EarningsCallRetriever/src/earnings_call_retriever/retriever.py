from __future__ import annotations
from pathlib import Path
from .downloader import PDFDownloader
from .html_resolver import HTMLToPDFLinkResolver
from .models import Company, DownloadResult, EarningsCallRequest, ScoredCandidate
from .scorer import EarningsCallScorer
from .search import EarningsCallSearch
from .storage import EarningsCallStorage
from .utils import extract_years, safe_filename, slugify


class EarningsCallRetriever:
    def __init__(self, root_dir="data/dossier_ingestion_0",
                 auto_download_threshold=80.0, human_review_threshold=60.0):
        self.root_dir = Path(root_dir)
        self.tmp_dir = self.root_dir / "tmp"
        self.search = EarningsCallSearch()
        self.scorer = EarningsCallScorer(auto_download_threshold=auto_download_threshold,
                                human_review_threshold=human_review_threshold)
        self.downloader = PDFDownloader()
        self.storage = EarningsCallStorage(root_dir=self.root_dir)
        self.html_resolver = HTMLToPDFLinkResolver()

    def download_high_score_candidates(self, company, fiscal_year, min_score=80.0):
        request = EarningsCallRequest(company=company, fiscal_year=fiscal_year)
        raw_candidates = self.search.search_candidates(company=company, fiscal_year=fiscal_year)
        ranked_candidates = self.scorer.rank_candidates(request=request, candidates=raw_candidates)
        selected_candidates = [c for c in ranked_candidates if c.score >= min_score]

        downloaded, failed, skipped = [], [], []
        seen_download_urls: set[str] = set()
        storage_rank = 1
        resolved_below_threshold_count = 0
        resolved_year_irrelevant_count = 0
        direct_year_irrelevant_count = 0

        for source_search_rank, candidate in enumerate(selected_candidates, start=1):
            if candidate.decision == "pdf_resolution_required":
                resolved = self.html_resolver.resolve(candidate)
                if resolved.status != "success" or not resolved.candidates:
                    skipped.append({"rank": source_search_rank, "source_search_rank": source_search_rank,
                        "title": candidate.title, "url": candidate.url,
                        "score": candidate.score, "decision": candidate.decision,
                        "reason": f"Résolution HTML -> PDF échouée : {resolved.status} - {resolved.message}"})
                    continue
                for resolved_candidate in self.scorer.rank_candidates(request=request, candidates=resolved.candidates):
                    if not self._is_candidate_year_relevant(resolved_candidate, fiscal_year):
                        resolved_year_irrelevant_count += 1
                        continue
                    if resolved_candidate.url in seen_download_urls:
                        skipped.append({"rank": source_search_rank, "source_search_rank": source_search_rank,
                            "title": resolved_candidate.title, "url": resolved_candidate.url,
                            "score": resolved_candidate.score, "decision": resolved_candidate.decision,
                            "reason": "PDF extrait déjà traité.", "resolved_from": candidate.url})
                        continue
                    if resolved_candidate.score < min_score:
                        resolved_below_threshold_count += 1
                        continue
                    if resolved_candidate.decision not in {"auto_download", "human_review_required"}:
                        skipped.append({"rank": source_search_rank, "source_search_rank": source_search_rank,
                            "title": resolved_candidate.title, "url": resolved_candidate.url,
                            "score": resolved_candidate.score, "decision": resolved_candidate.decision,
                            "reason": "PDF extrait mais décision non téléchargeable.", "resolved_from": candidate.url})
                        continue
                    temp_pdf_path = self._build_temp_pdf_path(company, fiscal_year, resolved_candidate.url)
                    download_response = self.downloader.download_pdf(url=resolved_candidate.url, output_path=temp_pdf_path)
                    if download_response.status != "download_success":
                        failed.append({"rank": storage_rank, "candidate_rank": storage_rank,
                            "source_search_rank": source_search_rank,
                            "title": resolved_candidate.title, "url": resolved_candidate.url,
                            "score": resolved_candidate.score, "decision": resolved_candidate.decision,
                            "download_status": download_response.status, "message": download_response.message,
                            "attempts": download_response.attempts, "resolved_from": candidate.url})
                        seen_download_urls.add(resolved_candidate.url)
                        storage_rank += 1
                        continue
                    manifest = self.storage.store_candidate_earnings_call(temp_pdf_path=download_response.output_path,
                        company=company, fiscal_year=fiscal_year,
                        candidate=resolved_candidate, candidate_rank=storage_rank)
                    downloaded.append({"rank": storage_rank, "candidate_rank": storage_rank,
                        "source_search_rank": source_search_rank,
                        "title": resolved_candidate.title, "url": resolved_candidate.url,
                        "score": resolved_candidate.score, "decision": resolved_candidate.decision,
                        "local_path": manifest["file"]["local_path"],
                        "manifest_path": manifest["file"]["manifest_path"],
                        "sha256": manifest["file"]["sha256"], "resolved_from": candidate.url})
                    seen_download_urls.add(resolved_candidate.url)
                    storage_rank += 1
                continue

            if not self._is_candidate_year_relevant(candidate, fiscal_year):
                direct_year_irrelevant_count += 1
                continue
            if candidate.decision not in {"auto_download", "human_review_required"}:
                skipped.append({"rank": source_search_rank, "source_search_rank": source_search_rank,
                    "title": candidate.title, "url": candidate.url,
                    "score": candidate.score, "decision": candidate.decision,
                    "reason": "Décision non téléchargeable automatiquement."})
                continue
            if candidate.url in seen_download_urls:
                skipped.append({"rank": source_search_rank, "source_search_rank": source_search_rank,
                    "title": candidate.title, "url": candidate.url,
                    "score": candidate.score, "decision": candidate.decision, "reason": "URL déjà traitée."})
                continue
            temp_pdf_path = self._build_temp_pdf_path(company, fiscal_year, candidate.url)
            download_response = self.downloader.download_pdf(url=candidate.url, output_path=temp_pdf_path)
            if download_response.status != "download_success":
                failed.append({"rank": storage_rank, "candidate_rank": storage_rank,
                    "source_search_rank": source_search_rank,
                    "title": candidate.title, "url": candidate.url,
                    "score": candidate.score, "decision": candidate.decision,
                    "download_status": download_response.status, "message": download_response.message,
                    "attempts": download_response.attempts})
                seen_download_urls.add(candidate.url)
                storage_rank += 1
                continue
            manifest = self.storage.store_candidate_earnings_call(temp_pdf_path=download_response.output_path,
                company=company, fiscal_year=fiscal_year,
                candidate=candidate, candidate_rank=storage_rank)
            downloaded.append({"rank": storage_rank, "candidate_rank": storage_rank,
                "source_search_rank": source_search_rank,
                "title": candidate.title, "url": candidate.url,
                "score": candidate.score, "decision": candidate.decision,
                "local_path": manifest["file"]["local_path"],
                "manifest_path": manifest["file"]["manifest_path"],
                "sha256": manifest["file"]["sha256"]})
            seen_download_urls.add(candidate.url)
            storage_rank += 1

        if resolved_below_threshold_count > 0:
            skipped.append({"rank": "?", "title": "PDFs extraits HTML sous le seuil",
                "url": None, "score": None, "decision": "reject",
                "reason": f"{resolved_below_threshold_count} PDF(s) ignorés (score < {min_score})."})
        if resolved_year_irrelevant_count > 0:
            skipped.append({"rank": "?", "title": "PDFs hors période",
                "url": None, "score": None, "decision": "reject",
                "reason": f"{resolved_year_irrelevant_count} PDF(s) hors période. Acceptés : {fiscal_year} et {fiscal_year - 1}."})
        if direct_year_irrelevant_count > 0:
            skipped.append({"rank": "?", "title": "Candidats directs hors période",
                "url": None, "score": None, "decision": "reject",
                "reason": f"{direct_year_irrelevant_count} candidat(s) hors période."})

        return DownloadResult(status="completed", message="Ingestion des candidats transcripts earnings calls terminée.",
            company_name=company.name, fiscal_year=fiscal_year,
            downloaded_count=len(downloaded), failed_count=len(failed), skipped_count=len(skipped),
            downloaded=downloaded, failed=failed, skipped=skipped)

    @staticmethod
    def _is_candidate_year_relevant(candidate, fiscal_year):
        years = extract_years(f"{candidate.title} {candidate.url}")
        if not years:
            return True
        return bool(years & {fiscal_year, fiscal_year - 1})

    def _build_temp_pdf_path(self, company, fiscal_year, source_url):
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        company_slug = slugify(company.name)
        filename = safe_filename(source_url.split("/")[-1] or "earnings_call.pdf")
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"
        return self.tmp_dir / f"{company_slug}_{fiscal_year}_{filename}"

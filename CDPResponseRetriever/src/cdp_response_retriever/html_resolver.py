from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .models import SearchCandidate


@dataclass
class ResolvedPDFLinks:
    source_url: str
    status: str
    message: str
    candidates: list[SearchCandidate]
    http_status_code: Optional[int] = None
    content_type: Optional[str] = None


class HTMLToPDFLinkResolver:
    """
    Résout une page HTML en liens PDF candidats.

    Cette classe ne télécharge pas les PDFs.
    Elle extrait seulement les liens PDF présents dans une page HTML.
    """

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def resolve(
        self,
        page_candidate: SearchCandidate,
    ) -> ResolvedPDFLinks:
        url = page_candidate.url
        headers = self._headers(url)

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            return ResolvedPDFLinks(
                source_url=url,
                status="network_error",
                message=f"Erreur réseau pendant la résolution HTML : {exc}",
                candidates=[],
            )

        content_type = response.headers.get("Content-Type", "")

        if response.status_code == 403:
            return ResolvedPDFLinks(
                source_url=url,
                status="forbidden_403",
                message="Accès refusé à la page HTML.",
                candidates=[],
                http_status_code=response.status_code,
                content_type=content_type,
            )

        if response.status_code == 404:
            return ResolvedPDFLinks(
                source_url=url,
                status="not_found_404",
                message="Page HTML introuvable.",
                candidates=[],
                http_status_code=response.status_code,
                content_type=content_type,
            )

        if response.status_code >= 400:
            return ResolvedPDFLinks(
                source_url=url,
                status="http_error",
                message=f"Erreur HTTP {response.status_code}.",
                candidates=[],
                http_status_code=response.status_code,
                content_type=content_type,
            )

        soup = BeautifulSoup(response.text, "html.parser")

        page_title = ""
        if soup.title and soup.title.string:
            page_title = soup.title.string.strip()

        pdf_candidates = self._extract_pdf_candidates(
            soup=soup,
            base_url=response.url,
            source_page_candidate=page_candidate,
            page_title=page_title,
        )

        return ResolvedPDFLinks(
            source_url=url,
            status="success",
            message=f"{len(pdf_candidates)} lien(s) PDF extrait(s).",
            candidates=pdf_candidates,
            http_status_code=response.status_code,
            content_type=content_type,
        )

    def _extract_pdf_candidates(
        self,
        soup: BeautifulSoup,
        base_url: str,
        source_page_candidate: SearchCandidate,
        page_title: str,
    ) -> list[SearchCandidate]:
        extracted: list[SearchCandidate] = []
        seen_urls = set()

        for tag in soup.find_all("a", href=True):
            href = tag.get("href", "").strip()
            full_url = urljoin(base_url, href)

            if not self._looks_like_pdf_link(full_url):
                continue

            if full_url in seen_urls:
                continue

            seen_urls.add(full_url)

            anchor_text = tag.get_text(" ", strip=True)
            title = anchor_text or self._filename_from_url(full_url) or page_title

            extracted.append(
                SearchCandidate(
                    title=title,
                    url=full_url,
                    snippet=(
                        f"PDF extrait depuis une page HTML. "
                        f"Page source : {source_page_candidate.url}. "
                        f"Titre page : {page_title}. "
                        f"Texte du lien : {anchor_text}."
                    ),
                    source_name="html_pdf_resolver",
                )
            )

        for tag_name, attr in [("iframe", "src"), ("embed", "src")]:
            for tag in soup.find_all(tag_name):
                src = tag.get(attr, "").strip()
                full_url = urljoin(base_url, src)

                if not self._looks_like_pdf_link(full_url):
                    continue

                if full_url in seen_urls:
                    continue

                seen_urls.add(full_url)

                extracted.append(
                    SearchCandidate(
                        title=self._filename_from_url(full_url) or page_title,
                        url=full_url,
                        snippet=(
                            f"PDF embarqué extrait depuis une page HTML. "
                            f"Page source : {source_page_candidate.url}. "
                            f"Titre page : {page_title}."
                        ),
                        source_name="html_pdf_resolver",
                    )
                )

        return extracted

    @staticmethod
    def _looks_like_pdf_link(url: str) -> bool:
        parsed = urlparse(url)
        lower_url = url.lower()
        lower_path = parsed.path.lower()

        return (
            lower_path.endswith(".pdf")
            or ".pdf?" in lower_url
            or ".pdf#" in lower_url
        )

    @staticmethod
    def _filename_from_url(url: str) -> str:
        parsed = urlparse(url)
        filename = parsed.path.rstrip("/").split("/")[-1]
        return filename

    @staticmethod
    def _headers(url: str) -> dict[str, str]:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "application/pdf,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
            "Referer": origin + "/",
            "Origin": origin,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

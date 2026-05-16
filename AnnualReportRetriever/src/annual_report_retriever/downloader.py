from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlunparse

import requests

from .utils import looks_like_pdf


@dataclass
class PDFDownloadAttempt:
    """
    Trace une tentative de téléchargement.
    """

    url: str
    strategy: str
    status: str
    message: str
    http_status_code: Optional[int] = None
    content_type: Optional[str] = None


@dataclass
class PDFDownloadResponse:
    """
    Résultat structuré du téléchargement.
    """

    status: str
    message: str
    url: str
    output_path: Optional[str] = None
    http_status_code: Optional[int] = None
    content_type: Optional[str] = None
    attempts: int = 0
    attempted_strategies: list[PDFDownloadAttempt] = field(default_factory=list)


class PDFDownloader:
    """
    Téléchargeur PDF robuste.

    Il gère :
    - session HTTP persistante ;
    - plusieurs profils de headers ;
    - variantes d'URL ;
    - retries ;
    - erreurs 403, 404, 429, 5xx ;
    - vérification réelle du contenu PDF.

    Il ne cherche pas à contourner agressivement les protections anti-bot.
    """

    DEFAULT_TIMEOUT = 60

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 2,
        backoff_seconds: float = 2.0,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def download_pdf(
        self,
        url: str,
        output_path: str | Path,
        user_agent: Optional[str] = None,
    ) -> PDFDownloadResponse:
        """
        Télécharge un PDF depuis une URL.

        La méthode essaie plusieurs stratégies générales avant de conclure.
        """

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        attempted_strategies: list[PDFDownloadAttempt] = []
        total_attempts = 0

        session = requests.Session()

        url_variants = self._build_url_variants(url)

        for candidate_url in url_variants:
            header_profiles = self._build_header_profiles(
                url=candidate_url,
                user_agent=user_agent,
            )

            for strategy_name, headers in header_profiles:
                for attempt_index in range(1, self.max_retries + 2):
                    total_attempts += 1

                    try:
                        response = session.get(
                            candidate_url,
                            headers=headers,
                            timeout=self.timeout,
                            allow_redirects=True,
                        )

                        content_type = response.headers.get("Content-Type", "")

                        # -------------------------------
                        # Succès HTTP apparent
                        # -------------------------------
                        if 200 <= response.status_code <= 299:
                            output_path.write_bytes(response.content)

                            if looks_like_pdf(output_path):
                                attempted_strategies.append(
                                    PDFDownloadAttempt(
                                        url=candidate_url,
                                        strategy=strategy_name,
                                        status="download_success",
                                        message="PDF valide téléchargé.",
                                        http_status_code=response.status_code,
                                        content_type=content_type,
                                    )
                                )

                                return PDFDownloadResponse(
                                    status="download_success",
                                    message="PDF téléchargé avec succès.",
                                    url=candidate_url,
                                    output_path=str(output_path),
                                    http_status_code=response.status_code,
                                    content_type=content_type,
                                    attempts=total_attempts,
                                    attempted_strategies=attempted_strategies,
                                )

                            output_path.unlink(missing_ok=True)

                            attempted_strategies.append(
                                PDFDownloadAttempt(
                                    url=candidate_url,
                                    strategy=strategy_name,
                                    status="not_a_pdf",
                                    message=(
                                        "Réponse HTTP 2xx, mais le contenu "
                                        "n'est pas un PDF valide."
                                    ),
                                    http_status_code=response.status_code,
                                    content_type=content_type,
                                )
                            )

                            # On essaie les autres stratégies : parfois le serveur
                            # renvoie une page HTML avec certains headers.
                            break

                        # -------------------------------
                        # Erreurs HTTP explicites
                        # -------------------------------
                        if response.status_code == 403:
                            attempted_strategies.append(
                                PDFDownloadAttempt(
                                    url=candidate_url,
                                    strategy=strategy_name,
                                    status="forbidden_403",
                                    message="Accès refusé par le serveur.",
                                    http_status_code=response.status_code,
                                    content_type=content_type,
                                )
                            )
                            break

                        if response.status_code == 404:
                            attempted_strategies.append(
                                PDFDownloadAttempt(
                                    url=candidate_url,
                                    strategy=strategy_name,
                                    status="not_found_404",
                                    message="Document introuvable.",
                                    http_status_code=response.status_code,
                                    content_type=content_type,
                                )
                            )
                            break

                        if response.status_code == 429:
                            attempted_strategies.append(
                                PDFDownloadAttempt(
                                    url=candidate_url,
                                    strategy=strategy_name,
                                    status="rate_limited_429",
                                    message="Trop de requêtes.",
                                    http_status_code=response.status_code,
                                    content_type=content_type,
                                )
                            )

                            if attempt_index <= self.max_retries:
                                time.sleep(self.backoff_seconds * attempt_index)
                                continue

                            break

                        if 500 <= response.status_code <= 599:
                            attempted_strategies.append(
                                PDFDownloadAttempt(
                                    url=candidate_url,
                                    strategy=strategy_name,
                                    status="server_error_5xx",
                                    message=f"Erreur serveur HTTP {response.status_code}.",
                                    http_status_code=response.status_code,
                                    content_type=content_type,
                                )
                            )

                            if attempt_index <= self.max_retries:
                                time.sleep(self.backoff_seconds * attempt_index)
                                continue

                            break

                        if 400 <= response.status_code <= 499:
                            attempted_strategies.append(
                                PDFDownloadAttempt(
                                    url=candidate_url,
                                    strategy=strategy_name,
                                    status="client_error_4xx",
                                    message=f"Erreur client HTTP {response.status_code}.",
                                    http_status_code=response.status_code,
                                    content_type=content_type,
                                )
                            )
                            break

                        attempted_strategies.append(
                            PDFDownloadAttempt(
                                url=candidate_url,
                                strategy=strategy_name,
                                status="unexpected_http_status",
                                message=f"Statut HTTP inattendu : {response.status_code}.",
                                http_status_code=response.status_code,
                                content_type=content_type,
                            )
                        )
                        break

                    except requests.Timeout:
                        attempted_strategies.append(
                            PDFDownloadAttempt(
                                url=candidate_url,
                                strategy=strategy_name,
                                status="timeout",
                                message="Timeout pendant le téléchargement.",
                            )
                        )

                        if attempt_index <= self.max_retries:
                            time.sleep(self.backoff_seconds * attempt_index)
                            continue

                        break

                    except requests.ConnectionError:
                        attempted_strategies.append(
                            PDFDownloadAttempt(
                                url=candidate_url,
                                strategy=strategy_name,
                                status="connection_error",
                                message="Erreur de connexion.",
                            )
                        )

                        if attempt_index <= self.max_retries:
                            time.sleep(self.backoff_seconds * attempt_index)
                            continue

                        break

                    except requests.RequestException as exc:
                        attempted_strategies.append(
                            PDFDownloadAttempt(
                                url=candidate_url,
                                strategy=strategy_name,
                                status="network_error",
                                message=f"Erreur réseau : {exc}",
                            )
                        )
                        break

        final_status = self._infer_final_status(attempted_strategies)

        return PDFDownloadResponse(
            status=final_status,
            message=self._final_message(final_status),
            url=url,
            output_path=None,
            http_status_code=self._last_http_status(attempted_strategies),
            content_type=self._last_content_type(attempted_strategies),
            attempts=total_attempts,
            attempted_strategies=attempted_strategies,
        )

    # ========================================================
    # Stratégies URL
    # ========================================================

    def _build_url_variants(self, url: str) -> list[str]:
        """
        Construit des variantes raisonnables de l'URL.

        Exemple :
        - URL originale avec paramètres
        - URL sans paramètres
        """

        variants = []

        original = url.strip()
        if original:
            variants.append(original)

        parsed = urlparse(original)

        if parsed.query:
            without_query = urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    "",
                    parsed.fragment,
                )
            )

            if without_query not in variants:
                variants.append(without_query)

        # Cas fréquent : URL terminant par ".pdf?"
        if original.endswith("?"):
            clean = original.rstrip("?")
            if clean not in variants:
                variants.append(clean)

        return variants

    # ========================================================
    # Stratégies headers
    # ========================================================

    def _build_header_profiles(
        self,
        url: str,
        user_agent: Optional[str] = None,
    ) -> list[tuple[str, dict[str, str]]]:
        """
        Construit plusieurs profils de headers HTTP.

        L'idée est de simuler une requête navigateur raisonnable,
        sans contournement agressif.
        """

        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        referer = origin + "/"

        ua = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        return [
            (
                "basic_pdf_request",
                {
                    "User-Agent": ua,
                    "Accept": "application/pdf,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
                    "Connection": "keep-alive",
                },
            ),
            (
                "browser_navigation_request",
                {
                    "User-Agent": ua,
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;q=0.9,"
                        "application/pdf,*/*;q=0.8"
                    ),
                    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
                    "Referer": referer,
                    "Origin": origin,
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
            ),
            (
                "browser_pdf_with_fetch_headers",
                {
                    "User-Agent": ua,
                    "Accept": "application/pdf,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
                    "Referer": referer,
                    "Origin": origin,
                    "Connection": "keep-alive",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1",
                },
            ),
        ]

    # ========================================================
    # Diagnostics finaux
    # ========================================================

    @staticmethod
    def _infer_final_status(
        attempts: list[PDFDownloadAttempt],
    ) -> str:
        statuses = [a.status for a in attempts]

        if "download_success" in statuses:
            return "download_success"

        if statuses and all(status == "forbidden_403" for status in statuses):
            return "forbidden_403"

        if "forbidden_403" in statuses:
            return "blocked_or_forbidden"

        if "rate_limited_429" in statuses:
            return "rate_limited_429"

        if "server_error_5xx" in statuses:
            return "server_error_5xx"

        if "not_a_pdf" in statuses:
            return "not_a_pdf"

        if "not_found_404" in statuses:
            return "not_found_404"

        if "timeout" in statuses:
            return "timeout"

        if "connection_error" in statuses:
            return "connection_error"

        if "network_error" in statuses:
            return "network_error"

        return "all_strategies_failed"

    @staticmethod
    def _final_message(status: str) -> str:
        messages = {
            "download_success": "PDF téléchargé avec succès.",
            "forbidden_403": "Accès refusé par le serveur pour toutes les stratégies.",
            "blocked_or_forbidden": "Le serveur bloque certaines ou toutes les stratégies de téléchargement.",
            "rate_limited_429": "Trop de requêtes : accès limité par le serveur.",
            "server_error_5xx": "Erreur serveur persistante.",
            "not_a_pdf": "Les réponses obtenues ne sont pas des PDFs valides.",
            "not_found_404": "Document introuvable.",
            "timeout": "Timeout pendant le téléchargement.",
            "connection_error": "Erreur de connexion.",
            "network_error": "Erreur réseau.",
            "all_strategies_failed": "Toutes les stratégies de téléchargement ont échoué.",
        }

        return messages.get(status, "Échec du téléchargement.")

    @staticmethod
    def _last_http_status(
        attempts: list[PDFDownloadAttempt],
    ) -> Optional[int]:
        for attempt in reversed(attempts):
            if attempt.http_status_code is not None:
                return attempt.http_status_code
        return None

    @staticmethod
    def _last_content_type(
        attempts: list[PDFDownloadAttempt],
    ) -> Optional[str]:
        for attempt in reversed(attempts):
            if attempt.content_type is not None:
                return attempt.content_type
        return None
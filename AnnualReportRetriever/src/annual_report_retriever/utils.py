from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse


def normalize_text(text: str) -> str:
    """
    Normalise un texte pour faciliter les comparaisons.

    Exemple :
        "Document d'Enregistrement Universel"
        devient :
        "document d enregistrement universel"
    """

    if text is None:
        return ""

    text = str(text).lower()
    text = remove_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def remove_accents(text: str) -> str:
    """
    Supprime les accents d'une chaîne de caractères.

    Exemple :
        "énergie" -> "energie"
        "société" -> "societe"
    """

    normalized = unicodedata.normalize("NFD", text)
    return "".join(
        char for char in normalized
        if unicodedata.category(char) != "Mn"
    )


def slugify(text: str) -> str:
    """
    Transforme un nom en identifiant utilisable dans un chemin de fichier.

    Exemple :
        "TotalEnergies SE" -> "totalenergies-se"
        "L'Oréal" -> "l-oreal"
    """

    text = normalize_text(text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)

    return text.strip("-") or "unknown"


def safe_filename(filename: str) -> str:
    """
    Nettoie un nom de fichier pour éviter les caractères problématiques.

    Exemple :
        "rapport annuel 2024.pdf" -> "rapport_annuel_2024.pdf"
    """

    filename = Path(filename).name
    filename = remove_accents(filename)
    filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename)
    filename = re.sub(r"_+", "_", filename)

    return filename.strip("_") or "document.pdf"


def extract_domain(url: str) -> str:
    """
    Extrait le domaine principal d'une URL.

    Exemple :
        "https://www.totalenergies.com/investors/report.pdf"
        -> "totalenergies.com"
    """

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def is_pdf_url(url: str) -> bool:
    """
    Vérifie si une URL semble pointer directement vers un PDF.

    Cas couverts :
    - https://site.com/report.pdf
    - https://site.com/report.pdf?download=1
    - https://site.com/viewDoc.aspx?filename=report.PDF
    """

    if not url:
        return False

    parsed = urlparse(url)
    full_url = url.lower()
    path = parsed.path.lower()
    query = parsed.query.lower()

    return (
        path.endswith(".pdf")
        or ".pdf?" in full_url
        or ".pdf#" in full_url
        or ".pdf" in query
    )


def compute_sha256(file_path: str | Path) -> str:
    """
    Calcule le hash SHA-256 d'un fichier.

    Le hash permet :
    - d'identifier un document de manière unique ;
    - de détecter les doublons ;
    - d'assurer la traçabilité.
    """

    file_path = Path(file_path)
    h = hashlib.sha256()

    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def looks_like_pdf(file_path: str | Path) -> bool:
    """
    Vérifie rapidement si un fichier ressemble à un PDF.

    Un fichier PDF commence généralement par les caractères binaires :
        %PDF-
    """

    file_path = Path(file_path)

    try:
        with file_path.open("rb") as f:
            header = f.read(5)
        return header == b"%PDF-"
    except OSError:
        return False


def file_size_mb(file_path: str | Path) -> float:
    """
    Retourne la taille du fichier en mégaoctets.
    """

    file_path = Path(file_path)
    return round(file_path.stat().st_size / (1024 * 1024), 4)


def extract_years(text: str) -> set[int]:
    """
    Extrait les années présentes dans un texte.

    Exemple :
        "Annual Report 2024 published in 2025"
        -> {2024, 2025}
    """

    years = set()

    for match in re.findall(r"\b(19\d{2}|20\d{2})\b", text):
        try:
            years.add(int(match))
        except ValueError:
            pass

    return years


def company_name_matches(company_name: str, text: str) -> bool:
    """
    Vérifie si le nom de l'entreprise semble apparaître dans un texte.

    Cette fonction reste volontairement simple pour l'instant.
    Elle sera améliorée plus tard si nécessaire.

    Exemple :
        company_name = "TotalEnergies"
        text = "TotalEnergies Universal Registration Document 2024"
        -> True
    """

    company_norm = normalize_text(company_name)
    text_norm = normalize_text(text)

    if not company_norm or not text_norm:
        return False

    company_compact = re.sub(r"[^a-z0-9]+", "", company_norm)
    text_compact = re.sub(r"[^a-z0-9]+", "", text_norm)

    if company_compact in text_compact:
        return True

    company_tokens = [
        token for token in company_norm.split()
        if len(token) >= 3
    ]

    if not company_tokens:
        return False

    matched_tokens = sum(
        1 for token in company_tokens
        if token in text_norm
    )

    return matched_tokens / len(company_tokens) >= 0.6


def official_domain_matches(candidate_domain: str, official_domain: str | None) -> bool:
    """
    Vérifie si le domaine candidat correspond au domaine officiel connu.

    Exemple :
        candidate_domain = "totalenergies.com"
        official_domain = "totalenergies.com"
        -> True
    """

    if not official_domain:
        return False

    candidate_domain = candidate_domain.lower().replace("www.", "")
    official_domain = official_domain.lower().replace("www.", "")

    return (
        candidate_domain == official_domain
        or candidate_domain.endswith("." + official_domain)
    )
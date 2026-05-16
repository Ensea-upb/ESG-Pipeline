from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse


def remove_accents(text: str) -> str:
    """
    Supprime les accents d'un texte.

    Exemple :
        "durabilité" -> "durabilite"
    """

    normalized = unicodedata.normalize("NFD", str(text))
    return "".join(
        char for char in normalized
        if unicodedata.category(char) != "Mn"
    )


def normalize_text(text: str) -> str:
    """
    Normalise un texte pour faciliter les comparaisons.

    Exemple :
        "Rapport de Durabilité 2024"
        -> "rapport de durabilite 2024"
    """

    if text is None:
        return ""

    text = str(text).lower()
    text = remove_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def compact_text(text: str) -> str:
    """
    Normalise un texte puis supprime les espaces.

    Exemple :
        "Sustainability Report 2024"
        -> "sustainabilityreport2024"
    """

    return normalize_text(text).replace(" ", "")


def slugify(text: str) -> str:
    """
    Transforme un nom en identifiant utilisable dans un chemin.

    Exemple :
        "Schneider Electric" -> "schneider-electric"
    """

    text = normalize_text(text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)

    return text.strip("-") or "unknown"


def safe_filename(filename: str) -> str:
    """
    Nettoie un nom de fichier pour éviter les caractères problématiques.
    """

    filename = Path(filename).name
    filename = remove_accents(filename)
    filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename)
    filename = re.sub(r"_+", "_", filename)

    return filename.strip("_") or "document.pdf"


def extract_domain(url: str) -> str:
    """
    Extrait le domaine d'une URL.

    Exemple :
        https://www.lvmh.com/documents/report.pdf
        -> lvmh.com
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


def extract_years(text: str) -> set[int]:
    """
    Extrait les années présentes dans un texte ou une URL.

    Cette version détecte aussi les années dans des noms de fichiers comme :
        NYSE_TTE_2021.pdf
        report-2024.pdf
        document_2023_en.pdf
    """

    years = set()

    if text is None:
        return years

    text = str(text)

    # On détecte les années non collées à d'autres chiffres.
    # Cela marche avec :
    # - "2024"
    # - "_2024"
    # - "-2024"
    # - "2024.pdf"
    # mais évite les nombres plus longs.
    matches = re.findall(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", text)

    for match in matches:
        try:
            years.add(int(match))
        except ValueError:
            pass

    return years


def compute_sha256(file_path: str | Path) -> str:
    """
    Calcule le hash SHA-256 d'un fichier.

    Sert à :
    - tracer le document ;
    - détecter les doublons ;
    - auditer l'ingestion.
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

    Un PDF commence généralement par :
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
    Retourne la taille d'un fichier en mégaoctets.
    """

    file_path = Path(file_path)
    return round(file_path.stat().st_size / (1024 * 1024), 4)


def company_name_matches(company_name: str, text: str) -> bool:
    """
    Vérifie si le nom de l'entreprise semble apparaître dans un texte.

    Exemple :
        company_name = "LVMH"
        text = "LVMH Sustainability Report 2024"
        -> True
    """

    company_norm = normalize_text(company_name)
    text_norm = normalize_text(text)

    if not company_norm or not text_norm:
        return False

    company_compact = compact_text(company_name)
    text_compact = compact_text(text)

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
    Vérifie si un domaine candidat correspond au domaine officiel.

    Exemple :
        candidate_domain = "sustainability.lvmh.com"
        official_domain = "lvmh.com"
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
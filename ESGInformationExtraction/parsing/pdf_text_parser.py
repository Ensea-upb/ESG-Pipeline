"""
pdf_text_parser.py
==================
Extrait le texte page par page d'un PDF.

Ce module est NON DESTRUCTIF : il ne modifie jamais le PDF source.
Il ne doit PAS être lancé massivement sans supervision.

Dépendance : pdfplumber (pip install pdfplumber).
Si pdfplumber n'est pas installé, les fonctions lèvent ImportError
avec un message explicite.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator


def _require_pdfplumber():
    try:
        import pdfplumber
        return pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber n'est pas installé. "
            "Lancez : pip install pdfplumber\n"
            "Ce module ne peut pas extraire de texte sans pdfplumber."
        )


def parse_pdf_pages(pdf_path: Path) -> list[dict]:
    """
    Extrait le texte de chaque page d'un PDF.
    Ne modifie pas le fichier source.

    Retourne une liste de dicts :
    {
        "page_number": int (1-indexé),
        "text": str,
        "char_count": int,
        "has_tables": bool,
    }

    Lève FileNotFoundError si le PDF n'existe pas.
    Lève ImportError si pdfplumber n'est pas installé.
    """
    pdfplumber = _require_pdfplumber()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF introuvable : {pdf_path}")

    results = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            tables = page.extract_tables() or []
            results.append({
                "page_number": i,
                "text": text,
                "char_count": len(text),
                "has_tables": len(tables) > 0,
            })
    return results


def parse_pdf_pages_iter(pdf_path: Path) -> Iterator[dict]:
    """
    Version itératrice de parse_pdf_pages — pour les grands PDFs.
    Yield une page à la fois pour limiter la mémoire utilisée.
    """
    pdfplumber = _require_pdfplumber()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF introuvable : {pdf_path}")

    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            tables = page.extract_tables() or []
            yield {
                "page_number": i,
                "text": text,
                "char_count": len(text),
                "has_tables": len(tables) > 0,
            }


def get_pdf_page_count(pdf_path: Path) -> int:
    """
    Retourne le nombre de pages sans extraire le texte.
    Utile pour filtrer les PDFs trop volumineux avant parsing.
    """
    pdfplumber = _require_pdfplumber()
    with pdfplumber.open(str(pdf_path)) as pdf:
        return len(pdf.pages)

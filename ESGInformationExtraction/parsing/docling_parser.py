"""
docling_parser.py
=================
Parser PDF moderne basé sur Docling (IBM Research, 2024-2025).

Docling utilise DocLayNet (RT-DETR) pour la mise en page et TableFormer
(vision transformer) pour reconstruire la structure des tableaux avec
headers multi-niveaux et cellules fusionnées.

Benchmark terrain (2025) : 97.9% sur tableaux complexes, 3.1 sec/page CPU.
Source : https://arxiv.org/html/2501.17887v1

Si Docling n'est pas installé, fallback transparent sur pdfplumber.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def _try_import_docling():
    try:
        from docling.document_converter import DocumentConverter
        return DocumentConverter
    except ImportError:
        return None


def parse_pdf_docling(pdf_path: Path) -> list[dict[str, Any]]:
    """Parse un PDF avec Docling et retourne une liste de pages enrichies.

    Interface compatible avec parse_pdf_pages() de pdf_text_parser.py.

    Chaque page retournée contient :
    {
        "page_number": int,
        "text": str,                  # texte complet de la page (paragraphes + tables)
        "char_count": int,
        "has_tables": bool,
        "blocks": list[dict],         # blocs typés : {type, text}
        "tables_structured": list[dict], # tables : {markdown, headers, rows}
        "parser": "docling" | "pdfplumber",
    }

    Fallback sur pdfplumber si Docling n'est pas installé.
    """
    DocumentConverter = _try_import_docling()
    if DocumentConverter is None:
        log.warning("Docling non installé — fallback pdfplumber. Installez : pip install docling")
        return _fallback_pdfplumber(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF introuvable : {pdf_path}")

    try:
        converter = DocumentConverter()
        result = converter.convert(str(pdf_path))
        return _build_pages_from_docling(result)
    except Exception as exc:
        log.warning("Docling a échoué (%s) — fallback pdfplumber", exc)
        return _fallback_pdfplumber(pdf_path)


def _build_pages_from_docling(result: Any) -> list[dict[str, Any]]:
    doc = result.document
    pages: dict[int, dict[str, Any]] = {}

    def _get_page(page_no: int) -> dict[str, Any]:
        if page_no not in pages:
            pages[page_no] = {
                "page_number": page_no,
                "text": "",
                "char_count": 0,
                "has_tables": False,
                "blocks": [],
                "tables_structured": [],
                "parser": "docling",
            }
        return pages[page_no]

    # Docling 2.x API: iterate_items() yields (item, level)
    for item, _level in doc.iterate_items():
        page_no = _page_no_from_item(item)
        page = _get_page(page_no)
        label = str(getattr(item, "label", "")).lower()

        if "table" in label:
            page["has_tables"] = True
            try:
                markdown = item.export_to_markdown()
            except Exception:
                markdown = ""
            table_entry: dict[str, Any] = {"markdown": markdown, "headers": [], "rows": []}
            try:
                df = item.export_to_dataframe()
                table_entry["headers"] = list(df.columns)
                table_entry["rows"] = [list(row) for row in df.values]
            except Exception:
                pass
            page["tables_structured"].append(table_entry)
            page["blocks"].append({"type": "table", "text": markdown})
            page["text"] += markdown + "\n"

        elif "section" in label or "heading" in label or "title" in label:
            text = getattr(item, "text", "") or ""
            page["blocks"].append({"type": "heading", "text": text})
            page["text"] += text + "\n"

        elif "text" in label or "paragraph" in label or "list" in label:
            text = getattr(item, "text", "") or ""
            page["blocks"].append({"type": "paragraph", "text": text})
            page["text"] += text + "\n"

    for page in pages.values():
        page["char_count"] = len(page["text"])

    return sorted(pages.values(), key=lambda p: p["page_number"])


def _page_no_from_item(item: Any) -> int:
    try:
        prov = getattr(item, "prov", None)
        if prov:
            first = prov[0] if isinstance(prov, list) else prov
            return int(getattr(first, "page_no", 1))
    except Exception:
        pass
    return 1


def _fallback_pdfplumber(pdf_path: Path) -> list[dict[str, Any]]:
    from .pdf_text_parser import parse_pdf_pages
    pages = parse_pdf_pages(pdf_path)
    for page in pages:
        page["parser"] = "pdfplumber"
        page.setdefault("blocks", [])
        page.setdefault("tables_structured", [])
    return pages

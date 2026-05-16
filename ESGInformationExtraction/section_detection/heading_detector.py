"""
heading_detector.py
===================
Détection de titres de sections par règles simples (sans modèle lourd).

Heuristiques utilisées :
- Ligne courte (< 80 caractères) sans point final
- Présence de mots-clés de la section_taxonomy_v0.yaml
- Majuscules ou numérotation (ex: "3.2 Émissions GES")
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional

import yaml


def _load_taxonomy(taxonomy_path: Optional[Path] = None) -> dict:
    if taxonomy_path is None:
        taxonomy_path = (
            Path(__file__).resolve().parents[1]
            / "config"
            / "section_taxonomy_v0.yaml"
        )
    if not taxonomy_path.exists():
        return {}
    return yaml.safe_load(taxonomy_path.read_text(encoding="utf-8")) or {}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text).strip()


_TOC_PATTERN = re.compile(r"\d+\s+\d+\.\d+|\s{3,}\d+\s*$")


def _is_heading_candidate(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 90:
        return False
    if line.endswith(".") and len(line) > 40:
        return False
    # Skip table-of-contents lines ("1.1 Title 6  7.2 Other title 12")
    if _TOC_PATTERN.search(line):
        return False
    # Numbered section: "1.2 Our strategy" or "3. Climate"
    if re.match(r"^[\d]{1,2}[\.\d]*\s{1,3}[A-ZÀ-Ža-z]", line):
        return True
    # All uppercase title with meaningful length (avoid page numbers like "06")
    if line == line.upper() and len(line) > 8 and re.search(r"[A-Z]{3,}", line):
        return True
    return False


def detect_headings(
    pages: list[dict],
    taxonomy: Optional[dict] = None,
) -> list[dict]:
    """
    Détecte les titres candidats dans une liste de pages.
    Ne modifie pas les pages source.

    Retourne une liste de dicts :
    {
        "line": str,
        "page_number": int,
        "section_type": str,
        "confidence": float,
    }
    """
    if taxonomy is None:
        taxonomy = _load_taxonomy()

    keyword_map: dict[str, str] = {}
    for section_type, info in taxonomy.items():
        for kw in info.get("heading_keywords_fr", []) + info.get("heading_keywords_en", []):
            keyword_map[_normalize(kw)] = section_type

    results = []
    for page in pages:
        page_number = page.get("page_number", 0)
        text = page.get("text", "")
        for line in text.splitlines():
            if not _is_heading_candidate(line):
                continue
            line_norm = _normalize(line)
            matched_type = "unknown"
            confidence = 0.3
            for kw, stype in keyword_map.items():
                if kw in line_norm:
                    matched_type = stype
                    confidence = 0.7
                    break
            results.append({
                "line": line.strip(),
                "page_number": page_number,
                "section_type": matched_type,
                "confidence": confidence,
            })
    return results

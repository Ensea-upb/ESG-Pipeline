"""
build_document_base.py
======================
Lit un dossier ESGFinalCorpus en lecture seule.
Détecte les couples (document.pdf, manifest.json) et construit
une liste de DocumentRecord.

Ce module NE MODIFIE JAMAIS le corpus source.
Toutes les sorties vont dans un dossier output séparé.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

from ..schemas.document_record import DocumentRecord


def _load_manifest(manifest_path: Path) -> dict:
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _slug_from_name(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


def scan_corpus(corpus_path: Path) -> list[DocumentRecord]:
    """
    Parcourt corpus_path en lecture seule.
    Detecte tous les PDFs accompagnés d'un manifest.json voisin.
    Retourne une liste de DocumentRecord.

    Le corpus n'est jamais modifié.
    """
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus introuvable : {corpus_path}")
    if not corpus_path.is_dir():
        raise NotADirectoryError(f"Le chemin n'est pas un dossier : {corpus_path}")

    records: list[DocumentRecord] = []

    for pdf_path in sorted(corpus_path.rglob("*.pdf")):
        manifest_path = pdf_path.with_suffix(".pdf").parent / "manifest.json"
        candidate_manifest = pdf_path.with_name(pdf_path.stem + "_manifest.json")

        actual_manifest: Optional[Path] = None
        if candidate_manifest.exists():
            actual_manifest = candidate_manifest
        elif manifest_path.exists():
            actual_manifest = manifest_path

        manifest_data = _load_manifest(actual_manifest) if actual_manifest else {}

        company_name = (
            manifest_data.get("company_name")
            or manifest_data.get("company", {}).get("name")
            or "unknown"
        )
        company_slug = (
            manifest_data.get("company_slug")
            or _slug_from_name(company_name)
        )
        fiscal_year = (
            manifest_data.get("fiscal_year")
            or manifest_data.get("reference_year")
            or 0
        )
        doc_type = (
            manifest_data.get("official_doc_type")
            or manifest_data.get("document_type")
            or "unknown"
        )
        doc_type_label = (
            manifest_data.get("official_doc_type_label")
            or doc_type.replace("_", " ").title()
        )
        sha256 = (
            manifest_data.get("sha256")
            or manifest_data.get("file", {}).get("sha256", "")
        )
        canonical_document_id = manifest_data.get("canonical_document_id")
        source_url = manifest_data.get("source_url") or manifest_data.get("source", {}).get("url")
        source_title = manifest_data.get("source_title") or manifest_data.get("source", {}).get("title")

        references_path = pdf_path.parent / "references.json"

        record = DocumentRecord(
            document_id=str(uuid.uuid4()),
            canonical_document_id=canonical_document_id,
            sha256=sha256,
            company_name=company_name,
            company_slug=company_slug,
            fiscal_year=int(fiscal_year) if fiscal_year else 0,
            official_doc_type=doc_type,
            official_doc_type_label=doc_type_label,
            document_path=str(pdf_path),
            manifest_path=str(actual_manifest) if actual_manifest else None,
            references_path=str(references_path) if references_path.exists() else None,
            source_url=source_url,
            source_title=source_title,
            selection_status="candidate",
            extraction_ready=bool(sha256 and fiscal_year),
        )
        records.append(record)

    return records


def write_document_base(
    records: list[DocumentRecord],
    output_dir: Path,
    filename: str = "document_base.jsonl",
) -> Path:
    """
    Écrit les DocumentRecord dans un fichier JSONL dans output_dir.
    N'écrit jamais dans le corpus source.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")
    return output_path


def build_document_base(
    corpus_path: Path,
    output_dir: Path,
) -> tuple[list[DocumentRecord], Path]:
    """
    Point d'entrée principal.
    Scanne corpus_path (lecture seule), construit les DocumentRecord,
    les écrit dans output_dir/document_base.jsonl.

    Retourne (records, output_path).
    """
    records = scan_corpus(corpus_path)
    output_path = write_document_base(records, output_dir)
    return records, output_path

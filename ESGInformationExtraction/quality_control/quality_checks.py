"""
quality_checks.py
=================
Contrôles qualité sur les records produits par le pipeline d'extraction.

Chaque check retourne un QualityCheckRecord.
Ne modifie jamais les données source.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from ..schemas.document_record import DocumentRecord
from ..schemas.page_record import PageRecord
from ..schemas.section_record import SectionRecord
from ..schemas.evidence_record import EvidenceRecord
from ..schemas.quality_check_record import QualityCheckRecord


def check_document_path_exists(document: DocumentRecord) -> QualityCheckRecord:
    path = Path(document.document_path)
    exists = path.exists()
    return QualityCheckRecord(
        quality_check_id=str(uuid.uuid4()),
        target_type="document",
        target_id=document.document_id,
        check_name="document_path_exists",
        status="pass" if exists else "fail",
        severity="critical",
        message=f"PDF trouvé : {path}" if exists else f"PDF introuvable : {path}",
        review_required=not exists,
    )


def check_fiscal_year_consistency(
    document: DocumentRecord,
    pages: list[PageRecord],
) -> QualityCheckRecord:
    """Vérifie que le fiscal_year du document est cohérent avec celui des pages."""
    inconsistent = [
        p.page_number
        for p in pages
        if p.fiscal_year != document.fiscal_year
    ]
    ok = len(inconsistent) == 0
    return QualityCheckRecord(
        quality_check_id=str(uuid.uuid4()),
        target_type="document",
        target_id=document.document_id,
        check_name="fiscal_year_consistency",
        status="pass" if ok else "fail",
        severity="major",
        message=(
            "fiscal_year cohérent sur toutes les pages."
            if ok
            else f"Incohérence fiscal_year sur pages : {inconsistent[:10]}"
        ),
        review_required=not ok,
    )


def check_empty_text(page: PageRecord, min_chars: int = 50) -> QualityCheckRecord:
    ok = page.char_count >= min_chars
    return QualityCheckRecord(
        quality_check_id=str(uuid.uuid4()),
        target_type="page",
        target_id=page.page_id,
        check_name="empty_text_check",
        status="pass" if ok else "warning",
        severity="minor",
        message=(
            f"Page {page.page_number} : {page.char_count} caractères."
            if ok
            else f"Page {page.page_number} vide ou quasi-vide ({page.char_count} chars)."
        ),
        review_required=False,
    )


def check_missing_evidence(
    document: DocumentRecord,
    evidence_records: list[EvidenceRecord],
) -> QualityCheckRecord:
    has_evidence = len(evidence_records) > 0
    return QualityCheckRecord(
        quality_check_id=str(uuid.uuid4()),
        target_type="document",
        target_id=document.document_id,
        check_name="missing_evidence_check",
        status="pass" if has_evidence else "warning",
        severity="major",
        message=(
            f"{len(evidence_records)} extrait(s) de preuve trouvé(s)."
            if has_evidence
            else "Aucune preuve textuelle détectée dans ce document."
        ),
        review_required=not has_evidence,
    )


def check_confidence_threshold(
    evidence: EvidenceRecord,
    min_confidence: float = 0.25,
) -> QualityCheckRecord:
    ok = evidence.confidence >= min_confidence
    return QualityCheckRecord(
        quality_check_id=str(uuid.uuid4()),
        target_type="evidence",
        target_id=evidence.evidence_id,
        check_name="confidence_threshold_check",
        status="pass" if ok else "warning",
        severity="minor",
        message=(
            f"Confidence {evidence.confidence:.2f} >= seuil {min_confidence}."
            if ok
            else f"Confidence {evidence.confidence:.2f} < seuil {min_confidence}."
        ),
        review_required=False,
    )


def write_quality_report(
    records: list[QualityCheckRecord],
    output_dir: Path,
    filename: str = "quality_report.jsonl",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    with output_path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")
    return output_path

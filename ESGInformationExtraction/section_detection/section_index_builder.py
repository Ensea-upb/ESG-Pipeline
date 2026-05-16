"""
section_index_builder.py
========================
Transforme les headings détectés en SectionRecord.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from ..schemas.document_record import DocumentRecord
from ..schemas.section_record import SectionRecord


def build_section_records(
    document: DocumentRecord,
    headings: list[dict],
) -> list[SectionRecord]:
    """
    Convertit les headings détectés (sortie de heading_detector.detect_headings)
    en SectionRecord.

    Calcule page_end = page_start du heading suivant - 1.
    Ne modifie pas le document source.
    """
    records = []
    for i, heading in enumerate(headings):
        page_start = heading["page_number"]
        page_end = headings[i + 1]["page_number"] - 1 if i + 1 < len(headings) else None

        records.append(SectionRecord(
            section_id=str(uuid.uuid4()),
            document_id=document.document_id,
            company_slug=document.company_slug,
            fiscal_year=document.fiscal_year,
            official_doc_type=document.official_doc_type,
            section_title=heading["line"],
            section_type=heading.get("section_type", "unknown"),
            page_start=page_start,
            page_end=page_end,
            confidence=heading.get("confidence", 0.0),
            detection_method="rule_based",
        ))
    return records


def write_section_index(
    records: list[SectionRecord],
    output_dir: Path,
    filename: str = "section_index.jsonl",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    with output_path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")
    return output_path

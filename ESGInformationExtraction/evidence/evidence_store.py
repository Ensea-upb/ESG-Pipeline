"""
evidence_store.py
=================
Construit et stocke les EvidenceRecord à partir des candidats métriques.

Un EvidenceRecord est un extrait de texte traçable (quote + page).
Il ne contient pas la valeur normalisée — c'est le MetricRecord qui porte ça.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from ..schemas.document_record import DocumentRecord
from ..schemas.section_record import SectionRecord
from ..schemas.evidence_record import EvidenceRecord


def build_evidence_records(
    document: DocumentRecord,
    metric_candidates: list[dict],
    section_records: list[SectionRecord],
) -> list[EvidenceRecord]:
    """
    Convertit des candidats métriques en EvidenceRecord.

    metric_candidates : sortie de metric_candidate_extractor.extract_metric_candidates
    section_records   : sortie de section_index_builder.build_section_records

    Associe chaque candidat à la section couvrant sa page (si disponible).
    Ne modifie pas les données source.
    """
    # Build a page → section_id lookup
    page_to_section: dict[int, str] = {}
    for sr in section_records:
        start = sr.page_start
        end = sr.page_end if sr.page_end is not None else start
        for p in range(start, end + 1):
            page_to_section[p] = sr.section_id

    records = []
    for candidate in metric_candidates:
        page_number = candidate.get("page_number", 0)
        quote = candidate.get("context_snippet", "")

        records.append(EvidenceRecord(
            evidence_id=str(uuid.uuid4()),
            document_id=document.document_id,
            company_slug=document.company_slug,
            fiscal_year=document.fiscal_year,
            official_doc_type=document.official_doc_type,
            page_number=page_number,
            section_id=page_to_section.get(page_number),
            quote=quote,
            confidence=candidate.get("confidence", 0.1),
            extraction_method="keyword_regex",
        ))
    return records


def write_evidence_store(
    records: list[EvidenceRecord],
    output_dir: Path,
    filename: str = "evidence_store.jsonl",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    with output_path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")
    return output_path

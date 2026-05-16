"""
test_schemas.py
===============
Tests minimaux d'instanciation pour les 6 schemas.
Vérifie que les champs obligatoires sont présents et que les defaults fonctionnent.
"""

import uuid
import pytest

from ESGInformationExtraction.schemas.document_record import DocumentRecord
from ESGInformationExtraction.schemas.page_record import PageRecord
from ESGInformationExtraction.schemas.section_record import SectionRecord
from ESGInformationExtraction.schemas.metric_record import MetricRecord
from ESGInformationExtraction.schemas.evidence_record import EvidenceRecord
from ESGInformationExtraction.schemas.quality_check_record import QualityCheckRecord


def _uid() -> str:
    return str(uuid.uuid4())


def test_document_record_minimal():
    doc = DocumentRecord(
        document_id=_uid(),
        sha256="a" * 64,
        company_name="Acme Corp",
        company_slug="acme-corp",
        fiscal_year=2023,
        official_doc_type="sustainability_report",
        official_doc_type_label="Sustainability Report",
        document_path="/corpus/acme/2023/report.pdf",
    )
    assert doc.schema_version == "1.0.0"
    assert doc.selection_status == "unknown"
    assert doc.extraction_ready is False
    assert doc.created_at != ""


def test_page_record_minimal():
    page = PageRecord(
        page_id=_uid(),
        document_id=_uid(),
        company_slug="acme-corp",
        fiscal_year=2023,
        official_doc_type="sustainability_report",
        page_number=1,
        text="Some text here.",
        char_count=15,
    )
    assert page.extraction_status == "ok"
    assert page.has_tables is False
    assert page.has_images is False


def test_section_record_minimal():
    section = SectionRecord(
        section_id=_uid(),
        document_id=_uid(),
        company_slug="acme-corp",
        fiscal_year=2023,
        official_doc_type="sustainability_report",
        section_title="Environmental Performance",
        section_type="unknown",
        page_start=5,
    )
    assert section.page_end is None
    assert section.confidence == 0.0
    assert section.detection_method == "rule_based"


def test_metric_record_minimal():
    metric = MetricRecord(
        metric_id=_uid(),
        company_slug="acme-corp",
        fiscal_year=2023,
        metric_name="GHG Scope 1",
        metric_category="environment",
        value_raw="12000",
        unit_raw="tCO2e",
        source_document_id=_uid(),
    )
    assert metric.review_required is True
    assert metric.value_normalized is None
    assert metric.confidence == 0.0


def test_evidence_record_minimal():
    ev = EvidenceRecord(
        evidence_id=_uid(),
        document_id=_uid(),
        company_slug="acme-corp",
        fiscal_year=2023,
        official_doc_type="sustainability_report",
        page_number=42,
        quote="Scope 1 emissions: 12,000 tCO2e in 2023.",
    )
    assert ev.section_id is None
    assert ev.confidence == 0.0
    assert ev.extraction_method == "keyword_regex"


def test_quality_check_record_minimal():
    qc = QualityCheckRecord(
        quality_check_id=_uid(),
        target_type="document",
        target_id=_uid(),
        check_name="document_path_exists",
        status="pass",
        severity="critical",
    )
    assert qc.review_required is False
    assert qc.message == ""
    assert qc.created_at != ""

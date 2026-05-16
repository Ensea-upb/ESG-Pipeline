from __future__ import annotations

import json
from pathlib import Path

from ESGInformationExtraction.schemas.evidence_record import EvidenceRecord


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "ESGInformationExtraction" / "outputs" / "pdf_v10_lvmh_2024_sustainability_test"


def test_real_evidence_store_matches_evidence_record_schema():
    path = OUTPUT / "evidence_store.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()[:25]]
    assert rows
    for row in rows:
        record = EvidenceRecord(**row)
        assert record.evidence_id
        assert record.document_id
        assert record.evidence_type
        assert record.page_number >= 1
        assert record.quote
        assert isinstance(record.review_required, bool)
    assert "company_slug" not in rows[0]
    assert EvidenceRecord(**rows[0]).company_slug is None


def test_table_and_figure_evidences_are_accepted_if_present():
    rows = [json.loads(line) for line in (OUTPUT / "evidence_store.jsonl").read_text(encoding="utf-8").splitlines()]
    selected = [row for row in rows if row.get("evidence_type") in {"table", "figure"}][:10]
    for row in selected:
        assert EvidenceRecord(**row).evidence_type in {"table", "figure"}

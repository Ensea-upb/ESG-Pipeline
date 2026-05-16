from __future__ import annotations

import json
from pathlib import Path

from ESGInformationExtraction.schemas.document_record import DocumentRecord
from ESGInformationExtraction.schemas.evidence_record import EvidenceRecord
from ESGInformationExtraction.schemas.page_record import PageRecord
from ESGInformationExtraction.schemas.quality_check_record import QualityCheckRecord
from ESGInformationExtraction.schemas.section_record import SectionRecord


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "ESGInformationExtraction" / "outputs" / "pdf_v10_lvmh_2024_sustainability_test"
CONTRACT = ROOT / "ESGInformationExtraction" / "contracts" / "output_contract_v1.json"


def _jsonl(path: Path, limit: int = 20) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()[:limit] if line.strip()]


def test_real_outputs_match_support_schemas():
    DocumentRecord(**json.loads((OUTPUT / "document_record.json").read_text(encoding="utf-8")))
    for row in _jsonl(OUTPUT / "page_index.jsonl"):
        PageRecord(**row)
    for row in _jsonl(OUTPUT / "section_index.jsonl"):
        SectionRecord(**row)
    for row in _jsonl(OUTPUT / "evidence_store.jsonl"):
        EvidenceRecord(**row)
    for row in _jsonl(OUTPUT / "quality_report.jsonl"):
        QualityCheckRecord(**row)


def test_contract_required_fields_present_in_real_outputs():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    for file_name, required in contract["required_fields_by_file"].items():
        path = OUTPUT / file_name
        if not path.exists() or file_name.endswith(".md"):
            continue
        if file_name.endswith(".jsonl"):
            rows = _jsonl(path, limit=5)
            if not rows:
                continue
            sample = rows[0]
        elif file_name.endswith(".json"):
            sample = json.loads(path.read_text(encoding="utf-8"))
        else:
            continue
        missing = [field for field in required if field not in sample]
        assert not missing, f"{file_name} missing {missing}"

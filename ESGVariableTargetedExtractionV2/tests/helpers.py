"""Synthetic fixtures for ESGVariableTargetedExtractionV2 tests. No real data needed."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any


DOCUMENT_ID = "canonical_test_aabbcc112233445566"
COMPANY = "test-company"
COMPANY_NAME = "Test Company SA"
COMPANY_SLUG = "test-company"
FISCAL_YEAR = "2024"
DOC_TYPE = "01_urd_annual_report"

SAMPLE_TEXT_BLOCKS = [
    {
        "text_block_id": f"{DOCUMENT_ID}_page_0001_block_0001",
        "document_id": DOCUMENT_ID,
        "page_id": f"{DOCUMENT_ID}_page_0001",
        "page_number": 1,
        "block_type": "paragraph",
        "text": "Total water withdrawal was 4.2 Mm3 in 2024, down 3% from prior year.",
        "is_header": False, "is_footer": False, "is_footnote": False,
        "section_id": f"{DOCUMENT_ID}_section_0001",
    },
    {
        "text_block_id": f"{DOCUMENT_ID}_page_0002_block_0001",
        "document_id": DOCUMENT_ID,
        "page_id": f"{DOCUMENT_ID}_page_0002",
        "page_number": 2,
        "block_type": "paragraph",
        "text": "Total headcount reached 52,000 employees at end of 2024, including 18,000 FTE in Europe.",
        "is_header": False, "is_footer": False, "is_footnote": False,
        "section_id": f"{DOCUMENT_ID}_section_0002",
    },
    {
        "text_block_id": f"{DOCUMENT_ID}_page_0003_block_0001",
        "document_id": DOCUMENT_ID,
        "page_id": f"{DOCUMENT_ID}_page_0003",
        "page_number": 3,
        "block_type": "paragraph",
        "text": "GHG emissions Scope 1+2 totalled 457 ktCO2e in 2024, a 15% reduction vs 2017 baseline.",
        "is_header": False, "is_footer": False, "is_footnote": False,
        "section_id": f"{DOCUMENT_ID}_section_0002",
    },
    {
        "text_block_id": f"{DOCUMENT_ID}_page_0004_block_0001",
        "document_id": DOCUMENT_ID,
        "page_id": f"{DOCUMENT_ID}_page_0004",
        "page_number": 4,
        "block_type": "paragraph",
        "text": "The company is certified under ISO 14001 and ISO 50001 for environmental management.",
        "is_header": False, "is_footer": False, "is_footnote": False,
        "section_id": "",
    },
    {
        "text_block_id": f"{DOCUMENT_ID}_page_0005_block_0001",
        "document_id": DOCUMENT_ID,
        "page_id": f"{DOCUMENT_ID}_page_0005",
        "page_number": 5,
        "block_type": "paragraph",
        "text": "Section 2.1 describes governance principles. Board independence rate is 75%.",
        "is_header": False, "is_footer": False, "is_footnote": False,
        "section_id": "",
    },
]

SAMPLE_TABLE_CELLS = [
    # Table with percentage that should NOT become "27 tonnes"
    {
        "cell_id": f"{DOCUMENT_ID}_page_0010_tbl_001_r000_c000",
        "table_id": f"{DOCUMENT_ID}_page_0010_tbl_001",
        "document_id": DOCUMENT_ID,
        "page_id": f"{DOCUMENT_ID}_page_0010",
        "page_number": 10,
        "row_index": 0, "column_index": 0,
        "text": "Metric",
        "is_header_cell": True,
        "normalized_text": "Metric",
    },
    {
        "cell_id": f"{DOCUMENT_ID}_page_0010_tbl_001_r000_c001",
        "table_id": f"{DOCUMENT_ID}_page_0010_tbl_001",
        "document_id": DOCUMENT_ID,
        "page_id": f"{DOCUMENT_ID}_page_0010",
        "page_number": 10,
        "row_index": 0, "column_index": 1,
        "text": "Value (%)",
        "is_header_cell": True,
        "normalized_text": "Value (%)",
    },
    {
        "cell_id": f"{DOCUMENT_ID}_page_0010_tbl_001_r001_c000",
        "table_id": f"{DOCUMENT_ID}_page_0010_tbl_001",
        "document_id": DOCUMENT_ID,
        "page_id": f"{DOCUMENT_ID}_page_0010",
        "page_number": 10,
        "row_index": 1, "column_index": 0,
        "text": "Women in management",
        "is_header_cell": False,
        "normalized_text": "Women in management",
    },
    {
        "cell_id": f"{DOCUMENT_ID}_page_0010_tbl_001_r001_c001",
        "table_id": f"{DOCUMENT_ID}_page_0010_tbl_001",
        "document_id": DOCUMENT_ID,
        "page_id": f"{DOCUMENT_ID}_page_0010",
        "page_number": 10,
        "row_index": 1, "column_index": 1,
        "text": "27",
        "is_header_cell": False,
        "normalized_text": "27",
    },
    # Table with unit conflict: column says tCO2e but row says sites
    {
        "cell_id": f"{DOCUMENT_ID}_page_0011_tbl_001_r000_c000",
        "table_id": f"{DOCUMENT_ID}_page_0011_tbl_001",
        "document_id": DOCUMENT_ID,
        "page_id": f"{DOCUMENT_ID}_page_0011",
        "page_number": 11,
        "row_index": 0, "column_index": 0,
        "text": "Indicator (tCO2e)",
        "is_header_cell": True,
        "normalized_text": "Indicator (tCO2e)",
    },
    {
        "cell_id": f"{DOCUMENT_ID}_page_0011_tbl_001_r001_c000",
        "table_id": f"{DOCUMENT_ID}_page_0011_tbl_001",
        "document_id": DOCUMENT_ID,
        "page_id": f"{DOCUMENT_ID}_page_0011",
        "page_number": 11,
        "row_index": 1, "column_index": 0,
        "text": "101 sites",
        "is_header_cell": False,
        "normalized_text": "101 sites",
    },
]

SAMPLE_EVIDENCE_STORE = [
    {
        "evidence_id": f"{DOCUMENT_ID}_evidence_000001",
        "document_id": DOCUMENT_ID,
        "page_number": 1,
        "evidence_type": "text_block",
        "quote": "Total water withdrawal was 4.2 Mm3 in 2024.",
        "section_id": f"{DOCUMENT_ID}_section_0001",
        "company": COMPANY,
        "company_name": COMPANY_NAME,
        "company_slug": COMPANY_SLUG,
        "fiscal_year": FISCAL_YEAR,
        "official_doc_type": DOC_TYPE,
    },
]

SAMPLE_SECTION_INDEX = [
    {
        "section_id": f"{DOCUMENT_ID}_section_0001",
        "document_id": DOCUMENT_ID,
        "section_title": "Environmental Performance",
        "section_type": "environmental",
        "page_start": 1,
        "page_end": 3,
    },
    {
        "section_id": f"{DOCUMENT_ID}_section_0002",
        "document_id": DOCUMENT_ID,
        "section_title": "Social & HR Data",
        "section_type": "social",
        "page_start": 4,
        "page_end": 6,
    },
]

DOCUMENT_RECORD = {
    "schema_version": "1.0.0",
    "document_id": DOCUMENT_ID,
    "company": COMPANY,
    "company_name": COMPANY_NAME,
    "company_slug": COMPANY_SLUG,
    "fiscal_year": FISCAL_YEAR,
    "official_doc_type": DOC_TYPE,
    "final_path": "/fake/path/document.pdf",
    "corpus_run_id": "test_run_001",
    "page_count": 15,
    "loading_status": "readable",
}


def make_input_dir(tmp_path: Path) -> Path:
    """Create a synthetic ESGInformationExtraction output dir in tmp_path."""
    input_dir = tmp_path / "01_information_extraction"
    input_dir.mkdir(parents=True, exist_ok=True)

    # Write document_record.json
    (input_dir / "document_record.json").write_text(
        json.dumps(DOCUMENT_RECORD), encoding="utf-8"
    )

    # Write text_blocks.jsonl
    with (input_dir / "text_blocks.jsonl").open("w", encoding="utf-8") as f:
        for block in SAMPLE_TEXT_BLOCKS:
            f.write(json.dumps(block) + "\n")

    # Write table_cells.jsonl
    with (input_dir / "table_cells.jsonl").open("w", encoding="utf-8") as f:
        for cell in SAMPLE_TABLE_CELLS:
            f.write(json.dumps(cell) + "\n")

    # Write evidence_store.jsonl
    with (input_dir / "evidence_store.jsonl").open("w", encoding="utf-8") as f:
        for ev in SAMPLE_EVIDENCE_STORE:
            f.write(json.dumps(ev) + "\n")

    # Write section_index.jsonl
    with (input_dir / "section_index.jsonl").open("w", encoding="utf-8") as f:
        for sec in SAMPLE_SECTION_INDEX:
            f.write(json.dumps(sec) + "\n")

    # Empty stubs for other files
    for fname in ["figure_index.jsonl", "table_index.jsonl", "page_index.jsonl",
                  "multimodal_evidence_index.jsonl"]:
        (input_dir / fname).touch()

    return input_dir


def make_sample_chunks() -> list[dict]:
    return [
        {
            "chunk_id": "chunk_water_001",
            "document_id": DOCUMENT_ID,
            "company": COMPANY,
            "company_name": COMPANY_NAME,
            "company_slug": COMPANY_SLUG,
            "fiscal_year": FISCAL_YEAR,
            "official_doc_type": DOC_TYPE,
            "final_path": "/fake/path/document.pdf",
            "page_number": "1",
            "section_id": "section_001",
            "evidence_id": "",
            "table_id": "",
            "figure_id": "",
            "crop_id": "",
            "source_type": "paragraph",
            "text": "Total water withdrawal was 4.2 Mm3 in 2024, down 3% from prior year.",
            "text_length": 68,
            "has_numeric_value": True,
            "has_unit_candidate": True,
            "numeric_values_detected": "4.2,3",
            "units_detected": "Mm3",
            "structural_noise_flags": "",
        },
        {
            "chunk_id": "chunk_employees_001",
            "document_id": DOCUMENT_ID,
            "company": COMPANY,
            "company_name": COMPANY_NAME,
            "company_slug": COMPANY_SLUG,
            "fiscal_year": FISCAL_YEAR,
            "official_doc_type": DOC_TYPE,
            "final_path": "/fake/path/document.pdf",
            "page_number": "2",
            "section_id": "section_002",
            "evidence_id": "",
            "table_id": "",
            "figure_id": "",
            "crop_id": "",
            "source_type": "paragraph",
            "text": "Total headcount reached 52,000 employees at end of 2024, including 18,000 FTE.",
            "text_length": 79,
            "has_numeric_value": True,
            "has_unit_candidate": True,
            "numeric_values_detected": "52000,18000",
            "units_detected": "employees,FTE",
            "structural_noise_flags": "",
        },
        {
            "chunk_id": "chunk_ghg_001",
            "document_id": DOCUMENT_ID,
            "company": COMPANY,
            "company_name": COMPANY_NAME,
            "company_slug": COMPANY_SLUG,
            "fiscal_year": FISCAL_YEAR,
            "official_doc_type": DOC_TYPE,
            "final_path": "/fake/path/document.pdf",
            "page_number": "3",
            "section_id": "section_001",
            "evidence_id": "",
            "table_id": "",
            "figure_id": "",
            "crop_id": "",
            "source_type": "paragraph",
            "text": "GHG emissions Scope 1+2 totalled 457 ktCO2e in 2024, a 15% reduction vs 2017.",
            "text_length": 78,
            "has_numeric_value": True,
            "has_unit_candidate": True,
            "numeric_values_detected": "457,15",
            "units_detected": "ktCO2e",
            "structural_noise_flags": "",
        },
        {
            "chunk_id": "chunk_iso_noise_001",
            "document_id": DOCUMENT_ID,
            "company": COMPANY,
            "company_name": COMPANY_NAME,
            "company_slug": COMPANY_SLUG,
            "fiscal_year": FISCAL_YEAR,
            "official_doc_type": DOC_TYPE,
            "final_path": "/fake/path/document.pdf",
            "page_number": "4",
            "section_id": "",
            "evidence_id": "",
            "table_id": "",
            "figure_id": "",
            "crop_id": "",
            "source_type": "paragraph",
            "text": "The company is certified under ISO 14001 and ISO 50001 for environmental management.",
            "text_length": 82,
            "has_numeric_value": True,
            "has_unit_candidate": False,
            "numeric_values_detected": "14001,50001",
            "units_detected": "",
            "structural_noise_flags": "ISO 14001,ISO 50001",
        },
    ]


def make_sample_candidate(
    target_variable: str = "water_consumption",
    raw_value: str = "4.2",
    raw_unit: str = "Mm3",
    status: str = "candidate_found",
    quote: str = "Total water withdrawal was 4.2 Mm3 in 2024.",
) -> dict:
    return {
        "candidate_id": f"cand_v2_test_{target_variable}",
        "schema_version": "2.0.0",
        "engine": "esg_variable_targeted_extraction_v2",
        "target_variable": target_variable,
        "indicator_family": "environmental",
        "document_id": DOCUMENT_ID,
        "company": COMPANY,
        "company_name": COMPANY_NAME,
        "company_slug": COMPANY_SLUG,
        "fiscal_year": FISCAL_YEAR,
        "official_doc_type": DOC_TYPE,
        "final_path": "/fake/path/document.pdf",
        "page_number": "1",
        "chunk_id": "chunk_water_001",
        "source_type": "paragraph",
        "raw_value": raw_value,
        "raw_unit": raw_unit,
        "normalized_value": raw_value,
        "normalized_unit": raw_unit,
        "raw_year": "2024",
        "prepared_year": "2024",
        "quote": quote,
        "evidence_id": "",
        "table_id": "",
        "figure_id": "",
        "crop_id": "",
        "retrieval_score": 0.72,
        "extraction_score": 0.65,
        "candidate_score": 0.68,
        "candidate_status": status,
        "rejection_reason": "",
        "warning_flags": "",
        "lineage": "v2|paragraph|chunk_water_001",
        "score_reason": "",
    }

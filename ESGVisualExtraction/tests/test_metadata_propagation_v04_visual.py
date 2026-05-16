"""Tests for company/fiscal_year propagation in ESGVisualExtraction — v0.4."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from esg_visual_extraction.loader import load_visual_inputs, _resolve_company_year


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _make_input_dir(
    tmp_path: Path,
    company: str = "",
    fiscal_year: str = "",
    in_document_record: bool = True,
    in_inventory: bool = False,
    in_corpus_path: bool = False,
) -> Path:
    """Build a minimal visual extraction input directory."""
    if in_corpus_path:
        input_dir = tmp_path / "ESGFinalCorpus" / company / fiscal_year / "extraction_output"
    else:
        input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = input_dir / "source.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% minimal placeholder\n")

    doc_record_payload: dict = {"document_id": "test_doc_visual"}
    if in_document_record and company:
        doc_record_payload["company"] = company
        doc_record_payload["fiscal_year"] = fiscal_year
    _write_json(input_dir / "document_record.json", doc_record_payload)

    inventory_payload: dict = {"document_id": "test_doc_visual", "pdf_path": str(pdf_path)}
    if in_inventory and company:
        inventory_payload["company"] = company
        inventory_payload["fiscal_year"] = fiscal_year
    _write_json(input_dir / "document_inventory.json", inventory_payload)

    _write_json(input_dir / "extraction_summary.json", {"document_id": "test_doc_visual", "pdf_path": str(pdf_path)})
    _write_json(input_dir / "figure_statistics.json", {"figures_count": 1})
    _write_jsonl(input_dir / "figure_index.jsonl", [
        {
            "figure_id": "fig_001",
            "document_id": "test_doc_visual",
            "page_number": 1,
            "section_id": "sec_1",
            "figure_bbox": None,
            "figure_type": "unknown_visual",
            "visual_object_level": "page_level_visual",
            "detection_method": "page_visual_heuristic",
            "nearby_caption_text": "CO2 emissions chart",
            "figure_quality_flags": [],
            "source_page_diagnostic_flags": [],
        }
    ])
    _write_jsonl(input_dir / "multimodal_evidence_index.jsonl", [])
    return input_dir


def test_resolve_company_year_from_document_record(tmp_path: Path) -> None:
    """company/fiscal_year must be read from document_record.json (priority 1)."""
    input_dir = _make_input_dir(tmp_path, "TotalEnergies", "2024", in_document_record=True)
    inputs = load_visual_inputs(input_dir)
    assert inputs["company"] == "TotalEnergies"
    assert inputs["fiscal_year"] == "2024"


def test_resolve_company_year_from_inventory_fallback(tmp_path: Path) -> None:
    """company/fiscal_year must be read from document_inventory.json when document_record has none."""
    input_dir = _make_input_dir(tmp_path, "TotalEnergies", "2024", in_document_record=False, in_inventory=True)
    inputs = load_visual_inputs(input_dir)
    assert inputs["company"] == "TotalEnergies"
    assert inputs["fiscal_year"] == "2024"


def test_resolve_company_year_empty_when_no_source(tmp_path: Path) -> None:
    """company/fiscal_year must be empty strings when no metadata source provides them."""
    input_dir = _make_input_dir(tmp_path, "", "", in_document_record=False, in_inventory=False)
    inputs = load_visual_inputs(input_dir)
    assert inputs["company"] == ""
    assert inputs["fiscal_year"] == ""


def test_resolve_company_year_from_corpus_path(tmp_path: Path) -> None:
    """company/fiscal_year must be inferred from ESGFinalCorpus/COMPANY/YEAR/ path when no metadata files."""
    input_dir = _make_input_dir(
        tmp_path, "TotalEnergies", "2024",
        in_document_record=False, in_inventory=False, in_corpus_path=True
    )
    company, fiscal_year = _resolve_company_year(input_dir, {}, {})
    assert company == "TotalEnergies"
    assert fiscal_year == "2024"


def test_visual_candidates_csv_has_company_fiscal_year_columns(tmp_path: Path) -> None:
    """visual_candidates.csv must include company and fiscal_year columns."""
    from esg_visual_extraction.candidate_extractor import CANDIDATE_FIELDS
    assert "company" in CANDIDATE_FIELDS, "company must be in CANDIDATE_FIELDS"
    assert "fiscal_year" in CANDIDATE_FIELDS, "fiscal_year must be in CANDIDATE_FIELDS"


def test_visual_extractor_writes_company_to_candidates(tmp_path: Path) -> None:
    """ESGVisualExtractor must write company/fiscal_year into visual_candidates.csv rows."""
    from esg_visual_extraction.candidate_extractor import ESGVisualExtractor

    input_dir = _make_input_dir(tmp_path, "TotalEnergies", "2024")
    output_dir = tmp_path / "out"

    extractor = ESGVisualExtractor(input_dir, output_dir, overwrite=False)
    result = extractor.run()

    candidates_csv = output_dir / "visual_candidates.csv"
    assert candidates_csv.exists()
    rows = _read_csv(candidates_csv)
    assert rows, "visual_candidates.csv must have at least one row"
    for row in rows:
        assert row.get("company") == "TotalEnergies", f"company missing in row: {row}"
        assert row.get("fiscal_year") == "2024", f"fiscal_year missing in row: {row}"


def test_visual_extractor_summary_contains_company_fiscal_year(tmp_path: Path) -> None:
    """visual_extraction_summary.json must include company and fiscal_year."""
    from esg_visual_extraction.candidate_extractor import ESGVisualExtractor

    input_dir = _make_input_dir(tmp_path, "TotalEnergies", "2024")
    output_dir = tmp_path / "out2"

    extractor = ESGVisualExtractor(input_dir, output_dir, overwrite=False)
    result = extractor.run()

    summary = json.loads((output_dir / "visual_extraction_summary.json").read_text(encoding="utf-8"))
    assert summary.get("company") == "TotalEnergies"
    assert summary.get("fiscal_year") == "2024"

from __future__ import annotations

from pathlib import Path

from .conftest import read_json, read_jsonl, run_cli


REQUIRED_FILES = {
    "document_record.json",
    "page_index.jsonl",
    "text_blocks.jsonl",
    "text_block_statistics.json",
    "section_candidates.jsonl",
    "section_index.jsonl",
    "section_statistics.json",
    "evidence_store.jsonl",
    "evidence_statistics.json",
    "suspicious_sections.jsonl",
    "quality_report.jsonl",
    "extraction_summary.json",
    # v0.5 additions
    "table_index.jsonl",
    "table_cells.jsonl",
    "table_statistics.json",
    # v0.6 additions
    "figure_index.jsonl",
    "figure_statistics.json",
    # v0.7 additions
    "document_inventory.json",
    "multimodal_evidence_index.jsonl",
    "multimodal_statistics.json",
    # v0.8 additions
    "consistency_report.json",
    "audit_findings.jsonl",
    "document_audit_report.md",
    # v0.9 additions
    "metric_candidates.jsonl",
    "metric_statistics.json",
}


def test_required_outputs_and_fields(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="doc_contract")
    assert result.returncode == 0, result.stderr

    assert REQUIRED_FILES == {path.name for path in output_dir.iterdir()}

    document = read_json(output_dir / "document_record.json")
    for field in {
        "schema_version",
        "document_id",
        "sha256",
        "document_path",
        "file_name",
        "page_count",
        "loading_status",
        "created_at",
    }:
        assert field in document

    page = read_jsonl(output_dir / "page_index.jsonl")[0]
    for field in {
        "schema_version",
        "page_id",
        "document_id",
        "page_number",
        "width",
        "height",
        "rotation",
        "extraction_status",
        "text_char_count",
        "has_text",
    }:
        assert field in page

    block = read_jsonl(output_dir / "text_blocks.jsonl")[0]
    for field in {
        "schema_version",
        "text_block_id",
        "document_id",
        "page_id",
        "page_number",
        "block_type",
        "text",
        "bbox",
        "reading_order",
    }:
        assert field in block


def test_page_numbers_and_ids_are_stable(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="doc_stable")
    assert result.returncode == 0, result.stderr

    pages = read_jsonl(output_dir / "page_index.jsonl")
    blocks = read_jsonl(output_dir / "text_blocks.jsonl")

    assert pages[0]["page_number"] == 1
    assert pages[0]["page_id"] == "doc_stable_page_0001"
    assert blocks[0]["text_block_id"] == "doc_stable_page_0001_block_0001"
    assert blocks[0]["reading_order"] == 1

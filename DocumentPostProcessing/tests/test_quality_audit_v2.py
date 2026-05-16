from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


def _load_audit_module():
    script_path = Path("DocumentPostProcessing/scripts/audit_selected_documents.py")
    spec = importlib.util.spec_from_file_location("audit_selected_documents", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_quality_audit_writes_indexes_summaries_and_markdown(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    selected_path = tmp_path / "selection" / "selected_documents.csv"
    validation_path = tmp_path / "validation" / "document_validation_results.csv"
    output_dir = tmp_path / "quality"
    selected_fields = [
        "company_name",
        "company_slug",
        "fiscal_year",
        "official_doc_type",
        "official_doc_type_label",
        "selected_canonical_document_id",
        "sha256",
        "final_path",
        "selection_status",
        "company_name_detected_in_text",
        "page_count",
    ]
    validation_fields = [
        "canonical_document_id",
        "company_slug",
        "fiscal_year",
        "document_validation_status",
        "company_name_detected_in_text",
    ]
    _write_csv(
        selected_path,
        [
            {
                "company_name": "LVMH",
                "company_slug": "lvmh",
                "fiscal_year": "2024",
                "official_doc_type": "01_urd_annual_report",
                "official_doc_type_label": "URD / annual report",
                "selected_canonical_document_id": "canonical_1",
                "sha256": "abc",
                "final_path": str(pdf_path),
                "selection_status": "selected",
                "company_name_detected_in_text": "True",
                "page_count": "10",
            },
            {
                "company_name": "LVMH",
                "company_slug": "lvmh",
                "fiscal_year": "2024",
                "official_doc_type": "08_anticorruption_policy",
                "official_doc_type_label": "Anti-corruption policy",
                "selected_canonical_document_id": "canonical_2",
                "sha256": "def",
                "final_path": str(pdf_path),
                "selection_status": "selected_needs_review",
                "company_name_detected_in_text": "False",
                "page_count": "2",
            },
        ],
        selected_fields,
    )
    _write_csv(
        validation_path,
        [
            {
                "canonical_document_id": "canonical_1",
                "company_slug": "lvmh",
                "fiscal_year": "2024",
                "document_validation_status": "likely_valid",
                "company_name_detected_in_text": "True",
            },
            {
                "canonical_document_id": "canonical_2",
                "company_slug": "lvmh",
                "fiscal_year": "2024",
                "document_validation_status": "likely_wrong_company",
                "company_name_detected_in_text": "False",
            },
        ],
        validation_fields,
    )

    module = _load_audit_module()
    module.main(selected_path, validation_path, output_dir, overwrite=True)

    assert (output_dir / "quality_summary_by_company.csv").exists()
    assert (output_dir / "quality_summary_by_doc_type.csv").exists()
    report = (output_dir / "quality_audit_report.md").read_text(encoding="utf-8")
    assert "Do not use raw ESGFinalCorpus directly" in report
    strict_rows = list(csv.DictReader((output_dir / "extraction_index_strict_likely_valid.csv").open(encoding="utf-8")))
    excluded_rows = list(csv.DictReader((output_dir / "exclusion_index_quarantine_wrong_company.csv").open(encoding="utf-8")))
    assert len(strict_rows) == 1
    assert len(excluded_rows) == 1

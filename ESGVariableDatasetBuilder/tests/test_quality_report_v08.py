from __future__ import annotations

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.io_utils import write_csv
from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.quality_report import build_quality_report


def test_quality_report_detects_errors_and_counts_missing(tmp_path):
    write_csv(
        tmp_path / "esg_variables_long.csv",
        [
            {"company": "A", "year": "2024", "variable_name": "co2_emissions", "value": "1", "unit": "", "status": "found", "source_document": "doc", "page_number": "1", "quote": "", "confidence": "1", "selection_reason": "", "lineage_id": "l1"},
            {"company": "A", "year": "2024", "variable_name": "roe", "value": "score 5", "unit": "%", "status": "found", "source_document": "external_source", "page_number": "", "quote": "", "confidence": "", "selection_reason": "", "lineage_id": "l2"},
            {"company": "A", "year": "2024", "variable_name": "waste", "value": "", "unit": "", "status": "missing_from_corpus", "source_document": "", "page_number": "", "quote": "", "confidence": "", "selection_reason": "", "lineage_id": "l3"},
        ],
        ["company", "year", "variable_name", "value", "unit", "status", "source_document", "page_number", "quote", "confidence", "selection_reason", "lineage_id"],
    )
    write_csv(tmp_path / "esg_variables_evidence.csv", [], ["company", "year", "variable_name"])
    write_csv(tmp_path / "selected_variable_values.csv", [], ["alternatives_count"])

    report = build_quality_report(tmp_path)

    assert report["found_without_evidence_count"] == 2
    assert report["final_score_detected_count"] >= 1
    assert report["external_source_detected_count"] >= 1
    assert report["missing_values_count"] == 1
    assert (tmp_path / "esg_variables_quality_report.md").exists()

from __future__ import annotations

import logging
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import build_database_audit
from .evidence_linker import EVIDENCE_FIELDS, build_evidence_links
from .io_utils import utcnow, write_csv, write_json, write_jsonl
from .lineage import build_lineage
from .loader import load_manual_review_outputs
from .schema_mapper import map_schema

logger = logging.getLogger(__name__)


DATABASE_FIELDS = [
    "preparation_indicator_id", "indicator_database_status", "candidate_id",
    "review_item_id", "document_id", "company", "fiscal_year", "source_engine",
    "information_type", "validation_status", "review_status", "indicator_family", "indicator_key", "indicator_label",
    "value_raw", "unit_raw", "year_raw", "value_prepared", "unit_prepared",
    "year_prepared", "value_source", "unit_source", "year_source",
    "preparation_quality_status", "page_number", "quote", "evidence_id",
    "table_id", "cell_id", "figure_id", "reviewer", "decision_reason",
    "reviewer_notes", "created_from_review_decision", "is_final_indicator",
    "score_produced", "indicator_domain", "indicator_topic",
    "indicator_metric_name", "indicator_unit_category", "indicator_period_type",
    "indicator_scope", "indicator_geography", "indicator_methodology",
    "indicator_standard_reference", "indicator_schema_confidence",
    "schema_mapping_notes",
]


@dataclass
class IndicatorDatabaseResult:
    output_dir: Path
    records_count: int
    summary: dict[str, Any]


class IndicatorDatabaseBuilder:
    def __init__(self, input_dir: Path, output_dir: Path, overwrite: bool = False) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.overwrite = overwrite

    def run(self) -> IndicatorDatabaseResult:
        if self.output_dir.exists() and not self.overwrite and any(self.output_dir.iterdir()):
            raise FileExistsError("output-dir already exists and is not empty; use --overwrite")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        accepted, inventory = load_manual_review_outputs(self.input_dir)
        records = [self._to_record(idx, row) for idx, row in enumerate(accepted, start=1)]

        # Metadata quality warnings
        metadata_missing_company_count = sum(1 for r in records if not str(r.get("company", "")).strip())
        metadata_missing_fiscal_year_count = sum(1 for r in records if not str(r.get("fiscal_year", "")).strip())
        if metadata_missing_company_count > 0:
            logger.warning(
                "metadata_missing_company: %d/%d records have empty company",
                metadata_missing_company_count, len(records),
            )
        if metadata_missing_fiscal_year_count > 0:
            logger.warning(
                "metadata_missing_fiscal_year: %d/%d records have empty fiscal_year",
                metadata_missing_fiscal_year_count, len(records),
            )
        # Report fiscal_year vs year_prepared differences (info level, never fixes them)
        reporting_vs_extracted_diff_count = sum(
            1 for r in records
            if r.get("fiscal_year") and r.get("year_prepared") and str(r.get("fiscal_year")) != str(r.get("year_prepared"))
        )
        if reporting_vs_extracted_diff_count > 0:
            logger.info(
                "reporting_year_vs_extracted_year_difference: %d records have fiscal_year != year_prepared",
                reporting_vs_extracted_diff_count,
            )

        links = build_evidence_links(records)
        lineage = build_lineage(records)
        write_json(self.output_dir / "indicator_database_input_inventory.json", inventory)
        fields = list(accepted[0].keys()) if accepted else []
        write_csv(self.output_dir / "accepted_candidates_loaded.csv", accepted, fields)
        write_jsonl(self.output_dir / "accepted_candidates_loaded.jsonl", accepted)
        write_csv(self.output_dir / "indicator_preparation_database.csv", records, DATABASE_FIELDS)
        write_jsonl(self.output_dir / "indicator_preparation_database.jsonl", records)
        write_csv(self.output_dir / "indicator_schema_mapping.csv", records, DATABASE_FIELDS)
        write_jsonl(self.output_dir / "indicator_schema_mapping.jsonl", records)
        write_json(self.output_dir / "indicator_schema_mapping_summary.json", {
            "schema_version": "1.0.0",
            "records_count": len(records),
            "indicator_domain_distribution": dict(Counter(r.get("indicator_domain", "") for r in records)),
            "indicator_topic_distribution": dict(Counter(r.get("indicator_topic", "") for r in records)),
        })
        write_csv(self.output_dir / "indicator_evidence_links.csv", links, EVIDENCE_FIELDS)
        write_jsonl(self.output_dir / "indicator_evidence_links.jsonl", links)
        write_json(self.output_dir / "evidence_link_summary.json", {
            "schema_version": "1.0.0",
            "evidence_links_count": len(links),
            "source_trace_type_distribution": dict(Counter(l.get("source_trace_type", "") for l in links)),
        })
        write_jsonl(self.output_dir / "indicator_lineage.jsonl", lineage)
        write_json(self.output_dir / "indicator_lineage_summary.json", {
            "schema_version": "1.0.0",
            "lineage_records_count": len(lineage),
            "lineage_complete_count": sum(1 for item in lineage if item["lineage_complete"]),
        })
        audit = build_database_audit(records, links, lineage, self.output_dir)
        summary = {
            "schema_version": "1.0.0",
            "module": "ESGIndicatorDatabase",
            "input_dir": str(self.input_dir.resolve()),
            "output_dir": str(self.output_dir.resolve()),
            "generated_at": utcnow(),
            "accepted_candidates_loaded_count": len(accepted),
            "preparation_indicators_count": len(records),
            "empty_database_warning": len(records) == 0,
            "evidence_links_count": len(links),
            "lineage_records_count": len(lineage),
            "indicator_database_status": "preparation_only",
            "final_indicators_count": 0,
            "score_produced_count": 0,
            "metadata_missing_company_count": metadata_missing_company_count,
            "metadata_missing_fiscal_year_count": metadata_missing_fiscal_year_count,
            "reporting_year_vs_extracted_year_difference_count": reporting_vs_extracted_diff_count,
            "audit_errors_count": audit["errors_count"],
            "audit_warnings_count": audit["warnings_count"],
        }
        write_json(self.output_dir / "indicator_database_summary.json", summary)
        return IndicatorDatabaseResult(self.output_dir, len(records), summary)

    def _to_record(self, idx: int, row: dict[str, str]) -> dict[str, Any]:
        schema = map_schema(row)
        value, value_source = _choose(row, "corrected_value", "normalized_value", "raw_value")
        unit, unit_source = _choose(row, "corrected_unit", "normalized_unit", "raw_unit")
        year, year_source = _choose(row, "corrected_year", "normalized_year", "fiscal_year")
        quality = []
        if not value:
            quality.append("needs_value_review")
        if not unit:
            quality.append("needs_unit_review")
        if not year:
            quality.append("needs_year_review")
        return {
            "preparation_indicator_id": f"prep_indicator_{idx:06d}",
            "indicator_database_status": "preparation_only",
            "candidate_id": row.get("candidate_id", ""),
            "review_item_id": row.get("review_item_id", ""),
            "document_id": row.get("document_id", ""),
            "company": row.get("company", ""),
            "fiscal_year": row.get("fiscal_year", ""),
            "source_engine": row.get("source_engine", ""),
            "information_type": row.get("information_type", ""),
            "validation_status": row.get("validation_status", ""),
            "review_status": row.get("review_status", ""),
            "indicator_family": row.get("corrected_indicator_family") or row.get("indicator_family", ""),
            "indicator_key": row.get("corrected_indicator_key") or row.get("indicator_key_candidate", ""),
            "indicator_label": row.get("label", ""),
            "value_raw": row.get("raw_value", ""),
            "unit_raw": row.get("raw_unit", ""),
            "year_raw": row.get("normalized_year", "") or row.get("fiscal_year", ""),
            "value_prepared": value,
            "unit_prepared": unit,
            "year_prepared": year,
            "value_source": value_source,
            "unit_source": unit_source,
            "year_source": year_source,
            "preparation_quality_status": "complete" if not quality else "|".join(quality),
            "page_number": row.get("page_number", ""),
            "quote": row.get("quote", ""),
            "evidence_id": row.get("evidence_id", ""),
            "table_id": row.get("table_id", ""),
            "cell_id": row.get("cell_id", ""),
            "figure_id": row.get("figure_id", ""),
            "reviewer": row.get("reviewer", ""),
            "decision_reason": row.get("decision_reason", ""),
            "reviewer_notes": row.get("reviewer_notes", ""),
            "created_from_review_decision": "True",
            "is_final_indicator": "False",
            "score_produced": "False",
            **schema,
        }


def _choose(row: dict[str, str], corrected: str, normalized: str, raw: str) -> tuple[str, str]:
    if row.get(corrected):
        return row[corrected], corrected
    if row.get(normalized):
        return row[normalized], normalized
    return row.get(raw, ""), raw if row.get(raw) else ""

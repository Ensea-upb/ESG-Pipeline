from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

from .audit import build_audit
from .deduplicator import apply_deduplication
from .family_mapper import map_indicator_family
from .io_utils import read_csv, utcnow, write_csv, write_json, write_jsonl
from .normalizer import normalize_candidate
from .review_queue import build_review_queue
from .status_rules import assign_validation_status, AUTO_ACCEPT_THRESHOLD, AUTO_REJECT_THRESHOLD


VALIDATION_FIELDS = [
    "candidate_id", "candidate_validation_id", "document_id", "company", "fiscal_year",
    "source_engine", "information_type", "original_information_type", "esg_category", "label",
    "raw_value", "raw_unit", "year", "normalized_value", "normalized_unit",
    "normalized_year", "year_inferred", "normalization_status", "normalization_notes",
    "unit_detection_source", "year_detection_source", "page_number", "section_id",
    "evidence_id", "table_id", "cell_id", "figure_id", "quote", "confidence",
    "validation_status", "validation_reason", "is_validated_indicator", "score_produced",
    "indicator_family", "indicator_key_candidate", "indicator_label_candidate",
    "indicator_mapping_confidence", "indicator_mapping_reason", "review_priority",
    "review_reason", "review_action_suggested", "reviewer_decision", "reviewer_notes",
    "ready_for_manual_review", "duplicate_group_id", "duplicate_status",
    "canonical_validation_candidate_id", "duplicate_reason", "review_required",
    "extraction_status",
]


@dataclass
class IndicatorValidationResult:
    validations_count: int
    output_dir: Path
    summary: dict[str, Any]


class IndicatorValidator:
    def __init__(self, input_dir: Path, output_dir: Path, overwrite: bool = False) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.overwrite = overwrite

    def run(self) -> IndicatorValidationResult:
        if self.output_dir.exists() and not self.overwrite and any(self.output_dir.iterdir()):
            raise FileExistsError("output-dir already exists and is not empty; use --overwrite")
        started_at = utcnow()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        candidates_path = self._candidate_path()
        if not candidates_path.exists():
            raise FileNotFoundError("missing consolidated candidates input")
        source_rows = read_csv(candidates_path)
        validations = [self._prevalidate_candidate(idx, row) for idx, row in enumerate(source_rows, start=1)]
        duplicate_groups = apply_deduplication(validations)
        review_queue = build_review_queue(validations)
        self._write_core_outputs(validations, duplicate_groups, review_queue)
        audit = build_audit(validations, duplicate_groups, self.output_dir)
        summary = {
            "schema_version": "1.0.0",
            "module": "ESGIndicatorValidation",
            "input_dir": str(self.input_dir.resolve()),
            "output_dir": str(self.output_dir.resolve()),
            "input_candidates_file": candidates_path.name,
            "started_at": started_at,
            "finished_at": utcnow(),
            "status": "success",
            "input_candidates_count": len(source_rows),
            "validations_count": len(validations),
            "possible_indicators_count": sum(1 for row in validations if row["validation_status"] == "possible_indicator"),
            "needs_review_count": sum(1 for row in validations if row["validation_status"] == "needs_review"),
            "rejected_candidates_count": sum(1 for row in validations if row["validation_status"] == "reject_candidate"),
            "validated_indicators_count": 0,
            "score_produced_count": 0,
            "validation_status_distribution": dict(Counter(row["validation_status"] for row in validations)),
            "indicator_family_distribution": dict(Counter(row["indicator_family"] for row in validations)),
            "review_priority_distribution": dict(Counter(row["review_priority"] for row in validations)),
            "duplicate_groups_count": len(duplicate_groups),
            "duplicate_candidates_count": sum(1 for row in validations if row["duplicate_status"] == "duplicate_candidate"),
            "audit_errors_count": audit["errors_count"],
            "audit_warnings_count": audit["warnings_count"],
            "candidate_only": True,
            "review_required": True,
            "is_validated_indicator": False,
            "scores_produced": False,
        }
        write_json(self.output_dir / "indicator_validation_summary.json", summary)
        return IndicatorValidationResult(len(validations), self.output_dir, summary)

    def _candidate_path(self) -> Path:
        unique_path = self.input_dir / "consolidated_unique_candidates.csv"
        if unique_path.exists():
            return unique_path
        return self.input_dir / "consolidated_candidates.csv"

    def _prevalidate_candidate(self, index: int, row: dict[str, str]) -> dict[str, Any]:
        normalized = normalize_candidate(row)
        family = map_indicator_family(row, normalized)
        status, reason = assign_validation_status(row, normalized, family)
        confidence = _safe_float(row.get("confidence"))
        if status == "possible_indicator" and confidence >= AUTO_ACCEPT_THRESHOLD:
            reason = f"auto-accepted: confidence {confidence:.2f} >= {AUTO_ACCEPT_THRESHOLD}"
        elif confidence < AUTO_REJECT_THRESHOLD:
            status = "reject_candidate"
            reason = f"auto-rejected: confidence {confidence:.2f} < {AUTO_REJECT_THRESHOLD}"
        candidate_id = row.get("canonical_candidate_id") or row.get("evidence_id") or row.get("cell_id") or row.get("figure_id") or f"candidate_{index:06d}"
        result = {
            "candidate_id": candidate_id,
            "candidate_validation_id": f"indicator_validation_{index:06d}",
            "document_id": row.get("document_id", ""),
            "company": row.get("company", ""),
            "fiscal_year": row.get("fiscal_year", row.get("year", "")),
            "source_engine": row.get("source_engine", ""),
            "information_type": row.get("information_type", ""),
            "original_information_type": row.get("information_type", ""),
            "esg_category": row.get("esg_category", ""),
            "label": row.get("label", ""),
            "raw_value": row.get("raw_value", ""),
            "raw_unit": row.get("raw_unit", ""),
            "year": row.get("year", ""),
            "normalized_value": normalized["normalized_value"],
            "normalized_unit": normalized["normalized_unit"],
            "normalized_year": normalized["normalized_year"],
            "year_inferred": normalized["year_inferred"],
            "normalization_status": normalized["normalization_status"],
            "normalization_notes": normalized["normalization_notes"],
            "unit_detection_source": normalized["unit_detection_source"],
            "year_detection_source": normalized["year_detection_source"],
            "page_number": row.get("page_number", ""),
            "section_id": row.get("section_id", ""),
            "evidence_id": row.get("evidence_id", ""),
            "table_id": row.get("table_id", ""),
            "cell_id": row.get("cell_id", ""),
            "figure_id": row.get("figure_id", ""),
            "quote": row.get("quote", ""),
            "confidence": f"{confidence:.2f}",
            "validation_status": status,
            "validation_reason": reason,
            "is_validated_indicator": "False",
            "score_produced": "False",
            "indicator_family": family["indicator_family"],
            "indicator_key_candidate": family["indicator_key_candidate"],
            "indicator_label_candidate": family["indicator_label_candidate"],
            "indicator_mapping_confidence": f"{family['indicator_mapping_confidence']:.2f}",
            "indicator_mapping_reason": family["indicator_mapping_reason"],
            "review_priority": "",
            "review_reason": "",
            "review_action_suggested": "",
            "reviewer_decision": "",
            "reviewer_notes": "",
            "ready_for_manual_review": "False" if (status == "reject_candidate" or confidence >= AUTO_ACCEPT_THRESHOLD) else "True",
            "duplicate_group_id": "",
            "duplicate_status": "unique",
            "canonical_validation_candidate_id": "",
            "duplicate_reason": "",
            "review_required": "True",
            "extraction_status": "candidate_only",
        }
        return result

    def _write_core_outputs(
        self,
        validations: list[dict[str, Any]],
        duplicate_groups: list[dict[str, Any]],
        review_queue: list[dict[str, Any]],
    ) -> None:
        write_csv(self.output_dir / "indicator_candidate_validations.csv", validations, VALIDATION_FIELDS)
        write_jsonl(self.output_dir / "indicator_candidate_validations.jsonl", validations)
        write_csv(self.output_dir / "possible_indicators.csv", [r for r in validations if r["validation_status"] == "possible_indicator"], VALIDATION_FIELDS)
        write_csv(self.output_dir / "rejected_candidates.csv", [r for r in validations if r["validation_status"] == "reject_candidate"], VALIDATION_FIELDS)
        write_csv(self.output_dir / "validation_review_queue.csv", review_queue, VALIDATION_FIELDS)
        write_jsonl(self.output_dir / "validation_review_queue.jsonl", review_queue)
        write_json(self.output_dir / "review_queue_summary.json", {
            "schema_version": "1.0.0",
            "review_queue_count": len(review_queue),
            "review_priority_distribution": dict(Counter(row["review_priority"] for row in review_queue)),
        })
        write_csv(self.output_dir / "normalized_indicator_candidates.csv", validations, VALIDATION_FIELDS)
        write_jsonl(self.output_dir / "indicator_duplicate_groups.jsonl", duplicate_groups)
        deduped = [row for row in validations if row["duplicate_status"] != "duplicate_candidate"]
        write_csv(self.output_dir / "indicator_candidate_validations_deduplicated.csv", deduped, VALIDATION_FIELDS)
        write_jsonl(self.output_dir / "indicator_candidate_validations_deduplicated.jsonl", deduped)
        write_json(self.output_dir / "indicator_deduplication_summary.json", {
            "schema_version": "1.0.0",
            "duplicate_groups_count": len(duplicate_groups),
            "duplicate_candidates_count": sum(1 for row in validations if row["duplicate_status"] == "duplicate_candidate"),
            "deduplicated_records_count": len(deduped),
        })


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        log.debug("_safe_float: cannot convert %r to float, defaulting to 0.0", value)
        return 0.0

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import build_decision_audit
from .io_utils import read_csv, utcnow, write_csv, write_json, write_jsonl
from .review_rules import ALLOWED_PROPOSED_DECISIONS, decision_to_status
from .review_workspace import WORKSPACE_FIELDS


REVIEWED_FIELDS = [
    *WORKSPACE_FIELDS,
    "proposed_decision", "review_status", "reviewer", "review_date", "decision_reason",
    "corrected_value", "corrected_unit", "corrected_year", "corrected_indicator_family",
    "corrected_indicator_key", "needs_more_evidence_reason", "original_raw_value",
    "original_raw_unit", "original_year", "validated_indicator", "score_produced",
]


@dataclass
class ApplyDecisionResult:
    output_dir: Path
    reviewed_count: int
    summary: dict[str, Any]


class ReviewDecisionApplier:
    def __init__(self, workspace_dir: Path, decisions_file: Path, output_dir: Path, overwrite: bool = False) -> None:
        self.workspace_dir = workspace_dir
        self.decisions_file = decisions_file
        self.output_dir = output_dir
        self.overwrite = overwrite

    def run(self) -> ApplyDecisionResult:
        if self.output_dir.exists() and not self.overwrite and any(self.output_dir.iterdir()):
            raise FileExistsError("output-dir already exists and is not empty; use --overwrite")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        workspace = read_csv(self.workspace_dir / "manual_review_workspace.csv")
        decisions = {row.get("review_item_id", ""): row for row in read_csv(self.decisions_file)}
        reviewed = [self._apply(row, decisions.get(row.get("review_item_id", ""), {})) for row in workspace]
        write_csv(self.output_dir / "reviewed_candidates.csv", reviewed, REVIEWED_FIELDS)
        write_jsonl(self.output_dir / "reviewed_candidates.jsonl", reviewed)
        write_csv(self.output_dir / "accepted_candidate_inputs.csv", [r for r in reviewed if r["review_status"] == "accepted_candidate"], REVIEWED_FIELDS)
        write_csv(self.output_dir / "rejected_review_candidates.csv", [r for r in reviewed if r["review_status"] == "rejected_by_reviewer"], REVIEWED_FIELDS)
        write_csv(self.output_dir / "needs_more_evidence_candidates.csv", [r for r in reviewed if r["review_status"] == "needs_more_evidence"], REVIEWED_FIELDS)
        write_csv(self.output_dir / "deferred_candidates.csv", [r for r in reviewed if r["review_status"] == "decision_deferred"], REVIEWED_FIELDS)
        audit = build_decision_audit(reviewed, self.output_dir)
        summary = {
            "schema_version": "1.0.0",
            "module": "ESGManualReview",
            "workspace_dir": str(self.workspace_dir.resolve()),
            "decisions_file": str(self.decisions_file.resolve()),
            "output_dir": str(self.output_dir.resolve()),
            "generated_at": utcnow(),
            "review_items_count": len(workspace),
            "decisions_count": sum(1 for r in reviewed if r["proposed_decision"]),
            "accepted_candidates_count": sum(1 for r in reviewed if r["review_status"] == "accepted_candidate"),
            "rejected_candidates_count": sum(1 for r in reviewed if r["review_status"] == "rejected_by_reviewer"),
            "needs_more_evidence_count": sum(1 for r in reviewed if r["review_status"] == "needs_more_evidence"),
            "deferred_candidates_count": sum(1 for r in reviewed if r["review_status"] == "decision_deferred"),
            "missing_decision_count": sum(1 for r in reviewed if r["review_status"] == "missing_decision"),
            "invalid_decision_count": sum(1 for r in reviewed if r["review_status"] == "invalid_decision"),
            "review_status_distribution": dict(Counter(r["review_status"] for r in reviewed)),
            "validated_indicators_count": 0,
            "score_produced_count": 0,
            "audit_errors_count": audit["errors_count"],
            "audit_warnings_count": audit["warnings_count"],
        }
        write_json(self.output_dir / "review_decision_summary.json", summary)
        return ApplyDecisionResult(self.output_dir, len(reviewed), summary)

    def _apply(self, workspace_row: dict[str, str], decision: dict[str, str]) -> dict[str, Any]:
        proposed = (decision.get("proposed_decision") or "").strip()
        status = decision_to_status(proposed)
        if proposed not in ALLOWED_PROPOSED_DECISIONS:
            status = "invalid_decision"
        row = {field: workspace_row.get(field, "") for field in WORKSPACE_FIELDS}
        row.update({
            "proposed_decision": proposed,
            "review_status": status,
            "reviewer": decision.get("reviewer", ""),
            "review_date": decision.get("review_date", ""),
            "decision_reason": decision.get("decision_reason", ""),
            "corrected_value": decision.get("corrected_value", ""),
            "corrected_unit": decision.get("corrected_unit", ""),
            "corrected_year": decision.get("corrected_year", ""),
            "corrected_indicator_family": decision.get("corrected_indicator_family", ""),
            "corrected_indicator_key": decision.get("corrected_indicator_key", ""),
            "needs_more_evidence_reason": decision.get("needs_more_evidence_reason", ""),
            "original_raw_value": workspace_row.get("raw_value", ""),
            "original_raw_unit": workspace_row.get("raw_unit", ""),
            "original_year": workspace_row.get("normalized_year", ""),
            "validated_indicator": "False",
            "score_produced": "False",
        })
        return row

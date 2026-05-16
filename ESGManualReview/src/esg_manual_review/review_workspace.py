from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .decision_schema import DECISION_SCHEMA, DECISION_TEMPLATE_FIELDS
from .io_utils import utcnow, write_csv, write_json, write_jsonl
from .loader import load_indicator_validation_outputs
from .review_rules import sort_review_rows


WORKSPACE_FIELDS = [
    "review_item_id", "candidate_id", "document_id", "company", "fiscal_year",
    "source_engine", "validation_status", "indicator_family", "indicator_key_candidate",
    "label", "raw_value", "raw_unit", "normalized_value", "normalized_unit",
    "normalized_year", "page_number", "section_id", "evidence_id", "table_id",
    "cell_id", "figure_id", "quote", "confidence", "review_priority",
    "review_reason", "suggested_review_action", "human_decision",
    "human_decision_reason", "reviewer_notes",
]


@dataclass
class WorkspaceResult:
    output_dir: Path
    items_count: int
    summary: dict[str, Any]


class ManualReviewWorkspaceBuilder:
    def __init__(self, input_dir: Path, output_dir: Path, overwrite: bool = False) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.overwrite = overwrite

    def run(self) -> WorkspaceResult:
        if self.output_dir.exists() and not self.overwrite and any(self.output_dir.iterdir()):
            raise FileExistsError("output-dir already exists and is not empty; use --overwrite")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows, inventory = load_indicator_validation_outputs(self.input_dir)
        workspace = sort_review_rows([self._to_workspace_row(i, row) for i, row in enumerate(rows, start=1)])
        write_json(self.output_dir / "manual_review_input_inventory.json", inventory)
        write_csv(self.output_dir / "manual_review_loaded_candidates.csv", rows, list(rows[0].keys()) if rows else [])
        write_jsonl(self.output_dir / "manual_review_loaded_candidates.jsonl", rows)
        write_csv(self.output_dir / "manual_review_workspace.csv", workspace, WORKSPACE_FIELDS)
        write_jsonl(self.output_dir / "manual_review_workspace.jsonl", workspace)
        self._write_workspace_markdown(workspace)
        template = [{field: (row.get(field, "") if field in {"review_item_id", "candidate_id"} else "") for field in DECISION_TEMPLATE_FIELDS} for row in workspace]
        write_csv(self.output_dir / "review_decisions_template.csv", template, DECISION_TEMPLATE_FIELDS)
        write_jsonl(self.output_dir / "review_decisions_template.jsonl", template)
        write_json(self.output_dir / "review_decision_schema.json", DECISION_SCHEMA)
        self._write_instructions()
        summary = {
            "schema_version": "1.0.0",
            "module": "ESGManualReview",
            "input_dir": str(self.input_dir.resolve()),
            "output_dir": str(self.output_dir.resolve()),
            "generated_at": utcnow(),
            "review_items_count": len(workspace),
            "validation_status_distribution": dict(Counter(row["validation_status"] for row in workspace)),
            "review_priority_distribution": dict(Counter(row["review_priority"] for row in workspace)),
            "human_decisions_prefilled_count": 0,
            "final_indicators_produced": False,
            "scores_produced": False,
        }
        write_json(self.output_dir / "manual_review_summary.json", summary)
        write_json(self.output_dir / "review_workspace_summary.json", summary)
        return WorkspaceResult(self.output_dir, len(workspace), summary)

    def _to_workspace_row(self, index: int, row: dict[str, str]) -> dict[str, Any]:
        return {
            "review_item_id": f"review_item_{index:06d}",
            "candidate_id": row.get("candidate_id") or row.get("candidate_validation_id", ""),
            "document_id": row.get("document_id", ""),
            "company": row.get("company", ""),
            "fiscal_year": row.get("fiscal_year", ""),
            "source_engine": row.get("source_engine", ""),
            "validation_status": row.get("validation_status", ""),
            "indicator_family": row.get("indicator_family", ""),
            "indicator_key_candidate": row.get("indicator_key_candidate", ""),
            "label": row.get("label", ""),
            "raw_value": row.get("raw_value", ""),
            "raw_unit": row.get("raw_unit", ""),
            "normalized_value": row.get("normalized_value", ""),
            "normalized_unit": row.get("normalized_unit", ""),
            "normalized_year": row.get("normalized_year", ""),
            "page_number": row.get("page_number", ""),
            "section_id": row.get("section_id", ""),
            "evidence_id": row.get("evidence_id", ""),
            "table_id": row.get("table_id", ""),
            "cell_id": row.get("cell_id", ""),
            "figure_id": row.get("figure_id", ""),
            "quote": row.get("quote", ""),
            "confidence": row.get("confidence", ""),
            "review_priority": row.get("review_priority", ""),
            "review_reason": row.get("review_reason", ""),
            "suggested_review_action": row.get("review_action_suggested", ""),
            "human_decision": "",
            "human_decision_reason": "",
            "reviewer_notes": "",
        }

    def _write_workspace_markdown(self, rows: list[dict[str, Any]]) -> None:
        lines = ["# Manual Review Workspace", "", "No decision is prefilled. `accept_candidate` is not a final ESG indicator.", ""]
        for row in rows[:50]:
            lines.append(f"- {row['review_item_id']} | {row['validation_status']} | {row['indicator_family']} | page {row['page_number']} | {row['quote'][:160]}")
        (self.output_dir / "manual_review_workspace.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_instructions(self) -> None:
        text = """# Review Decision Instructions

Allowed `proposed_decision` values:

- `accept_candidate`
- `reject_candidate`
- `needs_more_evidence`
- `defer_decision`

`accept_candidate` does not create a final ESG indicator. It only marks the candidate as accepted for a future preparation layer.
"""
        (self.output_dir / "review_decision_instructions.md").write_text(text, encoding="utf-8")

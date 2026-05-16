"""
output_adapter.py — Write all V2 outputs. Format compatible with V1 pipeline for future integration.
All outputs go to --output-dir. Never modifies source directories.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import ensure_dir, write_csv, write_json, write_jsonl

_CANDIDATE_COLUMNS = [
    "candidate_id", "schema_version", "engine", "target_variable",
    "indicator_family", "document_id", "company", "company_name",
    "company_slug", "fiscal_year", "official_doc_type", "final_path",
    "page_number", "chunk_id", "source_type", "raw_value", "raw_unit",
    "normalized_value", "normalized_unit", "raw_year", "prepared_year",
    "quote", "evidence_id", "table_id", "figure_id", "crop_id",
    "retrieval_score", "extraction_score", "candidate_score",
    "candidate_status", "rejection_reason", "warning_flags", "lineage",
    "score_reason",
]

_RETRIEVAL_COLUMNS = [
    "retrieval_id", "target_variable", "chunk_id", "document_id", "company",
    "fiscal_year", "official_doc_type", "page_number", "source_type",
    "retrieval_score", "embedding_score", "keyword_score", "unit_score",
    "section_score", "structural_penalty", "matched_terms", "matched_units",
    "text_snippet",
]

_CHUNK_COLUMNS = [
    "chunk_id", "document_id", "company", "company_name", "company_slug",
    "fiscal_year", "official_doc_type", "final_path", "page_number",
    "section_id", "evidence_id", "table_id", "figure_id", "crop_id",
    "source_type", "text", "text_length", "has_numeric_value",
    "has_unit_candidate", "numeric_values_detected", "units_detected",
    "structural_noise_flags",
]


class OutputAdapter:
    def __init__(self, output_dir: str | Path, schema_version: str = "2.0.0") -> None:
        self.output_dir = ensure_dir(output_dir)
        self.schema_version = schema_version

    def write_chunks(self, chunks: list[dict[str, Any]]) -> None:
        write_csv(self.output_dir / "document_chunks_v2.csv", chunks, _CHUNK_COLUMNS)
        write_jsonl(self.output_dir / "document_chunks_v2.jsonl", chunks)

    def write_retrieval_results(self, results: list[dict[str, Any]]) -> None:
        write_csv(self.output_dir / "retrieval_results_v2.csv", results, _RETRIEVAL_COLUMNS)
        write_jsonl(self.output_dir / "retrieval_results_v2.jsonl", results)

    def write_candidates(self, candidates: list[dict[str, Any]]) -> None:
        found = [c for c in candidates if not c.get("candidate_status", "").startswith("rejected_")]
        rejected = [c for c in candidates if c.get("candidate_status", "").startswith("rejected_")]

        write_csv(self.output_dir / "targeted_candidates_v2.csv", candidates, _CANDIDATE_COLUMNS)
        write_jsonl(self.output_dir / "targeted_candidates_v2.jsonl", candidates)

        if rejected:
            write_csv(self.output_dir / "rejected_candidates_v2.csv", rejected, _CANDIDATE_COLUMNS)

    def write_variable_query_catalog(self, catalog_rows: list[dict[str, Any]]) -> None:
        write_csv(
            self.output_dir / "variable_query_catalog_v2.csv",
            catalog_rows,
            ["target_variable", "domain", "query_terms_en", "query_terms_fr",
             "expected_units", "forbidden_units", "min_relevance_score"],
        )

    def write_summary(
        self,
        doc_input: Any,
        chunks: list[dict[str, Any]],
        retrieval_results: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        embedding_backend_status: str,
        variables_requested: list[str],
        elapsed_seconds: float = 0.0,
    ) -> dict[str, Any]:
        found = [c for c in candidates if c.get("candidate_status") == "candidate_found"]
        needs_review = [c for c in candidates if c.get("candidate_status") == "needs_review"]
        rejected = [c for c in candidates if c.get("candidate_status", "").startswith("rejected_")]

        by_variable: dict[str, int] = {}
        for c in found + needs_review:
            v = c.get("target_variable", "unknown")
            by_variable[v] = by_variable.get(v, 0) + 1

        covered_variables = sorted(set(
            c.get("target_variable", "") for c in found + needs_review
            if c.get("target_variable")
        ))

        summary: dict[str, Any] = {
            "schema_version": self.schema_version,
            "engine": "esg_variable_targeted_extraction_v2",
            "document_id": getattr(doc_input, "document_id", ""),
            "company": getattr(doc_input, "company", ""),
            "company_slug": getattr(doc_input, "company_slug", ""),
            "fiscal_year": getattr(doc_input, "fiscal_year", ""),
            "official_doc_type": getattr(doc_input, "official_doc_type", ""),
            "final_path": getattr(doc_input, "final_path", ""),
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed_seconds, 1),
            "embedding_backend_status": embedding_backend_status,
            "variables_requested": variables_requested,
            "variables_covered": covered_variables,
            "variables_requested_count": len(variables_requested),
            "variables_covered_count": len(covered_variables),
            "chunks_built": len(chunks),
            "retrieval_results_count": len(retrieval_results),
            "candidates_total": len(candidates),
            "candidates_found": len(found),
            "candidates_needs_review": len(needs_review),
            "candidates_rejected": len(rejected),
            "candidates_by_variable": by_variable,
            "load_warnings": getattr(doc_input, "load_warnings", []),
            "status": "success",
        }
        write_json(self.output_dir / "extraction_v2_summary.json", summary)
        return summary

    def write_quality_report(
        self,
        summary: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> None:
        lines: list[str] = [
            "# Extraction V2 Quality Report",
            "",
            f"**Engine**: {summary.get('engine', '')}",
            f"**Document**: {summary.get('document_id', '')}",
            f"**Company**: {summary.get('company', '')} | FY {summary.get('fiscal_year', '')}",
            f"**Generated**: {summary.get('generated_at', '')}",
            f"**Embedding backend**: {summary.get('embedding_backend_status', '')}",
            "",
            "## Candidate Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total candidates | {summary.get('candidates_total', 0)} |",
            f"| candidate_found | {summary.get('candidates_found', 0)} |",
            f"| needs_review | {summary.get('candidates_needs_review', 0)} |",
            f"| rejected | {summary.get('candidates_rejected', 0)} |",
            f"| Variables covered | {summary.get('variables_covered_count', 0)} / {summary.get('variables_requested_count', 0)} |",
            "",
            "## Variables Covered",
            "",
        ]
        for v in summary.get("variables_covered", []):
            count = summary.get("candidates_by_variable", {}).get(v, 0)
            lines.append(f"- `{v}`: {count} candidates")

        lines.extend([
            "",
            "## Top Candidates (found)",
            "",
            "| Variable | Value | Unit | Page | Score |",
            "|----------|-------|------|------|-------|",
        ])
        top = sorted(
            [c for c in candidates if c.get("candidate_status") == "candidate_found"],
            key=lambda c: float(c.get("candidate_score", 0)),
            reverse=True,
        )[:20]
        for c in top:
            lines.append(
                f"| {c.get('target_variable', '')} | {c.get('raw_value', '')} | "
                f"{c.get('raw_unit', '')} | {c.get('page_number', '')} | "
                f"{c.get('candidate_score', 0):.2f} |"
            )

        if summary.get("load_warnings"):
            lines.extend(["", "## Warnings", ""])
            for w in summary.get("load_warnings", []):
                lines.append(f"- {w}")

        (self.output_dir / "extraction_v2_quality_report.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )

    def write_contract_validation(self, validation_result: dict[str, Any]) -> None:
        write_json(
            self.output_dir / "targeted_candidates_v2_contract_validation.json",
            validation_result,
        )

    def write_all(
        self,
        doc_input: Any,
        chunks: list[dict[str, Any]],
        retrieval_results: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        embedding_backend_status: str,
        variables_requested: list[str],
        elapsed_seconds: float = 0.0,
    ) -> dict[str, Any]:
        self.write_chunks(chunks)
        self.write_retrieval_results(retrieval_results)
        self.write_candidates(candidates)

        summary = self.write_summary(
            doc_input, chunks, retrieval_results, candidates,
            embedding_backend_status, variables_requested, elapsed_seconds,
        )
        self.write_quality_report(summary, candidates)
        return summary

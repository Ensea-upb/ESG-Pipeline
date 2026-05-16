from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import build_table_audit
from .io_utils import normalize, read_json, utcnow, write_csv, write_json, write_jsonl
from .loader import load_table_inputs, loaded_cells, table_items
from .metric_classifier import classify_rows, classify_text, family_for_category
from .reconstructor import reconstruct_tables
from .structure_detector import detect_structures
from .typed_csv_exporter import write_typed_csvs


CANDIDATE_FIELDS = [
    "schema_version", "document_id", "company", "fiscal_year", "table_id", "cell_id",
    "row_index", "column_index", "page_number", "section_id", "metric_key", "metric_label",
    "metric_family", "esg_category", "raw_value", "raw_unit", "reported_year", "inferred_year",
    "row_label", "column_label", "source_cell_text", "source_row_text", "confidence",
    "review_required", "extraction_status", "validation_notes",
]
COMMON_TYPED_FIELDS = [
    "document_id", "company", "fiscal_year", "table_id", "cell_id", "row_index", "column_index",
    "page_number", "section_id", "metric_key", "metric_label", "metric_family", "raw_value",
    "raw_unit", "reported_year", "confidence", "review_required", "extraction_status", "validation_notes",
]
OUTPUT_FILES = (
    "table_input_inventory.json", "table_items.jsonl", "table_cells_loaded.jsonl",
    "reconstructed_tables.jsonl", "table_reconstruction_audit.jsonl", "table_reconstruction_summary.json",
    "table_structure_index.jsonl", "table_structure_summary.json",
    "table_row_classification.jsonl", "table_row_classification_summary.json",
    "table_metric_candidates.csv", "table_metric_candidates.jsonl", "table_candidate_extraction_summary.json",
    "table_observed_metrics.csv", "table_targets.csv", "table_contexts.csv", "table_rejected_candidates.csv",
    "table_audit_summary.json", "table_audit_findings.jsonl", "table_audit_samples.csv",
    "table_extraction_summary.json",
)
NUMERIC_RE = re.compile(r"^-?\(?\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?\)?%?$|^-?\d+(?:\.\d+)?%?$")
VALUE_RE = re.compile(r"-?\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?")
# Keep UNIT_RE in sync with structure_detector.UNIT_RE (extended ESG unit set).
UNIT_RE = re.compile(
    r"\b(%|(?:k|m|g)?tco2e?|co2eq?|gwh|mwh|kwh|gj|mj|tep|toe"
    r"|hm3|m3|m²|tonnes?|(?<!\w)ha(?!\w)|hectares?|km2|m2"
    r"|employees?|headcount|hours?|heures?|accidents?|fte"
    r"|(?<!\w)kt(?!\w)|(?<!\w)mt(?!\w))\b",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(20[0-4]\d|19[8-9]\d)\b")


@dataclass
class TableExtractionResult:
    candidates_count: int
    output_dir: Path
    summary: dict[str, Any]


_CORPUS_DIR_NAMES = {"ESGFinalCorpus", "ESGCorpus", "ESGCorpusTaxonomy", "corpus"}


def infer_company_year(document_id: str, inventory: dict[str, Any], summary: dict[str, Any]) -> tuple[str, str]:
    """Extract (company_slug, fiscal_year) from the document path or document_id.

    Tries in order:
    1. inventory/summary pdf_path: look for a known corpus directory segment.
    2. Regex on document_id: <company_slug>[-_]<4-digit year>.
    3. Regex on document_id: any 4-digit year with the prefix as company slug.
    """
    path_text = str(inventory.get("pdf_path") or summary.get("pdf_path") or "")
    parts = [part for part in re.split(r"[\\/]+", path_text) if part]
    for corpus_name in _CORPUS_DIR_NAMES:
        if corpus_name in parts:
            idx = parts.index(corpus_name)
            if len(parts) > idx + 2:
                return parts[idx + 1], parts[idx + 2]

    # Fall back to document_id pattern matching
    match = re.search(r"([a-z0-9][a-z0-9-]*)[_-](20\d{2})", document_id, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    # Last resort: extract any 4-digit year from document_id
    year_match = re.search(r"(20\d{2})", document_id)
    if year_match:
        company_slug = document_id[:year_match.start()].strip("-_").lower() or ""
        return company_slug, year_match.group(1)
    return "", ""


class ESGTableExtractor:
    def __init__(self, input_dir: Path, output_dir: Path, overwrite: bool = False) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.overwrite = overwrite

    def run(self) -> TableExtractionResult:
        self._validate_write_safety()
        started_at = utcnow()
        inputs = load_table_inputs(self.input_dir)
        document_id = inputs["document_id"]
        company, fiscal_year = infer_company_year(document_id, inputs["inventory"], inputs["summary"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        items = table_items(inputs["tables"])
        cells_loaded = loaded_cells(inputs["cells"])
        write_json(self.output_dir / "table_input_inventory.json", {
            "schema_version": "0.1.0", "document_id": document_id, "input_dir": str(self.input_dir.resolve()),
            "tables_count": len(items), "cells_count": len(cells_loaded), "review_required": True,
        })
        write_jsonl(self.output_dir / "table_items.jsonl", items)
        write_jsonl(self.output_dir / "table_cells_loaded.jsonl", cells_loaded)

        reconstructed, reconstruction_audit, reconstruction_summary = reconstruct_tables(items, cells_loaded)
        write_jsonl(self.output_dir / "reconstructed_tables.jsonl", reconstructed)
        write_jsonl(self.output_dir / "table_reconstruction_audit.jsonl", reconstruction_audit)
        write_json(self.output_dir / "table_reconstruction_summary.json", reconstruction_summary)

        structures, structure_summary = detect_structures(reconstructed, fiscal_year=fiscal_year)
        write_jsonl(self.output_dir / "table_structure_index.jsonl", structures)
        write_json(self.output_dir / "table_structure_summary.json", structure_summary)

        row_classes, row_summary = classify_rows(reconstructed)
        write_jsonl(self.output_dir / "table_row_classification.jsonl", row_classes)
        write_json(self.output_dir / "table_row_classification_summary.json", row_summary)

        candidates = self._extract_candidates(reconstructed, cells_loaded, structures, row_classes, company, fiscal_year)
        write_csv(self.output_dir / "table_metric_candidates.csv", candidates, CANDIDATE_FIELDS)
        write_jsonl(self.output_dir / "table_metric_candidates.jsonl", candidates)
        write_json(self.output_dir / "table_candidate_extraction_summary.json", {
            "schema_version": "0.5.0",
            "candidates_count": len(candidates),
            "metric_family_distribution": dict(Counter(row["metric_family"] for row in candidates)),
            "candidates_without_unit": sum(1 for row in candidates if not row["raw_unit"]),
            "candidates_without_year": sum(1 for row in candidates if not row["reported_year"]),
            "candidate_only": True,
        })
        typed_counts = write_typed_csvs(self.output_dir, candidates, CANDIDATE_FIELDS)
        audit_summary = build_table_audit(self.output_dir, candidates, CANDIDATE_FIELDS)

        summary = {
            "schema_version": "1.0.0", "module": "ESGTableExtraction", "document_id": document_id,
            "input_dir": str(self.input_dir.resolve()), "output_dir": str(self.output_dir.resolve()),
            "started_at": started_at, "finished_at": utcnow(), "status": "success",
            "tables_read_count": len(items), "cells_read_count": len(cells_loaded),
            "reconstructed_tables_count": len(reconstructed), "table_candidates_count": len(candidates),
            "metric_family_distribution": dict(Counter(row["metric_family"] for row in candidates)),
            "typed_csv_counts": typed_counts, "review_required_count": len(candidates), "candidate_only": True,
            "audit_errors_count": audit_summary["errors_count"], "audit_warnings_count": audit_summary["warnings_count"],
            "quality_warning": bool(audit_summary["warnings_count"]), "real_world_table_audit_pending": True,
            "outputs": list(OUTPUT_FILES),
        }
        write_json(self.output_dir / "table_extraction_summary.json", summary)
        return TableExtractionResult(len(candidates), self.output_dir, summary)

    def _validate_write_safety(self) -> None:
        if not self.input_dir.exists():
            raise FileNotFoundError(f"input-dir does not exist: {self.input_dir}")
        existing = [name for name in OUTPUT_FILES if (self.output_dir / name).exists()]
        if existing and not self.overwrite:
            raise FileExistsError("Table output files already exist. Use --overwrite to replace: " + ", ".join(existing))

    def _extract_candidates(self, tables: list[dict[str, Any]], cells: list[dict[str, Any]], structures: list[dict[str, Any]], row_classes: list[dict[str, Any]], company: str, fiscal_year: str) -> list[dict[str, Any]]:
        cells_by_table_row: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
        cell_by_key = {(cell["table_id"], int(cell["row_index"]), int(cell["column_index"])): cell for cell in cells}
        for cell in cells:
            cells_by_table_row[(cell["table_id"], int(cell["row_index"]))].append(cell)
        structure_by_table = {row["table_id"]: row for row in structures}
        row_class_by_key = {(row["table_id"], int(row["row_index"])): row for row in row_classes}
        candidates: list[dict[str, Any]] = []
        for table in tables:
            table_id = table["table_id"]
            structure = structure_by_table.get(table_id, {})
            unit_context = self._unit_context(structure)
            year_by_col = self._year_by_col(structure)
            label_cols = set(structure.get("candidate_label_columns") or [0])
            for r, row in enumerate(table.get("matrix") or []):
                row_cells = cells_by_table_row.get((table_id, r), [])
                row_text = " ".join(str(cell) for cell in row if str(cell).strip())
                row_class = row_class_by_key.get((table_id, r), {})
                category = row_class.get("row_category") or classify_text(row_text)[0]
                family = family_for_category(category)
                if category == "unknown" and not unit_context:
                    continue
                row_label = self._row_label(row, label_cols)
                for c, text in enumerate(row):
                    text = normalize(text)
                    if not text or not NUMERIC_RE.match(text):
                        continue
                    cell = cell_by_key.get((table_id, r, c), {})
                    if cell.get("is_header_cell"):
                        continue
                    raw_value_match = VALUE_RE.search(text)
                    if not raw_value_match:
                        continue
                    raw_value = raw_value_match.group(0)
                    direct_unit = self._unit_from_text(text) or self._unit_from_text(row_label)
                    raw_unit = direct_unit or unit_context
                    if category == "unknown" and not direct_unit:
                        continue
                    reported_year, inferred = year_by_col.get(c, ("", False))
                    if not reported_year:
                        reported_year, inferred = fiscal_year, True
                    notes = []
                    if not raw_unit:
                        notes.append("raw_unit_missing")
                    if inferred:
                        notes.append("year_inferred")
                    if table.get("source_extraction_status") == "low_confidence":
                        notes.append("low_confidence_table")
                    confidence = 0.45
                    if raw_unit:
                        confidence += 0.05
                    if not inferred:
                        confidence += 0.05
                    if table.get("source_extraction_status") == "low_confidence":
                        confidence -= 0.1
                    confidence = round(max(0.1, min(0.6, confidence)), 2)
                    candidates.append({
                        "schema_version": "0.5.0", "document_id": table.get("document_id", ""), "company": company,
                        "fiscal_year": fiscal_year, "table_id": table_id, "cell_id": cell.get("cell_id", ""),
                        "row_index": r, "column_index": c, "page_number": table.get("page_number"), "section_id": table.get("section_id", ""),
                        "metric_key": f"{family}_{category}", "metric_label": row_label or category,
                        "metric_family": family, "esg_category": category, "raw_value": raw_value, "raw_unit": raw_unit,
                        "reported_year": reported_year, "inferred_year": bool(inferred), "row_label": row_label,
                        "column_label": self._column_label(table.get("matrix") or [], c), "source_cell_text": text,
                        "source_row_text": row_text, "confidence": confidence, "review_required": True,
                        "extraction_status": "candidate_only", "validation_notes": ";".join(notes),
                    })
        return candidates

    def _unit_context(self, structure: dict[str, Any]) -> str:
        """Return the most reliable unit context for a table.

        Prefers units found in header rows (row_index in header_row_indices)
        over units found in body cells, since headers describe the whole column.
        """
        cells = structure.get("candidate_unit_cells") or []
        if not cells:
            return ""
        header_indices = set(structure.get("header_row_indices") or [])
        header_units = [c for c in cells if c.get("row_index") in header_indices]
        preferred = header_units if header_units else cells
        return str(preferred[0].get("unit", ""))

    def _year_by_col(self, structure: dict[str, Any]) -> dict[int, tuple[str, bool]]:
        result: dict[int, tuple[str, bool]] = {}
        for item in structure.get("candidate_year_columns") or []:
            col = item.get("column_index")
            if col is not None:
                result[int(col)] = (str(item.get("year", "")), bool(item.get("inferred_year", False)))
        return result

    def _unit_from_text(self, text: str) -> str:
        match = UNIT_RE.search(text or "")
        return match.group(1) if match else ""

    def _row_label(self, row: list[str], label_cols: set[int]) -> str:
        labels = [normalize(cell) for idx, cell in enumerate(row) if idx in label_cols and normalize(cell)]
        return " ".join(labels)[:300]

    def _column_label(self, matrix: list[list[str]], col: int) -> str:
        labels = [normalize(row[col]) for row in matrix[:3] if col < len(row) and normalize(row[col])]
        return " ".join(labels)[:200]


__all__ = ["CANDIDATE_FIELDS", "COMMON_TYPED_FIELDS", "ESGTableExtractor", "TableExtractionResult"]

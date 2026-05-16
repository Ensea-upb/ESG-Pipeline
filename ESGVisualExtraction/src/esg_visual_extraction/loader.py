from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _infer_company_year_from_path(input_dir: Path) -> tuple[str, str]:
    """Try to infer company and year from ESGFinalCorpus/COMPANY/YEAR/ path pattern."""
    parts = input_dir.resolve().parts
    for i, part in enumerate(parts):
        if part == "ESGFinalCorpus" and i + 2 < len(parts):
            return parts[i + 1], parts[i + 2]
    return "", ""


def _resolve_company_year(
    input_dir: Path,
    document_record: dict[str, Any],
    inventory: dict[str, Any],
) -> tuple[str, str]:
    """Resolve company and fiscal_year using authority order:
    1. document_record.json
    2. document_inventory.json
    3. infer_company_year() from path
    4. empty string with warning
    """
    # Level 1: document_record.json
    dr_path = input_dir / "document_record.json"
    if dr_path.exists():
        dr = read_json(dr_path)
        company = str(dr.get("company") or "").strip()
        fiscal_year = str(dr.get("fiscal_year") or "").strip()
        if company and fiscal_year:
            return company, fiscal_year
    # Level 2: document_inventory.json (already read)
    company = str(inventory.get("company") or "").strip()
    fiscal_year = str(inventory.get("fiscal_year") or "").strip()
    if company and fiscal_year:
        return company, fiscal_year
    # Level 3: infer from path
    inferred_company, inferred_year = _infer_company_year_from_path(input_dir)
    if inferred_company and inferred_year:
        return inferred_company, inferred_year
    # Level 4: empty with implicit warning (caller can log)
    return "", ""


def load_visual_inputs(input_dir: Path) -> dict[str, Any]:
    figure_index_path = input_dir / "figure_index.jsonl"
    if not figure_index_path.exists():
        raise FileNotFoundError(f"figure_index.jsonl is required: {figure_index_path}")
    inventory = read_json(input_dir / "document_inventory.json")
    document_record = read_json(input_dir / "document_record.json")
    summary = read_json(input_dir / "extraction_summary.json")
    figure_statistics = read_json(input_dir / "figure_statistics.json")
    figures = read_jsonl(figure_index_path)
    evidence_rows = read_jsonl(input_dir / "multimodal_evidence_index.jsonl")
    evidence_by_figure = {
        row.get("source_element_id"): row
        for row in evidence_rows
        if row.get("source_element_type") == "figure" or row.get("source_modality") == "figure"
    }
    document_id = str(inventory.get("document_id") or summary.get("document_id") or input_dir.name)
    pdf_path = str(inventory.get("pdf_path") or summary.get("pdf_path") or "")
    company, fiscal_year = _resolve_company_year(input_dir, document_record, inventory)
    return {
        "document_id": document_id,
        "pdf_path": pdf_path,
        "company": company,
        "fiscal_year": fiscal_year,
        "inventory": inventory,
        "summary": summary,
        "figure_statistics": figure_statistics,
        "figures": figures,
        "evidence_by_figure": evidence_by_figure,
    }


def build_visual_items(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    evidence_by_figure = inputs.get("evidence_by_figure") or {}
    for index, figure in enumerate(inputs.get("figures") or [], start=1):
        evidence = evidence_by_figure.get(figure.get("figure_id"), {})
        rows.append({
            "schema_version": "0.1.0",
            "visual_item_id": f"visual_item_{index:04d}",
            "document_id": inputs["document_id"],
            "figure_id": figure.get("figure_id", ""),
            "page_number": figure.get("page_number"),
            "section_id": figure.get("section_id"),
            "evidence_id": evidence.get("evidence_id", ""),
            "figure_type": figure.get("figure_type", "unknown_visual"),
            "visual_object_level": figure.get("visual_object_level", ""),
            "detection_method": figure.get("detection_method", ""),
            "nearby_caption_text": figure.get("nearby_caption_text") or "",
            "figure_bbox": figure.get("figure_bbox"),
            "figure_quality_flags": figure.get("figure_quality_flags") or [],
            "source_page_diagnostic_flags": figure.get("source_page_diagnostic_flags") or [],
            "extraction_status": "visual_item_loaded",
            "review_required": True,
        })
    return rows


__all__ = [
    "build_visual_items",
    "load_visual_inputs",
    "read_json",
    "read_jsonl",
    "utcnow",
    "write_json",
    "write_jsonl",
]

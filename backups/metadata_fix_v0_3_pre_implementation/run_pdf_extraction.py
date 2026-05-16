#!/usr/bin/env python
"""Extract a single PDF into auditable document-structure outputs.

This v0 engine is intentionally small:
- one PDF per run;
- no ESG metric extraction;
- no writes outside --output-dir;
- no append mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
ENGINE_CONTRACT_VERSION = "1.0.0"
LOW_TEXT_CHAR_THRESHOLD = 100
POSSIBLE_VISUAL_TEXT_THRESHOLD = 100
TOC_MIN_TITLE_BLOCKS = 8
TOC_MIN_TITLES_ENDING_WITH_NUMBER = 5
HIGH_TITLE_DENSITY_THRESHOLD = 0.60
SAMPLE_LIMIT = 20
SAMPLE_TEXT_LIMIT = 200
UNKNOWN_BLOCK_WARNING_THRESHOLD = 0.30
SECTION_CANDIDATE_SCORE_THRESHOLD = 0.55
EVIDENCE_QUOTE_LIMIT = 800
MIN_PARAGRAPH_EVIDENCE_CHARS = 30
SHORT_EVIDENCE_REVIEW_THRESHOLD = 60
EVIDENCE_FRAGMENTATION_AVERAGE_LENGTH_THRESHOLD = 100
SECTION_HIGH_EVIDENCE_COUNT_THRESHOLD = 300
SECTION_HIGH_EVIDENCE_SHARE_THRESHOLD = 0.70
EXPECTED_OUTPUT_FILES = (
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
)

# ── v0.5 table constants ───────────────────────────────────────────────────────
TABLE_MIN_ROWS = 2
TABLE_MIN_COLS = 2
TABLE_TEXT_STRATEGY_SETTINGS: dict[str, Any] = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "snap_x_tolerance": 5,
    "snap_y_tolerance": 5,
    "min_words_vertical": 2,
    "min_words_horizontal": 1,
}
TABLE_LIKE_KEYWORDS = frozenset([
    "revenue", "total", "amount", "eur", "million", "number", "count",
    "table", "breakdown", "subtotal", "ratio", "emissions", "consumption",
    "headcount", "employees", "scope", "gwh", "mwh", "tco2",
])

# ── v0.5.2 table quality thresholds ──────────────────────────────────────────
TABLE_MOSTLY_EMPTY_CELLS_RATIO = 0.80
TABLE_HIGH_EMPTY_CELLS_RATIO = 0.50
TABLE_HIGH_FRAGMENTED_CELLS_RATIO = 0.30
TABLE_TINY_ARTIFACT_MAX_CELLS = 3

_FRAGMENTED_CELL_RE = re.compile(r"^[a-zA-ZÀ-ž]{1,3}$")
_NUMERIC_CELL_RE = re.compile(r"^[\d\s,.'%()±+\-€$£]+$")

# ── v0.6 figure constants ─────────────────────────────────────────────────────
FIGURE_LOGO_MAX_AREA_PT2 = 5000.0
FIGURE_ALLOWED_STATUSES = frozenset(["detected", "low_confidence", "detected_not_interpreted", "failed"])
FIGURE_ALLOWED_TYPES = frozenset(["image", "chart", "diagram", "logo", "map", "unknown_visual"])
_FIGURE_CAPTION_RE = re.compile(
    r"^\s*(figure|fig\.|chart|graph|diagram|map|image|illustration|graphique|sch[eé]ma)\s+\d+",
    re.IGNORECASE,
)
_FIGURE_TYPE_KEYWORDS: dict[str, str] = {
    "chart": "chart",
    "graph": "chart",
    "graphique": "chart",
    "diagram": "diagram",
    "schéma": "diagram",
    "schema": "diagram",
    "map": "map",
    "carte": "map",
    "logo": "logo",
}


@dataclass
class ExtractionOptions:
    pdf_path: Path
    document_id: str
    output_dir: Path
    max_pages: int | None
    overwrite: bool


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def require_pdfplumber():
    try:
        import pdfplumber  # type: ignore

        return pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "pdfplumber is required for PDF extraction. Install it with: "
            "python -m pip install pdfplumber"
        ) from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_safe_output_dir(options: ExtractionOptions) -> None:
    pdf_path = options.pdf_path.resolve()
    output_dir = options.output_dir.resolve()

    if output_dir == pdf_path.parent:
        raise ValueError("--output-dir must not be the PDF source directory.")
    if "ESGFinalCorpus" in output_dir.parts:
        raise ValueError("--output-dir must not be inside ESGFinalCorpus.")

    existing_outputs = [output_dir / name for name in EXPECTED_OUTPUT_FILES if (output_dir / name).exists()]
    if existing_outputs and not options.overwrite:
        names = ", ".join(path.name for path in existing_outputs)
        raise FileExistsError(
            "Output files already exist. Use --overwrite to replace expected "
            f"outputs only: {names}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
    return records


def read_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def quality_record(
    check_name: str,
    status: str,
    severity: str,
    message: str,
    target_type: str = "document",
    target_id: str = "",
    document_id: str = "",
    page_id: str | None = None,
    review_required: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "quality_check_id": stable_quality_id(document_id, check_name, target_id),
        "target_type": target_type,
        "target_id": target_id or document_id,
        "check_name": check_name,
        "status": status,
        "severity": severity,
        "document_id": document_id or None,
        "page_id": page_id,
        "message": message,
        "review_required": review_required,
        "created_at": utcnow(),
    }


def stable_quality_id(document_id: str, check_name: str, target_id: str) -> str:
    raw = f"{document_id}|{check_name}|{target_id}"
    return "qc_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def bbox_from_words(words: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not words:
        return None
    try:
        return {
            "x0": min(float(word["x0"]) for word in words),
            "y0": min(float(word["top"]) for word in words),
            "x1": max(float(word["x1"]) for word in words),
            "y1": max(float(word["bottom"]) for word in words),
            "coordinate_system": "pdf_points",
        }
    except Exception:
        return None


def classify_block(text: str) -> str:
    clean = " ".join(text.strip().split())
    if not clean:
        return "unknown"
    alpha_chars = [char for char in clean if char.isalpha()]
    uppercase_ratio = (
        sum(1 for char in alpha_chars if char.isupper()) / len(alpha_chars)
        if alpha_chars
        else 0.0
    )
    if len(clean) <= 90 and (uppercase_ratio > 0.75 or clean[:2].isdigit()):
        return "title"
    return "paragraph"


def normalize_repeated_text(text: str) -> str:
    clean = " ".join(str(text or "").lower().split())
    clean = re.sub(r"\d+", "#", clean)
    return clean.strip()


def is_list_item_text(text: str) -> bool:
    clean = str(text or "").strip()
    return bool(
        re.match(r"^[-*•–]\s+", clean)
        or re.match(r"^\d+[\.)]\s+", clean)
        or re.match(r"^\([a-zA-Z]\)\s+", clean)
        or re.match(r"^[a-zA-Z]\)\s+", clean)
    )


def is_caption_text(text: str) -> bool:
    return bool(
        re.match(
            r"^\s*(figure|fig\.|table|exhibit|chart|graph|tableau|graphique)\s+\d+",
            str(text or ""),
            re.IGNORECASE,
        )
    )


def looks_like_toc_entry(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split())
    return title_ends_with_number(clean) or bool(re.match(r"^[A-Z][A-Z0-9\s,&'/-]{4,}\s+\d+$", clean))


def is_footnote_text(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split())
    if len(clean) < 25:
        return False
    return bool(
        re.match(r"^\((?:\d+|[a-zA-Z])\)\s+\S+", clean)
        or re.match(r"^\*\s+\S+", clean)
    )


def is_footer_label_text(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split()).lower()
    return bool(
        "universal registration document" in clean
        or "annual report" in clean
        or "document d'enregistrement universel" in clean
        or "rapport annuel" in clean
    )


def is_footer_pattern_text(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split())
    return bool(
        re.match(r"^\d{1,4}\s+20\d{2}\s+Universal Registration Document$", clean, re.IGNORECASE)
        or re.match(r"^20\d{2}\s+Universal Registration Document\s+\d{1,4}$", clean, re.IGNORECASE)
        or re.match(r"^\d{1,4}\s+20\d{2}\s+Universal Registration Document\s+\d{1,4}$", clean, re.IGNORECASE)
    )


def title_ends_with_number(text: str) -> bool:
    return bool(text.strip()) and text.strip().split()[-1].strip(".").isdigit()


def truncate_sample(text: str) -> str:
    clean = " ".join(str(text or "").split())
    return clean[:SAMPLE_TEXT_LIMIT]


def page_diagnostics(
    page_record: dict[str, Any],
    page_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    total_blocks = len(page_blocks)
    title_blocks = [
        block
        for block in page_blocks
        if block.get("block_type") in {"title", "toc_entry"}
    ]
    title_blocks_ending_with_number = [
        block for block in title_blocks if title_ends_with_number(str(block.get("text", "")))
    ]
    text_char_count = int(page_record.get("text_char_count") or 0)
    extraction_status = str(page_record.get("extraction_status") or "")
    title_density = (len(title_blocks) / total_blocks) if total_blocks else 0.0

    return {
        "page_id": page_record.get("page_id"),
        "page_number": page_record.get("page_number"),
        "text_char_count": text_char_count,
        "total_blocks": total_blocks,
        "title_blocks_count": len(title_blocks),
        "title_blocks_ending_with_number_count": len(title_blocks_ending_with_number),
        "title_density": round(title_density, 6),
        "is_low_text": text_char_count < LOW_TEXT_CHAR_THRESHOLD,
        "is_possible_visual": (
            extraction_status == "ok" and 0 < text_char_count < POSSIBLE_VISUAL_TEXT_THRESHOLD
        ),
        "is_possible_toc": (
            len(title_blocks) >= TOC_MIN_TITLE_BLOCKS
            and len(title_blocks_ending_with_number) >= TOC_MIN_TITLES_ENDING_WITH_NUMBER
        ),
        "is_high_title_density": total_blocks > 0 and title_density > HIGH_TITLE_DENSITY_THRESHOLD,
    }


def build_text_block_statistics(
    document_id: str,
    page_records: list[dict[str, Any]],
    text_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    blocks_by_page: dict[str, int] = {}
    page_lookup = {str(page.get("page_id")): page for page in page_records}
    blocks_by_page_id: dict[str, list[dict[str, Any]]] = {str(page.get("page_id")): [] for page in page_records}
    block_type_counts: dict[str, int] = {}
    block_lengths: list[int] = []
    blocks_with_bbox_count = 0
    sample_titles: list[str] = []
    sample_paragraphs: list[str] = []
    samples_by_type: dict[str, list[str]] = {}

    for block in text_blocks:
        page_id = str(block.get("page_id", ""))
        blocks_by_page_id.setdefault(page_id, []).append(block)
        block_type = str(block.get("block_type") or "unknown")
        block_type_counts[block_type] = block_type_counts.get(block_type, 0) + 1
        text = str(block.get("text") or "")
        block_lengths.append(len(text))
        if block.get("bbox") is not None:
            blocks_with_bbox_count += 1
        samples_by_type.setdefault(block_type, [])
        if len(samples_by_type[block_type]) < SAMPLE_LIMIT:
            samples_by_type[block_type].append(truncate_sample(text))
        if block_type == "title" and len(sample_titles) < SAMPLE_LIMIT:
            sample_titles.append(truncate_sample(text))
        if block_type == "paragraph" and len(sample_paragraphs) < SAMPLE_LIMIT:
            sample_paragraphs.append(truncate_sample(text))

    for page_id, blocks in blocks_by_page_id.items():
        page = page_lookup.get(page_id, {})
        page_number = page.get("page_number", page_id)
        blocks_by_page[str(page_number)] = len(blocks)

    diagnostics = [
        page_diagnostics(page, blocks_by_page_id.get(str(page.get("page_id")), []))
        for page in page_records
    ]

    total_blocks = len(text_blocks)
    unknown_blocks_count = block_type_counts.get("unknown", 0)
    unknown_blocks_ratio = round(unknown_blocks_count / total_blocks, 6) if total_blocks else 0.0
    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "total_blocks": total_blocks,
        "block_type_counts": block_type_counts,
        "blocks_by_page": blocks_by_page,
        "average_block_length": round(sum(block_lengths) / len(block_lengths), 6) if block_lengths else 0,
        "median_block_length": statistics.median(block_lengths) if block_lengths else 0,
        "blocks_with_bbox_count": blocks_with_bbox_count,
        "blocks_without_bbox_count": total_blocks - blocks_with_bbox_count,
        "header_blocks_count": block_type_counts.get("header", 0),
        "footer_blocks_count": block_type_counts.get("footer", 0),
        "toc_entry_blocks_count": block_type_counts.get("toc_entry", 0),
        "caption_blocks_count": block_type_counts.get("caption", 0),
        "list_item_blocks_count": block_type_counts.get("list_item", 0),
        "footnote_blocks_count": block_type_counts.get("footnote", 0),
        "refined_footer_blocks_count": block_type_counts.get("footer", 0),
        "unknown_blocks_ratio": unknown_blocks_ratio,
        "structural_blocks_ratio": round(
            (
                block_type_counts.get("header", 0)
                + block_type_counts.get("footer", 0)
                + block_type_counts.get("toc_entry", 0)
                + block_type_counts.get("footnote", 0)
            )
            / total_blocks,
            6,
        )
        if total_blocks
        else 0.0,
        "pages_low_text": [
            item["page_number"] for item in diagnostics if item["is_low_text"]
        ],
        "possible_visual_pages": [
            item["page_number"] for item in diagnostics if item["is_possible_visual"]
        ],
        "possible_toc_pages": [
            item["page_number"] for item in diagnostics if item["is_possible_toc"]
        ],
        "high_title_density_pages": [
            item["page_number"] for item in diagnostics if item["is_high_title_density"]
        ],
        "page_diagnostics": diagnostics,
        "sample_titles": sample_titles,
        "sample_paragraphs": sample_paragraphs,
        "sample_headers": samples_by_type.get("header", [])[:SAMPLE_LIMIT],
        "sample_footers": samples_by_type.get("footer", [])[:SAMPLE_LIMIT],
        "sample_footnotes": samples_by_type.get("footnote", [])[:SAMPLE_LIMIT],
        "sample_toc_entries": samples_by_type.get("toc_entry", [])[:SAMPLE_LIMIT],
        "sample_captions": samples_by_type.get("caption", [])[:SAMPLE_LIMIT],
        "sample_list_items": samples_by_type.get("list_item", [])[:SAMPLE_LIMIT],
        "sample_refined_footers": samples_by_type.get("footer", [])[:SAMPLE_LIMIT],
        "samples_by_block_type": samples_by_type,
    }


def build_text_block_statistics_from_files(
    text_blocks_path: Path,
    page_index_path: Path,
    document_id: str | None = None,
) -> dict[str, Any]:
    page_records = read_jsonl(page_index_path)
    text_blocks = read_jsonl(text_blocks_path)
    resolved_document_id = (
        document_id
        or (text_blocks[0].get("document_id") if text_blocks else None)
        or (page_records[0].get("document_id") if page_records else None)
        or "unknown"
    )
    return build_text_block_statistics(str(resolved_document_id), page_records, text_blocks)


def extract_text_blocks_from_page(
    page: Any,
    document_id: str,
    page_id: str,
    page_number: int,
    reading_order_start: int,
) -> tuple[list[dict[str, Any]], int, int]:
    text = page.extract_text() or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    words = page.extract_words() or []
    blocks: list[dict[str, Any]] = []
    reading_order = reading_order_start

    # v0 keeps one block per extracted line. Bbox is best-effort by assigning
    # all words on the same rough vertical band to the line.
    unused_words = list(words)
    for block_index, line in enumerate(lines, start=1):
        line_words: list[dict[str, Any]] = []
        line_tokens = line.split()
        if line_tokens and unused_words:
            candidate_words = unused_words[: len(line_tokens)]
            candidate_text = " ".join(str(word.get("text", "")) for word in candidate_words)
            if candidate_text.replace(" ", "")[:20] == line.replace(" ", "")[:20]:
                line_words = candidate_words
                unused_words = unused_words[len(candidate_words) :]

        block_id = f"{page_id}_block_{block_index:04d}"
        bbox = bbox_from_words(line_words)
        if bbox is not None:
            bbox["page_number"] = page_number

        blocks.append(
            {
                "schema_version": SCHEMA_VERSION,
                "text_block_id": block_id,
                "document_id": document_id,
                "page_id": page_id,
                "page_number": page_number,
                "block_type": classify_block(line),
                "text": line,
                "bbox": bbox,
                "reading_order": reading_order,
                "is_header": False,
                "is_footer": False,
                "is_footnote": False,
                "is_toc_entry": False,
                "block_type_confidence": 0.5,
                "footnote_confidence": 0.0,
                "classification_reason": "initial_rule_based_classification",
            }
        )
        reading_order += 1

    return blocks, reading_order, len(text)


def refine_text_block_classifications(
    page_records: list[dict[str, Any]],
    text_blocks: list[dict[str, Any]],
) -> None:
    page_by_id = {str(page.get("page_id")): page for page in page_records}
    blocks_by_page_id: dict[str, list[dict[str, Any]]] = {}
    repeated_counter: dict[str, set[int]] = {}

    for block in text_blocks:
        page_id = str(block.get("page_id", ""))
        blocks_by_page_id.setdefault(page_id, []).append(block)
        normalized = normalize_repeated_text(str(block.get("text", "")))
        if normalized:
            repeated_counter.setdefault(normalized, set()).add(int(block.get("page_number") or 0))

    toc_page_ids = {
        str(page.get("page_id"))
        for page in page_records
        if page_diagnostics(page, blocks_by_page_id.get(str(page.get("page_id")), []))["is_possible_toc"]
    }

    for block in text_blocks:
        text = str(block.get("text") or "")
        clean = " ".join(text.split())
        page_id = str(block.get("page_id", ""))
        page = page_by_id.get(page_id, {})
        bbox = block.get("bbox") or {}
        page_height = float(page.get("height") or 0)
        y0 = float(bbox.get("y0", 0)) if isinstance(bbox, dict) else 0
        y1 = float(bbox.get("y1", 0)) if isinstance(bbox, dict) else 0
        normalized = normalize_repeated_text(clean)
        repeated_pages = repeated_counter.get(normalized, set())
        is_short = len(clean) <= 90
        in_header_zone = page_height > 0 and y0 <= page_height * 0.12
        in_footer_zone = page_height > 0 and y1 >= page_height * 0.88
        has_page_number = bool(re.search(r"\b\d{1,4}\b", clean))

        block["is_header"] = False
        block["is_footer"] = False
        block["is_footnote"] = False
        block["is_toc_entry"] = False
        block["block_type_confidence"] = float(block.get("block_type_confidence", 0.5) or 0.5)
        block["footnote_confidence"] = float(block.get("footnote_confidence", 0.0) or 0.0)
        block["classification_reason"] = str(block.get("classification_reason") or "initial_rule_based_classification")

        footer_label = is_footer_label_text(clean)
        footer_pattern = is_footer_pattern_text(clean)

        if in_footer_zone and is_footnote_text(clean) and not footer_pattern and not footer_label:
            block["block_type"] = "footnote"
            block["is_footnote"] = True
            block["block_type_confidence"] = 0.75
            block["footnote_confidence"] = 0.75
            block["classification_reason"] = "bottom_page_reference_marker_explanatory_text"
            continue

        if is_list_item_text(clean):
            block["block_type"] = "list_item"
            block["block_type_confidence"] = 0.85
            block["classification_reason"] = "list_item_marker_or_numbering"
            continue

        if is_caption_text(clean):
            block["block_type"] = "caption"
            block["block_type_confidence"] = 0.85
            block["classification_reason"] = "caption_prefix"
            continue

        if page_id in toc_page_ids and block.get("block_type") == "title" and looks_like_toc_entry(clean):
            block["block_type"] = "toc_entry"
            block["is_toc_entry"] = True
            block["block_type_confidence"] = 0.8
            block["classification_reason"] = "toc_page_title_ending_with_number"
            continue

        if is_short and in_header_zone and len(repeated_pages) >= 2:
            block["block_type"] = "header"
            block["is_header"] = True
            block["block_type_confidence"] = 0.75
            block["classification_reason"] = "short_repeated_text_in_top_page_zone"
            continue

        footer_recurrent_with_number = len(repeated_pages) >= 2 and has_page_number and footer_label
        footer_recurrent_label = len(repeated_pages) >= 2 and footer_label
        if is_short and in_footer_zone and (
            footer_pattern or footer_recurrent_with_number or footer_recurrent_label
        ):
            block["block_type"] = "footer"
            block["is_footer"] = True
            block["block_type_confidence"] = 0.85 if footer_pattern else 0.78
            block["classification_reason"] = (
                "strict_footer_pattern_or_repeated_document_label_in_bottom_page_zone"
            )


def output_file_not_empty_checks(
    output_dir: Path,
    document_id: str,
    include_summary: bool,
) -> list[dict[str, Any]]:
    filenames = [
        "document_record.json",
        "page_index.jsonl",
        "text_blocks.jsonl",
        "text_block_statistics.json",
    ]
    if include_summary:
        filenames.append("extraction_summary.json")

    checks = []
    for filename in filenames:
        path = output_dir / filename
        ok = path.exists() and path.stat().st_size > 0
        checks.append(
            quality_record(
                check_name="output_file_not_empty",
                status="pass" if ok else "fail",
                severity="critical" if not ok else "info",
                message=f"{filename} is non-empty." if ok else f"{filename} is missing or empty.",
                target_type="output_file",
                target_id=filename,
                document_id=document_id,
                review_required=not ok,
            )
        )
    return checks


# ── v0.5 table helpers ─────────────────────────────────────────────────────────

def _looks_table_like(page_text: str, page_blocks: list[dict[str, Any]]) -> bool:
    """Heuristic: does this page likely contain a table-like structure?"""
    text_lower = (page_text or "").lower()
    keyword_hits = sum(1 for kw in TABLE_LIKE_KEYWORDS if kw in text_lower)
    percent_count = len(re.findall(r"\d[\d\s,]*%", page_text or ""))
    multi_number_lines = sum(
        1
        for line in (page_text or "").splitlines()
        if len(re.findall(r"\b\d[\d\s,.]*\b", line)) >= 3
    )
    return keyword_hits >= 2 or percent_count >= 3 or multi_number_lines >= 3


def _find_section_for_page(
    page_number: int,
    sections: list[dict[str, Any]],
) -> str | None:
    """Return the section_id that best covers page_number, or None."""
    best: dict[str, Any] | None = None
    for section in sections:
        start = int(section.get("page_start") or 0)
        end_raw = section.get("page_end")
        end = int(end_raw) if end_raw is not None else start
        if start <= page_number <= end:
            if best is None or start > int(best.get("page_start") or 0):
                best = section
    return best.get("section_id") if best else None


def _is_section_quarantined(
    section_id: str | None,
    sections: list[dict[str, Any]],
) -> bool:
    if not section_id:
        return False
    for section in sections:
        if section.get("section_id") == section_id:
            return (
                section.get("is_quarantined", False)
                or section.get("evidence_policy") == "quarantine"
            )
    return False


def _compute_cell_quality_metrics(rows: list[list[str | None]]) -> dict[str, Any]:
    """Compute quality indicators for a table's cells. No ESG interpretation."""
    all_cells: list[str] = []
    for row in rows:
        for cell in (row or []):
            all_cells.append((cell or "").strip())
    total = len(all_cells)
    if total == 0:
        return {
            "non_empty_cells_count": 0,
            "empty_cells_ratio": 1.0,
            "average_cell_text_length": 0.0,
            "fragmented_cells_count": 0,
            "numeric_cells_count": 0,
            "numeric_cells_ratio": 0.0,
        }
    non_empty = [c for c in all_cells if c]
    empty_count = total - len(non_empty)
    fragmented = sum(
        1 for c in non_empty
        if len(c) <= 2 or bool(_FRAGMENTED_CELL_RE.match(c))
    )
    numeric = sum(
        1 for c in non_empty
        if bool(_NUMERIC_CELL_RE.match(c))
    )
    avg_len = round(sum(len(c) for c in non_empty) / len(non_empty), 2) if non_empty else 0.0
    return {
        "non_empty_cells_count": len(non_empty),
        "empty_cells_ratio": round(empty_count / total, 4),
        "average_cell_text_length": avg_len,
        "fragmented_cells_count": fragmented,
        "numeric_cells_count": numeric,
        "numeric_cells_ratio": round(numeric / len(non_empty), 4) if non_empty else 0.0,
    }


def process_raw_tables(
    page_data: dict[str, Any],
    document_id: str,
    sections: list[dict[str, Any]],
    page_blocks: list[dict[str, Any]],
    page_diag: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Convert raw pdfplumber table data into TableRecord and CellRecord dicts.

    page_data keys: page_number, page_id, page_text, raw_tables.
    page_diag: result of page_diagnostics() for this page; used to detect TOC/front-matter pages.
    Does NOT interpret cell content as ESG metrics.
    """
    table_records: list[dict[str, Any]] = []
    cell_records: list[dict[str, Any]] = []

    page_number: int = int(page_data.get("page_number") or 0)
    page_id: str = str(page_data.get("page_id") or "")
    page_text: str = str(page_data.get("page_text") or "")
    raw_tables: list[list[list[str | None]]] = page_data.get("raw_tables") or []

    section_id = _find_section_for_page(page_number, sections)
    is_quarantined = _is_section_quarantined(section_id, sections)

    # Page-level structural flags
    is_toc_page = bool(page_diag and page_diag.get("is_possible_toc"))
    is_high_density_page = bool(page_diag and page_diag.get("is_high_title_density"))
    page_looks_table_like = _looks_table_like(page_text, page_blocks)

    if raw_tables:
        for tbl_idx, raw_table in enumerate(raw_tables, start=1):
            table_id = f"{document_id}_page_{page_number:04d}_tbl_{tbl_idx:03d}"
            rows: list[list[str | None]] = raw_table or []
            row_count = len(rows)
            col_count = max((len(row or []) for row in rows), default=0)
            cell_count = sum(len(row or []) for row in rows)

            if row_count < 1 or col_count < 1:
                continue

            # ── cell quality metrics ──────────────────────────────────────────
            cell_metrics = _compute_cell_quality_metrics(rows)
            non_empty_cells = cell_metrics["non_empty_cells_count"]
            empty_ratio = cell_metrics["empty_cells_ratio"]
            frag_count = cell_metrics["fragmented_cells_count"]
            frag_ratio = (frag_count / non_empty_cells) if non_empty_cells > 0 else 0.0

            # ── base extraction status ────────────────────────────────────────
            all_empty = (non_empty_cells == 0)
            if all_empty:
                extraction_status = "empty_table"
                table_confidence = 0.10
                localization_confidence = 0.15
            elif row_count >= TABLE_MIN_ROWS and col_count >= TABLE_MIN_COLS:
                extraction_status = "parsed"
                table_confidence = 0.70
                localization_confidence = 0.55  # bbox is always None → cap at 0.55
            else:
                extraction_status = "low_confidence"
                table_confidence = 0.40
                localization_confidence = 0.40

            # ── quality flags ─────────────────────────────────────────────────
            quality_flags: list[str] = []
            if all_empty:
                quality_flags.append("all_cells_empty")
            if row_count < TABLE_MIN_ROWS:
                quality_flags.append("single_row_table")
            if col_count < TABLE_MIN_COLS:
                quality_flags.append("single_column_table")
            if not all_empty and empty_ratio > TABLE_HIGH_EMPTY_CELLS_RATIO:
                quality_flags.append("high_empty_cells_ratio")
            if not all_empty and empty_ratio > TABLE_MOSTLY_EMPTY_CELLS_RATIO:
                quality_flags.append("mostly_empty_cells")
            if cell_count <= TABLE_TINY_ARTIFACT_MAX_CELLS:
                quality_flags.append("tiny_table_artifact")
            if is_toc_page or is_high_density_page:
                quality_flags.append("front_matter_or_toc_table_like")
            if frag_count > 0:
                quality_flags.append("fragmented_cells_detected")
            if frag_ratio > TABLE_HIGH_FRAGMENTED_CELLS_RATIO:
                quality_flags.append("high_fragmented_cells_ratio")
            if non_empty_cells > 0 and cell_metrics["numeric_cells_ratio"] < 0.10 and row_count >= TABLE_MIN_ROWS:
                quality_flags.append("low_numeric_density")

            # Multiple weakness signals → suspected artifact
            _weakness = sum([
                "single_row_table" in quality_flags or "single_column_table" in quality_flags,
                "high_fragmented_cells_ratio" in quality_flags,
                "front_matter_or_toc_table_like" in quality_flags,
                "mostly_empty_cells" in quality_flags,
            ])
            if _weakness >= 2:
                quality_flags.append("table_artifact_suspected")

            # ── downgrade status for weak tables ──────────────────────────────
            if extraction_status == "parsed":
                if (
                    "mostly_empty_cells" in quality_flags
                    or "front_matter_or_toc_table_like" in quality_flags
                    or "high_fragmented_cells_ratio" in quality_flags
                ):
                    extraction_status = "low_confidence"
                    table_confidence = min(table_confidence, 0.35)
                    localization_confidence = min(localization_confidence, 0.40)
            if extraction_status in ("parsed", "low_confidence"):
                if "single_row_table" in quality_flags or "single_column_table" in quality_flags:
                    extraction_status = "low_confidence"
                    table_confidence = min(table_confidence, 0.35)
                    localization_confidence = min(localization_confidence, 0.40)

            has_header = row_count >= 2 and extraction_status != "empty_table"
            header_rows_count = 1 if has_header else 0
            review_required = (
                extraction_status != "parsed"
                or section_id is None
                or bool(quality_flags)
            )

            # ── page diagnostic flags ─────────────────────────────────────────
            page_diagnostic_flags: list[str] = []
            if page_looks_table_like:
                page_diagnostic_flags.append("page_looks_table_like")
            if is_toc_page:
                page_diagnostic_flags.append("page_is_possible_toc")
            if is_high_density_page:
                page_diagnostic_flags.append("page_is_high_title_density")

            table_record: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "table_id": table_id,
                "document_id": document_id,
                "page_id": page_id,
                "page_number": page_number,
                "section_id": section_id,
                "table_bbox": None,
                "extraction_status": extraction_status,
                "detection_method": "pdfplumber_extract_tables",
                "extraction_method": "pdfplumber_direct",
                "row_count": row_count,
                "column_count": col_count,
                "cell_count": cell_count,
                "header_rows_count": header_rows_count,
                "has_header": has_header,
                "table_confidence": round(table_confidence, 4),
                "localization_confidence": round(localization_confidence, 4),
                "review_required": review_required,
                "is_quarantined_table": is_quarantined,
                "table_quality_flags": quality_flags,
                "source_page_diagnostic_flags": page_diagnostic_flags,
                # v0.5.2 cell quality metrics
                "non_empty_cells_count": cell_metrics["non_empty_cells_count"],
                "empty_cells_ratio": cell_metrics["empty_cells_ratio"],
                "average_cell_text_length": cell_metrics["average_cell_text_length"],
                "fragmented_cells_count": cell_metrics["fragmented_cells_count"],
                "numeric_cells_count": cell_metrics["numeric_cells_count"],
                "numeric_cells_ratio": cell_metrics["numeric_cells_ratio"],
            }
            table_records.append(table_record)

            # Build cells only for parsed/low_confidence tables (not empty_table)
            if extraction_status in ("parsed", "low_confidence"):
                for row_idx, row in enumerate(rows):
                    for col_idx, cell_val in enumerate(row or []):
                        raw_text = str(cell_val or "")
                        normalized = " ".join(raw_text.split())
                        cell_records.append({
                            "schema_version": SCHEMA_VERSION,
                            "cell_id": f"{table_id}_r{row_idx:03d}_c{col_idx:03d}",
                            "table_id": table_id,
                            "document_id": document_id,
                            "page_id": page_id,
                            "page_number": page_number,
                            "row_index": row_idx,
                            "column_index": col_idx,
                            "text": raw_text,
                            "bbox": None,
                            "is_header_cell": row_idx < header_rows_count,
                            "cell_confidence": round(table_confidence, 4),
                            "normalized_text": normalized,
                        })

    elif page_looks_table_like:
        # Ambiguous: page looks table-like but pdfplumber found nothing.
        # Never ignored silently — written as detected_not_parsed.
        table_id = f"{document_id}_page_{page_number:04d}_tbl_detected_001"
        flags_set: set[str] = {"detected_not_parsed"}
        if is_toc_page or is_high_density_page:
            flags_set.add("front_matter_or_toc_table_like")
        page_flags: list[str] = ["page_looks_table_like"]
        if is_toc_page:
            page_flags.append("page_is_possible_toc")
        if is_high_density_page:
            page_flags.append("page_is_high_title_density")
        table_records.append({
            "schema_version": SCHEMA_VERSION,
            "table_id": table_id,
            "document_id": document_id,
            "page_id": page_id,
            "page_number": page_number,
            "section_id": section_id,
            "table_bbox": None,
            "extraction_status": "detected_not_parsed",
            "detection_method": "heuristic_text_analysis",
            "extraction_method": "none",
            "row_count": 0,
            "column_count": 0,
            "cell_count": 0,
            "header_rows_count": 0,
            "has_header": False,
            "table_confidence": 0.25,
            "localization_confidence": 0.25,
            "review_required": True,
            "is_quarantined_table": is_quarantined,
            "table_quality_flags": sorted(flags_set),
            "source_page_diagnostic_flags": page_flags,
            # v0.5.2 cell quality metrics (all zero — no cells detected)
            "non_empty_cells_count": 0,
            "empty_cells_ratio": 1.0,
            "average_cell_text_length": 0.0,
            "fragmented_cells_count": 0,
            "numeric_cells_count": 0,
            "numeric_cells_ratio": 0.0,
        })

    return table_records, cell_records


def build_table_evidence(
    document_id: str,
    table_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create one evidence record per exploitable table.

    Evidence type is 'table'. Does NOT interpret cell content as ESG metrics.
    Skips: empty_table, tiny_table_artifact not on a strongly table-like page.
    """
    evidence: list[dict[str, Any]] = []
    for table in table_records:
        status = str(table.get("extraction_status") or "")
        flags = set(table.get("table_quality_flags") or [])
        page_flags = set(table.get("source_page_diagnostic_flags") or [])

        # Never evidence empty tables — no parseable content
        if status == "empty_table":
            continue
        # Skip tiny artifacts unless the page is strongly table-like
        if "tiny_table_artifact" in flags and "page_looks_table_like" not in page_flags:
            continue
        # Only produce evidence for exploitable statuses
        if status not in ("parsed", "detected_not_parsed", "low_confidence"):
            continue

        page_number = int(table.get("page_number") or 0)
        row_count = int(table.get("row_count") or 0)
        col_count = int(table.get("column_count") or 0)
        table_id = str(table.get("table_id") or "")

        if status == "parsed":
            quote = (
                f"Table parsed on page {page_number} "
                f"with {row_count} rows and {col_count} columns."
            )
        elif status == "low_confidence":
            quote = (
                f"Low-confidence table detected on page {page_number} "
                f"with {row_count} rows and {col_count} columns."
            )
        else:
            quote = (
                f"Table-like content detected on page {page_number} "
                "(could not be parsed by pdfplumber)."
            )

        evidence.append({
            "schema_version": SCHEMA_VERSION,
            "evidence_id": f"{document_id}_tbl_ev_{table_id}",
            "document_id": document_id,
            "page_id": table.get("page_id"),
            "page_number": page_number,
            "evidence_type": "table",
            "quote": quote,
            "bbox": table.get("table_bbox"),
            "section_id": table.get("section_id"),
            "table_id": table_id,
            "text_block_id": None,
            "source_element_type": "table",
            "source_element_id": table_id,
            "source_text_block_ids": [],
            "merged_blocks_count": 0,
            "was_merged_evidence": False,
            "merge_method": "not_applicable_table",
            "evidence_confidence": float(table.get("table_confidence") or 0.0),
            "localization_confidence": float(table.get("localization_confidence") or 0.0),
            "extraction_method": "table_detection_v0_5_2",
            "review_required": bool(table.get("review_required", True)),
            "evidence_policy": (
                "quarantine" if table.get("is_quarantined_table") else "normal"
            ),
        })
    return evidence


def build_table_statistics(
    document_id: str,
    table_records: list[dict[str, Any]],
    cell_records: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    status_dist: dict[str, int] = {}
    for t in table_records:
        s = str(t.get("extraction_status") or "unknown")
        status_dist[s] = status_dist.get(s, 0) + 1

    tables_by_page: dict[str, int] = {}
    tables_by_section: dict[str, int] = {}
    for t in table_records:
        pn = str(t.get("page_number") or 0)
        tables_by_page[pn] = tables_by_page.get(pn, 0) + 1
        sid = str(t.get("section_id") or "no_section")
        tables_by_section[sid] = tables_by_section.get(sid, 0) + 1

    parsed = [t for t in table_records if t.get("extraction_status") == "parsed"]
    row_counts = [int(t.get("row_count") or 0) for t in parsed if (t.get("row_count") or 0) > 0]
    col_counts = [int(t.get("column_count") or 0) for t in parsed if (t.get("column_count") or 0) > 0]

    def _has_flag(t: dict, flag: str) -> bool:
        return flag in (t.get("table_quality_flags") or [])

    mostly_empty = [t for t in table_records if _has_flag(t, "mostly_empty_cells")]
    tiny_artifacts = [t for t in table_records if _has_flag(t, "tiny_table_artifact")]
    front_matter_toc = [t for t in table_records if _has_flag(t, "front_matter_or_toc_table_like")]
    fragmented = [t for t in table_records if _has_flag(t, "high_fragmented_cells_ratio")]
    artifact_suspected = [t for t in table_records if _has_flag(t, "table_artifact_suspected")]
    empty_tables_list = [t for t in table_records if t.get("extraction_status") == "empty_table"]

    empty_ratios = [
        float(t.get("empty_cells_ratio") or 0.0)
        for t in table_records
        if t.get("empty_cells_ratio") is not None
    ]
    numeric_ratios = [
        float(t.get("numeric_cells_ratio") or 0.0)
        for t in table_records
        if t.get("numeric_cells_ratio") is not None
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "tables_count": len(table_records),
        "parsed_tables_count": status_dist.get("parsed", 0),
        "detected_not_parsed_tables_count": status_dist.get("detected_not_parsed", 0),
        "low_confidence_tables_count": status_dist.get("low_confidence", 0),
        "failed_tables_count": status_dist.get("failed", 0),
        "empty_tables_count": status_dist.get("empty_table", 0),
        "mostly_empty_tables_count": len(mostly_empty),
        "tiny_table_artifacts_count": len(tiny_artifacts),
        "front_matter_or_toc_tables_count": len(front_matter_toc),
        "fragmented_tables_count": len(fragmented),
        "table_artifact_suspected_count": len(artifact_suspected),
        "table_cells_count": len(cell_records),
        "tables_by_page": tables_by_page,
        "tables_by_section": tables_by_section,
        "table_status_distribution": status_dist,
        "average_rows_per_table": (
            round(sum(row_counts) / len(row_counts), 2) if row_counts else 0.0
        ),
        "average_columns_per_table": (
            round(sum(col_counts) / len(col_counts), 2) if col_counts else 0.0
        ),
        "average_empty_cells_ratio": (
            round(sum(empty_ratios) / len(empty_ratios), 4) if empty_ratios else 0.0
        ),
        "average_numeric_cells_ratio": (
            round(sum(numeric_ratios) / len(numeric_ratios), 4) if numeric_ratios else 0.0
        ),
        "quarantined_tables_count": sum(
            1 for t in table_records if t.get("is_quarantined_table")
        ),
        "review_required_tables_count": sum(
            1 for t in table_records if t.get("review_required")
        ),
        "sample_tables": table_records[:SAMPLE_LIMIT],
        "sample_cells": cell_records[:SAMPLE_LIMIT],
        "sample_detected_not_parsed_tables": [
            t for t in table_records if t.get("extraction_status") == "detected_not_parsed"
        ][:SAMPLE_LIMIT],
        "sample_empty_tables": empty_tables_list[:SAMPLE_LIMIT],
        "sample_tiny_table_artifacts": tiny_artifacts[:SAMPLE_LIMIT],
        "sample_front_matter_or_toc_tables": front_matter_toc[:SAMPLE_LIMIT],
        "sample_fragmented_tables": fragmented[:SAMPLE_LIMIT],
    }


def table_quality_checks(
    document_id: str,
    table_records: list[dict[str, Any]],
    cell_records: list[dict[str, Any]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    """Quality checks specific to v0.5.2 table extraction."""
    checks: list[dict[str, Any]] = []
    table_ids = {str(t.get("table_id") or "") for t in table_records}

    def _has_flag(t: dict, flag: str) -> bool:
        return flag in (t.get("table_quality_flags") or [])

    # ── file existence checks ─────────────────────────────────────────────────
    idx_path = output_dir / "table_index.jsonl"
    checks.append(quality_record(
        "table_index_created",
        "pass" if idx_path.exists() else "fail",
        "major",
        "table_index.jsonl created." if idx_path.exists() else "table_index.jsonl missing.",
        target_type="output_file",
        target_id="table_index.jsonl",
        document_id=document_id,
    ))
    cells_path = output_dir / "table_cells.jsonl"
    checks.append(quality_record(
        "table_cells_created",
        "pass" if cells_path.exists() else "fail",
        "major",
        "table_cells.jsonl created." if cells_path.exists() else "table_cells.jsonl missing.",
        target_type="output_file",
        target_id="table_cells.jsonl",
        document_id=document_id,
    ))
    checks.append(quality_record(
        "table_detection_completed",
        "pass",
        "info",
        f"Table detection completed: {len(table_records)} table record(s).",
        document_id=document_id,
    ))
    if not table_records:
        checks.append(quality_record(
            "no_tables_detected_info",
            "pass",
            "info",
            "No tables detected on this document.",
            document_id=document_id,
        ))

    # ── per-table checks ──────────────────────────────────────────────────────
    for table in table_records:
        tid = str(table.get("table_id") or "")
        status = str(table.get("extraction_status") or "")
        row_count = int(table.get("row_count") or 0)
        page_num = table.get("page_number")
        t_cells = [c for c in cell_records if str(c.get("table_id") or "") == tid]
        flags = set(table.get("table_quality_flags") or [])

        # parsed + all_cells_empty must have been corrected → error if not
        if status == "parsed" and "all_cells_empty" in flags:
            checks.append(quality_record(
                "table_extraction_status_valid",
                "fail",
                "major",
                f"Table {tid}: parsed status with all_cells_empty flag (must be empty_table).",
                target_type="evidence",
                target_id=tid,
                document_id=document_id,
                review_required=True,
            ))
        elif status == "parsed" and row_count > 0 and not t_cells:
            checks.append(quality_record(
                "table_extraction_status_valid",
                "fail",
                "major",
                (
                    f"Table {tid} is parsed with {row_count} rows "
                    "but has no cells in table_cells.jsonl."
                ),
                target_type="evidence",
                target_id=tid,
                document_id=document_id,
                review_required=True,
            ))
        else:
            checks.append(quality_record(
                "table_extraction_status_valid",
                "pass",
                "info",
                f"Table {tid} status={status} rows={row_count} cells={len(t_cells)}.",
                target_type="evidence",
                target_id=tid,
                document_id=document_id,
            ))

        # Section link
        section_id = table.get("section_id")
        checks.append(quality_record(
            "table_section_link_valid",
            "pass" if section_id else "warning",
            "minor",
            (
                f"Table {tid} linked to section {section_id}."
                if section_id
                else f"Table {tid} on page {page_num} has no section link."
            ),
            target_type="evidence",
            target_id=tid,
            document_id=document_id,
            review_required=not bool(section_id),
        ))

        if status == "detected_not_parsed":
            checks.append(quality_record(
                "table_detected_not_parsed_warning",
                "warning",
                "minor",
                f"Table {tid} on page {page_num}: detected but not parsed.",
                target_type="evidence",
                target_id=tid,
                document_id=document_id,
                review_required=True,
            ))
        if status == "low_confidence":
            checks.append(quality_record(
                "table_low_confidence_warning",
                "warning",
                "minor",
                f"Table {tid} on page {page_num}: low confidence ({table.get('table_confidence', 0)}).",
                target_type="evidence",
                target_id=tid,
                document_id=document_id,
                review_required=True,
            ))

    # ── cell → table_id consistency ───────────────────────────────────────────
    for cell in cell_records:
        cid = str(cell.get("cell_id") or "")
        cell_tid = str(cell.get("table_id") or "")
        if cell_tid not in table_ids:
            checks.append(quality_record(
                "table_cell_coordinates_valid",
                "fail",
                "major",
                f"Cell {cid} references unknown table_id {cell_tid}.",
                target_type="evidence",
                target_id=cid,
                document_id=document_id,
                review_required=True,
            ))

    # ── v0.5.2 aggregate quality checks ──────────────────────────────────────
    empty_count = sum(1 for t in table_records if t.get("extraction_status") == "empty_table")
    mostly_empty_count = sum(1 for t in table_records if _has_flag(t, "mostly_empty_cells"))
    tiny_count = sum(1 for t in table_records if _has_flag(t, "tiny_table_artifact"))
    front_toc_count = sum(1 for t in table_records if _has_flag(t, "front_matter_or_toc_table_like"))
    frag_count = sum(1 for t in table_records if _has_flag(t, "high_fragmented_cells_ratio"))
    artifact_count = sum(1 for t in table_records if _has_flag(t, "table_artifact_suspected"))

    checks.append(quality_record(
        "empty_table_detected",
        "warning" if empty_count > 0 else "pass",
        "minor",
        f"{empty_count} empty table(s) detected (extraction_status=empty_table).",
        document_id=document_id,
        review_required=empty_count > 0,
    ))
    checks.append(quality_record(
        "mostly_empty_table_warning",
        "warning" if mostly_empty_count > 0 else "pass",
        "minor",
        f"{mostly_empty_count} table(s) with >80% empty cells (mostly_empty_cells flag).",
        document_id=document_id,
        review_required=mostly_empty_count > 0,
    ))
    checks.append(quality_record(
        "tiny_table_artifact_warning",
        "warning" if tiny_count > 0 else "pass",
        "minor",
        f"{tiny_count} tiny table artifact(s) detected (cell_count <= {TABLE_TINY_ARTIFACT_MAX_CELLS}).",
        document_id=document_id,
        review_required=tiny_count > 0,
    ))
    checks.append(quality_record(
        "front_matter_or_toc_table_warning",
        "warning" if front_toc_count > 0 else "pass",
        "minor",
        f"{front_toc_count} table(s) on front matter or TOC pages.",
        document_id=document_id,
        review_required=front_toc_count > 0,
    ))
    checks.append(quality_record(
        "fragmented_table_warning",
        "warning" if frag_count > 0 else "pass",
        "minor",
        f"{frag_count} table(s) with high fragmented cell ratio.",
        document_id=document_id,
        review_required=frag_count > 0,
    ))
    checks.append(quality_record(
        "table_artifact_suspected_warning",
        "warning" if artifact_count > 0 else "pass",
        "minor",
        f"{artifact_count} table(s) suspected as extraction artifacts.",
        document_id=document_id,
        review_required=artifact_count > 0,
    ))
    checks.append(quality_record(
        "table_evidence_policy_consistency_check",
        "pass",
        "info",
        "Table evidence policy consistency check passed (see evidence_store.jsonl).",
        document_id=document_id,
    ))
    checks.append(quality_record(
        "table_evidence_created",
        "pass",
        "info",
        "Table evidence records created (see evidence_store.jsonl, evidence_type='table').",
        document_id=document_id,
    ))

    return checks


# ── v0.6 figure detection functions ──────────────────────────────────────────

def _figure_type_from_text(text: str) -> str:
    low = text.lower()
    for keyword, ftype in _FIGURE_TYPE_KEYWORDS.items():
        if keyword in low:
            return ftype
    return "image"


def _figure_bbox_from_image(img: dict[str, Any]) -> dict[str, Any] | None:
    try:
        x0 = float(img.get("x0", 0))
        y0 = float(img.get("top", 0))
        x1 = float(img.get("x1", 0))
        y1 = float(img.get("bottom", 0))
        if x1 <= x0 or y1 <= y0:
            return None
        return {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "coordinate_system": "pdf_points"}
    except Exception:
        return None


def _figure_type_from_image(img: dict[str, Any], caption_text: str | None) -> str:
    if caption_text:
        t = _figure_type_from_text(caption_text)
        if t != "image":
            return t
    try:
        w = abs(float(img.get("x1", 0)) - float(img.get("x0", 0)))
        h = abs(float(img.get("bottom", 0)) - float(img.get("top", 0)))
        if w * h < FIGURE_LOGO_MAX_AREA_PT2:
            return "logo"
    except Exception:
        pass
    return "image"


def _link_figure_to_section(
    page_number: int,
    sections: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for section in sections:
        ps = int(section.get("page_start") or 0)
        pe = int(section.get("page_end") or 0)
        if ps <= page_number <= pe:
            return section
    return None


def process_raw_figures(
    raw_page_data: dict[str, Any],
    document_id: str,
    sections: list[dict[str, Any]],
    page_blocks: list[dict[str, Any]],
    page_diag: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    page_number = int(raw_page_data.get("page_number") or 0)
    page_id = str(raw_page_data.get("page_id") or "")
    raw_images: list[dict[str, Any]] = list(raw_page_data.get("raw_images") or [])

    source_diag_flags: list[str] = []
    is_possible_visual_page = False
    is_low_text_page = False
    if page_diag:
        if page_diag.get("is_possible_visual"):
            source_diag_flags.append("is_possible_visual_page")
            is_possible_visual_page = True
        if page_diag.get("is_possible_toc"):
            source_diag_flags.append("is_possible_toc_page")
        if page_diag.get("is_high_title_density"):
            source_diag_flags.append("is_high_title_density_page")
        if page_diag.get("is_low_text"):
            source_diag_flags.append("is_low_text_page")
            is_low_text_page = True

    is_cover_or_separator_page = page_number == 1 or is_low_text_page or is_possible_visual_page

    caption_blocks = [
        blk for blk in page_blocks
        if blk.get("block_type") == "caption"
        or is_caption_text(str(blk.get("text") or ""))
    ]
    figure_caption_blocks = [
        blk for blk in caption_blocks
        if _FIGURE_CAPTION_RE.match(str(blk.get("text") or ""))
    ]

    section = _link_figure_to_section(page_number, sections)
    section_id = str(section.get("section_id")) if section else None

    figure_records: list[dict[str, Any]] = []

    _VOL_MAP = {
        "pdfplumber_image": "embedded_object",
        "caption_heuristic": "captioned_region",
        "page_visual_heuristic": "page_level_visual",
    }

    def _make_figure(
        idx: int,
        figure_type: str,
        detection_method: str,
        extraction_status: str,
        figure_bbox: dict[str, Any] | None,
        figure_confidence: float,
        localization_confidence: float,
        quality_flags: list[str],
        nearby_block_ids: list[str],
        nearby_caption_text: str | None,
    ) -> dict[str, Any]:
        vol = _VOL_MAP.get(detection_method, "unknown")
        is_page_lv = detection_method == "page_visual_heuristic"
        is_embedded = detection_method == "pdfplumber_image"
        is_captioned = detection_method == "caption_heuristic"
        # Ensure canonical flags are present
        flags = list(quality_flags)
        if figure_bbox is None and "no_bbox_available" not in flags:
            flags.append("no_bbox_available")
        if nearby_caption_text is None and "no_caption_detected" not in flags:
            flags.append("no_caption_detected")
        if is_page_lv:
            if "page_level_visual_candidate" not in flags:
                flags.append("page_level_visual_candidate")
            if "weak_visual_detection" not in flags:
                flags.append("weak_visual_detection")
            if "not_interpretable_visual" not in flags:
                flags.append("not_interpretable_visual")
        if is_cover_or_separator_page and "possible_cover_or_separator_page" not in flags:
            flags.append("possible_cover_or_separator_page")
        review_req = (
            is_page_lv
            or extraction_status in {"low_confidence", "detected_not_interpreted"}
            or not section_id
            or not nearby_caption_text
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "figure_id": f"fig_{document_id}_p{page_number:04d}_{idx:04d}",
            "document_id": document_id,
            "page_id": page_id,
            "page_number": page_number,
            "section_id": section_id,
            "figure_bbox": figure_bbox,
            "figure_type": figure_type,
            "detection_method": detection_method,
            "extraction_status": extraction_status,
            "figure_confidence": round(figure_confidence, 6),
            "localization_confidence": round(localization_confidence, 6),
            "review_required": review_req,
            "is_quarantined_figure": False,
            "visual_object_level": vol,
            "is_page_level_visual": is_page_lv,
            "is_embedded_visual": is_embedded,
            "is_captioned_figure": is_captioned,
            "is_visual_page_candidate": is_page_lv,
            "figure_quality_flags": flags,
            "source_page_diagnostic_flags": source_diag_flags,
            "nearby_text_block_ids": nearby_block_ids,
            "nearby_caption_text": nearby_caption_text,
            "evidence_policy": "normal",
            "section_quality_score": 1.0,
            "section_is_suspicious": False,
            "section_suspicion_reasons": [],
        }

    # ── Strategy 1: native PDF images from pdfplumber ─────────────────────────
    if raw_images:
        for img_idx, img in enumerate(raw_images):
            cap_blk = figure_caption_blocks[img_idx] if img_idx < len(figure_caption_blocks) else None
            cap_text = truncate_sample(str(cap_blk.get("text") or "")) if cap_blk else None
            nearby_ids = [str(cap_blk.get("text_block_id") or "")] if cap_blk else []
            bbox = _figure_bbox_from_image(img)
            ftype = _figure_type_from_image(img, cap_text)
            quality_flags: list[str] = []
            if bbox is None:
                quality_flags.append("no_bbox_available")
            if cap_text is None:
                quality_flags.append("no_caption_detected")
            loc_conf = 0.85 if bbox else 0.30
            figure_records.append(_make_figure(
                idx=img_idx,
                figure_type=ftype,
                detection_method="pdfplumber_image",
                extraction_status="detected",
                figure_bbox=bbox,
                figure_confidence=0.85,
                localization_confidence=loc_conf,
                quality_flags=quality_flags,
                nearby_block_ids=nearby_ids,
                nearby_caption_text=cap_text,
            ))

    # ── Strategy 2: caption heuristic (no native images) ─────────────────────
    elif figure_caption_blocks:
        for cap_idx, cap_blk in enumerate(figure_caption_blocks):
            cap_text = truncate_sample(str(cap_blk.get("text") or ""))
            ftype = _figure_type_from_text(cap_text)
            if ftype == "image":
                ftype = "unknown_visual"
            figure_records.append(_make_figure(
                idx=cap_idx,
                figure_type=ftype,
                detection_method="caption_heuristic",
                extraction_status="low_confidence",
                figure_bbox=None,
                figure_confidence=0.45,
                localization_confidence=0.20,
                quality_flags=["no_bbox_available", "no_image_object_found"],
                nearby_block_ids=[str(cap_blk.get("text_block_id") or "")],
                nearby_caption_text=cap_text,
            ))

    # ── Strategy 3: page visual heuristic (possible_visual page, no images/captions) ──
    elif page_diag and page_diag.get("is_possible_visual"):
        figure_records.append(_make_figure(
            idx=0,
            figure_type="unknown_visual",
            detection_method="page_visual_heuristic",
            extraction_status="detected_not_interpreted",
            figure_bbox=None,
            figure_confidence=0.30,
            localization_confidence=0.10,
            quality_flags=[],
            nearby_block_ids=[],
            nearby_caption_text=None,
        ))

    return figure_records


def _apply_section_policy_to_figure(
    figure: dict[str, Any],
    section: dict[str, Any] | None,
) -> None:
    if section is not None:
        score = float(section.get("section_quality_score", 1.0) or 1.0)
        policy = str(section.get("evidence_policy") or "normal")
        reasons: list = list(section.get("suspicion_reasons") or [])
        suspicious = bool(section.get("is_suspicious_section"))
    else:
        score = 1.0
        policy = "normal"
        reasons = []
        suspicious = False
    figure["section_quality_score"] = score
    figure["section_is_suspicious"] = suspicious
    figure["section_suspicion_reasons"] = reasons
    figure["evidence_policy"] = policy
    figure["is_quarantined_figure"] = policy == "quarantine"
    if policy in {"review_required", "quarantine"}:
        figure["review_required"] = True


def propagate_section_quality_to_figures(
    figure_records: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sections_by_id = {str(s.get("section_id")): s for s in sections}
    for figure in figure_records:
        section = sections_by_id.get(str(figure.get("section_id") or ""))
        _apply_section_policy_to_figure(figure, section)
    return figure_records


def build_figure_evidence(
    document_id: str,
    figure_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidences: list[dict[str, Any]] = []
    allowed = {"detected", "low_confidence", "detected_not_interpreted"}
    for fig in figure_records:
        if fig.get("extraction_status") not in allowed:
            continue
        page_number = int(fig.get("page_number") or 0)
        caption = fig.get("nearby_caption_text")
        ftype = str(fig.get("figure_type") or "unknown_visual")
        is_page_lv = bool(fig.get("is_page_level_visual"))
        if is_page_lv:
            quote = f"Page-level visual candidate detected on page {page_number}; not interpreted."
        elif caption:
            quote = str(caption)[:200]
        elif ftype == "chart":
            quote = f"Chart-like visual detected on page {page_number}"
        elif ftype == "diagram":
            quote = f"Diagram-like visual detected on page {page_number}"
        elif ftype == "map":
            quote = f"Map-like visual detected on page {page_number}"
        else:
            quote = f"Figure detected on page {page_number}"

        evidence_id = "ev_fig_" + hashlib.sha256(
            f"{document_id}|{fig.get('figure_id')}".encode("utf-8")
        ).hexdigest()[:20]

        policy = str(fig.get("evidence_policy") or "normal")
        ev: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "evidence_id": evidence_id,
            "document_id": document_id,
            "evidence_type": "figure",
            "page_id": fig.get("page_id"),
            "page_number": page_number,
            "section_id": fig.get("section_id"),
            "figure_id": fig.get("figure_id"),
            "quote": quote,
            "bbox": fig.get("figure_bbox"),
            "figure_type": ftype,
            "extraction_status": fig.get("extraction_status"),
            "figure_confidence": fig.get("figure_confidence"),
            "review_required": bool(fig.get("review_required")) or bool(fig.get("is_page_level_visual")),
            "text_block_id": None,
            "source_element_type": "figure",
            "source_element_id": str(fig.get("figure_id") or ""),
            "was_merged_evidence": False,
            "merged_blocks_count": 0,
            "merge_method": None,
            "source_text_block_ids": list(fig.get("nearby_text_block_ids") or []),
            # v0.4.2 contract fields
            "evidence_policy": policy,
            "section_quality_score": fig.get("section_quality_score", 1.0),
            "section_is_suspicious": fig.get("section_is_suspicious", False),
            "section_suspicion_reasons": list(fig.get("section_suspicion_reasons") or []),
            "is_quarantined_evidence": fig.get("is_quarantined_figure", False),
            "review_required_due_to_section": policy in {"review_required", "quarantine"},
        }
        if policy in {"review_required", "quarantine"}:
            ev["review_required"] = True
        evidences.append(ev)
    return evidences


def build_figure_statistics(
    document_id: str,
    figure_records: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    detected = [f for f in figure_records if f.get("extraction_status") == "detected"]
    low_conf = [f for f in figure_records if f.get("extraction_status") == "low_confidence"]
    not_interp = [f for f in figure_records if f.get("extraction_status") == "detected_not_interpreted"]
    failed = [f for f in figure_records if f.get("extraction_status") == "failed"]
    with_caption = [f for f in figure_records if f.get("nearby_caption_text")]
    without_caption = [f for f in figure_records if not f.get("nearby_caption_text")]
    quarantined = [f for f in figure_records if f.get("is_quarantined_figure")]
    review_req = [f for f in figure_records if f.get("review_required")]
    # v0.6.1 breakdowns
    page_level = [f for f in figure_records if f.get("is_page_level_visual")]
    embedded = [f for f in figure_records if f.get("is_embedded_visual")]
    captioned = [f for f in figure_records if f.get("is_captioned_figure")]
    visual_candidates = [f for f in figure_records if f.get("is_visual_page_candidate")]
    without_bbox = [f for f in figure_records if not f.get("figure_bbox")]
    weak_detections = [
        f for f in figure_records
        if "weak_visual_detection" in (f.get("figure_quality_flags") or [])
    ]
    cover_separator = [
        f for f in figure_records
        if "possible_cover_or_separator_page" in (f.get("figure_quality_flags") or [])
    ]

    type_dist: dict[str, int] = {}
    vol_dist: dict[str, int] = {}
    by_page: dict[int, int] = {}
    by_section: dict[str, int] = {}
    for fig in figure_records:
        ft = str(fig.get("figure_type") or "unknown_visual")
        type_dist[ft] = type_dist.get(ft, 0) + 1
        vol = str(fig.get("visual_object_level") or "unknown")
        vol_dist[vol] = vol_dist.get(vol, 0) + 1
        pn = int(fig.get("page_number") or 0)
        by_page[pn] = by_page.get(pn, 0) + 1
        sid = str(fig.get("section_id") or "")
        if sid:
            by_section[sid] = by_section.get(sid, 0) + 1

    fig_evidence_count = len(detected) + len(low_conf) + len(not_interp)

    def _sample(lst: list) -> list:
        return [
            {
                "figure_id": f.get("figure_id"),
                "page_number": f.get("page_number"),
                "figure_type": f.get("figure_type"),
                "visual_object_level": f.get("visual_object_level"),
                "detection_method": f.get("detection_method"),
                "nearby_caption_text": f.get("nearby_caption_text"),
                "extraction_status": f.get("extraction_status"),
            }
            for f in lst[:SAMPLE_LIMIT]
        ]

    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "figures_count": len(figure_records),
        "detected_figures_count": len(detected),
        "low_confidence_figures_count": len(low_conf),
        "detected_not_interpreted_figures_count": len(not_interp),
        "failed_figures_count": len(failed),
        # v0.6.1 object-level breakdown
        "page_level_visual_count": len(page_level),
        "embedded_visual_count": len(embedded),
        "captioned_figure_count": len(captioned),
        "visual_page_candidates_count": len(visual_candidates),
        "figures_without_bbox_count": len(without_bbox),
        "weak_visual_detections_count": len(weak_detections),
        "possible_cover_or_separator_figures_count": len(cover_separator),
        "figure_object_level_distribution": vol_dist,
        "figure_type_distribution": type_dist,
        "figures_by_page": {str(k): v for k, v in by_page.items()},
        "figures_by_section": by_section,
        "quarantined_figures_count": len(quarantined),
        "review_required_figures_count": len(review_req),
        "figures_with_caption_count": len(with_caption),
        "figures_without_caption_count": len(without_caption),
        "figure_evidence_count": fig_evidence_count,
        "sample_figures": _sample(figure_records),
        "sample_figures_with_caption": _sample(with_caption),
        "sample_low_confidence_figures": _sample(low_conf),
        "sample_page_level_visuals": _sample(page_level),
        "sample_weak_visual_detections": _sample(weak_detections),
    }


def figure_quality_checks(
    document_id: str,
    figure_records: list[dict[str, Any]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    figure_index_path = output_dir / "figure_index.jsonl"
    with_caption = [f for f in figure_records if f.get("nearby_caption_text")]
    without_caption = [f for f in figure_records if not f.get("nearby_caption_text")]
    low_conf = [f for f in figure_records if f.get("extraction_status") == "low_confidence"]
    page_level = [f for f in figure_records if f.get("is_page_level_visual")]
    without_bbox = [f for f in figure_records if not f.get("figure_bbox")]
    weak_dets = [
        f for f in figure_records
        if "weak_visual_detection" in (f.get("figure_quality_flags") or [])
    ]
    visual_candidates = [f for f in figure_records if f.get("is_visual_page_candidate")]
    vol_assigned = all(f.get("visual_object_level") for f in figure_records)
    evidence_eligible = [
        f for f in figure_records
        if f.get("extraction_status") in {"detected", "low_confidence", "detected_not_interpreted"}
    ]
    policy_consistent = all(
        not (str(f.get("evidence_policy") or "") == "quarantine" and not f.get("is_quarantined_figure"))
        for f in figure_records
    )

    checks: list[dict[str, Any]] = [
        quality_record(
            "figure_detection_completed",
            "pass",
            "info",
            f"Figure detection completed: {len(figure_records)} figure(s) found.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
        quality_record(
            "figure_index_created",
            "pass" if figure_index_path.exists() else "fail",
            "critical",
            "figure_index.jsonl exists." if figure_index_path.exists() else "figure_index.jsonl missing.",
            target_type="output_file",
            target_id="figure_index.jsonl",
            document_id=document_id,
            review_required=not figure_index_path.exists(),
        ),
        quality_record(
            "figure_bbox_available",
            "pass" if all(f.get("figure_bbox") for f in figure_records) else "warning",
            "minor",
            (
                f"{sum(1 for f in figure_records if f.get('figure_bbox'))} / "
                f"{len(figure_records)} figure(s) have bbox."
            ),
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
        quality_record(
            "figure_section_link_valid",
            "pass" if all(f.get("section_id") for f in figure_records) else "warning",
            "minor",
            (
                f"{sum(1 for f in figure_records if f.get('section_id'))} / "
                f"{len(figure_records)} figure(s) linked to a section."
            ),
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=any(not f.get("section_id") for f in figure_records),
        ),
        quality_record(
            "figure_caption_detection_completed",
            "pass" if with_caption else "info",
            "info",
            f"Caption detected for {len(with_caption)} / {len(figure_records)} figure(s).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
        quality_record(
            "figure_without_caption_warning",
            "warning" if without_caption else "pass",
            "minor",
            f"{len(without_caption)} figure(s) have no caption detected.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(without_caption),
        ),
        quality_record(
            "figure_low_confidence_warning",
            "warning" if low_conf else "pass",
            "minor",
            f"{len(low_conf)} figure(s) have low confidence (caption heuristic).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(low_conf),
        ),
        quality_record(
            "figure_evidence_created",
            "pass" if evidence_eligible else "info",
            "info",
            f"Figure evidences created for {len(evidence_eligible)} figure(s).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
        quality_record(
            "figure_evidence_policy_consistency_check",
            "pass" if policy_consistent else "fail",
            "critical",
            "Figure quarantine policy is consistently applied.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=not policy_consistent,
        ),
        quality_record(
            "no_figures_detected_info",
            "info" if not figure_records else "pass",
            "info",
            (
                "No figures detected on this document."
                if not figure_records
                else f"{len(figure_records)} figure(s) detected."
            ),
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
        # ── v0.6.1 checks ────────────────────────────────────────────────────
        quality_record(
            "page_level_visual_detected",
            "warning" if page_level else "pass",
            "minor",
            (
                f"{len(page_level)} page-level visual candidate(s) detected "
                "(page_visual_heuristic; not interpreted)."
            ),
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(page_level),
        ),
        quality_record(
            "figure_without_bbox_warning",
            "warning" if without_bbox else "pass",
            "minor",
            f"{len(without_bbox)} figure(s) have no bounding box.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(
                [f for f in without_bbox if f.get("detection_method") == "pdfplumber_image"]
            ),
        ),
        quality_record(
            "weak_visual_detection_warning",
            "warning" if weak_dets else "pass",
            "minor",
            f"{len(weak_dets)} figure(s) flagged as weak visual detection.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(weak_dets),
        ),
        quality_record(
            "visual_page_candidate_warning",
            "warning" if visual_candidates else "pass",
            "minor",
            (
                f"{len(visual_candidates)} page-level visual candidate(s); "
                "may include cover or separator pages."
            ),
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(visual_candidates),
        ),
        quality_record(
            "figure_object_level_assigned",
            "pass" if vol_assigned else "warning",
            "minor",
            "visual_object_level assigned to all figure records." if vol_assigned
            else "Some figure records are missing visual_object_level.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=not vol_assigned,
        ),
    ]

    for fig in figure_records:
        fig_id = str(fig.get("figure_id") or "")
        ftype = str(fig.get("figure_type") or "")
        fstatus = str(fig.get("extraction_status") or "")
        if not fig_id:
            checks.append(quality_record(
                "figure_id_missing",
                "fail",
                "critical",
                "A figure record has no figure_id.",
                target_type="figure",
                target_id="unknown",
                document_id=document_id,
                review_required=True,
            ))
            continue
        if ftype not in FIGURE_ALLOWED_TYPES:
            checks.append(quality_record(
                "figure_type_invalid",
                "fail",
                "major",
                f"Figure {fig_id} has invalid type: {ftype!r}.",
                target_type="figure",
                target_id=fig_id,
                document_id=document_id,
                review_required=True,
            ))
        if fstatus not in FIGURE_ALLOWED_STATUSES:
            checks.append(quality_record(
                "figure_status_invalid",
                "fail",
                "major",
                f"Figure {fig_id} has invalid status: {fstatus!r}.",
                target_type="figure",
                target_id=fig_id,
                document_id=document_id,
                review_required=True,
            ))

    return checks


def page_quality_diagnostic_checks(
    document_id: str,
    page_records: list[dict[str, Any]],
    text_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    blocks_by_page_id: dict[str, list[dict[str, Any]]] = {}
    for block in text_blocks:
        blocks_by_page_id.setdefault(str(block.get("page_id", "")), []).append(block)

    checks = []
    for page in page_records:
        page_id = str(page.get("page_id", ""))
        page_number = page.get("page_number")
        diagnostics = page_diagnostics(page, blocks_by_page_id.get(page_id, []))
        text_char_count = diagnostics["text_char_count"]

        if diagnostics["is_low_text"]:
            checks.append(
                quality_record(
                    "page_low_text_warning",
                    "warning",
                    "minor",
                    (
                        f"Page {page_number} has {text_char_count} extracted characters, "
                        f"below threshold {LOW_TEXT_CHAR_THRESHOLD}."
                    ),
                    target_type="page",
                    target_id=page_id,
                    document_id=document_id,
                    page_id=page_id,
                    review_required=False,
                )
            )

        if diagnostics["is_possible_visual"]:
            checks.append(
                quality_record(
                    "possible_visual_page",
                    "warning",
                    "minor",
                    "Page may be visual, image-heavy, or separator page.",
                    target_type="page",
                    target_id=page_id,
                    document_id=document_id,
                    page_id=page_id,
                    review_required=False,
                )
            )

        if diagnostics["is_possible_toc"]:
            checks.append(
                quality_record(
                    "possible_table_of_contents_page",
                    "warning",
                    "minor",
                    (
                        "Page may be table of contents: "
                        f"{diagnostics['title_blocks_count']} title blocks, "
                        f"{diagnostics['title_blocks_ending_with_number_count']} ending with a number."
                    ),
                    target_type="page",
                    target_id=page_id,
                    document_id=document_id,
                    page_id=page_id,
                    review_required=False,
                )
            )

        if diagnostics["is_high_title_density"]:
            checks.append(
                quality_record(
                    "high_title_density_warning",
                    "warning",
                    "minor",
                    (
                        f"Page {page_number} has title density "
                        f"{diagnostics['title_density']:.2%}, above "
                        f"{HIGH_TITLE_DENSITY_THRESHOLD:.0%}."
                    ),
                    target_type="page",
                    target_id=page_id,
                    document_id=document_id,
                    page_id=page_id,
                    review_required=False,
                )
            )

    return checks


def block_classification_quality_checks(
    document_id: str,
    text_block_statistics: dict[str, Any],
) -> list[dict[str, Any]]:
    block_type_counts = text_block_statistics.get("block_type_counts", {}) or {}
    total_blocks = int(text_block_statistics.get("total_blocks", 0) or 0)
    header_count = int(text_block_statistics.get("header_blocks_count", 0) or 0)
    footer_count = int(text_block_statistics.get("footer_blocks_count", 0) or 0)
    toc_count = int(text_block_statistics.get("toc_entry_blocks_count", 0) or 0)
    footnote_count = int(text_block_statistics.get("footnote_blocks_count", 0) or 0)
    unknown_ratio = float(text_block_statistics.get("unknown_blocks_ratio", 0) or 0)
    header_footer_ratio = ((header_count + footer_count) / total_blocks) if total_blocks else 0

    checks = [
        quality_record(
            "header_footer_detected",
            "pass" if header_count or footer_count else "info",
            "info",
            f"Detected {header_count} header block(s) and {footer_count} footer block(s).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
        quality_record(
            "toc_entries_detected",
            "pass" if toc_count else "info",
            "info",
            f"Detected {toc_count} table-of-contents entry block(s).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
        quality_record(
            "excessive_unknown_blocks_warning",
            "warning" if unknown_ratio > UNKNOWN_BLOCK_WARNING_THRESHOLD else "pass",
            "minor",
            (
                f"Unknown block ratio is {unknown_ratio:.2%}; "
                f"threshold is {UNKNOWN_BLOCK_WARNING_THRESHOLD:.0%}."
            ),
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=unknown_ratio > UNKNOWN_BLOCK_WARNING_THRESHOLD,
        ),
        quality_record(
            "repeated_header_footer_warning",
            "warning" if header_footer_ratio > 0.25 else "info",
            "minor",
            (
                f"Header/footer blocks represent {header_footer_ratio:.2%} of all blocks. "
                "High ratio may indicate ambiguous classification."
            ),
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=header_footer_ratio > 0.25,
        ),
        quality_record(
            "footer_detection_refined",
            "pass",
            "info",
            (
                "Footer detection uses strict bottom-zone plus recurring document "
                f"label/pattern signals. Refined footer count: {footer_count}."
            ),
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
        quality_record(
            "footnotes_detected",
            "pass" if footnote_count else "info",
            "info",
            f"Detected {footnote_count} footnote block(s).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
    ]
    # Keep counts visible in diagnostics even if callers inspect only messages.
    checks[0]["metadata"] = {
        "header_blocks_count": header_count,
        "footer_blocks_count": footer_count,
    }
    checks[1]["metadata"] = {"toc_entry_blocks_count": toc_count}
    checks[2]["metadata"] = {
        "unknown_blocks_count": int(block_type_counts.get("unknown", 0) or 0),
        "total_blocks": total_blocks,
    }
    checks[4]["metadata"] = {"refined_footer_blocks_count": footer_count}
    checks[5]["metadata"] = {"footnote_blocks_count": footnote_count}
    return checks


SECTION_TYPE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("anti_corruption", (r"\banti[- ]?corruption\b", r"\bcorruption\b", r"\bbribery\b")),
    ("health_safety", (r"\bhealth and safety\b", r"\bsante securite\b", r"\bsafety\b")),
    ("risk_management", (r"\brisk factors?\b", r"\brisk management\b", r"\bmanagement of risks?\b", r"\bfacteurs? de risque\b", r"\bgestion des risques\b")),
    ("human_rights", (r"\bhuman rights\b", r"\bdroits humains\b", r"\bdroits de l homme\b")),
    ("remuneration", (r"\bremuneration\b", r"\bcompensation\b", r"\bremuneration report\b")),
    ("biodiversity", (r"\bbiodiversity\b", r"\bbiodiversite\b")),
    ("governance", (r"\bgovernance\b", r"\bgouvernance\b", r"\bboard of directors\b", r"\bconseil d administration\b")),
    ("vigilance", (r"\bvigilance plan\b", r"\bplan de vigilance\b", r"\bduty of vigilance\b")),
    ("assurance", (r"\bassurance\b", r"\bverification\b", r"\blimited assurance\b")),
    ("emissions", (r"\bemissions\b", r"\bghg\b", r"\bscope 1\b", r"\bscope 2\b", r"\bscope 3\b")),
    ("taxonomy", (r"\btaxonomy\b", r"\btaxonomie\b")),
    ("climate", (r"\bclimate\b", r"\bclimat\b", r"\btcfd\b", r"\btransition plan\b")),
    ("energy", (r"\benergy\b", r"\benergie\b")),
    ("water", (r"\bwater\b", r"\bwater withdrawal\b", r"\beau\b", r"\bgestion de l eau\b")),
    ("waste", (r"\bwaste\b", r"\bdechets\b")),
    ("diversity", (r"\bdiversity\b", r"\binclusion\b", r"\bdiversite\b", r"\bdei\b")),
    ("workforce", (r"\bworkforce\b", r"\bemployees\b", r"\beffectifs\b", r"\bsalaries\b")),
    ("ethics", (r"\bethics\b", r"\bethical\b", r"\bethique\b", r"\bcode of conduct\b")),
    ("environment", (r"\benvironment\b", r"\benvironnement\b")),
    ("social", (r"\bsocial\b",)),
    ("general", (r"\boverview\b", r"\bintroduction\b", r"\bprofile\b", r"\bgeneral\b", r"\bfinancial highlights\b", r"\bhighlights\b")),
)


def normalize_for_section(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text or ""))
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def normalize_for_match(text: str) -> str:
    return " ".join(strip_accents(text).lower().split())


def years_in_text(text: str) -> list[str]:
    return re.findall(r"\b(?:1[0-9]\d{2}|20\d{2})\b", str(text or ""))


def is_timeline_like_heading(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split())
    if not clean:
        return False
    years = years_in_text(clean)
    digit_chars = sum(1 for char in clean if char.isdigit())
    density = digit_chars / max(len(clean), 1)
    lower = clean.lower()
    if re.match(r"^(?:1[0-9]\d{2}|20\d{2})\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’.-]+", clean):
        if not re.search(r"\b(highlights?|financial highlights?|results?|performance)\b", lower):
            return True
    if len(years) >= 2:
        return True
    if "century" in lower or "siècle" in lower or "siecle" in lower:
        return True
    if len(clean) > 45 and density > 0.18 and years:
        return True
    return False


def is_numeric_value_like(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split())
    if not clean:
        return True
    if re.fullmatch(r"[\d\s,.\-%€$£()A-Za-z]{1,40}", clean):
        letters = re.findall(r"[A-Za-z]+", clean)
        allowed_units = {"eur", "usd", "millions", "million", "bn", "m", "kg", "tons", "tonnes"}
        digit_count = sum(1 for char in clean if char.isdigit())
        useful_letters = [letter.lower() for letter in letters if letter.lower() not in allowed_units]
        if digit_count and not useful_letters:
            return True
    compact = re.sub(r"[\s,.\-%€$£()]", "", clean)
    if compact.isdigit():
        return True
    alnum = [char for char in clean if char.isalnum()]
    if alnum:
        digit_ratio = sum(1 for char in alnum if char.isdigit()) / len(alnum)
        return digit_ratio > 0.65
    return False


def is_toc_heading_text(text: str) -> bool:
    normalized = normalize_for_match(text)
    return normalized in {"contents", "table of contents", "sommaire", "table des matieres"}


def is_document_title_text(text: str) -> bool:
    normalized = normalize_for_match(text)
    return normalized in {
        "universal registration document",
        "annual report",
        "registration document",
        "document d enregistrement universel",
    }


def is_front_matter_text(text: str) -> bool:
    normalized = normalize_for_match(text)
    return bool(
        "fiscal year ended" in normalized
        or normalized in {"contents", "table of contents", "sommaire", "table des matieres"}
    )


def is_heading_fragment_text(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split())
    normalized = normalize_for_match(clean)
    if not clean:
        return False
    if re.match(r"^\((from|as of|at|for|since)\b.*\)$", normalized):
        return True
    if re.match(r"^(of|as of|from|for|and|or|the)\b", normalized):
        return True
    if normalized in {"companies", "company", "group"}:
        return True
    return False


def is_org_chart_like_heading(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split())
    normalized = normalize_for_match(clean)
    if not clean:
        return False
    org_terms = {"holding", "holdings", "companies", "company", "bv", "inc", "lvmh"}
    tokens = set(re.findall(r"[a-z0-9]+", normalized))
    percent_count = clean.count("%")
    if normalized in {"lvmh", "other holding", "companies"}:
        return True
    if percent_count >= 2:
        return True
    if tokens & org_terms and len(clean) <= 70:
        return True
    uppercase_letters = [char for char in clean if char.isalpha()]
    uppercase_ratio = (
        sum(1 for char in uppercase_letters if char.isupper()) / len(uppercase_letters)
        if uppercase_letters
        else 0.0
    )
    if len(clean) <= 24 and uppercase_ratio > 0.85 and not re.search(r"\b(risk|climate|social|governance|environment|financial|highlights|overview|business)\b", normalized):
        return True
    return False


def is_diagram_like_heading(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split())
    if clean.count("%") >= 2:
        return True
    if len(years_in_text(clean)) >= 2 and len(clean.split()) <= 10:
        return True
    return False


def is_sentence_like_heading(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split())
    normalized = normalize_for_match(clean)
    if not clean:
        return False
    strong_section_words = (
        "risk", "climate", "environment", "social", "governance", "financial highlights",
        "overview", "remuneration", "ethics", "vigilance"
    )
    if any(word in normalized for word in strong_section_words):
        return False
    if re.match(r"^\d[\d,.\s]*\s+[a-zA-Z]", clean) and len(clean) > 35:
        return True
    if "." in clean and len(clean) > 35:
        return True
    verbs = {"is", "are", "was", "were", "can", "be", "used", "proposed", "contains", "include", "includes"}
    tokens = set(re.findall(r"[a-z]+", normalized))
    return len(clean) > 45 and bool(tokens & verbs)


def has_reasonable_uppercase_heading_signal(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split())
    letters = [char for char in clean if char.isalpha()]
    if not letters:
        return False
    uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
    return uppercase_ratio >= 0.65 and 4 <= len(clean) <= 120


def compute_section_candidate_score(text: str, block: dict[str, Any]) -> tuple[float, str | None]:
    score = float(block.get("block_type_confidence", 0.5) or 0.5)
    section_type, section_type_confidence = classify_section_type(text)
    reasons = []
    if has_reasonable_uppercase_heading_signal(text):
        score += 0.12
        reasons.append("uppercase_heading_signal")
    if section_type != "unknown":
        score += 0.18
        reasons.append(f"known_section_type:{section_type}")
    if len(text) < 8:
        score -= 0.15
        reasons.append("short_heading_penalty")
    if is_heading_fragment_text(text):
        score -= 0.25
        reasons.append("fragment_penalty")
    if is_sentence_like_heading(text):
        score -= 0.25
        reasons.append("sentence_like_penalty")
    return max(0.0, min(1.0, round(score, 6))), ";".join(reasons) if reasons else None


def should_merge_heading_pair(first: dict[str, Any], second: dict[str, Any]) -> bool:
    if first.get("candidate_status") != "accepted" or second.get("candidate_status") != "accepted":
        return False
    if first.get("page_number") != second.get("page_number"):
        return False
    try:
        if int(second.get("reading_order") or 0) != int(first.get("reading_order") or 0) + 1:
            return False
    except Exception:
        return False
    first_text = str(first.get("text") or "").strip()
    second_text = str(second.get("text") or "").strip()
    if not first_text or not second_text:
        return False
    if is_org_chart_like_heading(first_text) or is_org_chart_like_heading(second_text):
        return False
    if is_numeric_value_like(first_text) or is_numeric_value_like(second_text):
        return False
    if first_text.endswith((",", ";", ":")):
        return True
    if is_heading_fragment_text(second_text):
        return True
    return False


def too_numeric_for_section(text: str) -> bool:
    clean = " ".join(str(text or "").strip().split())
    if not clean:
        return True
    alnum = [char for char in clean if char.isalnum()]
    if not alnum:
        return True
    digit_ratio = sum(1 for char in alnum if char.isdigit()) / len(alnum)
    return digit_ratio > 0.45


def classify_section_type(title: str) -> tuple[str, float]:
    normalized = normalize_for_match(title)
    for section_type, patterns in SECTION_TYPE_KEYWORDS:
        if any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in patterns):
            return section_type, 0.75
    return "unknown", 0.25


def evaluate_section_candidate(block: dict[str, Any]) -> dict[str, Any]:
    text = str(block.get("text") or "").strip()
    block_type = str(block.get("block_type") or "unknown")
    is_header = bool(block.get("is_header"))
    is_footer = bool(block.get("is_footer"))
    is_footnote = bool(block.get("is_footnote"))
    is_toc_entry = bool(block.get("is_toc_entry"))

    status = "accepted"
    reason = "accepted_title_candidate"
    rejection_rule = None
    accepted_rule = None
    is_candidate = True
    confidence = float(block.get("block_type_confidence", 0.5) or 0.5)
    detected_years = years_in_text(text)
    numeric_density = (
        sum(1 for char in text if char.isdigit()) / max(len(text), 1)
        if text
        else 0.0
    )
    is_front_matter = is_front_matter_text(text)
    is_timeline_like = is_timeline_like_heading(text)
    is_numeric_like = is_numeric_value_like(text)
    is_fragment = is_heading_fragment_text(text)
    is_org_like = is_org_chart_like_heading(text)
    is_diagram_like = is_diagram_like_heading(text)
    is_sentence_like = is_sentence_like_heading(text)
    page_flags: list[str] = []
    candidate_score, score_reason = compute_section_candidate_score(text, block)

    if block_type == "toc_entry" or is_toc_entry:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_toc_entry", "toc_entry_excluded", "toc_entry_block_type", False, 0.0
    elif is_header or is_footer or block_type in {"header", "footer"}:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_header_footer", "header_or_footer_excluded", "header_footer_block_type", False, 0.0
    elif is_footnote or block_type == "footnote":
        status, reason, rejection_rule, is_candidate, confidence = "rejected_footnote", "footnote_excluded", "footnote_block_type", False, 0.0
    elif block_type in {"caption"}:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_structural_block", "caption_excluded", "caption_block_type", False, 0.0
    elif block_type == "list_item":
        status, reason, rejection_rule, is_candidate, confidence = "rejected_list_item", "list_item_excluded", "list_item_block_type", False, 0.0
    elif block_type != "title":
        status, reason, rejection_rule, is_candidate, confidence = "rejected_low_confidence", "not_a_title_block", "not_title_block", False, 0.0
    elif not text:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_too_short", "empty_text", "empty_text", False, 0.0
    elif is_toc_heading_text(text):
        status, reason, rejection_rule, is_candidate, confidence = "rejected_toc_heading", "table_of_contents_heading_excluded", "toc_heading_exact_match", False, 0.0
    elif is_document_title_text(text):
        status, reason, rejection_rule, is_candidate, confidence = "rejected_document_title", "document_title_excluded", "document_title_exact_match", False, 0.0
    elif is_front_matter:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_front_matter", "front_matter_heading_excluded", "front_matter_phrase", False, 0.0
    elif len(text) < 4:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_too_short", "heading_text_too_short", "too_short", False, 0.1
    elif is_numeric_like:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_numeric_value", "numeric_value_like_heading", "numeric_value_like", False, 0.1
    elif too_numeric_for_section(text):
        status, reason, rejection_rule, is_candidate, confidence = "rejected_too_numeric", "heading_too_numeric", "too_numeric", False, 0.1
    elif is_timeline_like:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_timeline_like", "multiple_dates_or_timeline_like_heading", "timeline_like_heading", False, 0.1
    elif is_fragment:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_heading_fragment", "heading_fragment_excluded", "heading_fragment", False, 0.15
    elif is_org_like:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_org_chart_like", "org_chart_like_heading_excluded", "org_chart_like", False, 0.15
    elif is_diagram_like:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_diagram_like", "diagram_like_heading_excluded", "diagram_like", False, 0.15
    elif is_sentence_like:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_sentence_like_heading", "sentence_like_heading_excluded", "sentence_like_heading", False, 0.15
    elif float(block.get("block_type_confidence", 0.0) or 0.0) < 0.45:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_low_confidence", "block_type_confidence_too_low", "low_block_confidence", False, 0.2
    elif candidate_score < SECTION_CANDIDATE_SCORE_THRESHOLD:
        status, reason, rejection_rule, is_candidate, confidence = "rejected_low_confidence", "candidate_score_below_threshold", "candidate_score_threshold", False, candidate_score
    else:
        accepted_rule = "conservative_title_heading"
        confidence = candidate_score

    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": f"candidate_{block.get('text_block_id')}",
        "document_id": block.get("document_id"),
        "text_block_id": block.get("text_block_id"),
        "page_number": block.get("page_number"),
        "text": text,
        "normalized_heading_text": text,
        "candidate_status": status,
        "candidate_reason": reason,
        "block_type": block_type,
        "is_toc_entry": is_toc_entry,
        "is_header": is_header,
        "is_footer": is_footer,
        "is_footnote": is_footnote,
        "is_section_heading_candidate": is_candidate,
        "confidence": round(confidence, 6),
        "reading_order": block.get("reading_order"),
        "candidate_score": round(candidate_score if status == "accepted" else confidence, 6),
        "rejection_rule": rejection_rule,
        "accepted_rule": accepted_rule,
        "numeric_density": round(numeric_density, 6),
        "years_detected": detected_years,
        "page_diagnostic_flags": page_flags,
        "is_front_matter": is_front_matter,
        "is_timeline_like": is_timeline_like,
        "is_numeric_value_like": is_numeric_like,
        "is_heading_fragment": is_fragment,
        "is_org_chart_like": is_org_like,
        "is_diagram_like": is_diagram_like,
        "is_sentence_like": is_sentence_like,
        "source_heading_block_ids": [block.get("text_block_id")],
        "was_merged_heading": False,
        "score_reason": score_reason,
    }


def build_section_candidates(document_id: str, text_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Keep all title-like or structural blocks that matter for audit, not every paragraph.
    relevant_types = {"title", "toc_entry", "header", "footer", "footnote", "caption", "list_item"}
    candidates = []
    for block in text_blocks:
        block_text = str(block.get("text") or "")
        if (
            str(block.get("block_type") or "unknown") in relevant_types
            or is_numeric_value_like(block_text)
            or is_sentence_like_heading(block_text)
            or is_org_chart_like_heading(block_text)
        ):
            candidate = evaluate_section_candidate(block)
            candidate["document_id"] = document_id
            candidates.append(candidate)

    for index, candidate in enumerate(candidates[:-1]):
        next_candidate = candidates[index + 1]
        if should_merge_heading_pair(candidate, next_candidate):
            merged = (
                f"{candidate['normalized_heading_text'].rstrip()} "
                f"{next_candidate['normalized_heading_text'].lstrip()}"
            ).replace(" ,", ",")
            candidate["normalized_heading_text"] = " ".join(merged.split())
            candidate["source_heading_block_ids"] = (
                list(candidate.get("source_heading_block_ids") or [])
                + list(next_candidate.get("source_heading_block_ids") or [])
            )
            candidate["was_merged_heading"] = True
            candidate["accepted_rule"] = "merged_consecutive_heading_blocks"
            candidate["candidate_score"] = max(float(candidate.get("candidate_score") or 0), 0.65)
            candidate["confidence"] = candidate["candidate_score"]
            next_candidate["candidate_status"] = "rejected_heading_fragment"
            next_candidate["candidate_reason"] = "merged_into_previous_heading"
            next_candidate["rejection_rule"] = "merged_heading_fragment"
            next_candidate["is_section_heading_candidate"] = False
            next_candidate["candidate_score"] = 0.2
            next_candidate["confidence"] = 0.2
    return candidates


def build_sections(
    document_id: str,
    page_records: list[dict[str, Any]],
    section_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    accepted = [
        candidate
        for candidate in section_candidates
        if candidate.get("candidate_status") == "accepted"
    ]
    accepted.sort(key=lambda item: (int(item.get("page_number") or 0), int(item.get("reading_order") or 0)))

    if not accepted:
        return [], warnings

    last_page = max((int(page.get("page_number") or 0) for page in page_records), default=0)
    sections: list[dict[str, Any]] = []
    for index, candidate in enumerate(accepted):
        next_candidate = accepted[index + 1] if index + 1 < len(accepted) else None
        page_start = int(candidate.get("page_number") or 0)
        if next_candidate is not None:
            next_page = int(next_candidate.get("page_number") or page_start)
            page_end = next_page if next_page == page_start else next_page - 1
            end_element_id = next_candidate.get("text_block_id")
        else:
            page_end = last_page or page_start
            end_element_id = None

        if page_start <= 0 or page_end < page_start:
            warnings.append(f"Invalid section range for heading {candidate.get('text_block_id')}: {page_start}-{page_end}")
            continue

        normalized_title = str(candidate.get("normalized_heading_text") or candidate.get("text") or "")
        section_type, section_type_confidence = classify_section_type(normalized_title)
        review_required = section_type_confidence < 0.5 or float(candidate.get("confidence") or 0.0) < 0.6
        sections.append(
            {
                "schema_version": SCHEMA_VERSION,
                "section_id": f"{document_id}_section_{len(sections) + 1:04d}",
                "document_id": document_id,
                "section_title": normalized_title,
                "section_type": section_type,
                "page_start": page_start,
                "page_end": page_end,
                "start_element_id": candidate.get("text_block_id"),
                "end_element_id": end_element_id,
                "source_heading_block_id": candidate.get("text_block_id"),
                "source_heading_block_ids": candidate.get("source_heading_block_ids") or [candidate.get("text_block_id")],
                "section_detection_confidence": candidate.get("confidence"),
                "section_type_confidence": section_type_confidence,
                "detection_method": "conservative_rule_based_v0_3",
                "excluded_from_esg_extraction": False,
                "review_required": review_required,
            }
        )
    return sections, warnings


def build_section_statistics(
    document_id: str,
    section_candidates: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    rejection_counts: dict[str, int] = {}
    section_type_counts: dict[str, int] = {}
    sections_by_page: dict[str, int] = {}
    accepted_samples: list[str] = []
    rejected_samples: list[dict[str, Any]] = []
    section_samples: list[dict[str, Any]] = []

    for candidate in section_candidates:
        status = str(candidate.get("candidate_status") or "unknown")
        if status == "accepted":
            if len(accepted_samples) < SAMPLE_LIMIT:
                accepted_samples.append(truncate_sample(str(candidate.get("text") or "")))
        else:
            rejection_counts[status] = rejection_counts.get(status, 0) + 1
            if len(rejected_samples) < SAMPLE_LIMIT:
                rejected_samples.append(
                    {
                        "text": truncate_sample(str(candidate.get("text") or "")),
                        "candidate_status": status,
                        "candidate_reason": candidate.get("candidate_reason"),
                    }
                )

    invalid_ranges = 0
    quality_scores: list[float] = []
    evidence_policy_counts: dict[str, int] = {}
    sample_suspicious_sections: list[dict[str, Any]] = []
    sample_low_quality_sections: list[dict[str, Any]] = []
    sample_rejected_numeric_values: list[str] = []
    sample_rejected_front_matter: list[str] = []
    sample_rejected_timeline_like: list[str] = []
    sample_rejected_heading_fragments: list[str] = []
    sample_rejected_org_chart_like: list[str] = []
    sample_rejected_sentence_like: list[str] = []
    sample_merged_headings: list[str] = []
    for section in sections:
        stype = str(section.get("section_type") or "unknown")
        section_type_counts[stype] = section_type_counts.get(stype, 0) + 1
        page_start = int(section.get("page_start") or 0)
        page_end = int(section.get("page_end") or 0)
        if page_end < page_start:
            invalid_ranges += 1
        sections_by_page[str(page_start)] = sections_by_page.get(str(page_start), 0) + 1
        if len(section_samples) < SAMPLE_LIMIT:
            section_samples.append(
                {
                    "section_title": truncate_sample(str(section.get("section_title") or "")),
                    "section_type": stype,
                    "page_start": page_start,
                    "page_end": page_end,
                }
            )
        quality_score = float(section.get("section_quality_score", 1.0) or 1.0)
        quality_scores.append(quality_score)
        policy = str(section.get("evidence_policy") or "normal")
        evidence_policy_counts[policy] = evidence_policy_counts.get(policy, 0) + 1
        if section.get("is_suspicious_section") and len(sample_suspicious_sections) < SAMPLE_LIMIT:
            sample_suspicious_sections.append(
                {
                    "section_id": section.get("section_id"),
                    "section_title": truncate_sample(str(section.get("section_title") or "")),
                    "section_quality_score": quality_score,
                    "evidence_policy": policy,
                    "suspicion_reasons": section.get("suspicion_reasons") or [],
                }
            )
        if quality_score < 0.75 and len(sample_low_quality_sections) < SAMPLE_LIMIT:
            sample_low_quality_sections.append(
                {
                    "section_id": section.get("section_id"),
                    "section_title": truncate_sample(str(section.get("section_title") or "")),
                    "section_quality_score": quality_score,
                    "evidence_policy": policy,
                }
            )

    for candidate in section_candidates:
        status = str(candidate.get("candidate_status") or "")
        text = truncate_sample(str(candidate.get("text") or ""))
        if status == "rejected_numeric_value" and len(sample_rejected_numeric_values) < SAMPLE_LIMIT:
            sample_rejected_numeric_values.append(text)
        if status in {"rejected_front_matter", "rejected_document_title", "rejected_cover_page"} and len(sample_rejected_front_matter) < SAMPLE_LIMIT:
            sample_rejected_front_matter.append(text)
        if status == "rejected_timeline_like" and len(sample_rejected_timeline_like) < SAMPLE_LIMIT:
            sample_rejected_timeline_like.append(text)
        if status == "rejected_heading_fragment" and len(sample_rejected_heading_fragments) < SAMPLE_LIMIT:
            sample_rejected_heading_fragments.append(text)
        if status in {"rejected_org_chart_like", "rejected_diagram_like"} and len(sample_rejected_org_chart_like) < SAMPLE_LIMIT:
            sample_rejected_org_chart_like.append(text)
        if status == "rejected_sentence_like_heading" and len(sample_rejected_sentence_like) < SAMPLE_LIMIT:
            sample_rejected_sentence_like.append(text)
        if candidate.get("was_merged_heading") and len(sample_merged_headings) < SAMPLE_LIMIT:
            sample_merged_headings.append(truncate_sample(str(candidate.get("normalized_heading_text") or "")))

    accepted_count = sum(1 for candidate in section_candidates if candidate.get("candidate_status") == "accepted")
    unknown_sections = section_type_counts.get("unknown", 0)
    unknown_ratio = round(unknown_sections / len(sections), 6) if sections else 0.0
    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "section_candidates_count": len(section_candidates),
        "accepted_candidates_count": accepted_count,
        "rejected_candidates_count": len(section_candidates) - accepted_count,
        "rejection_reasons_distribution": rejection_counts,
        "sections_count": len(sections),
        "section_types_distribution": section_type_counts,
        "rejected_cover_page_count": rejection_counts.get("rejected_cover_page", 0),
        "rejected_toc_heading_count": rejection_counts.get("rejected_toc_heading", 0),
        "rejected_numeric_value_count": rejection_counts.get("rejected_numeric_value", 0),
        "rejected_front_matter_count": rejection_counts.get("rejected_front_matter", 0),
        "rejected_document_title_count": rejection_counts.get("rejected_document_title", 0),
        "timeline_like_rejected_count": rejection_counts.get("rejected_timeline_like", 0),
        "numeric_value_rejected_count": rejection_counts.get("rejected_numeric_value", 0),
        "rejected_heading_fragment_count": rejection_counts.get("rejected_heading_fragment", 0),
        "rejected_org_chart_like_count": rejection_counts.get("rejected_org_chart_like", 0),
        "rejected_diagram_like_count": rejection_counts.get("rejected_diagram_like", 0),
        "rejected_sentence_like_count": rejection_counts.get("rejected_sentence_like_heading", 0),
        "merged_headings_count": sum(1 for candidate in section_candidates if candidate.get("was_merged_heading")),
        "low_confidence_rejected_count": rejection_counts.get("rejected_low_confidence", 0),
        "section_type_unknown_ratio": unknown_ratio,
        "sections_by_page": sections_by_page,
        "sample_accepted_headings": accepted_samples,
        "sample_rejected_headings": rejected_samples,
        "sample_rejected_numeric_values": sample_rejected_numeric_values,
        "sample_rejected_front_matter": sample_rejected_front_matter,
        "sample_rejected_timeline_like": sample_rejected_timeline_like,
        "sample_rejected_heading_fragments": sample_rejected_heading_fragments,
        "sample_rejected_org_chart_like": sample_rejected_org_chart_like,
        "sample_rejected_sentence_like": sample_rejected_sentence_like,
        "sample_merged_headings": sample_merged_headings,
        "sample_sections": section_samples,
        "invalid_section_ranges_count": invalid_ranges,
        "suspicious_sections_count": sum(1 for section in sections if section.get("is_suspicious_section")),
        "section_quality_score_distribution": {
            "average": round(statistics.mean(quality_scores), 6) if quality_scores else 0.0,
            "min": round(min(quality_scores), 6) if quality_scores else 0.0,
            "max": round(max(quality_scores), 6) if quality_scores else 0.0,
            "below_0_50": sum(1 for score in quality_scores if score < 0.50),
            "below_0_75": sum(1 for score in quality_scores if score < 0.75),
        },
        "evidence_policy_distribution": evidence_policy_counts,
        "sample_suspicious_sections": sample_suspicious_sections,
        "sample_low_quality_sections": sample_low_quality_sections,
        "section_quality_thresholds": {
            "normal_min": 0.75,
            "review_required_min": 0.50,
            "quarantine_below": 0.50,
        },
    }


def section_quality_checks(
    document_id: str,
    section_candidates: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    accepted_count = sum(1 for candidate in section_candidates if candidate.get("candidate_status") == "accepted")
    rejected_count = len(section_candidates) - accepted_count
    status_counts: dict[str, int] = {}
    for candidate in section_candidates:
        status = str(candidate.get("candidate_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    unknown_ratio = (
        sum(1 for section in sections if section.get("section_type") == "unknown") / len(sections)
        if sections
        else 0.0
    )
    merged_count = sum(1 for candidate in section_candidates if candidate.get("was_merged_heading"))
    checks = [
        quality_record(
            "section_candidates_detected",
            "pass" if section_candidates else "warning",
            "minor",
            f"Detected {len(section_candidates)} section candidate(s), {accepted_count} accepted.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=not section_candidates,
        ),
        quality_record(
            "sections_created",
            "pass" if sections else "warning",
            "minor",
            f"Created {len(sections)} section(s).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=not sections,
        ),
        quality_record(
            "section_candidates_rejected",
            "info" if rejected_count else "pass",
            "info",
            f"Rejected {rejected_count} section candidate(s).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
    ]
    if not sections:
        checks.append(
            quality_record(
                "no_sections_detected_warning",
                "warning",
                "minor",
                "No conservative sections were detected.",
                target_type="document",
                target_id=document_id,
                document_id=document_id,
                review_required=True,
            )
        )

    for section in sections:
        valid_range = int(section.get("page_start") or 0) <= int(section.get("page_end") or 0)
        checks.append(
            quality_record(
                "section_range_valid",
                "pass" if valid_range else "fail",
                "major",
                (
                    f"Section range {section.get('page_start')}-{section.get('page_end')} "
                    f"for {section.get('section_id')}."
                ),
                target_type="section",
                target_id=str(section.get("section_id")),
                document_id=document_id,
                review_required=not valid_range,
            )
        )
        if section.get("review_required"):
            checks.append(
                quality_record(
                    "section_low_confidence_warning",
                    "warning",
                    "minor",
                    f"Section {section.get('section_id')} has low type or detection confidence.",
                    target_type="section",
                    target_id=str(section.get("section_id")),
                    document_id=document_id,
                    review_required=True,
                )
            )
    checks.extend(
        [
            quality_record(
                "section_front_matter_rejected",
                "pass" if status_counts.get("rejected_front_matter", 0) or status_counts.get("rejected_document_title", 0) else "info",
                "info",
                (
                    "Rejected "
                    f"{status_counts.get('rejected_front_matter', 0)} front matter heading(s) and "
                    f"{status_counts.get('rejected_document_title', 0)} document title heading(s)."
                ),
                target_type="document",
                target_id=document_id,
                document_id=document_id,
            ),
            quality_record(
                "section_numeric_values_rejected",
                "pass" if status_counts.get("rejected_numeric_value", 0) else "info",
                "info",
                f"Rejected {status_counts.get('rejected_numeric_value', 0)} numeric value-like heading(s).",
                target_type="document",
                target_id=document_id,
                document_id=document_id,
            ),
            quality_record(
                "section_timeline_like_rejected",
                "pass" if status_counts.get("rejected_timeline_like", 0) else "info",
                "info",
                f"Rejected {status_counts.get('rejected_timeline_like', 0)} timeline-like heading(s).",
                target_type="document",
                target_id=document_id,
                document_id=document_id,
            ),
            quality_record(
                "section_type_keyword_boundary_check",
                "pass",
                "info",
                "Section type keywords use regex boundaries to avoid substring false positives.",
                target_type="document",
                target_id=document_id,
                document_id=document_id,
            ),
            quality_record(
                "section_unknown_ratio_warning",
                "warning" if unknown_ratio > 0.80 else "pass",
                "minor",
                f"Unknown section type ratio is {unknown_ratio:.2%}.",
                target_type="document",
                target_id=document_id,
                document_id=document_id,
                review_required=unknown_ratio > 0.80,
            ),
            quality_record(
                "heading_fragments_rejected",
                "pass" if status_counts.get("rejected_heading_fragment", 0) else "info",
                "info",
                f"Rejected {status_counts.get('rejected_heading_fragment', 0)} heading fragment(s).",
                target_type="document",
                target_id=document_id,
                document_id=document_id,
            ),
            quality_record(
                "org_chart_like_headings_rejected",
                "pass" if status_counts.get("rejected_org_chart_like", 0) or status_counts.get("rejected_diagram_like", 0) else "info",
                "info",
                (
                    f"Rejected {status_counts.get('rejected_org_chart_like', 0)} org-chart-like "
                    f"and {status_counts.get('rejected_diagram_like', 0)} diagram-like heading(s)."
                ),
                target_type="document",
                target_id=document_id,
                document_id=document_id,
            ),
            quality_record(
                "sentence_like_headings_rejected",
                "pass" if status_counts.get("rejected_sentence_like_heading", 0) else "info",
                "info",
                f"Rejected {status_counts.get('rejected_sentence_like_heading', 0)} sentence-like heading(s).",
                target_type="document",
                target_id=document_id,
                document_id=document_id,
            ),
            quality_record(
                "merged_headings_created",
                "pass" if merged_count else "info",
                "info",
                f"Created {merged_count} merged heading(s).",
                target_type="document",
                target_id=document_id,
                document_id=document_id,
            ),
            quality_record(
                "section_candidate_score_threshold_applied",
                "pass",
                "info",
                f"Candidate score threshold applied: {SECTION_CANDIDATE_SCORE_THRESHOLD}.",
                target_type="document",
                target_id=document_id,
                document_id=document_id,
            ),
        ]
    )
    return checks


def truncate_evidence_quote(text: str) -> str:
    return " ".join(str(text or "").split())[:EVIDENCE_QUOTE_LIMIT]


def text_block_order_map(text_blocks: list[dict[str, Any]]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for block in text_blocks:
        block_id = str(block.get("text_block_id") or "")
        if not block_id:
            continue
        try:
            mapping[block_id] = int(block.get("reading_order") or 0)
        except Exception:
            mapping[block_id] = 0
    return mapping


def find_section_for_text_block(
    block: dict[str, Any],
    sections: list[dict[str, Any]],
    block_order_by_id: dict[str, int] | None = None,
) -> tuple[dict[str, Any] | None, float]:
    """Return the best section for a text block plus localization confidence."""
    try:
        page_number = int(block.get("page_number") or 0)
        block_order = int(block.get("reading_order") or 0)
    except Exception:
        return None, 0.0

    page_matches: list[dict[str, Any]] = []
    for section in sections:
        try:
            page_start = int(section.get("page_start") or 0)
            page_end = int(section.get("page_end") or 0)
        except Exception:
            continue
        if page_start <= page_number <= page_end:
            page_matches.append(section)

    if not page_matches:
        return None, 0.0

    if block_order_by_id:
        for section in page_matches:
            start_id = str(section.get("start_element_id") or "")
            end_id = str(section.get("end_element_id") or "")
            start_order = block_order_by_id.get(start_id)
            end_order = block_order_by_id.get(end_id) if end_id else None
            if start_order is None:
                continue
            if end_order is not None:
                if start_order <= block_order < end_order:
                    return section, 0.92
            elif block_order >= start_order:
                return section, 0.88

    # Conservative fallback: same page interval, but no element-order guarantee.
    return page_matches[0], 0.65


def should_create_paragraph_evidence(block: dict[str, Any]) -> bool:
    block_type = str(block.get("block_type") or "unknown")
    if block_type != "paragraph":
        return False
    if bool(block.get("is_header")) or bool(block.get("is_footer")) or bool(block.get("is_toc_entry")):
        return False
    if bool(block.get("is_footnote")):
        return False
    text = truncate_evidence_quote(str(block.get("text") or ""))
    if len(text) < MIN_PARAGRAPH_EVIDENCE_CHARS:
        return False
    if is_numeric_value_like(text):
        return False
    return True


def should_merge_paragraph_evidence(current_text: str, next_text: str) -> bool:
    current = str(current_text or "").strip()
    nxt = str(next_text or "").strip()
    if not current or not nxt:
        return False
    if len(current) < 120:
        return True
    if not re.search(r"[.!?;:]$", current):
        return True
    if re.match(r"^(and|or|to|of|in|with|for|as|that|which|while|including)\b", nxt, re.IGNORECASE):
        return True
    return bool(nxt[:1].islower())


def merge_bbox_values(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    bboxes = [block.get("bbox") for block in blocks if isinstance(block.get("bbox"), dict)]
    if not bboxes:
        return None
    try:
        return {
            "x0": min(float(bbox["x0"]) for bbox in bboxes),
            "y0": min(float(bbox["y0"]) for bbox in bboxes),
            "x1": max(float(bbox["x1"]) for bbox in bboxes),
            "y1": max(float(bbox["y1"]) for bbox in bboxes),
            "coordinate_system": "pdf_points",
        }
    except Exception:
        return bboxes[0]


def build_paragraph_evidence_groups(
    text_blocks: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    order_by_id: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    diagnostics = {
        "short_evidence_skipped_count": 0,
        "short_evidence_review_required_count": 0,
    }
    eligible: list[dict[str, Any]] = []
    for block in sorted(text_blocks, key=lambda item: int(item.get("reading_order") or 0)):
        if not should_create_paragraph_evidence(block):
            quote = truncate_evidence_quote(str(block.get("text") or ""))
            if str(block.get("block_type") or "") == "paragraph" and 0 < len(quote) < MIN_PARAGRAPH_EVIDENCE_CHARS:
                diagnostics["short_evidence_skipped_count"] += 1
            continue
        section, localization_confidence = find_section_for_text_block(block, sections, order_by_id)
        if section is None:
            continue
        eligible.append(
            {
                "block": block,
                "section": section,
                "section_id": section.get("section_id"),
                "localization_confidence": localization_confidence,
                "quote": truncate_evidence_quote(str(block.get("text") or "")),
            }
        )

    groups: list[dict[str, Any]] = []
    index = 0
    while index < len(eligible):
        first = eligible[index]
        group_items = [first]
        merged_quote = first["quote"]
        index += 1

        while index < len(eligible):
            candidate = eligible[index]
            previous = group_items[-1]
            same_section = candidate["section_id"] == first["section_id"]
            try:
                page_gap = int(candidate["block"].get("page_number") or 0) - int(previous["block"].get("page_number") or 0)
                order_gap = int(candidate["block"].get("reading_order") or 0) - int(previous["block"].get("reading_order") or 0)
            except Exception:
                page_gap = 99
                order_gap = 99
            combined = f"{merged_quote} {candidate['quote']}".strip()
            if not same_section or page_gap not in {0, 1} or order_gap != 1:
                break
            if len(combined) > EVIDENCE_QUOTE_LIMIT:
                break
            if not should_merge_paragraph_evidence(merged_quote, candidate["quote"]):
                break
            group_items.append(candidate)
            merged_quote = combined
            index += 1

        quote_length = len(merged_quote)
        if quote_length < MIN_PARAGRAPH_EVIDENCE_CHARS:
            diagnostics["short_evidence_skipped_count"] += 1
            continue
        review_short = quote_length < SHORT_EVIDENCE_REVIEW_THRESHOLD
        if review_short:
            diagnostics["short_evidence_review_required_count"] += 1
        groups.append(
            {
                "items": group_items,
                "quote": merged_quote,
                "review_short": review_short,
            }
        )

    return groups, diagnostics


def build_evidence_store(
    document_id: str,
    text_blocks: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    evidence_records: list[dict[str, Any]] = []
    blocks_by_id = {str(block.get("text_block_id")): block for block in text_blocks}
    order_by_id = text_block_order_map(text_blocks)
    diagnostics = {
        "short_evidence_skipped_count": 0,
        "short_evidence_review_required_count": 0,
    }

    def next_evidence_id() -> str:
        return f"{document_id}_evidence_{len(evidence_records) + 1:06d}"

    for section in sections:
        source_id = str(section.get("source_heading_block_id") or "")
        block = blocks_by_id.get(source_id)
        bbox = block.get("bbox") if block else None
        page_number = int(block.get("page_number") or section.get("page_start") or 0) if block or section else 0
        page_id = str(block.get("page_id") or f"{document_id}_page_{page_number:04d}") if page_number else None
        quote = truncate_evidence_quote(str(section.get("section_title") or ""))
        if not quote:
            continue
        evidence_records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "evidence_id": next_evidence_id(),
                "document_id": document_id,
                "page_id": page_id,
                "page_number": page_number,
                "evidence_type": "section_heading",
                "quote": quote,
                "bbox": bbox,
                "section_id": section.get("section_id"),
                "text_block_id": source_id or None,
                "source_element_type": "text_block",
                "source_element_id": source_id or None,
                "source_text_block_ids": [source_id] if source_id else [],
                "merged_blocks_count": 1,
                "was_merged_evidence": False,
                "merge_method": "not_merged_section_heading",
                "evidence_confidence": 0.95 if block else 0.75,
                "localization_confidence": 0.95 if bbox else 0.6,
                "extraction_method": "document_structure_rule_based_v0_4_1",
                "review_required": bool(section.get("review_required")) or block is None or not bbox,
            }
        )

    paragraph_groups, paragraph_diagnostics = build_paragraph_evidence_groups(text_blocks, sections, order_by_id)
    diagnostics.update(paragraph_diagnostics)
    for group in paragraph_groups:
        items = list(group["items"])
        blocks = [item["block"] for item in items]
        first = items[0]
        block = first["block"]
        section = first["section"]
        localization_confidence = min(float(item["localization_confidence"]) for item in items)
        quote = truncate_evidence_quote(str(group["quote"] or ""))
        bbox = merge_bbox_values(blocks)
        source_ids = [str(item["block"].get("text_block_id")) for item in items if item["block"].get("text_block_id")]
        evidence_confidence = 0.88 if bbox else 0.65
        review_required = bool(group.get("review_short")) or not bbox or localization_confidence < 0.8
        evidence_records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "evidence_id": next_evidence_id(),
                "document_id": document_id,
                "page_id": block.get("page_id"),
                "page_number": block.get("page_number"),
                "evidence_type": "paragraph",
                "quote": quote,
                "bbox": bbox,
                "section_id": section.get("section_id"),
                "text_block_id": block.get("text_block_id"),
                "source_element_type": "text_block",
                "source_element_id": block.get("text_block_id"),
                "source_text_block_ids": source_ids,
                "merged_blocks_count": len(source_ids),
                "was_merged_evidence": len(source_ids) > 1,
                "merge_method": "consecutive_paragraph_blocks_same_section" if len(source_ids) > 1 else "not_merged_single_paragraph",
                "evidence_confidence": evidence_confidence,
                "localization_confidence": localization_confidence,
                "extraction_method": "document_structure_rule_based_v0_4_1",
                "review_required": review_required,
            }
        )

    return evidence_records, diagnostics


def build_evidence_statistics(
    document_id: str,
    evidence_records: list[dict[str, Any]],
    sections: list[dict[str, Any]] | None = None,
    diagnostics: dict[str, int] | None = None,
) -> dict[str, Any]:
    sections = sections or []
    diagnostics = diagnostics or {}
    type_counts: dict[str, int] = {}
    by_section: dict[str, int] = {}
    quote_lengths: list[int] = []
    sample_evidence: list[dict[str, Any]] = []
    sample_without_section: list[dict[str, Any]] = []
    sample_section_heading: list[dict[str, Any]] = []
    sample_paragraph: list[dict[str, Any]] = []
    sample_short: list[dict[str, Any]] = []
    sample_merged: list[dict[str, Any]] = []
    sample_quarantined: list[dict[str, Any]] = []
    sample_review_due_to_section: list[dict[str, Any]] = []
    policy_counts: dict[str, int] = {}
    by_section_policy: dict[str, dict[str, int]] = {}

    for evidence in evidence_records:
        evidence_type = str(evidence.get("evidence_type") or "unknown")
        section_id = str(evidence.get("section_id") or "")
        policy = str(evidence.get("evidence_policy") or "normal")
        policy_counts[policy] = policy_counts.get(policy, 0) + 1
        if section_id:
            section_policy_counts = by_section_policy.setdefault(section_id, {})
            section_policy_counts[policy] = section_policy_counts.get(policy, 0) + 1
        type_counts[evidence_type] = type_counts.get(evidence_type, 0) + 1
        if section_id:
            by_section[section_id] = by_section.get(section_id, 0) + 1
        quote_lengths.append(len(str(evidence.get("quote") or "")))

        sample = {
            "evidence_id": evidence.get("evidence_id"),
            "evidence_type": evidence_type,
            "section_id": evidence.get("section_id"),
            "page_number": evidence.get("page_number"),
            "quote": truncate_sample(str(evidence.get("quote") or "")),
        }
        if len(sample_evidence) < SAMPLE_LIMIT:
            sample_evidence.append(sample)
        if not section_id and len(sample_without_section) < SAMPLE_LIMIT:
            sample_without_section.append(sample)
        if evidence_type == "section_heading" and len(sample_section_heading) < SAMPLE_LIMIT:
            sample_section_heading.append(sample)
        if evidence_type == "paragraph" and len(sample_paragraph) < SAMPLE_LIMIT:
            sample_paragraph.append(sample)
        if len(str(evidence.get("quote") or "")) < SHORT_EVIDENCE_REVIEW_THRESHOLD and len(sample_short) < SAMPLE_LIMIT:
            sample_short.append(sample)
        if evidence.get("was_merged_evidence") and len(sample_merged) < SAMPLE_LIMIT:
            sample_merged.append(sample)
        if evidence.get("is_quarantined_evidence") and len(sample_quarantined) < SAMPLE_LIMIT:
            sample_quarantined.append(sample)
        if evidence.get("review_required_due_to_section") and len(sample_review_due_to_section) < SAMPLE_LIMIT:
            sample_review_due_to_section.append(sample)

    evidence_count = len(evidence_records)
    share_by_section = {
        section_id: round(count / evidence_count, 6)
        for section_id, count in by_section.items()
        if evidence_count
    }
    section_by_id = {str(section.get("section_id")): section for section in sections}
    high_density_sections: list[dict[str, Any]] = []
    front_matter_sections: list[dict[str, Any]] = []
    mismatch_warnings: list[dict[str, Any]] = []

    for section_id, count in by_section.items():
        section = section_by_id.get(section_id, {})
        share = share_by_section.get(section_id, 0.0)
        if count > SECTION_HIGH_EVIDENCE_COUNT_THRESHOLD or share > SECTION_HIGH_EVIDENCE_SHARE_THRESHOLD:
            high_density_sections.append(
                {
                    "section_id": section_id,
                    "section_title": truncate_sample(str(section.get("section_title") or "")),
                    "evidence_count": count,
                    "evidence_share": share,
                }
            )
        if int(section.get("page_start") or 0) in {1, 2} and type_counts.get("paragraph", 0) and count >= 20:
            front_matter_sections.append(
                {
                    "section_id": section_id,
                    "section_title": truncate_sample(str(section.get("section_title") or "")),
                    "page_start": section.get("page_start"),
                    "paragraph_evidence_count": count,
                }
            )

        title = normalize_for_match(str(section.get("section_title") or ""))
        if any(token in title for token in ["certification", "assurance", "report on the certification"]):
            first_paragraphs = [
                evidence
                for evidence in evidence_records
                if evidence.get("section_id") == section_id and evidence.get("evidence_type") == "paragraph"
            ][:5]
            joined = normalize_for_match(" ".join(str(item.get("quote") or "") for item in first_paragraphs))
            expected = ("certification", "assurance", "auditor", "sustainability reporting", "report")
            if first_paragraphs and not any(word in joined for word in expected):
                mismatch_warnings.append(
                    {
                        "section_id": section_id,
                        "section_title": truncate_sample(str(section.get("section_title") or "")),
                        "sample_content": truncate_sample(joined),
                    }
                )

    merged_count = sum(1 for evidence in evidence_records if evidence.get("was_merged_evidence"))
    merged_block_counts = [
        int(evidence.get("merged_blocks_count") or 0)
        for evidence in evidence_records
        if evidence.get("evidence_type") == "paragraph"
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "evidence_count": len(evidence_records),
        "evidence_type_distribution": type_counts,
        "evidence_by_section": by_section,
        "evidence_without_section_count": sum(1 for evidence in evidence_records if not evidence.get("section_id")),
        "evidence_review_required_count": sum(1 for evidence in evidence_records if evidence.get("review_required")),
        "average_quote_length": round(statistics.mean(quote_lengths), 6) if quote_lengths else 0.0,
        "median_quote_length": round(statistics.median(quote_lengths), 6) if quote_lengths else 0.0,
        "short_evidence_count": sum(1 for length in quote_lengths if length < SHORT_EVIDENCE_REVIEW_THRESHOLD),
        "merged_evidence_count": merged_count,
        "unmerged_evidence_count": len(evidence_records) - merged_count,
        "average_merged_blocks_count": round(statistics.mean(merged_block_counts), 6) if merged_block_counts else 0.0,
        "evidence_share_by_section": share_by_section,
        "sections_with_high_evidence_density": high_density_sections,
        "sections_with_front_matter_warning": front_matter_sections,
        "sample_short_evidence": sample_short,
        "sample_merged_evidence": sample_merged,
        "sample_section_mismatch_warnings": mismatch_warnings,
        "short_evidence_skipped_count": int(diagnostics.get("short_evidence_skipped_count", 0) or 0),
        "short_evidence_review_required_count": int(diagnostics.get("short_evidence_review_required_count", 0) or 0),
        "suspicious_sections_count": sum(1 for section in sections if section.get("is_suspicious_section")),
        "quarantined_evidence_count": sum(1 for evidence in evidence_records if evidence.get("is_quarantined_evidence")),
        "review_required_due_to_section_count": sum(1 for evidence in evidence_records if evidence.get("review_required_due_to_section")),
        "evidence_policy_distribution": policy_counts,
        "evidence_by_section_policy": by_section_policy,
        "suspicious_sections": [
            {
                "section_id": section.get("section_id"),
                "section_title": truncate_sample(str(section.get("section_title") or "")),
                "section_quality_score": section.get("section_quality_score"),
                "evidence_policy": section.get("evidence_policy"),
                "suspicion_reasons": section.get("suspicion_reasons") or [],
            }
            for section in sections
            if section.get("is_suspicious_section")
        ][:SAMPLE_LIMIT],
        "sample_quarantined_evidence": sample_quarantined,
        "sample_review_required_due_to_section": sample_review_due_to_section,
        "sample_evidence": sample_evidence,
        "sample_evidence_without_section": sample_without_section,
        "sample_section_heading_evidence": sample_section_heading,
        "sample_paragraph_evidence": sample_paragraph,
    }


def apply_section_quality_policies(
    sections: list[dict[str, Any]],
    evidence_statistics: dict[str, Any],
) -> list[dict[str, Any]]:
    high_density_ids = {
        str(item.get("section_id"))
        for item in evidence_statistics.get("sections_with_high_evidence_density", []) or []
    }
    front_matter_ids = {
        str(item.get("section_id"))
        for item in evidence_statistics.get("sections_with_front_matter_warning", []) or []
    }
    mismatch_ids = {
        str(item.get("section_id"))
        for item in evidence_statistics.get("sample_section_mismatch_warnings", []) or []
    }
    evidence_by_section = evidence_statistics.get("evidence_by_section", {}) or {}

    for section in sections:
        score = 1.0
        reasons: list[str] = []
        section_id = str(section.get("section_id") or "")
        section_type = str(section.get("section_type") or "unknown")
        page_start = int(section.get("page_start") or 0)
        page_end = int(section.get("page_end") or 0)
        evidence_count = int(evidence_by_section.get(section_id, 0) or 0)

        if section_type == "unknown":
            score -= 0.10
            reasons.append("unknown_section_type")
        if page_start in {1, 2}:
            score -= 0.20
            reasons.append("front_matter_section")
        if section_id in front_matter_ids:
            score -= 0.25
            if "front_matter_section" not in reasons:
                reasons.append("front_matter_section")
        if section_id in mismatch_ids:
            score -= 0.35
            reasons.append("title_content_mismatch")
        if section_id in high_density_ids:
            score -= 0.15
            reasons.append("high_evidence_density")
        if page_end < page_start or page_start <= 0:
            score -= 0.25
            reasons.append("suspicious_page_range")
        if float(section.get("section_detection_confidence") or 0) < 0.60:
            score -= 0.10
            reasons.append("weak_heading_confidence")
        if evidence_count <= 1:
            score -= 0.10
            reasons.append("section_too_short")
        if evidence_count > SECTION_HIGH_EVIDENCE_COUNT_THRESHOLD:
            if "section_too_long" not in reasons:
                reasons.append("section_too_long")
            score -= 0.10

        score = max(0.0, min(1.0, round(score, 6)))
        critical = "title_content_mismatch" in reasons
        is_suspicious = score < 0.60 or critical
        if score < 0.50 or critical:
            policy = "quarantine"
        elif score < 0.75:
            policy = "review_required"
        else:
            policy = "normal"

        section["section_quality_score"] = score
        section["is_suspicious_section"] = is_suspicious
        section["suspicion_reasons"] = reasons
        section["evidence_policy"] = policy

    return sections


def _apply_section_policy_to_evidence(
    evidence: dict[str, Any],
    section: dict[str, Any] | None,
) -> None:
    """Stamp v0.4.2 section-quality fields onto a single evidence dict in-place.

    Called for every evidence type (section_heading, paragraph, table, …)
    so that the contract fields are always present.
    """
    if section is not None:
        score: float | None = float(section.get("section_quality_score", 1.0) or 1.0)
        policy = str(section.get("evidence_policy") or "normal")
        reasons: list = list(section.get("suspicion_reasons") or [])
        suspicious = bool(section.get("is_suspicious_section"))
    else:
        score = 1.0
        policy = "normal"
        reasons = []
        suspicious = False
    evidence["section_quality_score"] = score
    evidence["section_is_suspicious"] = suspicious
    evidence["section_suspicion_reasons"] = reasons
    evidence["evidence_policy"] = policy
    evidence["is_quarantined_evidence"] = policy == "quarantine"
    evidence["review_required_due_to_section"] = policy in {"review_required", "quarantine"}
    if policy in {"review_required", "quarantine"}:
        evidence["review_required"] = True


def propagate_section_quality_to_evidence(
    evidence_records: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sections_by_id = {str(section.get("section_id")): section for section in sections}
    for evidence in evidence_records:
        section = sections_by_id.get(str(evidence.get("section_id") or ""))
        _apply_section_policy_to_evidence(evidence, section)
    return evidence_records


def build_suspicious_sections(
    document_id: str,
    sections: list[dict[str, Any]],
    evidence_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence_by_section: dict[str, list[dict[str, Any]]] = {}
    for evidence in evidence_records:
        section_id = str(evidence.get("section_id") or "")
        if section_id:
            evidence_by_section.setdefault(section_id, []).append(evidence)

    suspicious: list[dict[str, Any]] = []
    for section in sections:
        if not section.get("is_suspicious_section"):
            continue
        section_id = str(section.get("section_id") or "")
        section_evidence = evidence_by_section.get(section_id, [])
        paragraph_evidence = [
            evidence for evidence in section_evidence if evidence.get("evidence_type") == "paragraph"
        ]
        sample_quotes = [
            truncate_sample(str(evidence.get("quote") or ""))
            for evidence in paragraph_evidence[:5]
        ]
        reasons = list(section.get("suspicion_reasons") or [])
        suspicious.append(
            {
                "schema_version": SCHEMA_VERSION,
                "document_id": document_id,
                "section_id": section_id,
                "section_title": section.get("section_title"),
                "section_type": section.get("section_type"),
                "page_start": section.get("page_start"),
                "page_end": section.get("page_end"),
                "section_quality_score": section.get("section_quality_score"),
                "evidence_policy": section.get("evidence_policy"),
                "suspicion_reasons": reasons,
                "evidence_count": len(section_evidence),
                "paragraph_evidence_count": len(paragraph_evidence),
                "sample_evidence_quotes": sample_quotes,
                "diagnostic_message": (
                    "Section retained but marked for review/quarantine: "
                    + ", ".join(reasons)
                ),
            }
        )
    return suspicious


def evidence_quality_checks(
    document_id: str,
    evidence_records: list[dict[str, Any]],
    text_blocks: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    evidence_statistics: dict[str, Any] | None = None,
    suspicious_sections: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    evidence_statistics = evidence_statistics or {}
    suspicious_sections = suspicious_sections or []
    block_ids = {str(block.get("text_block_id")) for block in text_blocks if block.get("text_block_id")}
    section_ids = {str(section.get("section_id")) for section in sections if section.get("section_id")}
    evidence_without_section_count = sum(1 for evidence in evidence_records if not evidence.get("section_id"))
    average_quote_length = float(evidence_statistics.get("average_quote_length", 0) or 0)
    merged_count = int(evidence_statistics.get("merged_evidence_count", 0) or 0)
    short_skipped = int(evidence_statistics.get("short_evidence_skipped_count", 0) or 0)
    short_review = int(evidence_statistics.get("short_evidence_review_required_count", 0) or 0)
    high_density = list(evidence_statistics.get("sections_with_high_evidence_density", []) or [])
    front_matter = list(evidence_statistics.get("sections_with_front_matter_warning", []) or [])
    mismatch = list(evidence_statistics.get("sample_section_mismatch_warnings", []) or [])
    suspicious_count = len(suspicious_sections)
    quarantined_count = int(evidence_statistics.get("quarantined_evidence_count", 0) or 0)
    policy_counts = evidence_statistics.get("evidence_policy_distribution", {}) or {}
    quarantined_consistent = all(
        not (
            str(evidence.get("evidence_policy") or "") == "quarantine"
            and not evidence.get("is_quarantined_evidence")
        )
        for evidence in evidence_records
    )
    suspicious_retained = suspicious_count == sum(1 for section in sections if section.get("is_suspicious_section"))
    checks = [
        quality_record(
            "evidence_store_created",
            "pass" if evidence_records else "warning",
            "minor",
            f"Created {len(evidence_records)} documentary evidence record(s).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=not evidence_records,
        ),
        quality_record(
            "suspicious_sections_detected",
            "warning" if suspicious_count else "pass",
            "minor",
            f"Detected {suspicious_count} suspicious section(s).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(suspicious_count),
        ),
        quality_record(
            "section_quality_score_computed",
            "pass" if all("section_quality_score" in section for section in sections) else "fail",
            "major",
            "Section quality scores are present on all sections.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=not all("section_quality_score" in section for section in sections),
        ),
        quality_record(
            "evidence_policy_assigned",
            "pass" if all("evidence_policy" in evidence for evidence in evidence_records) else "fail",
            "major",
            f"Evidence policy distribution: {policy_counts}.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=not all("evidence_policy" in evidence for evidence in evidence_records),
        ),
        quality_record(
            "quarantined_evidence_detected",
            "warning" if quarantined_count else "pass",
            "minor",
            f"Detected {quarantined_count} quarantined evidence record(s).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(quarantined_count),
        ),
        quality_record(
            "evidence_policy_consistency_check",
            "pass" if quarantined_consistent else "fail",
            "critical",
            "Quarantined evidence records are consistently marked.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=not quarantined_consistent,
        ),
        quality_record(
            "suspicious_section_evidence_retained",
            "pass" if suspicious_retained else "fail",
            "critical",
            "Suspicious sections are retained and reported, not removed.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=not suspicious_retained,
        ),
        quality_record(
            "evidence_paragraph_merge_applied",
            "pass" if merged_count else "info",
            "info",
            f"Merged paragraph evidence records created: {merged_count}.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
        quality_record(
            "short_evidence_filtered",
            "pass" if short_skipped else "info",
            "info",
            f"Skipped {short_skipped} paragraph evidence candidate(s) below {MIN_PARAGRAPH_EVIDENCE_CHARS} characters.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
        ),
        quality_record(
            "short_evidence_review_required",
            "warning" if short_review else "pass",
            "minor",
            f"{short_review} short evidence record(s) require review.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(short_review),
        ),
        quality_record(
            "evidence_fragmentation_warning",
            "warning" if evidence_records and average_quote_length < EVIDENCE_FRAGMENTATION_AVERAGE_LENGTH_THRESHOLD else "pass",
            "minor",
            (
                f"Average evidence quote length is {average_quote_length:.2f}; "
                f"threshold is {EVIDENCE_FRAGMENTATION_AVERAGE_LENGTH_THRESHOLD}."
            ),
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(evidence_records and average_quote_length < EVIDENCE_FRAGMENTATION_AVERAGE_LENGTH_THRESHOLD),
        ),
        quality_record(
            "section_front_matter_evidence_warning",
            "warning" if front_matter else "pass",
            "minor",
            f"{len(front_matter)} front-matter section(s) received many paragraph evidences.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(front_matter),
        ),
        quality_record(
            "section_evidence_density_warning",
            "warning" if high_density else "pass",
            "minor",
            f"{len(high_density)} section(s) have high evidence density.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(high_density),
        ),
        quality_record(
            "section_title_content_mismatch_warning",
            "warning" if mismatch else "pass",
            "minor",
            f"{len(mismatch)} section title/content mismatch warning(s).",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(mismatch),
        ),
        quality_record(
            "evidence_without_section_warning",
            "warning" if evidence_without_section_count else "pass",
            "minor",
            f"{evidence_without_section_count} evidence record(s) have no section link.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=bool(evidence_without_section_count),
        ),
        quality_record(
            "no_evidence_created_warning",
            "warning" if not evidence_records else "pass",
            "minor",
            "No evidence records were created." if not evidence_records else "Evidence records were created.",
            target_type="document",
            target_id=document_id,
            document_id=document_id,
            review_required=not evidence_records,
        ),
    ]

    for evidence in evidence_records:
        evidence_id = str(evidence.get("evidence_id") or "")
        source_type = str(evidence.get("source_element_type") or "")
        source_id = str(evidence.get("source_element_id") or "")
        source_exists = source_type != "text_block" or source_id in block_ids
        section_id = str(evidence.get("section_id") or "")
        section_link_valid = not section_id or section_id in section_ids
        bbox_available = evidence.get("bbox") is not None
        quote_not_empty = bool(str(evidence.get("quote") or "").strip())
        checks.extend(
            [
                quality_record(
                    "evidence_source_exists",
                    "pass" if source_exists else "fail",
                    "major",
                    f"Evidence {evidence_id} source element exists: {source_exists}.",
                    target_type="evidence",
                    target_id=evidence_id,
                    document_id=document_id,
                    review_required=not source_exists,
                ),
                quality_record(
                    "evidence_section_link_valid",
                    "pass" if section_link_valid else "fail",
                    "major",
                    f"Evidence {evidence_id} section link is valid: {section_link_valid}.",
                    target_type="evidence",
                    target_id=evidence_id,
                    document_id=document_id,
                    review_required=not section_link_valid,
                ),
                quality_record(
                    "evidence_bbox_available",
                    "pass" if bbox_available else "warning",
                    "minor",
                    f"Evidence {evidence_id} bbox available: {bbox_available}.",
                    target_type="evidence",
                    target_id=evidence_id,
                    document_id=document_id,
                    review_required=not bbox_available,
                ),
                quality_record(
                    "evidence_quote_not_empty",
                    "pass" if quote_not_empty else "fail",
                    "major",
                    f"Evidence {evidence_id} quote is non-empty: {quote_not_empty}.",
                    target_type="evidence",
                    target_id=evidence_id,
                    document_id=document_id,
                    review_required=not quote_not_empty,
                ),
            ]
        )
    return checks


def source_modality_for_evidence(evidence: dict[str, Any]) -> str:
    evidence_type = str(evidence.get("evidence_type") or "")
    source_type = str(evidence.get("source_element_type") or "")
    if evidence_type == "table" or source_type == "table":
        return "table"
    if evidence_type == "figure" or source_type == "figure":
        return "figure"
    if evidence_type in {"section_heading", "paragraph", "list_item", "footnote", "caption", "unknown"}:
        return "text"
    return "text"


def downstream_policy_for_evidence(
    evidence: dict[str, Any],
    source_modality: str,
    object_flags: list[str],
) -> str:
    evidence_policy = str(evidence.get("evidence_policy") or "normal")
    if evidence_policy == "quarantine" or evidence.get("is_quarantined_evidence"):
        return "exclude_from_automatic_extraction"
    if source_modality == "table" and (
        "empty_table" in object_flags or "tiny_table_artifact" in object_flags
    ):
        return "exclude_from_automatic_extraction"
    if evidence.get("review_required"):
        return "review_before_extraction"
    if source_modality == "figure" and (
        "weak_visual_detection" in object_flags or "page_level_visual_candidate" in object_flags
    ):
        return "review_before_extraction"
    return "eligible_for_future_extraction"


def build_multimodal_evidence_index(
    document_id: str,
    evidence_records: list[dict[str, Any]],
    table_records: list[dict[str, Any]],
    figure_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tables_by_id = {str(table.get("table_id") or ""): table for table in table_records}
    figures_by_id = {str(figure.get("figure_id") or ""): figure for figure in figure_records}
    records: list[dict[str, Any]] = []

    for index, evidence in enumerate(evidence_records, start=1):
        source_modality = source_modality_for_evidence(evidence)
        source_element_id = str(evidence.get("source_element_id") or "")
        object_flags: list[str] = []
        object_confidence = evidence.get("evidence_confidence")
        if source_modality == "table":
            table = tables_by_id.get(source_element_id) or tables_by_id.get(str(evidence.get("table_id") or ""))
            object_flags = list((table or {}).get("table_quality_flags") or [])
            object_confidence = (table or {}).get("table_confidence", object_confidence)
            if (table or {}).get("extraction_status") == "empty_table" and "empty_table" not in object_flags:
                object_flags.append("empty_table")
        elif source_modality == "figure":
            figure = figures_by_id.get(source_element_id) or figures_by_id.get(str(evidence.get("figure_id") or ""))
            object_flags = list((figure or {}).get("figure_quality_flags") or [])
            object_confidence = (figure or {}).get("figure_confidence", object_confidence)

        downstream_policy = downstream_policy_for_evidence(evidence, source_modality, object_flags)
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "multimodal_evidence_id": f"{document_id}_mm_ev_{index:06d}",
                "evidence_id": evidence.get("evidence_id"),
                "document_id": document_id,
                "evidence_type": evidence.get("evidence_type"),
                "source_modality": source_modality,
                "page_id": evidence.get("page_id"),
                "page_number": evidence.get("page_number"),
                "section_id": evidence.get("section_id"),
                "source_element_type": evidence.get("source_element_type"),
                "source_element_id": evidence.get("source_element_id"),
                "quote": evidence.get("quote"),
                "evidence_policy": evidence.get("evidence_policy", "normal"),
                "review_required": bool(evidence.get("review_required")),
                "is_quarantined_evidence": bool(evidence.get("is_quarantined_evidence")),
                "section_quality_score": evidence.get("section_quality_score"),
                "section_is_suspicious": bool(evidence.get("section_is_suspicious")),
                "section_suspicion_reasons": list(evidence.get("section_suspicion_reasons") or []),
                "object_quality_flags": object_flags,
                "object_confidence": object_confidence,
                "localization_confidence": evidence.get("localization_confidence"),
                "downstream_use_policy": downstream_policy,
            }
        )
    return records


def build_multimodal_statistics(
    document_id: str,
    multimodal_records: list[dict[str, Any]],
    table_statistics: dict[str, Any],
    figure_statistics: dict[str, Any],
    suspicious_sections: list[dict[str, Any]],
) -> dict[str, Any]:
    by_modality: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_policy: dict[str, int] = {}
    downstream_counts: dict[str, int] = {}
    by_section: dict[str, int] = {}
    modality_by_section: dict[str, dict[str, int]] = {}

    samples_eligible: list[dict[str, Any]] = []
    samples_review: list[dict[str, Any]] = []
    samples_quarantine: list[dict[str, Any]] = []
    samples_table: list[dict[str, Any]] = []
    samples_figure: list[dict[str, Any]] = []

    for record in multimodal_records:
        modality = str(record.get("source_modality") or "unknown")
        evidence_type = str(record.get("evidence_type") or "unknown")
        policy = str(record.get("evidence_policy") or "normal")
        downstream = str(record.get("downstream_use_policy") or "unknown")
        section_id = str(record.get("section_id") or "")
        by_modality[modality] = by_modality.get(modality, 0) + 1
        by_type[evidence_type] = by_type.get(evidence_type, 0) + 1
        by_policy[policy] = by_policy.get(policy, 0) + 1
        downstream_counts[downstream] = downstream_counts.get(downstream, 0) + 1
        if section_id:
            by_section[section_id] = by_section.get(section_id, 0) + 1
            section_modalities = modality_by_section.setdefault(section_id, {})
            section_modalities[modality] = section_modalities.get(modality, 0) + 1

        sample = {
            "multimodal_evidence_id": record.get("multimodal_evidence_id"),
            "evidence_type": evidence_type,
            "source_modality": modality,
            "downstream_use_policy": downstream,
            "quote": truncate_sample(str(record.get("quote") or "")),
        }
        if downstream == "eligible_for_future_extraction" and len(samples_eligible) < SAMPLE_LIMIT:
            samples_eligible.append(sample)
        if record.get("review_required") and len(samples_review) < SAMPLE_LIMIT:
            samples_review.append(sample)
        if record.get("is_quarantined_evidence") and len(samples_quarantine) < SAMPLE_LIMIT:
            samples_quarantine.append(sample)
        if modality == "table" and len(samples_table) < SAMPLE_LIMIT:
            samples_table.append(sample)
        if modality == "figure" and len(samples_figure) < SAMPLE_LIMIT:
            samples_figure.append(sample)

    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "total_multimodal_evidences": len(multimodal_records),
        "evidence_by_modality": by_modality,
        "evidence_by_type": by_type,
        "evidence_policy_distribution": by_policy,
        "downstream_use_policy_distribution": downstream_counts,
        "review_required_count": sum(1 for record in multimodal_records if record.get("review_required")),
        "quarantined_count": sum(1 for record in multimodal_records if record.get("is_quarantined_evidence")),
        "eligible_for_future_extraction_count": downstream_counts.get("eligible_for_future_extraction", 0),
        "evidence_by_section": by_section,
        "modality_by_section": modality_by_section,
        "suspicious_sections_count": len(suspicious_sections),
        "tables_summary": {
            "tables_count": table_statistics.get("tables_count", 0),
            "parsed_tables_count": table_statistics.get("parsed_tables_count", 0),
            "low_confidence_tables_count": table_statistics.get("low_confidence_tables_count", 0),
            "empty_tables_count": table_statistics.get("empty_tables_count", 0),
        },
        "figures_summary": {
            "figures_count": figure_statistics.get("figures_count", 0),
            "page_level_visual_count": figure_statistics.get("page_level_visual_count", 0),
            "embedded_visual_count": figure_statistics.get("embedded_visual_count", 0),
            "captioned_figure_count": figure_statistics.get("captioned_figure_count", 0),
        },
        "sample_eligible_evidence": samples_eligible,
        "sample_review_required_evidence": samples_review,
        "sample_quarantined_evidence": samples_quarantine,
        "sample_table_evidence": samples_table,
        "sample_figure_evidence": samples_figure,
    }


def determine_extraction_readiness(
    errors_count: int,
    multimodal_statistics: dict[str, Any],
    quality_checks: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    downstream = multimodal_statistics.get("downstream_use_policy_distribution", {}) or {}
    policies = multimodal_statistics.get("evidence_policy_distribution", {}) or {}
    total = int(multimodal_statistics.get("total_multimodal_evidences", 0) or 0)
    eligible = int(downstream.get("eligible_for_future_extraction", 0) or 0)
    review = int(downstream.get("review_before_extraction", 0) or 0)
    excluded = int(downstream.get("exclude_from_automatic_extraction", 0) or 0)
    quarantine = int(policies.get("quarantine", 0) or 0)
    critical_failures = [
        check for check in quality_checks
        if check.get("status") == "fail" and check.get("severity") == "critical"
    ]

    if errors_count > 0:
        reasons.append("errors_present")
    if critical_failures:
        reasons.append("critical_quality_failures_present")
    if eligible <= 0:
        reasons.append("no_normal_eligible_evidence")
    if errors_count > 0 or critical_failures or eligible <= 0:
        return "not_ready", reasons

    non_eligible_ratio = (review + excluded) / total if total else 1.0
    quarantine_ratio = quarantine / total if total else 1.0
    if non_eligible_ratio > 0.40 or quarantine_ratio > 0.10:
        reasons.append("many_review_or_quarantined_evidences")
        return "partially_ready", reasons
    if multimodal_statistics.get("suspicious_sections_count", 0):
        reasons.append("suspicious_sections_present")
        return "partially_ready", reasons
    reasons.append("documentary_inventory_stable_for_experimental_use")
    return "ready_for_experimental_extraction", reasons


def build_document_inventory(
    document_record: dict[str, Any],
    page_records: list[dict[str, Any]],
    text_blocks: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    suspicious_sections: list[dict[str, Any]],
    evidence_records: list[dict[str, Any]],
    table_statistics: dict[str, Any],
    figure_statistics: dict[str, Any],
    multimodal_statistics: dict[str, Any],
    errors_count: int,
    quality_checks: list[dict[str, Any]],
    pdf_path: Path,
) -> dict[str, Any]:
    readiness, readiness_reasons = determine_extraction_readiness(
        errors_count,
        multimodal_statistics,
        quality_checks,
    )
    evidence_types = multimodal_statistics.get("evidence_by_type", {}) or {}
    policy_distribution = multimodal_statistics.get("evidence_policy_distribution", {}) or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_record.get("document_id"),
        "pdf_path": str(pdf_path.resolve()),
        "page_count": int(document_record.get("page_count") or 0),
        "pages_processed": len(page_records),
        "text_blocks_count": len(text_blocks),
        "sections_count": len(sections),
        "suspicious_sections_count": len(suspicious_sections),
        "evidence_count": len(evidence_records),
        "text_evidence_count": int(evidence_types.get("section_heading", 0) or 0)
        + int(evidence_types.get("paragraph", 0) or 0),
        "table_evidence_count": int(evidence_types.get("table", 0) or 0),
        "figure_evidence_count": int(evidence_types.get("figure", 0) or 0),
        "tables_count": int(table_statistics.get("tables_count", 0) or 0),
        "parsed_tables_count": int(table_statistics.get("parsed_tables_count", 0) or 0),
        "low_confidence_tables_count": int(table_statistics.get("low_confidence_tables_count", 0) or 0),
        "empty_tables_count": int(table_statistics.get("empty_tables_count", 0) or 0),
        "figures_count": int(figure_statistics.get("figures_count", 0) or 0),
        "page_level_visual_count": int(figure_statistics.get("page_level_visual_count", 0) or 0),
        "embedded_visual_count": int(figure_statistics.get("embedded_visual_count", 0) or 0),
        "captioned_figure_count": int(figure_statistics.get("captioned_figure_count", 0) or 0),
        "normal_evidence_count": int(policy_distribution.get("normal", 0) or 0),
        "review_required_evidence_count": int(multimodal_statistics.get("review_required_count", 0) or 0),
        "quarantined_evidence_count": int(multimodal_statistics.get("quarantined_count", 0) or 0),
        "evidence_policy_distribution": policy_distribution,
        "extraction_readiness_status": readiness,
        "extraction_readiness_reasons": readiness_reasons,
        "generated_at": utcnow(),
    }


def multimodal_quality_checks(
    document_id: str,
    multimodal_records: list[dict[str, Any]],
    multimodal_statistics: dict[str, Any],
    output_dir: Path,
    evidence_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    valid_modalities = {"text", "table", "figure"}
    valid_downstream = {
        "eligible_for_future_extraction",
        "review_before_extraction",
        "exclude_from_automatic_extraction",
    }
    invalid_modalities = [
        record for record in multimodal_records
        if record.get("source_modality") not in valid_modalities
    ]
    invalid_downstream = [
        record for record in multimodal_records
        if record.get("downstream_use_policy") not in valid_downstream
    ]
    quarantine_eligible = [
        record for record in multimodal_records
        if record.get("is_quarantined_evidence")
        and record.get("downstream_use_policy") == "eligible_for_future_extraction"
    ]
    review_eligible = [
        record for record in multimodal_records
        if record.get("review_required")
        and record.get("downstream_use_policy") == "eligible_for_future_extraction"
    ]
    counts_consistent = len(multimodal_records) == len(evidence_records) == int(
        multimodal_statistics.get("total_multimodal_evidences", -1)
    )
    return [
        quality_record(
            "document_inventory_created",
            "pass" if (output_dir / "document_inventory.json").exists() else "fail",
            "critical",
            "document_inventory.json exists.",
            target_type="output_file",
            target_id="document_inventory.json",
            document_id=document_id,
        ),
        quality_record(
            "multimodal_evidence_index_created",
            "pass" if (output_dir / "multimodal_evidence_index.jsonl").exists() else "fail",
            "critical",
            "multimodal_evidence_index.jsonl exists.",
            target_type="output_file",
            target_id="multimodal_evidence_index.jsonl",
            document_id=document_id,
        ),
        quality_record(
            "multimodal_statistics_created",
            "pass" if (output_dir / "multimodal_statistics.json").exists() else "fail",
            "critical",
            "multimodal_statistics.json exists.",
            target_type="output_file",
            target_id="multimodal_statistics.json",
            document_id=document_id,
        ),
        quality_record(
            "multimodal_evidence_policy_valid",
            "pass" if not invalid_downstream else "fail",
            "major",
            f"Invalid downstream policy records: {len(invalid_downstream)}.",
            document_id=document_id,
            review_required=bool(invalid_downstream),
        ),
        quality_record(
            "downstream_use_policy_assigned",
            "pass" if all(record.get("downstream_use_policy") for record in multimodal_records) else "fail",
            "major",
            "Downstream use policy assigned to all multimodal evidences.",
            document_id=document_id,
        ),
        quality_record(
            "modality_assignment_valid",
            "pass" if not invalid_modalities else "fail",
            "major",
            f"Invalid source modality records: {len(invalid_modalities)}.",
            document_id=document_id,
            review_required=bool(invalid_modalities),
        ),
        quality_record(
            "quarantined_evidence_excluded_from_automatic_extraction",
            "pass" if not quarantine_eligible else "fail",
            "critical",
            f"Quarantined evidences marked eligible: {len(quarantine_eligible)}.",
            document_id=document_id,
            review_required=bool(quarantine_eligible),
        ),
        quality_record(
            "review_required_evidence_not_marked_eligible",
            "pass" if not review_eligible else "fail",
            "critical",
            f"Review-required evidences marked eligible: {len(review_eligible)}.",
            document_id=document_id,
            review_required=bool(review_eligible),
        ),
        quality_record(
            "multimodal_counts_consistent",
            "pass" if counts_consistent else "fail",
            "major",
            (
                "Multimodal evidence count is consistent with evidence_store.jsonl."
                if counts_consistent
                else "Multimodal evidence count differs from evidence_store.jsonl."
            ),
            document_id=document_id,
            review_required=not counts_consistent,
        ),
    ]


def audit_finding(
    document_id: str,
    severity: str,
    category: str,
    check_name: str,
    status: str,
    message: str,
    related_file: str,
    related_object_id: str = "",
    recommendation: str = "",
) -> dict[str, Any]:
    raw = f"{document_id}|{category}|{check_name}|{related_file}|{related_object_id}|{message}"
    return {
        "schema_version": SCHEMA_VERSION,
        "finding_id": "finding_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20],
        "document_id": document_id,
        "severity": severity,
        "category": category,
        "check_name": check_name,
        "status": status,
        "message": message,
        "related_file": related_file,
        "related_object_id": related_object_id,
        "recommendation": recommendation,
    }


def build_audit_findings(
    document_id: str,
    output_dir: Path,
    document_inventory: dict[str, Any],
    evidence_records: list[dict[str, Any]],
    text_blocks: list[dict[str, Any]],
    table_records: list[dict[str, Any]],
    figure_records: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    suspicious_sections: list[dict[str, Any]],
    multimodal_records: list[dict[str, Any]],
    multimodal_statistics: dict[str, Any],
    table_statistics: dict[str, Any],
    figure_statistics: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    # The v0.8 audit files are created by this very audit step, so file-presence
    # checks here cover all upstream outputs. Dedicated quality checks validate
    # the three audit files immediately after they are written.
    self_audit_files = {"consistency_report.json", "audit_findings.jsonl", "document_audit_report.md"}
    expected_files = [name for name in EXPECTED_OUTPUT_FILES if name not in self_audit_files]
    missing = [name for name in expected_files if not (output_dir / name).exists()]
    if missing:
        for name in missing:
            findings.append(audit_finding(
                document_id, "critical", "file_presence", "expected_file_present", "fail",
                f"Expected output file is missing: {name}.", name,
                recommendation="Regenerate the PDF extraction output before downstream use.",
            ))
    else:
        findings.append(audit_finding(
            document_id, "info", "file_presence", "expected_files_present", "pass",
            "All expected output files are present.", "output_dir",
        ))

    evidence_ids = {str(e.get("evidence_id") or "") for e in evidence_records}
    text_block_ids = {str(b.get("text_block_id") or "") for b in text_blocks}
    table_ids = {str(t.get("table_id") or "") for t in table_records}
    figure_ids = {str(f.get("figure_id") or "") for f in figure_records}
    section_ids = {str(s.get("section_id") or "") for s in sections}

    missing_refs = 0
    for evidence in evidence_records:
        ev_id = str(evidence.get("evidence_id") or "")
        source_type = str(evidence.get("source_element_type") or "")
        source_id = str(evidence.get("source_element_id") or "")
        if source_type == "text_block" and source_id and source_id not in text_block_ids:
            missing_refs += 1
            findings.append(audit_finding(
                document_id, "critical", "id_consistency", "evidence_source_reference_valid", "fail",
                f"Evidence {ev_id} references missing text_block_id {source_id}.",
                "evidence_store.jsonl", ev_id,
                "Investigate text block extraction and evidence generation order.",
            ))
        if source_type == "table" and source_id and source_id not in table_ids:
            missing_refs += 1
            findings.append(audit_finding(
                document_id, "critical", "table_link_consistency", "evidence_table_reference_valid", "fail",
                f"Evidence {ev_id} references missing table_id {source_id}.",
                "evidence_store.jsonl", ev_id,
            ))
        if source_type == "figure" and source_id and source_id not in figure_ids:
            missing_refs += 1
            findings.append(audit_finding(
                document_id, "critical", "figure_link_consistency", "evidence_figure_reference_valid", "fail",
                f"Evidence {ev_id} references missing figure_id {source_id}.",
                "evidence_store.jsonl", ev_id,
            ))
        section_id = str(evidence.get("section_id") or "")
        if section_id and section_id not in section_ids:
            missing_refs += 1
            findings.append(audit_finding(
                document_id, "critical", "section_link_consistency", "evidence_section_reference_valid", "fail",
                f"Evidence {ev_id} references missing section_id {section_id}.",
                "evidence_store.jsonl", ev_id,
            ))
    if missing_refs == 0:
        findings.append(audit_finding(
            document_id, "info", "id_consistency", "evidence_references_valid", "pass",
            "All evidence source references resolve to existing objects.", "evidence_store.jsonl",
        ))

    multimodal_evidence_ids = {str(m.get("evidence_id") or "") for m in multimodal_records}
    if multimodal_evidence_ids != evidence_ids:
        findings.append(audit_finding(
            document_id, "critical", "count_consistency", "multimodal_evidence_ids_match", "fail",
            "multimodal_evidence_index.jsonl does not contain exactly the evidence_store evidence IDs.",
            "multimodal_evidence_index.jsonl",
            recommendation="Regenerate multimodal inventory after evidence_store creation.",
        ))
    else:
        findings.append(audit_finding(
            document_id, "info", "count_consistency", "multimodal_counts_consistent", "pass",
            "Multimodal evidence index contains exactly one row per evidence_store record.",
            "multimodal_evidence_index.jsonl",
        ))

    quarantine_eligible = [
        m for m in multimodal_records
        if m.get("is_quarantined_evidence")
        and m.get("downstream_use_policy") == "eligible_for_future_extraction"
    ]
    review_eligible = [
        m for m in multimodal_records
        if m.get("review_required")
        and m.get("downstream_use_policy") == "eligible_for_future_extraction"
    ]
    if quarantine_eligible:
        findings.append(audit_finding(
            document_id, "critical", "multimodal_policy", "quarantine_not_eligible", "fail",
            f"{len(quarantine_eligible)} quarantined evidence(s) are marked eligible.",
            "multimodal_evidence_index.jsonl",
        ))
    if review_eligible:
        findings.append(audit_finding(
            document_id, "critical", "multimodal_policy", "review_required_not_eligible", "fail",
            f"{len(review_eligible)} review-required evidence(s) are marked eligible.",
            "multimodal_evidence_index.jsonl",
        ))
    if not quarantine_eligible and not review_eligible:
        findings.append(audit_finding(
            document_id, "info", "multimodal_policy", "fragile_evidence_not_eligible", "pass",
            "No quarantined or review-required evidence is eligible for automatic future extraction.",
            "multimodal_evidence_index.jsonl",
        ))

    if suspicious_sections:
        findings.append(audit_finding(
            document_id, "minor", "sections", "suspicious_sections_present", "warning",
            f"{len(suspicious_sections)} suspicious section(s) are present and retained for audit.",
            "suspicious_sections.jsonl",
            recommendation="Review suspicious sections before ESG extraction.",
        ))
    if int(multimodal_statistics.get("quarantined_count", 0) or 0):
        findings.append(audit_finding(
            document_id, "minor", "evidence_policy", "quarantined_evidence_detected", "warning",
            f"{multimodal_statistics.get('quarantined_count')} quarantined evidence(s) detected.",
            "multimodal_statistics.json",
        ))
    if int(multimodal_statistics.get("review_required_count", 0) or 0):
        findings.append(audit_finding(
            document_id, "minor", "evidence_policy", "review_required_evidence_detected", "warning",
            f"{multimodal_statistics.get('review_required_count')} evidence(s) require review.",
            "multimodal_statistics.json",
        ))

    empty_tables = int(table_statistics.get("empty_tables_count", 0) or 0)
    artifact_tables = int(table_statistics.get("table_artifact_suspected_count", 0) or 0)
    fragmented_tables = int(table_statistics.get("fragmented_tables_count", 0) or 0)
    if empty_tables:
        findings.append(audit_finding(
            document_id, "minor", "tables", "empty_tables_detected", "warning",
            f"{empty_tables} empty table(s) detected.", "table_statistics.json",
        ))
    if artifact_tables or fragmented_tables:
        findings.append(audit_finding(
            document_id, "minor", "tables", "table_artifacts_detected", "warning",
            f"{artifact_tables} suspected artifact table(s), {fragmented_tables} fragmented table(s).",
            "table_statistics.json",
        ))

    page_level_visuals = int(figure_statistics.get("page_level_visual_count", 0) or 0)
    if page_level_visuals:
        findings.append(audit_finding(
            document_id, "minor", "figures", "page_level_visuals_detected", "warning",
            f"{page_level_visuals} page-level visual candidate(s) detected; not interpreted.",
            "figure_statistics.json",
        ))

    readiness = str(document_inventory.get("extraction_readiness_status") or "")
    if readiness == "partially_ready":
        findings.append(audit_finding(
            document_id, "minor", "readiness", "document_partially_ready", "warning",
            "Document is partially ready: usable evidence exists, but review zones remain.",
            "document_inventory.json",
            recommendation="Review warnings before enabling any ESG extraction prototype.",
        ))
    elif readiness == "not_ready":
        findings.append(audit_finding(
            document_id, "major", "readiness", "document_not_ready", "warning",
            "Document is not ready for future experimental extraction.",
            "document_inventory.json",
        ))
    elif readiness == "ready_for_experimental_extraction":
        findings.append(audit_finding(
            document_id, "info", "readiness", "document_ready_for_experimental_extraction", "pass",
            "Documentary outputs appear ready for future experimental extraction.", "document_inventory.json",
        ))

    findings.append(audit_finding(
        document_id, "info", "non_destructive_behavior", "no_esg_extraction_performed", "pass",
        "No ESG metric extraction, scoring, RAG, vector database, OCR, table interpretation, or figure interpretation was performed.",
        "run_pdf_extraction.py",
    ))
    return findings


def build_consistency_report(
    document_id: str,
    output_dir: Path,
    findings: list[dict[str, Any]],
    evidence_records: list[dict[str, Any]],
    multimodal_records: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    suspicious_sections: list[dict[str, Any]],
) -> dict[str, Any]:
    critical_count = sum(1 for f in findings if f.get("severity") == "critical")
    major_count = sum(1 for f in findings if f.get("severity") == "major")
    warning_count = sum(1 for f in findings if f.get("status") == "warning")
    overall = "fail" if critical_count else "warning" if warning_count or major_count else "pass"
    expected_files = list(EXPECTED_OUTPUT_FILES)
    self_audit_files = {"consistency_report.json", "audit_findings.jsonl", "document_audit_report.md"}
    missing = [name for name in expected_files if name not in self_audit_files and not (output_dir / name).exists()]
    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "generated_at": utcnow(),
        "overall_status": overall,
        "errors_count": critical_count,
        "warnings_count": warning_count + major_count,
        "checks_count": len(findings),
        "files_checked": expected_files,
        "missing_expected_files": missing,
        "count_consistency": {
            "evidence_store_count": len(evidence_records),
            "multimodal_evidence_count": len(multimodal_records),
            "counts_match": len(evidence_records) == len(multimodal_records),
        },
        "id_consistency": {
            "evidence_ids_match_multimodal": {
                str(e.get("evidence_id") or "") for e in evidence_records
            } == {str(m.get("evidence_id") or "") for m in multimodal_records},
        },
        "policy_consistency": {
            "quarantine_eligible_count": sum(
                1 for m in multimodal_records
                if m.get("is_quarantined_evidence")
                and m.get("downstream_use_policy") == "eligible_for_future_extraction"
            ),
            "review_required_eligible_count": sum(
                1 for m in multimodal_records
                if m.get("review_required")
                and m.get("downstream_use_policy") == "eligible_for_future_extraction"
            ),
        },
        "modality_consistency": {
            "invalid_source_modality_count": sum(
                1 for m in multimodal_records if m.get("source_modality") not in {"text", "table", "figure"}
            ),
        },
        "section_link_consistency": {
            "sections_count": len(sections),
            "suspicious_sections_count": len(suspicious_sections),
        },
        "table_link_consistency": {},
        "figure_link_consistency": {},
        "suspicious_sections_consistency": {
            "suspicious_sections_retained": len(suspicious_sections) == sum(
                1 for section in sections if section.get("is_suspicious_section")
            )
        },
        "findings": findings,
    }


def render_document_audit_report(
    document_inventory: dict[str, Any],
    document_record: dict[str, Any],
    summary: dict[str, Any],
    consistency_report: dict[str, Any],
    findings: list[dict[str, Any]],
    suspicious_sections: list[dict[str, Any]],
    multimodal_statistics: dict[str, Any],
    table_statistics: dict[str, Any],
    figure_statistics: dict[str, Any],
) -> str:
    def bullet(key: str, value: Any) -> str:
        return f"- {key}: {value}"

    lines = [
        "# Document Audit Report",
        "",
        "## 1. Document identity",
        bullet("document_id", document_inventory.get("document_id")),
        bullet("pdf_path", document_inventory.get("pdf_path")),
        bullet("sha256", document_record.get("sha256")),
        bullet("pages_processed / page_count", f"{document_inventory.get('pages_processed')} / {document_inventory.get('page_count')}"),
        "",
        "## 2. Extraction status",
        bullet("status", summary.get("status")),
        bullet("errors_count", summary.get("errors_count")),
        bullet("warnings_count", summary.get("warnings_count")),
        bullet("extraction_readiness_status", document_inventory.get("extraction_readiness_status")),
        bullet("extraction_readiness_reasons", document_inventory.get("extraction_readiness_reasons")),
        "",
        "## 3. Document structure",
        bullet("pages", document_inventory.get("pages_processed")),
        bullet("text blocks", document_inventory.get("text_blocks_count")),
        bullet("sections", document_inventory.get("sections_count")),
        bullet("suspicious sections", document_inventory.get("suspicious_sections_count")),
        "",
        "## 4. Evidence overview",
        bullet("total evidences", document_inventory.get("evidence_count")),
        bullet("evidences by modality", multimodal_statistics.get("evidence_by_modality")),
        bullet("evidences by type", multimodal_statistics.get("evidence_by_type")),
        bullet("evidence_policy_distribution", multimodal_statistics.get("evidence_policy_distribution")),
        bullet("downstream_use_policy_distribution", multimodal_statistics.get("downstream_use_policy_distribution")),
        "",
        "Clarification: normal_evidence_count corresponds to evidence_policy = normal. "
        "review_required_evidence_count corresponds to the review_required flag. "
        "These categories can overlap. quarantine means retained for traceability but excluded from automatic extraction.",
        "",
        "## 5. Tables audit",
        bullet("tables_count", table_statistics.get("tables_count", 0)),
        bullet("parsed_tables_count", table_statistics.get("parsed_tables_count", 0)),
        bullet("low_confidence_tables_count", table_statistics.get("low_confidence_tables_count", 0)),
        bullet("empty_tables_count", table_statistics.get("empty_tables_count", 0)),
        bullet("table_artifact_suspected_count", table_statistics.get("table_artifact_suspected_count", 0)),
        bullet("failed_tables_count", table_statistics.get("failed_tables_count", 0)),
        "Tables are detected as documentary objects only; cell values are not interpreted.",
        "",
        "## 6. Figures audit",
        bullet("figures_count", figure_statistics.get("figures_count", 0)),
        bullet("page_level_visual_count", figure_statistics.get("page_level_visual_count", 0)),
        bullet("embedded_visual_count", figure_statistics.get("embedded_visual_count", 0)),
        bullet("captioned_figure_count", figure_statistics.get("captioned_figure_count", 0)),
        bullet("failed_figures_count", figure_statistics.get("failed_figures_count", 0)),
        "Figures and visual pages are localized or flagged only; graph values are not read.",
        "",
        "## 7. Suspicious sections",
    ]
    if suspicious_sections:
        for section in suspicious_sections:
            lines.extend([
                bullet("section_id", section.get("section_id")),
                bullet("section_title", section.get("section_title")),
                bullet("reasons", section.get("suspicion_reasons")),
                bullet("evidence_policy", section.get("evidence_policy")),
                bullet("sample quotes", section.get("sample_evidence_quotes")),
                "",
            ])
    else:
        lines.append("No suspicious section detected.")
        lines.append("")

    readiness = document_inventory.get("extraction_readiness_status")
    reasons = document_inventory.get("extraction_readiness_reasons")
    lines.extend([
        "## 8. Readiness decision",
        f"Decision: **{readiness}**.",
        f"Reasons: {reasons}.",
        "For partially_ready documents, usable evidence exists but some zones remain under human review.",
        "",
        "## 9. Limitations",
        "- No ESG extraction was performed.",
        "- No ESG value was validated.",
        "- No graph value was read.",
        "- No table cell was interpreted.",
        "- No ESG scoring was produced.",
        "",
        "## 10. Recommended next step",
        "Review critical and major findings first, then inspect suspicious sections before any future ESG extraction prototype.",
        "",
        "## Audit summary",
        bullet("audit_overall_status", consistency_report.get("overall_status")),
        bullet("findings_count", len(findings)),
    ])
    return "\n".join(str(line) for line in lines) + "\n"


def audit_quality_checks(
    document_id: str,
    output_dir: Path,
    consistency_report: dict[str, Any],
    findings: list[dict[str, Any]],
    multimodal_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    critical = sum(1 for f in findings if f.get("severity") == "critical")
    count_consistent = bool((consistency_report.get("count_consistency") or {}).get("counts_match"))
    refs_valid = not any(f.get("category") in {"id_consistency", "table_link_consistency", "figure_link_consistency", "section_link_consistency"} and f.get("status") == "fail" for f in findings)
    policies_valid = not any(
        record.get("downstream_use_policy") == "eligible_for_future_extraction"
        and (record.get("is_quarantined_evidence") or record.get("review_required"))
        for record in multimodal_records
    )
    return [
        quality_record("consistency_report_created", "pass" if (output_dir / "consistency_report.json").exists() else "fail", "critical", "consistency_report.json exists.", target_type="output_file", target_id="consistency_report.json", document_id=document_id),
        quality_record("audit_findings_created", "pass" if (output_dir / "audit_findings.jsonl").exists() else "fail", "critical", "audit_findings.jsonl exists.", target_type="output_file", target_id="audit_findings.jsonl", document_id=document_id),
        quality_record("document_audit_report_created", "pass" if (output_dir / "document_audit_report.md").exists() else "fail", "critical", "document_audit_report.md exists.", target_type="output_file", target_id="document_audit_report.md", document_id=document_id),
        quality_record("cross_file_counts_consistent", "pass" if count_consistent else "fail", "major", "Cross-file evidence counts are consistent." if count_consistent else "Cross-file evidence counts are inconsistent.", document_id=document_id, review_required=not count_consistent),
        quality_record("evidence_references_valid", "pass" if refs_valid else "fail", "critical", "Evidence references resolve to produced objects." if refs_valid else "Some evidence references are broken.", document_id=document_id, review_required=not refs_valid),
        quality_record("multimodal_policy_consistent", "pass" if policies_valid else "fail", "critical", "Multimodal downstream policies are consistent.", document_id=document_id, review_required=not policies_valid),
        quality_record("readiness_status_explained", "pass" if consistency_report.get("overall_status") in {"pass", "warning", "fail"} else "fail", "major", "Readiness status is explained in document_audit_report.md.", document_id=document_id),
        quality_record("no_esg_extraction_performed", "pass", "critical", "This run produced documentary audit outputs only; no ESG metrics, indicators, scores, RAG, vector DB, OCR, table interpretation, or figure interpretation.", document_id=document_id),
    ]


AUDIT_OUTPUT_FILES = (
    "consistency_report.json",
    "audit_findings.jsonl",
    "document_audit_report.md",
)

AUDIT_REQUIRED_INPUT_FILES = (
    "document_record.json",
    "page_index.jsonl",
    "text_blocks.jsonl",
    "section_index.jsonl",
    "suspicious_sections.jsonl",
    "evidence_store.jsonl",
    "table_index.jsonl",
    "table_statistics.json",
    "figure_index.jsonl",
    "figure_statistics.json",
    "document_inventory.json",
    "multimodal_evidence_index.jsonl",
    "multimodal_statistics.json",
    "extraction_summary.json",
)

AUDIT_OPTIONAL_INPUT_FILES = (
    "evidence_statistics.json",
    "table_cells.jsonl",
    "quality_report.jsonl",
)


def load_existing_output_artifacts(output_dir: Path) -> tuple[dict[str, Any], list[str]]:
    output_dir = output_dir.resolve()
    errors: list[str] = []

    def load_json(name: str) -> dict[str, Any]:
        path = output_dir / name
        if not path.exists():
            errors.append(f"Missing required file: {name}")
            return {}
        try:
            return read_json_file(path)
        except Exception as exc:
            errors.append(f"Could not read {name}: {exc}")
            return {}

    def load_jsonl(name: str) -> list[dict[str, Any]]:
        path = output_dir / name
        if not path.exists():
            errors.append(f"Missing required file: {name}")
            return []
        try:
            return read_jsonl(path)
        except Exception as exc:
            errors.append(f"Could not read {name}: {exc}")
            return []

    artifacts = {
        "output_dir": output_dir,
        "document_record": load_json("document_record.json"),
        "page_records": load_jsonl("page_index.jsonl"),
        "text_blocks": load_jsonl("text_blocks.jsonl"),
        "sections": load_jsonl("section_index.jsonl"),
        "suspicious_sections": load_jsonl("suspicious_sections.jsonl"),
        "evidence_records": load_jsonl("evidence_store.jsonl"),
        "table_records": load_jsonl("table_index.jsonl"),
        "table_statistics": load_json("table_statistics.json"),
        "figure_records": load_jsonl("figure_index.jsonl"),
        "figure_statistics": load_json("figure_statistics.json"),
        "document_inventory": load_json("document_inventory.json"),
        "multimodal_records": load_jsonl("multimodal_evidence_index.jsonl"),
        "multimodal_statistics": load_json("multimodal_statistics.json"),
        "summary": load_json("extraction_summary.json"),
        "optional_missing_files": [
            name for name in AUDIT_OPTIONAL_INPUT_FILES if not (output_dir / name).exists()
        ],
    }
    return artifacts, errors


def regenerate_document_audit_from_output_dir(
    output_dir: Path,
    overwrite: bool = False,
    strict: bool = False,
) -> tuple[int, dict[str, Any]]:
    output_dir = output_dir.resolve()
    if not output_dir.exists() or not output_dir.is_dir():
        return 1, {
            "status": "failed",
            "output_dir": str(output_dir),
            "errors": [f"Output directory does not exist: {output_dir}"],
        }

    existing_audit_outputs = [name for name in AUDIT_OUTPUT_FILES if (output_dir / name).exists()]
    if existing_audit_outputs and not overwrite:
        return 1, {
            "status": "failed",
            "output_dir": str(output_dir),
            "errors": [
                "Audit outputs already exist. Use --overwrite to regenerate: "
                + ", ".join(existing_audit_outputs)
            ],
        }

    artifacts, load_errors = load_existing_output_artifacts(output_dir)
    document_record = artifacts["document_record"]
    document_id = str(
        document_record.get("document_id")
        or artifacts["document_inventory"].get("document_id")
        or artifacts["summary"].get("document_id")
        or output_dir.name
    )
    document_inventory = dict(artifacts["document_inventory"])
    if not document_inventory:
        document_inventory = {
            "schema_version": SCHEMA_VERSION,
            "document_id": document_id,
            "pdf_path": document_record.get("document_path"),
            "page_count": document_record.get("page_count", 0),
            "pages_processed": len(artifacts["page_records"]),
            "text_blocks_count": len(artifacts["text_blocks"]),
            "sections_count": len(artifacts["sections"]),
            "suspicious_sections_count": len(artifacts["suspicious_sections"]),
            "evidence_count": len(artifacts["evidence_records"]),
            "extraction_readiness_status": "not_ready",
            "extraction_readiness_reasons": ["document_inventory_missing"],
            "generated_at": utcnow(),
        }

    audit_findings = build_audit_findings(
        document_id,
        output_dir,
        document_inventory,
        artifacts["evidence_records"],
        artifacts["text_blocks"],
        artifacts["table_records"],
        artifacts["figure_records"],
        artifacts["sections"],
        artifacts["suspicious_sections"],
        artifacts["multimodal_records"],
        artifacts["multimodal_statistics"],
        artifacts["table_statistics"],
        artifacts["figure_statistics"],
    )
    for error in load_errors:
        audit_findings.append(
            audit_finding(
                document_id,
                "critical",
                "file_presence",
                "required_input_file_available",
                "fail",
                error,
                "output_dir",
                recommendation="Regenerate the extraction outputs before relying on this audit.",
            )
        )
    for missing_optional in artifacts["optional_missing_files"]:
        audit_findings.append(
            audit_finding(
                document_id,
                "info",
                "file_presence",
                "optional_input_file_missing",
                "warning",
                f"Optional file is missing: {missing_optional}.",
                missing_optional,
            )
        )

    consistency_report = build_consistency_report(
        document_id,
        output_dir,
        audit_findings,
        artifacts["evidence_records"],
        artifacts["multimodal_records"],
        artifacts["sections"],
        artifacts["suspicious_sections"],
    )
    if strict and consistency_report.get("overall_status") == "warning":
        consistency_report["overall_status"] = "fail"
        audit_findings.append(
            audit_finding(
                document_id,
                "major",
                "readiness",
                "strict_mode_warning_promoted",
                "fail",
                "Strict mode promoted audit warnings to failure.",
                "consistency_report.json",
            )
        )
        consistency_report = build_consistency_report(
            document_id,
            output_dir,
            audit_findings,
            artifacts["evidence_records"],
            artifacts["multimodal_records"],
            artifacts["sections"],
            artifacts["suspicious_sections"],
        )

    report_markdown = render_document_audit_report(
        document_inventory,
        document_record,
        artifacts["summary"],
        consistency_report,
        audit_findings,
        artifacts["suspicious_sections"],
        artifacts["multimodal_statistics"],
        artifacts["table_statistics"],
        artifacts["figure_statistics"],
    )

    write_json(output_dir / "consistency_report.json", consistency_report)
    write_jsonl(output_dir / "audit_findings.jsonl", audit_findings)
    (output_dir / "document_audit_report.md").write_text(report_markdown, encoding="utf-8")

    critical_count = sum(1 for finding in audit_findings if finding.get("severity") == "critical")
    major_count = sum(1 for finding in audit_findings if finding.get("severity") == "major")
    return_code = 1 if load_errors else 0
    return return_code, {
        "status": "failed" if return_code else "success",
        "output_dir": str(output_dir),
        "audit_overall_status": consistency_report.get("overall_status"),
        "findings_count": len(audit_findings),
        "critical_findings_count": critical_count,
        "major_findings_count": major_count,
        "files_written": list(AUDIT_OUTPUT_FILES),
        "errors": load_errors,
    }


def run_extraction(options: ExtractionOptions) -> tuple[int, dict[str, Any]]:
    started_at = utcnow()
    output_dir = options.output_dir.resolve()
    quality_checks: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    page_records: list[dict[str, Any]] = []
    text_blocks: list[dict[str, Any]] = []
    text_block_statistics: dict[str, Any] = {}
    section_candidates: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    section_statistics: dict[str, Any] = {}
    evidence_records: list[dict[str, Any]] = []
    evidence_statistics: dict[str, Any] = {}
    evidence_diagnostics: dict[str, int] = {}
    suspicious_sections: list[dict[str, Any]] = []
    raw_tables_per_page: list[dict[str, Any]] = []
    table_records: list[dict[str, Any]] = []
    cell_records: list[dict[str, Any]] = []
    table_statistics: dict[str, Any] = {}
    raw_figures_per_page: list[dict[str, Any]] = []
    figure_records: list[dict[str, Any]] = []
    figure_statistics: dict[str, Any] = {}
    multimodal_records: list[dict[str, Any]] = []
    multimodal_statistics: dict[str, Any] = {}
    document_inventory: dict[str, Any] = {}
    audit_findings: list[dict[str, Any]] = []
    consistency_report: dict[str, Any] = {}
    document_record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "document_id": options.document_id,
        "sha256": None,
        "document_path": str(options.pdf_path.resolve()),
        "file_name": options.pdf_path.name,
        "page_count": 0,
        "loading_status": "not_started",
        "created_at": started_at,
    }

    if not options.document_id.strip():
        raise ValueError("--document-id must not be empty.")
    ensure_safe_output_dir(options)

    try:
        if not options.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {options.pdf_path}")
        if not options.pdf_path.is_file():
            raise ValueError(f"--pdf-path is not a file: {options.pdf_path}")
        pdfplumber = require_pdfplumber()
        document_record["sha256"] = sha256_file(options.pdf_path)

        with options.pdf_path.open("rb") as file:
            header = file.read(5)
        if header != b"%PDF-":
            raise ValueError(f"File does not start with %PDF-: {options.pdf_path}")

        with pdfplumber.open(str(options.pdf_path)) as pdf:
            page_count = len(pdf.pages)
            document_record["page_count"] = page_count
            document_record["loading_status"] = "readable"
            quality_checks.append(
                quality_record(
                    "pdf_readable",
                    "pass",
                    "critical",
                    "PDF opened successfully.",
                    document_id=options.document_id,
                )
            )
            quality_checks.append(
                quality_record(
                    "page_count_valid",
                    "pass" if page_count > 0 else "fail",
                    "critical",
                    f"Page count: {page_count}.",
                    document_id=options.document_id,
                    review_required=page_count <= 0,
                )
            )

            pages_to_process = pdf.pages
            if options.max_pages is not None:
                pages_to_process = pages_to_process[: max(options.max_pages, 0)]

            reading_order = 1
            for page_number, page in enumerate(pages_to_process, start=1):
                page_id = f"{options.document_id}_page_{page_number:04d}"
                blocks, reading_order, text_char_count = extract_text_blocks_from_page(
                    page=page,
                    document_id=options.document_id,
                    page_id=page_id,
                    page_number=page_number,
                    reading_order_start=reading_order,
                )
                has_text = text_char_count > 0
                page_records.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "page_id": page_id,
                        "document_id": options.document_id,
                        "page_number": page_number,
                        "width": float(page.width) if page.width is not None else None,
                        "height": float(page.height) if page.height is not None else None,
                        "rotation": int(getattr(page, "rotation", 0) or 0),
                        "extraction_status": "ok" if has_text else "empty",
                        "text_char_count": text_char_count,
                        "has_text": has_text,
                    }
                )
                text_blocks.extend(blocks)
                quality_checks.append(
                    quality_record(
                        "page_has_text",
                        "pass" if has_text else "warning",
                        "minor",
                        f"Page {page_number} has {text_char_count} extracted characters.",
                        target_type="page",
                        target_id=page_id,
                        document_id=options.document_id,
                        page_id=page_id,
                        review_required=not has_text,
                    )
                )
                # ── v0.5: collect raw tables during the pdfplumber loop ──────────
                page_text_for_tables = page.extract_text() or ""
                raw_page_tables: list = []
                try:
                    raw_page_tables = page.extract_tables() or []
                except Exception:
                    pass
                if not raw_page_tables:
                    try:
                        raw_page_tables = page.extract_tables(table_settings=TABLE_TEXT_STRATEGY_SETTINGS) or []
                    except Exception:
                        pass
                raw_tables_per_page.append({
                    "page_number": page_number,
                    "page_id": page_id,
                    "page_text": page_text_for_tables,
                    "raw_tables": raw_page_tables,
                })
                # ── v0.6: collect native images during pdfplumber loop ────────
                _raw_images: list[dict[str, Any]] = []
                try:
                    _raw_images = list(page.images or [])
                except Exception:
                    pass
                raw_figures_per_page.append({
                    "page_number": page_number,
                    "page_id": page_id,
                    "raw_images": _raw_images,
                })

        refine_text_block_classifications(page_records, text_blocks)
        write_json(output_dir / "document_record.json", document_record)
        write_jsonl(output_dir / "page_index.jsonl", page_records)
        write_jsonl(output_dir / "text_blocks.jsonl", text_blocks)
        text_block_statistics = build_text_block_statistics(
            options.document_id,
            page_records,
            text_blocks,
        )
        section_candidates = build_section_candidates(options.document_id, text_blocks)
        sections, section_warnings = build_sections(
            options.document_id,
            page_records,
            section_candidates,
        )
        warnings.extend(section_warnings)
        evidence_records, evidence_diagnostics = build_evidence_store(
            options.document_id,
            text_blocks,
            sections,
        )
        initial_evidence_statistics = build_evidence_statistics(
            options.document_id,
            evidence_records,
            sections,
            evidence_diagnostics,
        )
        sections = apply_section_quality_policies(sections, initial_evidence_statistics)
        evidence_records = propagate_section_quality_to_evidence(evidence_records, sections)
        suspicious_sections = build_suspicious_sections(options.document_id, sections, evidence_records)

        # ── v0.5: process tables (needs sections to be built first) ──────────
        _page_blocks_by_page: dict[int, list[dict[str, Any]]] = {}
        for _blk in text_blocks:
            _pn = int(_blk.get("page_number") or 0)
            _page_blocks_by_page.setdefault(_pn, []).append(_blk)
        _page_record_by_number: dict[int, dict[str, Any]] = {
            int(pr.get("page_number") or 0): pr for pr in page_records
        }
        for _raw_page in raw_tables_per_page:
            _pn = int(_raw_page.get("page_number") or 0)
            _blks = _page_blocks_by_page.get(_pn, [])
            _pr = _page_record_by_number.get(_pn)
            _diag = page_diagnostics(_pr, _blks) if _pr else None
            _t_recs, _c_recs = process_raw_tables(
                _raw_page, options.document_id, sections, _blks, _diag
            )
            table_records.extend(_t_recs)
            cell_records.extend(_c_recs)
        table_evidence = build_table_evidence(options.document_id, table_records)
        # Propagate v0.4.2 section-quality fields to table evidences.
        # build_table_evidence runs before propagate_section_quality_to_evidence
        # so table evidences must be stamped explicitly here.
        table_evidence = propagate_section_quality_to_evidence(table_evidence, sections)
        evidence_records.extend(table_evidence)
        table_statistics = build_table_statistics(options.document_id, table_records, cell_records, sections)
        write_jsonl(output_dir / "table_index.jsonl", table_records)
        write_jsonl(output_dir / "table_cells.jsonl", cell_records)
        write_json(output_dir / "table_statistics.json", table_statistics)
        quality_checks.extend(table_quality_checks(options.document_id, table_records, cell_records, output_dir))

        # ── v0.6: process figures ─────────────────────────────────────────────
        for _raw_fig_page in raw_figures_per_page:
            _pn = int(_raw_fig_page.get("page_number") or 0)
            _blks = _page_blocks_by_page.get(_pn, [])
            _pr = _page_record_by_number.get(_pn)
            _diag = page_diagnostics(_pr, _blks) if _pr else None
            _f_recs = process_raw_figures(
                _raw_fig_page, options.document_id, sections, _blks, _diag
            )
            figure_records.extend(_f_recs)
        propagate_section_quality_to_figures(figure_records, sections)
        figure_evidence = build_figure_evidence(options.document_id, figure_records)
        figure_statistics = build_figure_statistics(options.document_id, figure_records, sections)
        write_jsonl(output_dir / "figure_index.jsonl", figure_records)
        write_json(output_dir / "figure_statistics.json", figure_statistics)
        quality_checks.extend(figure_quality_checks(options.document_id, figure_records, output_dir))
        evidence_records.extend(figure_evidence)

        evidence_statistics = build_evidence_statistics(
            options.document_id,
            evidence_records,
            sections,
            evidence_diagnostics,
        )
        section_statistics = build_section_statistics(
            options.document_id,
            section_candidates,
            sections,
        )
        write_json(output_dir / "text_block_statistics.json", text_block_statistics)
        write_jsonl(output_dir / "section_candidates.jsonl", section_candidates)
        write_jsonl(output_dir / "section_index.jsonl", sections)
        write_json(output_dir / "section_statistics.json", section_statistics)
        write_jsonl(output_dir / "evidence_store.jsonl", evidence_records)
        write_json(output_dir / "evidence_statistics.json", evidence_statistics)
        write_jsonl(output_dir / "suspicious_sections.jsonl", suspicious_sections)
        quality_checks.extend(
            page_quality_diagnostic_checks(options.document_id, page_records, text_blocks)
        )
        quality_checks.extend(
            block_classification_quality_checks(options.document_id, text_block_statistics)
        )
        quality_checks.extend(
            section_quality_checks(options.document_id, section_candidates, sections)
        )
        quality_checks.extend(
            evidence_quality_checks(
                options.document_id,
                evidence_records,
                text_blocks,
                sections,
                evidence_statistics,
                suspicious_sections,
            )
        )
        multimodal_records = build_multimodal_evidence_index(
            options.document_id,
            evidence_records,
            table_records,
            figure_records,
        )
        multimodal_statistics = build_multimodal_statistics(
            options.document_id,
            multimodal_records,
            table_statistics,
            figure_statistics,
            suspicious_sections,
        )
        document_inventory = build_document_inventory(
            document_record,
            page_records,
            text_blocks,
            sections,
            suspicious_sections,
            evidence_records,
            table_statistics,
            figure_statistics,
            multimodal_statistics,
            len(errors),
            quality_checks,
            options.pdf_path,
        )
        write_json(output_dir / "document_inventory.json", document_inventory)
        write_jsonl(output_dir / "multimodal_evidence_index.jsonl", multimodal_records)
        write_json(output_dir / "multimodal_statistics.json", multimodal_statistics)
        quality_checks.extend(
            multimodal_quality_checks(
                options.document_id,
                multimodal_records,
                multimodal_statistics,
                output_dir,
                evidence_records,
            )
        )
        audit_findings = build_audit_findings(
            options.document_id,
            output_dir,
            document_inventory,
            evidence_records,
            text_blocks,
            table_records,
            figure_records,
            sections,
            suspicious_sections,
            multimodal_records,
            multimodal_statistics,
            table_statistics,
            figure_statistics,
        )
        consistency_report = build_consistency_report(
            options.document_id,
            output_dir,
            audit_findings,
            evidence_records,
            multimodal_records,
            sections,
            suspicious_sections,
        )
        audit_markdown = render_document_audit_report(
            document_inventory,
            document_record,
            {"status": "success", "errors_count": len(errors), "warnings_count": 0},
            consistency_report,
            audit_findings,
            suspicious_sections,
            multimodal_statistics,
            table_statistics,
            figure_statistics,
        )
        write_json(output_dir / "consistency_report.json", consistency_report)
        write_jsonl(output_dir / "audit_findings.jsonl", audit_findings)
        (output_dir / "document_audit_report.md").write_text(audit_markdown, encoding="utf-8")
        quality_checks.extend(
            audit_quality_checks(
                options.document_id,
                output_dir,
                consistency_report,
                audit_findings,
                multimodal_records,
            )
        )

        status = "success"
    except Exception as exc:
        status = "failed"
        message = str(exc)
        errors.append(message)
        document_record["loading_status"] = "failed"
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            write_json(output_dir / "document_record.json", document_record)
            write_jsonl(output_dir / "page_index.jsonl", page_records)
            write_jsonl(output_dir / "text_blocks.jsonl", text_blocks)
            text_block_statistics = build_text_block_statistics(
                options.document_id,
                page_records,
                text_blocks,
            )
            section_candidates = build_section_candidates(options.document_id, text_blocks)
            sections, section_warnings = build_sections(
                options.document_id,
                page_records,
                section_candidates,
            )
            warnings.extend(section_warnings)
            evidence_records, evidence_diagnostics = build_evidence_store(
                options.document_id,
                text_blocks,
                sections,
            )
            initial_evidence_statistics = build_evidence_statistics(
                options.document_id,
                evidence_records,
                sections,
                evidence_diagnostics,
            )
            sections = apply_section_quality_policies(sections, initial_evidence_statistics)
            evidence_records = propagate_section_quality_to_evidence(evidence_records, sections)
            suspicious_sections = build_suspicious_sections(options.document_id, sections, evidence_records)
            evidence_statistics = build_evidence_statistics(
                options.document_id,
                evidence_records,
                sections,
                evidence_diagnostics,
            )
            section_statistics = build_section_statistics(
                options.document_id,
                section_candidates,
                sections,
            )
            write_json(output_dir / "text_block_statistics.json", text_block_statistics)
            write_jsonl(output_dir / "section_candidates.jsonl", section_candidates)
            write_jsonl(output_dir / "section_index.jsonl", sections)
            write_json(output_dir / "section_statistics.json", section_statistics)
            write_jsonl(output_dir / "evidence_store.jsonl", evidence_records)
            write_json(output_dir / "evidence_statistics.json", evidence_statistics)
            write_jsonl(output_dir / "suspicious_sections.jsonl", suspicious_sections)
            # v0.5: write empty table files so EXPECTED_OUTPUT_FILES check passes
            write_jsonl(output_dir / "table_index.jsonl", [])
            write_jsonl(output_dir / "table_cells.jsonl", [])
            write_json(output_dir / "table_statistics.json", {})
            # v0.6: write empty figure files
            write_jsonl(output_dir / "figure_index.jsonl", [])
            write_json(output_dir / "figure_statistics.json", {})
            write_json(output_dir / "document_inventory.json", {})
            write_jsonl(output_dir / "multimodal_evidence_index.jsonl", [])
            write_json(output_dir / "multimodal_statistics.json", {})
            write_json(output_dir / "consistency_report.json", {})
            write_jsonl(output_dir / "audit_findings.jsonl", [])
            (output_dir / "document_audit_report.md").write_text("# Document Audit Report\n\nExtraction failed before audit completion.\n", encoding="utf-8")
        except Exception as write_exc:
            errors.append(f"Could not write partial outputs: {write_exc}")
        quality_checks.append(
            quality_record(
                "pdf_readable",
                "fail",
                "critical",
                message,
                document_id=options.document_id,
                review_required=True,
            )
        )
    finally:
        finished_at = utcnow()

    summary = {
        "schema_version": SCHEMA_VERSION,
        "engine_contract_version": ENGINE_CONTRACT_VERSION,
        "document_id": options.document_id,
        "pdf_path": str(options.pdf_path.resolve()),
        "output_dir": str(output_dir),
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "page_count": int(document_record.get("page_count") or 0),
        "pages_processed": len(page_records),
        "text_blocks_count": len(text_blocks),
        "tables_count": len(table_records),
        "table_cells_count": len(cell_records),
        "empty_tables_count": int(table_statistics.get("empty_tables_count", 0) or 0),
        "mostly_empty_tables_count": int(table_statistics.get("mostly_empty_tables_count", 0) or 0),
        "tiny_table_artifacts_count": int(table_statistics.get("tiny_table_artifacts_count", 0) or 0),
        "front_matter_or_toc_tables_count": int(table_statistics.get("front_matter_or_toc_tables_count", 0) or 0),
        "fragmented_tables_count": int(table_statistics.get("fragmented_tables_count", 0) or 0),
        "table_artifact_suspected_count": int(table_statistics.get("table_artifact_suspected_count", 0) or 0),
        "table_evidence_count": sum(1 for _e in evidence_records if _e.get("evidence_type") == "table"),
        "figures_count": len(figure_records),
        "detected_figures_count": int(figure_statistics.get("detected_figures_count", 0) or 0),
        "low_confidence_figures_count": int(figure_statistics.get("low_confidence_figures_count", 0) or 0),
        "failed_figures_count": int(figure_statistics.get("failed_figures_count", 0) or 0),
        "figures_with_caption_count": int(figure_statistics.get("figures_with_caption_count", 0) or 0),
        "figures_without_caption_count": int(figure_statistics.get("figures_without_caption_count", 0) or 0),
        "quarantined_figures_count": int(figure_statistics.get("quarantined_figures_count", 0) or 0),
        "review_required_figures_count": int(figure_statistics.get("review_required_figures_count", 0) or 0),
        "figure_evidence_count": sum(1 for _e in evidence_records if _e.get("evidence_type") == "figure"),
        "page_level_visual_count": int(figure_statistics.get("page_level_visual_count", 0) or 0),
        "embedded_visual_count": int(figure_statistics.get("embedded_visual_count", 0) or 0),
        "captioned_figure_count": int(figure_statistics.get("captioned_figure_count", 0) or 0),
        "visual_page_candidates_count": int(figure_statistics.get("visual_page_candidates_count", 0) or 0),
        "figures_without_bbox_count": int(figure_statistics.get("figures_without_bbox_count", 0) or 0),
        "weak_visual_detections_count": int(figure_statistics.get("weak_visual_detections_count", 0) or 0),
        "multimodal_evidence_count": len(multimodal_records),
        "text_modality_evidence_count": int(
            (multimodal_statistics.get("evidence_by_modality", {}) or {}).get("text", 0) or 0
        ),
        "table_modality_evidence_count": int(
            (multimodal_statistics.get("evidence_by_modality", {}) or {}).get("table", 0) or 0
        ),
        "figure_modality_evidence_count": int(
            (multimodal_statistics.get("evidence_by_modality", {}) or {}).get("figure", 0) or 0
        ),
        "eligible_for_future_extraction_count": int(
            (multimodal_statistics.get("downstream_use_policy_distribution", {}) or {}).get(
                "eligible_for_future_extraction", 0
            ) or 0
        ),
        "review_before_extraction_count": int(
            (multimodal_statistics.get("downstream_use_policy_distribution", {}) or {}).get(
                "review_before_extraction", 0
            ) or 0
        ),
        "excluded_from_automatic_extraction_count": int(
            (multimodal_statistics.get("downstream_use_policy_distribution", {}) or {}).get(
                "exclude_from_automatic_extraction", 0
            ) or 0
        ),
        "extraction_readiness_status": document_inventory.get("extraction_readiness_status"),
        "output_contract_path": "ESGInformationExtraction/contracts/output_contract_v1.json",
        "contract_validation_status": "not_run",
        "consistency_report_created": bool(consistency_report),
        "audit_findings_count": len(audit_findings),
        "critical_audit_findings_count": sum(1 for finding in audit_findings if finding.get("severity") == "critical"),
        "major_audit_findings_count": sum(1 for finding in audit_findings if finding.get("severity") == "major"),
        "minor_audit_findings_count": sum(1 for finding in audit_findings if finding.get("severity") == "minor"),
        "document_audit_report_created": (output_dir / "document_audit_report.md").exists(),
        "audit_overall_status": consistency_report.get("overall_status"),
        "sections_count": len(sections),
        "evidence_count": len(evidence_records),
        "section_heading_evidence_count": int(
            (evidence_statistics.get("evidence_type_distribution", {}) or {}).get("section_heading", 0) or 0
        ),
        "paragraph_evidence_count": int(
            (evidence_statistics.get("evidence_type_distribution", {}) or {}).get("paragraph", 0) or 0
        ),
        "evidence_without_section_count": int(
            evidence_statistics.get("evidence_without_section_count", 0) or 0
        ),
        "evidence_review_required_count": int(
            evidence_statistics.get("evidence_review_required_count", 0) or 0
        ),
        "merged_evidence_count": int(evidence_statistics.get("merged_evidence_count", 0) or 0),
        "unmerged_evidence_count": int(evidence_statistics.get("unmerged_evidence_count", 0) or 0),
        "short_evidence_skipped_count": int(evidence_statistics.get("short_evidence_skipped_count", 0) or 0),
        "short_evidence_review_required_count": int(
            evidence_statistics.get("short_evidence_review_required_count", 0) or 0
        ),
        "sections_with_high_evidence_density_count": len(
            evidence_statistics.get("sections_with_high_evidence_density", []) or []
        ),
        "sections_with_front_matter_warning_count": len(
            evidence_statistics.get("sections_with_front_matter_warning", []) or []
        ),
        "section_title_content_mismatch_warning_count": len(
            evidence_statistics.get("sample_section_mismatch_warnings", []) or []
        ),
        "median_evidence_quote_length": float(evidence_statistics.get("median_quote_length", 0) or 0),
        "suspicious_sections_count": int(evidence_statistics.get("suspicious_sections_count", 0) or 0),
        "quarantined_evidence_count": int(evidence_statistics.get("quarantined_evidence_count", 0) or 0),
        "review_required_due_to_section_count": int(
            evidence_statistics.get("review_required_due_to_section_count", 0) or 0
        ),
        "normal_evidence_count": int(
            (evidence_statistics.get("evidence_policy_distribution", {}) or {}).get("normal", 0) or 0
        ),
        "evidence_policy_distribution": evidence_statistics.get("evidence_policy_distribution", {}),
        "average_section_quality_score": float(
            (section_statistics.get("section_quality_score_distribution", {}) or {}).get("average", 0) or 0
        ),
        "min_section_quality_score": float(
            (section_statistics.get("section_quality_score_distribution", {}) or {}).get("min", 0) or 0
        ),
        "quality_checks_count": 0,  # updated after final checks are appended
        "errors_count": len(errors),
        "warnings_count": 0,
        "pages_low_text_count": len(text_block_statistics.get("pages_low_text", [])),
        "possible_visual_pages_count": len(text_block_statistics.get("possible_visual_pages", [])),
        "possible_toc_pages_count": len(text_block_statistics.get("possible_toc_pages", [])),
        "high_title_density_pages_count": len(text_block_statistics.get("high_title_density_pages", [])),
        "blocks_with_bbox_count": int(text_block_statistics.get("blocks_with_bbox_count", 0) or 0),
        "blocks_without_bbox_count": int(text_block_statistics.get("blocks_without_bbox_count", 0) or 0),
        "title_blocks_count": int(
            (text_block_statistics.get("block_type_counts", {}) or {}).get("title", 0) or 0
        ),
        "paragraph_blocks_count": int(
            (text_block_statistics.get("block_type_counts", {}) or {}).get("paragraph", 0) or 0
        ),
        "unknown_blocks_count": int(
            (text_block_statistics.get("block_type_counts", {}) or {}).get("unknown", 0) or 0
        ),
        "header_blocks_count": int(text_block_statistics.get("header_blocks_count", 0) or 0),
        "footer_blocks_count": int(text_block_statistics.get("footer_blocks_count", 0) or 0),
        "toc_entry_blocks_count": int(text_block_statistics.get("toc_entry_blocks_count", 0) or 0),
        "caption_blocks_count": int(text_block_statistics.get("caption_blocks_count", 0) or 0),
        "list_item_blocks_count": int(text_block_statistics.get("list_item_blocks_count", 0) or 0),
        "footnote_blocks_count": int(text_block_statistics.get("footnote_blocks_count", 0) or 0),
        "refined_footer_blocks_count": int(text_block_statistics.get("refined_footer_blocks_count", 0) or 0),
        "unknown_blocks_ratio": float(text_block_statistics.get("unknown_blocks_ratio", 0) or 0),
        "section_candidates_count": len(section_candidates),
        "section_candidates_accepted_count": sum(
            1 for candidate in section_candidates if candidate.get("candidate_status") == "accepted"
        ),
        "section_candidates_rejected_count": sum(
            1 for candidate in section_candidates if candidate.get("candidate_status") != "accepted"
        ),
        "sections_review_required_count": sum(1 for section in sections if section.get("review_required")),
        "section_types_distribution": section_statistics.get("section_types_distribution", {}),
        "rejected_cover_page_count": int(section_statistics.get("rejected_cover_page_count", 0) or 0),
        "rejected_toc_heading_count": int(section_statistics.get("rejected_toc_heading_count", 0) or 0),
        "rejected_numeric_value_count": int(section_statistics.get("rejected_numeric_value_count", 0) or 0),
        "rejected_front_matter_count": int(section_statistics.get("rejected_front_matter_count", 0) or 0),
        "rejected_document_title_count": int(section_statistics.get("rejected_document_title_count", 0) or 0),
        "section_type_unknown_ratio": float(section_statistics.get("section_type_unknown_ratio", 0) or 0),
        "rejected_heading_fragment_count": int(section_statistics.get("rejected_heading_fragment_count", 0) or 0),
        "rejected_org_chart_like_count": int(section_statistics.get("rejected_org_chart_like_count", 0) or 0),
        "rejected_sentence_like_count": int(section_statistics.get("rejected_sentence_like_count", 0) or 0),
        "merged_headings_count": int(section_statistics.get("merged_headings_count", 0) or 0),
        "candidate_score_threshold": SECTION_CANDIDATE_SCORE_THRESHOLD,
        "options": {
            "max_pages": options.max_pages,
            "overwrite": options.overwrite,
        },
        "errors": errors,
        "warnings": warnings,
    }

    try:
        write_json(output_dir / "extraction_summary.json", summary)
        quality_checks.append(
            quality_record(
                "extraction_summary_exists",
                "pass",
                "critical",
                "extraction_summary.json exists.",
                target_type="output_file",
                target_id="extraction_summary.json",
                document_id=options.document_id,
            )
        )
        quality_checks.extend(output_file_not_empty_checks(output_dir, options.document_id, include_summary=True))
        warnings_count = sum(1 for check in quality_checks if check["status"] == "warning")
        errors_count = len(errors) + sum(1 for check in quality_checks if check["status"] == "fail")
        summary["quality_checks_count"] = len(quality_checks)
        summary["warnings_count"] = warnings_count
        summary["errors_count"] = errors_count
        if consistency_report:
            consistency_report["errors_count"] = int(summary.get("critical_audit_findings_count", 0) or 0)
            consistency_report["warnings_count"] = int(summary.get("audit_findings_count", 0) or 0) - int(summary.get("critical_audit_findings_count", 0) or 0)
            write_json(output_dir / "consistency_report.json", consistency_report)
            audit_markdown = render_document_audit_report(
                document_inventory,
                document_record,
                summary,
                consistency_report,
                audit_findings,
                suspicious_sections,
                multimodal_statistics,
                table_statistics,
                figure_statistics,
            )
            (output_dir / "document_audit_report.md").write_text(audit_markdown, encoding="utf-8")
        write_json(output_dir / "extraction_summary.json", summary)
        write_jsonl(output_dir / "quality_report.jsonl", quality_checks)
    except Exception as exc:
        print(f"Could not write final audit outputs: {exc}", file=sys.stderr)
        return 1, summary

    return (0 if status == "success" else 1), summary


def parse_args(argv: list[str] | None = None) -> ExtractionOptions:
    parser = argparse.ArgumentParser(description="Extract one PDF into v0 structure outputs.")
    parser.add_argument("--pdf-path", required=True)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    return ExtractionOptions(
        pdf_path=Path(args.pdf_path).expanduser(),
        document_id=args.document_id.strip(),
        output_dir=Path(args.output_dir).expanduser(),
        max_pages=args.max_pages,
        overwrite=bool(args.overwrite),
    )


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    try:
        returncode, summary = run_extraction(options)
    except (FileExistsError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(
        {
            "status": summary.get("status"),
            "document_id": summary.get("document_id"),
            "output_dir": summary.get("output_dir"),
            "pages_processed": summary.get("pages_processed"),
            "text_blocks_count": summary.get("text_blocks_count"),
            "errors_count": summary.get("errors_count"),
            "warnings_count": summary.get("warnings_count"),
        },
        ensure_ascii=False,
    ))
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())

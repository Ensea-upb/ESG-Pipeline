from __future__ import annotations

import csv
import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import build_visual_audit
from .classifier import classify_visuals
from .cropper import crop_visual_items
from .loader import build_visual_items, load_visual_inputs, utcnow, write_json, write_jsonl
from .ocr import run_ocr

log = logging.getLogger(__name__)


CANDIDATE_FIELDS = [
    "document_id",
    "company",
    "fiscal_year",
    "figure_id",
    "crop_id",
    "page_number",
    "section_id",
    "visual_type",
    "information_type",
    "esg_category",
    "label",
    "raw_value",
    "raw_unit",
    "year",
    "caption",
    "ocr_text",
    "source_image_path",
    "confidence",
    "review_required",
    "extraction_status",
]
OUTPUT_FILES = (
    "visual_input_inventory.json",
    "visual_items.jsonl",
    "visual_crops_index.jsonl",
    "visual_ocr_outputs.jsonl",
    "visual_ocr_summary.json",
    "visual_classification.jsonl",
    "visual_classification_summary.json",
    "visual_candidates.csv",
    "visual_candidates.jsonl",
    "visual_audit_summary.json",
    "visual_audit_findings.jsonl",
    "visual_audit_samples.csv",
    "visual_extraction_summary.json",
)
INFORMATION_TYPES = {
    "visual_metric_candidate",
    "visual_target_candidate",
    "visual_policy_evidence",
    "visual_risk_evidence",
    "visual_context_evidence",
}
# Extended unit set aligned with ESGTableExtraction and ESGInformationExtraction.
NUMBER_UNIT_RE = re.compile(
    r"(?P<value>\b\d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?|\b\d+(?:\.\d+)?)\s*"
    r"(?P<unit>%|(?:k|m|g)?tco2e?|co2eq?|gwh|mwh|kwh|gj|mj|tep|toe"
    r"|hm3|m3|tonnes?|(?<!\w)kt(?!\w)|(?<!\w)mt(?!\w)"
    r"|hectares?|(?<!\w)ha(?!\w)|km2|m2|employees?|headcount|hours?|heures?|fte)?",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(20[0-4]\d|19[8-9]\d)\b")


@dataclass
class VisualExtractionResult:
    candidates_count: int
    output_dir: Path
    summary: dict[str, Any]


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


_CATEGORY_TOKENS: list[tuple[str, list[str]]] = [
    ("climate", ["emission", "co2", "ghg", "carbon", "scope 1", "scope 2", "scope 3", "tco2e", "net zero", "climate"]),
    ("energy", ["energy", "electricity", "mwh", "gwh", "kwh", "renewable", "fossil", "fuel", "heat"]),
    ("water", ["water", "m3", "withdrawal", "discharge", "sewage"]),
    ("waste", ["waste", "recycling", "landfill", "hazardous", "diverted"]),
    ("workforce", ["employee", "workforce", "safety", "headcount", "fte", "staff"]),
    ("diversity", ["women", "female", "gender", "diversity", "parity", "inclusion"]),
    ("health_safety", ["injury", "accident", "fatality", "frequency rate", "trir", "ltir", "lost time"]),
    ("governance", ["governance", "board", "directors", "ethics", "independence", "committee"]),
    ("target", ["target", "objective", "commitment", "net zero", "by 2030", "by 2035", "by 2050", "reduction"]),
    ("biodiversity", ["biodiversity", "ecosystem", "habitat", "species", "hectares", "deforestation"]),
]


def detect_category(text: str) -> str:
    """Return the ESG category best matching text.

    Primary: semantic embedding similarity (multilingual, handles OCR noise).
    Fallback: keyword count if the model is unavailable or score is too low.
    """
    try:
        from .semantic_classifier import classify_esg_category
        category, confidence = classify_esg_category(text, threshold=0.28)
        if category != "general" and confidence > 0.0:
            return category
    except Exception:
        pass

    lower = text.lower()
    best_category = "general"
    best_count = 0
    for category, tokens in _CATEGORY_TOKENS:
        count = sum(1 for token in tokens if token in lower)
        if count > best_count:
            best_category = category
            best_count = count
    return best_category


def first_metric(text: str) -> tuple[str, str]:
    for match in NUMBER_UNIT_RE.finditer(text):
        value = normalize_text(match.group("value"))
        unit = normalize_text(match.group("unit"))
        digits = value.replace(",", "").replace(" ", "")
        if digits.isdigit() and 1900 <= int(digits) <= 2050 and not unit:
            continue
        return value, unit
    return "", ""


def detect_year(text: str) -> str:
    match = YEAR_RE.search(text)
    return match.group(1) if match else ""


def visual_information_type(text: str, visual_type: str, raw_value: str) -> str:
    lower = text.lower()
    # Use word-boundary for "target" to avoid false matches on "targeting".
    if re.search(r"\btarget\b|\bby\s+20[0-4]\d\b|\bobjective\b|\bnet.zero\b", lower):
        return "visual_target_candidate"
    if raw_value:
        return "visual_metric_candidate"
    if re.search(r"\brisk\b", lower):
        return "visual_risk_evidence"
    if re.search(r"\bpolicy\b|\bcommitment\b|\bengagement\b", lower):
        return "visual_policy_evidence"
    return "visual_context_evidence"


class ESGVisualExtractor:
    def __init__(self, input_dir: Path, output_dir: Path, overwrite: bool = False) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.overwrite = overwrite

    def run(self) -> VisualExtractionResult:
        self._validate_write_safety()
        started_at = utcnow()
        inputs = load_visual_inputs(self.input_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        visual_items = build_visual_items(inputs)
        write_json(self.output_dir / "visual_input_inventory.json", {
            "schema_version": "0.1.0",
            "document_id": inputs["document_id"],
            "input_dir": str(self.input_dir.resolve()),
            "pdf_path": inputs.get("pdf_path", ""),
            "figures_count": len(inputs.get("figures") or []),
            "visual_items_count": len(visual_items),
            "review_required": True,
        })
        write_jsonl(self.output_dir / "visual_items.jsonl", visual_items)

        # Best-effort: crop and OCR failures produce warnings but never crash the extractor.
        crop_pipeline_warning = ""
        try:
            crops = crop_visual_items(visual_items, inputs.get("pdf_path", ""), self.output_dir)
        except Exception as exc:
            crop_pipeline_warning = f"crop_visual_items failed: {exc}"
            log.warning("crop_visual_items raised an exception (best-effort, continuing): %s", exc)
            crops = []
        write_jsonl(self.output_dir / "visual_crops_index.jsonl", crops)

        try:
            ocr_rows, ocr_summary = run_ocr(crops)
        except Exception as exc:
            log.warning("run_ocr raised an exception (best-effort, continuing): %s", exc)
            ocr_rows = []
            ocr_summary = {
                "ocr_outputs_count": 0,
                "ocr_engine_available": False,
                "ocr_status_distribution": {},
            }
        write_jsonl(self.output_dir / "visual_ocr_outputs.jsonl", ocr_rows)
        write_json(self.output_dir / "visual_ocr_summary.json", {"schema_version": "0.3.0", **ocr_summary})
        classifications, classification_summary = classify_visuals(visual_items, ocr_rows)
        write_jsonl(self.output_dir / "visual_classification.jsonl", classifications)
        write_json(self.output_dir / "visual_classification_summary.json", {"schema_version": "0.4.0", **classification_summary})

        company = inputs.get("company", "")
        fiscal_year = inputs.get("fiscal_year", "")
        candidates = self._build_candidates(visual_items, crops, ocr_rows, classifications, company=company, fiscal_year=fiscal_year)
        write_csv(self.output_dir / "visual_candidates.csv", candidates, CANDIDATE_FIELDS)
        write_jsonl(self.output_dir / "visual_candidates.jsonl", candidates)
        audit_summary = build_visual_audit(self.output_dir, crops, ocr_rows, classifications, candidates)

        crops_with_warnings = [r for r in crops if r.get("visual_warning")]
        pipeline_status = "warning" if (crop_pipeline_warning or crops_with_warnings) else "success"

        summary = {
            "schema_version": "1.0.0",
            "module": "ESGVisualExtraction",
            "input_dir": str(self.input_dir.resolve()),
            "output_dir": str(self.output_dir.resolve()),
            "document_id": inputs["document_id"],
            "company": company,
            "fiscal_year": fiscal_year,
            "started_at": started_at,
            "finished_at": utcnow(),
            "status": pipeline_status,
            "crop_pipeline_warning": crop_pipeline_warning,
            "crops_with_warnings_count": len(crops_with_warnings),
            "visual_items_count": len(visual_items),
            "crops_count": len(crops),
            "ocr_outputs_count": len(ocr_rows),
            "visual_classifications_count": len(classifications),
            "visual_candidates_count": len(candidates),
            "information_type_distribution": dict(Counter(row["information_type"] for row in candidates)),
            "visual_type_distribution": dict(Counter(row["visual_type"] for row in candidates)),
            "ocr_status_distribution": ocr_summary.get("ocr_status_distribution", {}),
            "candidate_only": True,
            "review_required_count": len(candidates),
            "audit_errors_count": audit_summary.get("errors_count", 0),
            "audit_warnings_count": audit_summary.get("warnings_count", 0),
            "quality_warning": bool(audit_summary.get("warnings_count", 0)),
            "real_world_visual_audit_pending": True,
            "outputs": list(OUTPUT_FILES),
        }
        write_json(self.output_dir / "visual_extraction_summary.json", summary)
        return VisualExtractionResult(len(candidates), self.output_dir, summary)

    def _validate_write_safety(self) -> None:
        if not self.input_dir.exists() or not self.input_dir.is_dir():
            raise FileNotFoundError(f"input-dir does not exist: {self.input_dir}")
        existing = [name for name in OUTPUT_FILES if (self.output_dir / name).exists()]
        if existing and not self.overwrite:
            raise FileExistsError("Visual output files already exist. Use --overwrite to replace: " + ", ".join(existing))

    def _build_candidates(
        self,
        visual_items: list[dict[str, Any]],
        crops: list[dict[str, Any]],
        ocr_rows: list[dict[str, Any]],
        classifications: list[dict[str, Any]],
        company: str = "",
        fiscal_year: str = "",
    ) -> list[dict[str, Any]]:
        crop_by_figure = {row.get("figure_id"): row for row in crops}
        ocr_by_figure = {row.get("figure_id"): row for row in ocr_rows}
        class_by_figure = {row.get("figure_id"): row for row in classifications}
        candidates: list[dict[str, Any]] = []
        for item in visual_items:
            figure_id = item.get("figure_id")
            crop = crop_by_figure.get(figure_id, {})
            ocr = ocr_by_figure.get(figure_id, {})
            classification = class_by_figure.get(figure_id, {})
            caption = normalize_text(item.get("nearby_caption_text"))
            ocr_text = normalize_text(ocr.get("ocr_text"))
            combined = normalize_text(f"{caption} {ocr_text} {item.get('figure_type', '')} {classification.get('visual_type', '')}")
            raw_value, raw_unit = first_metric(combined)
            visual_type = classification.get("visual_type", "unknown_visual")
            info_type = visual_information_type(combined, visual_type, raw_value)
            if info_type not in INFORMATION_TYPES:
                info_type = "visual_context_evidence"
            esg_category = detect_category(combined)
            quality_flags = item.get("figure_quality_flags") or []

            confidence = 0.2
            if ocr_text:
                confidence += 0.1
            if raw_value and raw_unit:
                confidence += 0.1
            if visual_type in {"chart", "scanned_table", "diagram"}:
                confidence += 0.05
            # Downgrade for known quality issues
            if any(flag in quality_flags for flag in ("low_resolution", "blurry", "partial_crop", "ocr_failed")):
                confidence -= 0.05
            confidence = round(min(confidence, 0.5), 2)

            # Build a meaningful label instead of a fixed placeholder.
            type_label = info_type.replace("visual_", "").replace("_", " ")
            label = f"{esg_category} {type_label}" if esg_category != "general" else type_label

            candidates.append({
                "document_id": item.get("document_id", ""),
                "company": company,
                "fiscal_year": fiscal_year,
                "figure_id": figure_id,
                "crop_id": crop.get("crop_id", ""),
                "page_number": item.get("page_number"),
                "section_id": item.get("section_id") or "",
                "visual_type": visual_type,
                "information_type": info_type,
                "esg_category": esg_category,
                "label": label,
                "raw_value": raw_value,
                "raw_unit": raw_unit,
                "year": detect_year(combined),
                "caption": caption,
                "ocr_text": ocr_text[:1000],
                "source_image_path": crop.get("crop_image_path", ""),
                "confidence": confidence,
                "review_required": True,
                "extraction_status": "candidate_only",
            })
        return candidates


__all__ = ["CANDIDATE_FIELDS", "ESGVisualExtractor", "VisualExtractionResult"]

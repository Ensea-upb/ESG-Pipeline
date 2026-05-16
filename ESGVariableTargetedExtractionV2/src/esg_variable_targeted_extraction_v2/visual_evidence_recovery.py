"""
visual_evidence_recovery.py — Best-effort recovery of visual evidence (crops, figures, captions).
Local OCR optional. No API calls. No crash if crops missing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .input_adapter import DocumentV2Input
from .io_utils import write_jsonl


class VisualEvidenceRecovery:
    def __init__(
        self,
        use_ocr: bool = False,
        crops_base_dir: Path | None = None,
    ) -> None:
        self.use_ocr = use_ocr
        self.crops_base_dir = crops_base_dir

    def recover(
        self,
        doc: DocumentV2Input,
        input_dir: Path | None = None,
    ) -> list[dict[str, Any]]:
        """
        Process all figures/crops from the document.
        Returns visual_recovery_findings records.
        Never raises. Warns on missing crops.
        """
        findings: list[dict[str, Any]] = []

        # 1. Process figure index entries
        for fig in doc.figure_index:
            finding = self._process_figure(fig, doc, input_dir)
            findings.append(finding)

        # 2. Process multimodal evidence with crop references
        for ev in doc.multimodal_evidence:
            if ev.get("evidence_type") in ("figure", "crop", "visual"):
                finding = self._process_multimodal_evidence(ev, doc, input_dir)
                findings.append(finding)

        # 3. Look for crops directory explicitly
        if input_dir:
            crops_dir = Path(input_dir) / "visual" / "crops"
            if not crops_dir.exists():
                # Try looking in parent's 02_orchestrator
                parent = Path(input_dir).parent
                crops_dir = parent / "02_orchestrator" / "visual" / "crops"

            if crops_dir.exists():
                crop_paths = sorted(crops_dir.glob("*.png")) + sorted(crops_dir.glob("*.jpg"))
                for crop_path in crop_paths[:200]:  # cap at 200
                    if not any(f.get("crop_path") == str(crop_path) for f in findings):
                        findings.append(self._process_crop_file(crop_path, doc))

        return findings

    def _process_figure(
        self,
        fig: dict[str, Any],
        doc: DocumentV2Input,
        input_dir: Path | None,
    ) -> dict[str, Any]:
        fig_id = fig.get("figure_id", "")
        page_number = fig.get("page_number", "")
        caption = fig.get("caption", fig.get("figure_caption", ""))
        crop_path = fig.get("crop_path", fig.get("image_path", ""))

        crop_exists = bool(crop_path and Path(crop_path).exists())
        detected_text = caption or ""
        detection_method = "caption" if caption else "none"
        extraction_possible = bool(caption)
        visual_warning = ""

        if crop_path and not crop_exists:
            visual_warning = f"crop_file_missing: {crop_path}"
        elif not caption:
            visual_warning = "no_caption_and_no_crop"

        if self.use_ocr and crop_exists and not detected_text:
            detected_text, detection_method = self._run_ocr(Path(crop_path))

        return {
            "figure_id": fig_id,
            "crop_id": "",
            "crop_path": str(crop_path),
            "crop_file_exists": crop_exists,
            "page_number": str(page_number),
            "detected_text": detected_text[:500] if detected_text else "",
            "detection_method": detection_method,
            "visual_warning": visual_warning,
            "extraction_possible": extraction_possible,
            "document_id": doc.document_id,
            "company": doc.company,
            "fiscal_year": doc.fiscal_year,
        }

    def _process_multimodal_evidence(
        self,
        ev: dict[str, Any],
        doc: DocumentV2Input,
        input_dir: Path | None,
    ) -> dict[str, Any]:
        ev_id = ev.get("evidence_id", "")
        page_number = ev.get("page_number", "")
        quote = ev.get("quote", "")
        crop_path = ev.get("crop_path", ev.get("image_path", ""))
        crop_exists = bool(crop_path and Path(crop_path).exists())

        return {
            "figure_id": ev_id,
            "crop_id": "",
            "crop_path": str(crop_path) if crop_path else "",
            "crop_file_exists": crop_exists,
            "page_number": str(page_number),
            "detected_text": quote[:500] if quote else "",
            "detection_method": "evidence_quote" if quote else "none",
            "visual_warning": "crop_file_missing" if crop_path and not crop_exists else "",
            "extraction_possible": bool(quote),
            "document_id": doc.document_id,
            "company": doc.company,
            "fiscal_year": doc.fiscal_year,
        }

    def _process_crop_file(
        self,
        crop_path: Path,
        doc: DocumentV2Input,
    ) -> dict[str, Any]:
        detected_text = ""
        detection_method = "none"
        visual_warning = ""

        if self.use_ocr:
            detected_text, detection_method = self._run_ocr(crop_path)
        else:
            visual_warning = "visual_text_unavailable"
            detection_method = "ocr_disabled"

        return {
            "figure_id": "",
            "crop_id": crop_path.stem,
            "crop_path": str(crop_path),
            "crop_file_exists": True,
            "page_number": "",
            "detected_text": detected_text[:500] if detected_text else "",
            "detection_method": detection_method,
            "visual_warning": visual_warning,
            "extraction_possible": bool(detected_text),
            "document_id": doc.document_id,
            "company": doc.company,
            "fiscal_year": doc.fiscal_year,
        }

    def _run_ocr(self, crop_path: Path) -> tuple[str, str]:
        """Attempt local OCR. Returns (text, method). No API calls."""
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(crop_path)
            text = pytesseract.image_to_string(img, lang="fra+eng")
            return text.strip(), "tesseract_local"
        except ImportError:
            pass

        try:
            import easyocr
            reader = easyocr.Reader(["en", "fr"], gpu=False, verbose=False)
            results = reader.readtext(str(crop_path), detail=0)
            return " ".join(results).strip(), "easyocr_local"
        except ImportError:
            pass

        return "", "ocr_unavailable"


def recover_visual_evidence(
    doc: DocumentV2Input,
    input_dir: Path | None = None,
    use_ocr: bool = False,
) -> list[dict[str, Any]]:
    recovery = VisualEvidenceRecovery(use_ocr=use_ocr)
    return recovery.recover(doc, input_dir)


def write_visual_findings(findings: list[dict[str, Any]], output_dir) -> None:
    from pathlib import Path
    write_jsonl(Path(output_dir) / "visual_recovery_findings_v2.jsonl", findings)

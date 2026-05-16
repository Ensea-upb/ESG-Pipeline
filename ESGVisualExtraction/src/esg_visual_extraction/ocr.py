from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def find_tesseract_cli() -> str:
    found = shutil.which("tesseract")
    if found:
        return found
    for candidate in [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]:
        if Path(candidate).exists():
            return candidate
    return ""


def run_ocr(crops: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        import pytesseract  # type: ignore
        from PIL import Image

        engine_available = True
        cli_path = ""
    except Exception:
        pytesseract = None
        Image = None
        cli_path = find_tesseract_cli()
        engine_available = bool(cli_path)

    rows: list[dict[str, Any]] = []
    for index, crop in enumerate(crops, start=1):
        image_path = str(crop.get("crop_image_path") or "")
        text = ""
        confidence = 0.0
        status = "ocr_unavailable"
        engine = "none"
        if pytesseract is not None and engine_available and image_path and Path(image_path).exists():
            try:
                text = str(pytesseract.image_to_string(Image.open(image_path)))  # type: ignore[union-attr]
                confidence = 0.35 if text.strip() else 0.1
                status = "success" if text.strip() else "empty_text"
                engine = "pytesseract"
            except Exception:
                status = "ocr_failed"
                engine = "pytesseract"
        elif cli_path and image_path and Path(image_path).exists():
            try:
                completed = subprocess.run(
                    [cli_path, image_path, "stdout", "-l", "eng", "--psm", "6"],
                    text=True,
                    capture_output=True,
                    timeout=60,
                )
                text = completed.stdout if completed.returncode == 0 else ""
                confidence = 0.3 if text.strip() else 0.1
                status = "success" if text.strip() else "empty_text"
                engine = "tesseract_cli"
            except Exception:
                status = "ocr_failed"
                engine = "tesseract_cli"
        rows.append({
            "schema_version": "0.3.0",
            "ocr_id": f"ocr_{index:04d}",
            "crop_id": crop.get("crop_id", ""),
            "document_id": crop.get("document_id", ""),
            "figure_id": crop.get("figure_id", ""),
            "page_number": crop.get("page_number"),
            "ocr_text": " ".join(text.split()),
            "ocr_confidence": confidence,
            "ocr_status": status,
            "ocr_engine": engine,
            "review_required": True,
        })
    summary = {
        "ocr_outputs_count": len(rows),
        "ocr_engine_available": engine_available,
        "ocr_status_distribution": {status: sum(1 for row in rows if row["ocr_status"] == status) for status in sorted({row["ocr_status"] for row in rows})},
    }
    return rows, summary


__all__ = ["run_ocr"]

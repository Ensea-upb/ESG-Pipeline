from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

log = logging.getLogger(__name__)


def _placeholder(path: Path, text: str, size: tuple[int, int] = (1200, 1600)) -> None:
    image = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 40), text[:500], fill="black")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def crop_visual_items(visual_items: list[dict[str, Any]], pdf_path: str, output_dir: Path) -> list[dict[str, Any]]:
    crops_dir = output_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    pdf = Path(pdf_path) if pdf_path else Path()
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(visual_items, start=1):
        crop_id = f"crop_{index:04d}"
        # Short filename avoids Windows MAX_PATH (260 chars) on long document paths.
        # The figure_id is preserved in the crop record metadata below.
        image_path = crops_dir / f"{crop_id}.png"
        try:
            status = "success"
            method = "pdfplumber_page_or_bbox"
            bbox = item.get("figure_bbox")
            if not pdf_path or not pdf.exists():
                status = "missing_source_pdf"
                method = "no_crop_missing_source_pdf"
            else:
                try:
                    import pdfplumber  # type: ignore

                    with pdfplumber.open(str(pdf)) as doc:
                        page_index = max(int(item.get("page_number") or 1) - 1, 0)
                        page = doc.pages[page_index]
                        render_page = page.crop(tuple(bbox)) if bbox else page
                        render_page.to_image(resolution=120).save(str(image_path), format="PNG")
                except Exception as render_exc:
                    log.warning(
                        "Crop render failed for figure_id=%s (index=%d): %s",
                        item.get("figure_id"), index, render_exc,
                    )
                    status = "render_fallback_placeholder"
                    method = "placeholder_after_render_failure"
                    _placeholder(
                        image_path,
                        f"Visual crop placeholder\nfigure_id={item.get('figure_id')}\npage={item.get('page_number')}",
                    )
            if status == "missing_source_pdf":
                image_value = ""
                crop_file_exists = False
                visual_warning = ""
            else:
                if not image_path.exists():
                    _placeholder(image_path, f"Visual crop placeholder\nfigure_id={item.get('figure_id')}")
                crop_file_exists = image_path.exists()
                image_value = str(image_path) if crop_file_exists else ""
                visual_warning = "" if crop_file_exists else "crop_file_missing"
            rows.append({
                "schema_version": "0.2.0",
                "crop_id": crop_id,
                "document_id": item.get("document_id", ""),
                "figure_id": item.get("figure_id", ""),
                "page_number": item.get("page_number"),
                "source_pdf_path": pdf_path,
                "crop_image_path": image_value,
                "crop_method": method,
                "bbox_used": bbox,
                "crop_status": status,
                "crop_file_exists": crop_file_exists,
                "visual_warning": visual_warning,
                "review_required": True,
            })
        except Exception as exc:
            log.warning(
                "Unexpected crop failure for figure_id=%s (index=%d): %s",
                item.get("figure_id"), index, exc,
            )
            rows.append({
                "schema_version": "0.2.0",
                "crop_id": crop_id,
                "document_id": item.get("document_id", ""),
                "figure_id": item.get("figure_id", ""),
                "page_number": item.get("page_number"),
                "source_pdf_path": pdf_path,
                "crop_image_path": "",
                "crop_method": "failed",
                "bbox_used": item.get("figure_bbox"),
                "crop_status": "failed",
                "crop_file_exists": False,
                "visual_warning": "crop_creation_failed",
                "review_required": True,
            })
    return rows


__all__ = ["crop_visual_items"]

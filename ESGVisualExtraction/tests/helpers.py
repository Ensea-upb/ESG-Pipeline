from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_CLI = PROJECT_ROOT / "ESGVisualExtraction" / "scripts" / "run_visual_extraction.py"
VALIDATE_CLI = PROJECT_ROOT / "ESGVisualExtraction" / "scripts" / "validate_visual_outputs.py"
CONTRACT = PROJECT_ROOT / "ESGVisualExtraction" / "contracts" / "visual_output_contract_v0.json"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def make_visual_input(tmp_path: Path, with_figure_index: bool = True, pdf_exists: bool = True) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    pdf_path = input_dir / "source.pdf"
    if pdf_exists:
        pdf_path.write_bytes(b"%PDF-1.4\n% minimal placeholder\n")
    write_json(input_dir / "document_inventory.json", {
        "document_id": "lvmh_visual_test",
        "pdf_path": str(pdf_path),
    })
    write_json(input_dir / "extraction_summary.json", {
        "document_id": "lvmh_visual_test",
        "pdf_path": str(pdf_path),
    })
    write_json(input_dir / "figure_statistics.json", {"document_id": "lvmh_visual_test", "figures_count": 2})
    if with_figure_index:
        write_jsonl(input_dir / "figure_index.jsonl", [
            {
                "figure_id": "fig_001",
                "document_id": "lvmh_visual_test",
                "page_number": 1,
                "section_id": "sec_1",
                "figure_bbox": None,
                "figure_type": "unknown_visual",
                "visual_object_level": "page_level_visual",
                "detection_method": "page_visual_heuristic",
                "nearby_caption_text": "Chart showing emissions reduction target by 2030",
                "figure_quality_flags": ["page_level_visual_candidate"],
                "source_page_diagnostic_flags": ["is_possible_visual_page"],
            },
            {
                "figure_id": "fig_002",
                "document_id": "lvmh_visual_test",
                "page_number": 2,
                "section_id": "sec_2",
                "figure_bbox": [0, 0, 100, 100],
                "figure_type": "unknown_visual",
                "visual_object_level": "embedded_visual",
                "detection_method": "figure_heuristic",
                "nearby_caption_text": "Scanned table with 12,500 tCO2e in 2024",
                "figure_quality_flags": [],
                "source_page_diagnostic_flags": [],
            },
        ])
    write_jsonl(input_dir / "multimodal_evidence_index.jsonl", [
        {"evidence_id": "ev_fig_1", "source_modality": "figure", "source_element_type": "figure", "source_element_id": "fig_001"}
    ])
    return input_dir


def run_visual(input_dir: Path, output_dir: Path, *extra: str):
    return subprocess.run(
        [sys.executable, str(RUN_CLI), "--input-dir", str(input_dir), "--output-dir", str(output_dir), *extra],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def run_validator(output_dir: Path):
    return subprocess.run(
        [sys.executable, str(VALIDATE_CLI), "--output-dir", str(output_dir), "--contract-path", str(CONTRACT)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def hash_tree(path: Path) -> dict[str, str]:
    return {
        str(file.relative_to(path)): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }

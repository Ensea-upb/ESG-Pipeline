from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "ESGExtractionOrchestrator" / "scripts" / "run_full_extraction.py"
VALIDATE = ROOT / "ESGExtractionOrchestrator" / "scripts" / "validate_full_extraction_outputs.py"
MULTI = ROOT / "ESGExtractionOrchestrator" / "scripts" / "run_multi_document_full_extraction.py"
CONTRACT = ROOT / "ESGExtractionOrchestrator" / "contracts" / "full_extraction_output_contract_v0.json"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def make_input(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True)
    pdf_path = input_dir / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    write_json(input_dir / "document_inventory.json", {"document_id": "lvmh_2024_full", "pdf_path": str(pdf_path)})
    write_json(input_dir / "extraction_summary.json", {"document_id": "lvmh_2024_full", "pdf_path": str(pdf_path)})
    write_jsonl(input_dir / "multimodal_evidence_index.jsonl", [
        {"evidence_id": "ev1", "document_id": "lvmh_2024_full", "evidence_type": "paragraph", "source_modality": "text", "page_number": 1, "section_id": "sec1", "quote": "Scope 1 emissions were 12,500 tCO2e in 2024.", "downstream_use_policy": "eligible_for_future_extraction"},
        {"evidence_id": "ev2", "document_id": "lvmh_2024_full", "evidence_type": "figure", "source_modality": "figure", "source_element_type": "figure", "source_element_id": "fig1", "page_number": 2, "section_id": "sec1", "quote": "Figure on emissions", "downstream_use_policy": "review_before_extraction"},
    ])
    write_json(input_dir / "figure_statistics.json", {"figures_count": 1})
    write_jsonl(input_dir / "figure_index.jsonl", [{"figure_id": "fig1", "document_id": "lvmh_2024_full", "page_number": 2, "section_id": "sec1", "figure_type": "unknown_visual", "visual_object_level": "page_level_visual", "detection_method": "test", "nearby_caption_text": "Chart emissions 2024"}])
    write_json(input_dir / "table_statistics.json", {"tables_count": 1})
    write_jsonl(input_dir / "table_index.jsonl", [{"table_id": "tbl1", "document_id": "lvmh_2024_full", "page_number": 3, "section_id": "sec1", "extraction_status": "parsed", "row_count": 2, "column_count": 2, "cell_count": 4, "table_confidence": 0.7, "table_quality_flags": []}])
    write_jsonl(input_dir / "table_cells.jsonl", [
        {"cell_id": "c00", "table_id": "tbl1", "document_id": "lvmh_2024_full", "page_number": 3, "row_index": 0, "column_index": 0, "text": "Metric", "normalized_text": "Metric", "is_header_cell": True, "cell_confidence": 0.8},
        {"cell_id": "c01", "table_id": "tbl1", "document_id": "lvmh_2024_full", "page_number": 3, "row_index": 0, "column_index": 1, "text": "2024", "normalized_text": "2024", "is_header_cell": True, "cell_confidence": 0.8},
        {"cell_id": "c10", "table_id": "tbl1", "document_id": "lvmh_2024_full", "page_number": 3, "row_index": 1, "column_index": 0, "text": "Scope 1 emissions tCO2e", "normalized_text": "Scope 1 emissions tCO2e", "is_header_cell": False, "cell_confidence": 0.8},
        {"cell_id": "c11", "table_id": "tbl1", "document_id": "lvmh_2024_full", "page_number": 3, "row_index": 1, "column_index": 1, "text": "1,200", "normalized_text": "1,200", "is_header_cell": False, "cell_confidence": 0.8},
    ])
    return input_dir


def run_full(input_dir: Path, output_dir: Path, *extra: str):
    return subprocess.run([sys.executable, str(RUN), "--input-dir", str(input_dir), "--output-dir", str(output_dir), *extra], cwd=ROOT, text=True, capture_output=True)


def validate(output_dir: Path):
    return subprocess.run([sys.executable, str(VALIDATE), "--output-dir", str(output_dir), "--contract-path", str(CONTRACT)], cwd=ROOT, text=True, capture_output=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def hash_tree(path: Path) -> dict[str, str]:
    return {str(file.relative_to(path)): hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(path.rglob("*")) if file.is_file()}

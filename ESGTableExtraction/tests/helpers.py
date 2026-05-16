from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "ESGTableExtraction" / "scripts" / "run_table_extraction.py"
VALIDATE = ROOT / "ESGTableExtraction" / "scripts" / "validate_table_outputs.py"
MULTI = ROOT / "ESGTableExtraction" / "scripts" / "run_multi_document_table_audit.py"
CONTRACT = ROOT / "ESGTableExtraction" / "contracts" / "table_output_contract_v0.json"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def make_input(tmp_path: Path, missing: str = "") -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True)
    write_json(input_dir / "document_inventory.json", {"document_id": "lvmh_2024_table", "pdf_path": "ESGFinalCorpus/lvmh/2024/x/document.pdf"})
    write_json(input_dir / "extraction_summary.json", {"document_id": "lvmh_2024_table"})
    write_json(input_dir / "table_statistics.json", {"tables_count": 2, "table_cells_count": 8})
    if missing != "table_index":
        write_jsonl(input_dir / "table_index.jsonl", [
            {"table_id": "tbl1", "document_id": "lvmh_2024_table", "page_number": 1, "section_id": "sec1", "extraction_status": "parsed", "row_count": 3, "column_count": 3, "cell_count": 9, "table_confidence": 0.7, "table_quality_flags": []},
            {"table_id": "tbl_empty", "document_id": "lvmh_2024_table", "page_number": 2, "section_id": "sec2", "extraction_status": "empty_table", "row_count": 1, "column_count": 2, "cell_count": 2, "table_confidence": 0.1, "table_quality_flags": ["all_cells_empty"]},
        ])
    if missing != "table_cells":
        cells = [
            ("c00", "tbl1", 0, 0, "Metric", True), ("c01", "tbl1", 0, 1, "2023", True), ("c02", "tbl1", 0, 2, "2024", True),
            ("c10", "tbl1", 1, 0, "Scope 1 emissions tCO2e", False), ("c11", "tbl1", 1, 1, "1,200", False), ("c12", "tbl1", 1, 2, "1,100", False),
            ("c20", "tbl1", 2, 0, "Employees headcount", False), ("c21", "tbl1", 2, 1, "50", False), ("c22", "tbl1", 2, 2, "55", False),
            ("e00", "tbl_empty", 0, 0, "", False), ("e01", "tbl_empty", 0, 1, "", False),
        ]
        write_jsonl(input_dir / "table_cells.jsonl", [{"cell_id": cid, "table_id": tid, "document_id": "lvmh_2024_table", "page_number": 1, "row_index": r, "column_index": c, "text": txt, "normalized_text": txt, "is_header_cell": h, "cell_confidence": 0.8} for cid, tid, r, c, txt, h in cells])
    return input_dir


def run(input_dir: Path, output_dir: Path, *extra: str):
    return subprocess.run([sys.executable, str(RUN), "--input-dir", str(input_dir), "--output-dir", str(output_dir), *extra], cwd=ROOT, text=True, capture_output=True)


def validate(output_dir: Path):
    return subprocess.run([sys.executable, str(VALIDATE), "--output-dir", str(output_dir), "--contract-path", str(CONTRACT)], cwd=ROOT, text=True, capture_output=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def hash_tree(path: Path) -> dict[str, str]:
    return {str(file.relative_to(path)): hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(path.rglob("*")) if file.is_file()}

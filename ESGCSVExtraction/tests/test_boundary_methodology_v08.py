from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLI = PROJECT_ROOT / "ESGCSVExtraction" / "scripts" / "run_csv_extraction.py"


def test_boundary_and_methodology_context_fields(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "document_inventory.json").write_text(json.dumps({"document_id": "doc", "pdf_path": "ESGFinalCorpus/lvmh/2024/x/document.pdf"}), encoding="utf-8")
    (input_dir / "extraction_summary.json").write_text(json.dumps({"document_id": "doc"}), encoding="utf-8")
    rows = [
        {"evidence_id": "ev1", "source_modality": "text", "evidence_type": "paragraph", "page_number": 1, "section_id": "sec", "quote": "The data covers the Group including France and Europe, excluding minor subsidiaries."},
        {"evidence_id": "ev2", "source_modality": "text", "evidence_type": "paragraph", "page_number": 2, "section_id": "sec", "quote": "Emissions are calculated using the GHG Protocol and ESRS methodology."},
    ]
    (input_dir / "multimodal_evidence_index.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, str(CLI), "--input-dir", str(input_dir), "--output-dir", str(out)], cwd=PROJECT_ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout
    with (out / "boundary_contexts.csv").open("r", encoding="utf-8", newline="") as file:
        boundary = list(csv.DictReader(file))
    with (out / "methodology_contexts.csv").open("r", encoding="utf-8", newline="") as file:
        methodology = list(csv.DictReader(file))
    assert boundary
    assert methodology
    assert boundary[0]["boundary_value"] in {"Group", "France", "Europe"}
    assert boundary[0]["information_type"] == "boundary_context"
    assert methodology[0]["standard_or_method"] in {"GHG Protocol", "ESRS"}
    assert methodology[0]["information_type"] == "methodology_context"

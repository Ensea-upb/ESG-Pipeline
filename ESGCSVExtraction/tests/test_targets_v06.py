from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLI = PROJECT_ROOT / "ESGCSVExtraction" / "scripts" / "run_csv_extraction.py"


def test_target_fields_are_extracted(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "document_inventory.json").write_text(json.dumps({"document_id": "doc", "pdf_path": "ESGFinalCorpus/lvmh/2024/x/document.pdf"}), encoding="utf-8")
    (input_dir / "extraction_summary.json").write_text(json.dumps({"document_id": "doc"}), encoding="utf-8")
    (input_dir / "multimodal_evidence_index.jsonl").write_text(json.dumps({
        "evidence_id": "ev",
        "source_modality": "text",
        "evidence_type": "paragraph",
        "page_number": 2,
        "section_id": "sec",
        "quote": "Target to reduce Scope 1 emissions by 30% by 2030 from baseline year 2019.",
        "downstream_use_policy": "review_before_extraction",
    }) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, str(CLI), "--input-dir", str(input_dir), "--output-dir", str(out)], cwd=PROJECT_ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout
    with (out / "targets.csv").open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows
    row = rows[0]
    assert row["target_value"] == "30"
    assert row["target_unit"] == "%"
    assert row["target_year"] == "2030"
    assert row["baseline_year"] == "2019"
    assert row["target_status"] == "candidate_only"
    assert "score" not in row

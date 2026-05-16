from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLI = PROJECT_ROOT / "ESGCSVExtraction" / "scripts" / "run_csv_extraction.py"


def make_run(tmp_path: Path, quote: str) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "document_inventory.json").write_text(json.dumps({"document_id": "doc", "pdf_path": "ESGFinalCorpus/lvmh/2024/x/document.pdf"}), encoding="utf-8")
    (input_dir / "extraction_summary.json").write_text(json.dumps({"document_id": "doc"}), encoding="utf-8")
    (input_dir / "multimodal_evidence_index.jsonl").write_text(json.dumps({"evidence_id": "ev", "source_modality": "text", "evidence_type": "paragraph", "page_number": 1, "section_id": "sec", "quote": quote}) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, str(CLI), "--input-dir", str(input_dir), "--output-dir", str(out)], cwd=PROJECT_ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout
    return out


def read(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_policy_does_not_require_raw_value(tmp_path: Path):
    out = make_run(tmp_path, "The Group maintains a human rights policy and supplier code of conduct.")
    rows = read(out / "policies.csv")
    assert rows
    assert rows[0]["raw_value"] == ""
    assert rows[0]["claim"]
    assert rows[0]["evidence_id"] == "ev"


def test_risk_statement_never_outputs_score(tmp_path: Path):
    out = make_run(tmp_path, "Climate risk and transition risk may affect operations.")
    rows = read(out / "risks.csv")
    assert rows
    assert all("score" not in key.lower() for key in rows[0])
    assert rows[0]["risk_description"]

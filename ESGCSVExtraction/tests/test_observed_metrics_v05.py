from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLI = PROJECT_ROOT / "ESGCSVExtraction" / "scripts" / "run_csv_extraction.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def run_case(tmp_path: Path, quote: str) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    write_json(input_dir / "document_inventory.json", {"document_id": "doc_2024", "pdf_path": "ESGFinalCorpus/lvmh/2024/x/document.pdf"})
    write_json(input_dir / "extraction_summary.json", {"document_id": "doc_2024"})
    write_jsonl(input_dir / "multimodal_evidence_index.jsonl", [{
        "evidence_id": "ev1",
        "evidence_type": "paragraph",
        "source_modality": "text",
        "page_number": 1,
        "section_id": "sec1",
        "quote": quote,
        "downstream_use_policy": "eligible_for_future_extraction",
    }])
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, str(CLI), "--input-dir", str(input_dir), "--output-dir", str(out)], cwd=PROJECT_ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout
    return out


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_observed_metric_has_specific_fields_and_known_unit(tmp_path: Path):
    out = run_case(tmp_path, "Scope 1 emissions were 12,500 tCO2e in 2024.")
    rows = read_csv(out / "observed_metrics.csv")
    assert rows
    row = rows[0]
    assert row["raw_value"] == "12,500"
    assert row["raw_unit"] == "tCO2e"
    assert row["normalized_value"] == "12500"
    assert row["normalized_unit"] == "tCO2e"
    assert row["reported_year"] == "2024"
    assert row["value_kind"] in {"actual", "unknown"}


def test_target_phrase_is_not_classified_as_observed_metric(tmp_path: Path):
    out = run_case(tmp_path, "The company targets a 30% reduction in emissions by 2030.")
    rows = read_csv(out / "observed_metrics.csv")
    assert rows == []
    targets = read_csv(out / "targets.csv")
    assert targets

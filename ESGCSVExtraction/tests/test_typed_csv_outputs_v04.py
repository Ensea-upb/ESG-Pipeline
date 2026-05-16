from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esg_csv_extraction.extractor import CANDIDATE_FIELDS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLI = PROJECT_ROOT / "ESGCSVExtraction" / "scripts" / "run_csv_extraction.py"
TYPED_FILES = {
    "observed_metrics.csv": "observed_metric",
    "targets.csv": "target",
    "policies.csv": "policy_or_commitment",
    "risks.csv": "risk_statement",
    "boundary_contexts.csv": "boundary_context",
    "methodology_contexts.csv": "methodology_context",
    "visual_evidences.csv": "visual_evidence",
}


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def make_input(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    write_json(input_dir / "document_inventory.json", {
        "document_id": "lvmh_2024_test",
        "pdf_path": "C:/Users/hp/Desktop/ESG/ESGFinalCorpus/lvmh/2024/02_sustainability_statement_csrd_esrs/document.pdf",
    })
    write_json(input_dir / "extraction_summary.json", {"document_id": "lvmh_2024_test"})
    write_jsonl(input_dir / "multimodal_evidence_index.jsonl", [
        {
            "evidence_id": "ev_metric",
            "document_id": "lvmh_2024_test",
            "evidence_type": "paragraph",
            "source_modality": "text",
            "page_number": 1,
            "section_id": "sec_1",
            "quote": "The Group reported emissions of 12,500 tCO2e in 2024.",
            "review_required": False,
            "is_quarantined_evidence": False,
            "downstream_use_policy": "eligible_for_future_extraction",
        },
        {
            "evidence_id": "ev_target",
            "document_id": "lvmh_2024_test",
            "evidence_type": "paragraph",
            "source_modality": "text",
            "page_number": 2,
            "section_id": "sec_1",
            "quote": "The company has a target to reduce energy by 30% by 2030.",
            "review_required": True,
            "is_quarantined_evidence": False,
            "downstream_use_policy": "review_before_extraction",
        },
        {
            "evidence_id": "ev_policy",
            "document_id": "lvmh_2024_test",
            "evidence_type": "paragraph",
            "source_modality": "text",
            "page_number": 3,
            "section_id": "sec_2",
            "quote": "The Group maintains a human rights policy and anti-corruption code of conduct.",
            "review_required": True,
            "is_quarantined_evidence": False,
            "downstream_use_policy": "review_before_extraction",
        },
        {
            "evidence_id": "ev_risk",
            "document_id": "lvmh_2024_test",
            "evidence_type": "paragraph",
            "source_modality": "text",
            "page_number": 4,
            "section_id": "sec_2",
            "quote": "Climate risk and transition risk may affect operations.",
            "review_required": True,
            "is_quarantined_evidence": False,
            "downstream_use_policy": "review_before_extraction",
        },
        {
            "evidence_id": "ev_method",
            "document_id": "lvmh_2024_test",
            "evidence_type": "paragraph",
            "source_modality": "text",
            "page_number": 5,
            "section_id": "sec_3",
            "quote": "Emissions are calculated according to the GHG Protocol and ESRS standards.",
            "review_required": True,
            "is_quarantined_evidence": False,
            "downstream_use_policy": "review_before_extraction",
        },
        {
            "evidence_id": "ev_table",
            "document_id": "lvmh_2024_test",
            "evidence_type": "table",
            "source_modality": "table",
            "page_number": 6,
            "section_id": "sec_3",
            "quote": "Table detected on page 6 with 8 rows and 5 columns",
            "review_required": True,
            "is_quarantined_evidence": False,
            "downstream_use_policy": "review_before_extraction",
        },
    ])
    return input_dir


def run_cli(input_dir: Path, output_dir: Path):
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def test_typed_csv_files_are_produced_with_stable_schema(tmp_path: Path):
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    for file_name in TYPED_FILES:
        path = output_dir / file_name
        assert path.exists()
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            assert reader.fieldnames == CANDIDATE_FIELDS


def test_typed_csv_files_only_contain_their_information_type(tmp_path: Path):
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    for file_name, information_type in TYPED_FILES.items():
        rows = read_csv(output_dir / file_name)
        assert all(row["information_type"] == information_type for row in rows)
        assert all(row["extraction_status"] == "candidate_only" for row in rows)
        assert all(row["review_required"] == "True" for row in rows)


def test_global_csv_is_kept_and_summary_reports_typed_counts(tmp_path: Path):
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_dir, output_dir)
    assert result.returncode == 0, result.stdout

    assert (output_dir / "esg_information_candidates.csv").exists()
    assert (output_dir / "esg_information_candidates.jsonl").exists()
    summary = json.loads((output_dir / "extraction_summary.json").read_text(encoding="utf-8"))
    assert "typed_csv_counts" in summary
    for file_name in TYPED_FILES:
        assert file_name in summary["typed_csv_counts"]

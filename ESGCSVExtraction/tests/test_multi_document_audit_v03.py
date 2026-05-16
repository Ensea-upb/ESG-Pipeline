from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLI = PROJECT_ROOT / "ESGCSVExtraction" / "scripts" / "run_multi_document_audit.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def hash_tree(path: Path) -> dict[str, str]:
    return {
        str(file.relative_to(path)): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def make_doc(root: Path, name: str, quote: str) -> Path:
    doc = root / name
    doc.mkdir(parents=True)
    write_json(doc / "document_inventory.json", {
        "document_id": name,
        "pdf_path": f"C:/Users/hp/Desktop/ESG/ESGFinalCorpus/{name}/2024/doc/document.pdf",
    })
    write_json(doc / "extraction_summary.json", {"document_id": name, "status": "success"})
    write_jsonl(doc / "multimodal_evidence_index.jsonl", [
        {
            "evidence_id": f"{name}_ev_001",
            "document_id": name,
            "evidence_type": "paragraph",
            "source_modality": "text",
            "page_number": 1,
            "section_id": f"{name}_sec_001",
            "quote": quote,
            "review_required": False,
            "is_quarantined_evidence": False,
            "downstream_use_policy": "eligible_for_future_extraction",
        }
    ])
    return doc


def make_input_root(tmp_path: Path) -> Path:
    root = tmp_path / "inputs"
    root.mkdir()
    make_doc(root, "lvmh_2024_doc", "The Group reported emissions of 12,500 tCO2e in 2024.")
    make_doc(root, "totalenergies_2024_doc", "The company has a target to reduce energy by 30% by 2030.")
    (root / "not_an_output").mkdir()
    return root


def run_cli(input_root: Path, output_dir: Path, *extra: str):
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--input-root",
            str(input_root),
            "--output-dir",
            str(output_dir),
            *extra,
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def test_multi_document_audit_produces_expected_files(tmp_path: Path):
    input_root = make_input_root(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_root, output_dir)
    assert result.returncode == 0, result.stdout

    assert (output_dir / "multi_document_candidate_audit_summary.json").exists()
    assert (output_dir / "multi_document_candidate_audit.csv").exists()
    assert (output_dir / "multi_document_candidate_audit.md").exists()


def test_multi_document_audit_counts_documents_and_candidates(tmp_path: Path):
    input_root = make_input_root(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_root, output_dir)
    payload = json.loads(result.stdout)
    assert result.returncode == 0, result.stdout
    assert payload["documents_tested_count"] == 2
    assert payload["total_candidates_count"] >= 2

    summary = read_json(output_dir / "multi_document_candidate_audit_summary.json")
    assert summary["documents_tested_count"] == 2
    assert summary["confidence_above_0_6_total"] == 0
    assert summary["review_required_missing_or_false_total"] == 0


def test_multi_document_audit_csv_has_expected_columns(tmp_path: Path):
    input_root = make_input_root(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_root, output_dir)
    assert result.returncode == 0, result.stdout

    with (output_dir / "multi_document_candidate_audit.csv").open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames == [
            "input_dir",
            "output_dir",
            "document_id",
            "status",
            "candidates_count",
            "observed_metric_without_unit",
            "target_without_target_year",
            "visual_evidence_low_confidence",
            "confidence_above_0_6",
            "review_required_missing_or_false",
            "information_type_distribution",
        ]
        rows = list(reader)
    assert len(rows) == 2


def test_multi_document_audit_markdown_contains_title(tmp_path: Path):
    input_root = make_input_root(tmp_path)
    output_dir = tmp_path / "out"
    result = run_cli(input_root, output_dir)
    assert result.returncode == 0, result.stdout

    markdown = (output_dir / "multi_document_candidate_audit.md").read_text(encoding="utf-8")
    assert "Multi-document Candidate Audit" in markdown
    assert "Gate Decision" in markdown


def test_multi_document_audit_does_not_modify_inputs(tmp_path: Path):
    input_root = make_input_root(tmp_path)
    before = hash_tree(input_root)
    output_dir = tmp_path / "out"
    result = run_cli(input_root, output_dir)
    assert result.returncode == 0, result.stdout
    after = hash_tree(input_root)
    assert before == after


def test_multi_document_audit_overwrite_guard(tmp_path: Path):
    input_root = make_input_root(tmp_path)
    output_dir = tmp_path / "out"
    first = run_cli(input_root, output_dir)
    assert first.returncode == 0, first.stdout
    second = run_cli(input_root, output_dir)
    assert second.returncode != 0
    payload = json.loads(second.stdout)
    assert payload["status"] == "failed"
    third = run_cli(input_root, output_dir, "--overwrite")
    assert third.returncode == 0, third.stdout

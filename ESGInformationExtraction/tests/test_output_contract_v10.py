from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .conftest import PROJECT_ROOT, read_json, read_jsonl, run_cli


CONTRACT_DOC = PROJECT_ROOT / "ESGInformationExtraction" / "docs" / "OUTPUT_CONTRACT_V1.md"
CONTRACT_JSON = PROJECT_ROOT / "ESGInformationExtraction" / "contracts" / "output_contract_v1.json"
VALIDATOR = PROJECT_ROOT / "ESGInformationExtraction" / "tools" / "validate_output_contract.py"


def _validate(output_dir: Path):
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--output-dir",
            str(output_dir),
            "--contract-path",
            str(CONTRACT_JSON),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def test_contract_document_exists():
    assert CONTRACT_DOC.exists()


def test_contract_json_exists_and_version():
    contract = read_json(CONTRACT_JSON)
    assert contract["engine_contract_version"] == "1.0.0"


def test_validator_exists():
    assert VALIDATOR.exists()


def test_validator_succeeds_on_valid_output(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="v10_valid")
    assert result.returncode == 0, result.stderr

    validation = _validate(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode == 0, validation.stdout
    assert payload["status"] == "success"
    assert payload["contract_version"] == "1.0.0"
    assert payload["errors_count"] == 0


def test_validator_fails_when_required_file_missing(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="v10_missing_file")
    assert result.returncode == 0, result.stderr
    (output_dir / "evidence_store.jsonl").unlink()

    validation = _validate(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode != 0
    assert payload["status"] == "failed"
    assert any("evidence_store.jsonl" in error for error in payload["errors"])


def test_validator_fails_when_required_field_missing(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="v10_missing_field")
    assert result.returncode == 0, result.stderr
    records = read_jsonl(output_dir / "multimodal_evidence_index.jsonl")
    records[0].pop("downstream_use_policy", None)
    (output_dir / "multimodal_evidence_index.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    validation = _validate(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode != 0
    assert any("downstream_use_policy" in error for error in payload["errors"])


def test_validator_detects_invalid_downstream_policy(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="v10_invalid_policy")
    assert result.returncode == 0, result.stderr
    records = read_jsonl(output_dir / "multimodal_evidence_index.jsonl")
    records[0]["downstream_use_policy"] = "bad_policy"
    (output_dir / "multimodal_evidence_index.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    validation = _validate(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode != 0
    assert any("bad_policy" in error for error in payload["errors"])


def test_validator_detects_quarantine_marked_eligible(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="v10_quarantine_eligible")
    assert result.returncode == 0, result.stderr
    records = read_jsonl(output_dir / "multimodal_evidence_index.jsonl")
    records[0]["is_quarantined_evidence"] = True
    records[0]["evidence_policy"] = "quarantine"
    records[0]["downstream_use_policy"] = "eligible_for_future_extraction"
    (output_dir / "multimodal_evidence_index.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    validation = _validate(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode != 0
    assert any("quarantined" in error.lower() for error in payload["errors"])


def test_extraction_summary_contains_contract_version(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir, document_id="v10_summary")
    assert result.returncode == 0, result.stderr
    summary = read_json(output_dir / "extraction_summary.json")
    assert summary["engine_contract_version"] == "1.0.0"

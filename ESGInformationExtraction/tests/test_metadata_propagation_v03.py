"""Tests for metadata propagation via CLI args in run_pdf_extraction.py — v0.3."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "ESGInformationExtraction" / "run_pdf_extraction.py"


def run_cli_with_metadata(
    pdf_path: Path,
    output_dir: Path,
    document_id: str = "doc_test_meta",
    company: str | None = None,
    fiscal_year: str | None = None,
    official_doc_type: str | None = None,
    company_slug: str | None = None,
    corpus_run_id: str | None = None,
    overwrite: bool = False,
):
    command = [
        sys.executable, str(SCRIPT_PATH),
        "--pdf-path", str(pdf_path),
        "--document-id", document_id,
        "--output-dir", str(output_dir),
        "--max-pages", "1",
    ]
    if overwrite:
        command.append("--overwrite")
    if company:
        command.extend(["--company", company])
    if fiscal_year:
        command.extend(["--fiscal-year", fiscal_year])
    if official_doc_type:
        command.extend(["--official-doc-type", official_doc_type])
    if company_slug:
        command.extend(["--company-slug", company_slug])
    if corpus_run_id:
        command.extend(["--corpus-run-id", corpus_run_id])
    return subprocess.run(command, text=True, capture_output=True, cwd=PROJECT_ROOT)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture
def require_pdfplumber():
    import importlib.util
    if importlib.util.find_spec("pdfplumber") is None:
        pytest.skip("pdfplumber is not installed")


@pytest.fixture
def small_pdf(tmp_path: Path) -> Path:
    """Create a minimal valid PDF for testing."""
    from ESGInformationExtraction.tests.conftest import write_test_pdf
    return write_test_pdf(
        tmp_path / "sample_meta.pdf",
        [["SUSTAINABILITY REPORT", "Company metadata propagation test."]]
    )


def test_company_and_fiscal_year_written_to_document_record(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    """--company and --fiscal-year must appear in document_record.json."""
    output_dir = tmp_path / "out_meta"
    result = run_cli_with_metadata(small_pdf, output_dir, company="TotalEnergies", fiscal_year="2024")
    assert result.returncode == 0, result.stderr

    record = _read_json(output_dir / "document_record.json")
    assert record.get("company") == "TotalEnergies"
    assert record.get("fiscal_year") == "2024"


def test_document_inventory_contains_company_and_fiscal_year(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    """document_inventory.json must contain company and fiscal_year from CLI args."""
    output_dir = tmp_path / "out_inv"
    result = run_cli_with_metadata(small_pdf, output_dir, company="TotalEnergies", fiscal_year="2024")
    assert result.returncode == 0, result.stderr

    inventory = _read_json(output_dir / "document_inventory.json")
    assert inventory.get("company") == "TotalEnergies"
    assert inventory.get("fiscal_year") == "2024"


def test_evidence_store_records_have_company_and_fiscal_year(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    """All records in evidence_store.jsonl must have company and fiscal_year."""
    output_dir = tmp_path / "out_ev"
    result = run_cli_with_metadata(small_pdf, output_dir, company="TotalEnergies", fiscal_year="2024")
    assert result.returncode == 0, result.stderr

    records = _read_jsonl(output_dir / "evidence_store.jsonl")
    assert records, "evidence_store.jsonl must not be empty"
    for rec in records:
        assert rec.get("company") == "TotalEnergies", f"company missing in evidence record: {rec.get('evidence_id')}"
        assert rec.get("fiscal_year") == "2024", f"fiscal_year missing in evidence record: {rec.get('evidence_id')}"


def test_multimodal_evidence_index_records_have_company_and_fiscal_year(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    """All records in multimodal_evidence_index.jsonl must have company and fiscal_year."""
    output_dir = tmp_path / "out_mm"
    result = run_cli_with_metadata(small_pdf, output_dir, company="TotalEnergies", fiscal_year="2024")
    assert result.returncode == 0, result.stderr

    records = _read_jsonl(output_dir / "multimodal_evidence_index.jsonl")
    assert records, "multimodal_evidence_index.jsonl must not be empty"
    for rec in records:
        assert rec.get("company") == "TotalEnergies", f"company missing in multimodal record: {rec.get('evidence_id')}"
        assert rec.get("fiscal_year") == "2024", f"fiscal_year missing in multimodal record: {rec.get('evidence_id')}"


def test_run_without_company_still_works_backward_compat(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    """Running without --company must still succeed (backward compatibility)."""
    output_dir = tmp_path / "out_nocompany"
    result = run_cli_with_metadata(small_pdf, output_dir)  # no company, no fiscal_year
    assert result.returncode == 0, result.stderr

    record = _read_json(output_dir / "document_record.json")
    assert record.get("document_id") == "doc_test_meta"
    # company should not be present (not injected)
    assert "company" not in record or record.get("company") is None or record.get("company") == ""


def test_additional_optional_metadata_written_to_document_record(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    """Other optional metadata fields (official_doc_type, company_slug, corpus_run_id) must appear in document_record."""
    output_dir = tmp_path / "out_extra"
    result = run_cli_with_metadata(
        small_pdf, output_dir,
        company="TotalEnergies",
        fiscal_year="2024",
        official_doc_type="URD",
        company_slug="totalenergies",
        corpus_run_id="run_2024_001",
    )
    assert result.returncode == 0, result.stderr

    record = _read_json(output_dir / "document_record.json")
    assert record.get("official_doc_type") == "URD"
    assert record.get("company_slug") == "totalenergies"
    assert record.get("corpus_run_id") == "run_2024_001"


def test_fiscal_year_not_overwritten_by_evidence_year(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    """fiscal_year in document_record.json must stay as the CLI value, unaffected by content years."""
    output_dir = tmp_path / "out_fy"
    result = run_cli_with_metadata(small_pdf, output_dir, company="TotalEnergies", fiscal_year="2024")
    assert result.returncode == 0, result.stderr

    record = _read_json(output_dir / "document_record.json")
    assert record.get("fiscal_year") == "2024", "fiscal_year must not be overwritten by content"

    # Check that evidence store records have fiscal_year=2024 not year_raw-like values
    ev_records = _read_jsonl(output_dir / "evidence_store.jsonl")
    for rec in ev_records:
        if "fiscal_year" in rec:
            assert rec["fiscal_year"] == "2024", f"fiscal_year overwritten in evidence record {rec.get('evidence_id')}"

from __future__ import annotations

import hashlib
from pathlib import Path

from .conftest import read_json, run_cli


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pdf_source_is_not_modified(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    before_hash = _sha256(small_pdf)
    before_bytes = small_pdf.read_bytes()
    output_dir = tmp_path / "out"

    result = run_cli(small_pdf, output_dir)

    assert result.returncode == 0, result.stderr
    assert _sha256(small_pdf) == before_hash
    assert small_pdf.read_bytes() == before_bytes
    document = read_json(output_dir / "document_record.json")
    assert document["sha256"] == before_hash


def test_refuses_to_write_in_source_directory(require_pdfplumber, small_pdf: Path):
    result = run_cli(small_pdf, small_pdf.parent)

    assert result.returncode != 0
    assert "source directory" in result.stderr or "source directory" in result.stdout

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_scripts_documentation_exists() -> None:
    text = (ROOT / "LEGACY_SCRIPTS.md").read_text(encoding="utf-8")
    assert "run_pdf_extraction.py" in text
    assert "run_extraction_test.py" in text
    assert "active" in text


def test_run_extraction_test_has_legacy_warning() -> None:
    text = (ROOT / "run_extraction_test.py").read_text(encoding="utf-8")
    assert "LEGACY WARNING" in text
    assert "ESGInformationExtraction/run_pdf_extraction.py" in text

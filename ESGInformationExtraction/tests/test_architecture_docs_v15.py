from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_module_usage_map_and_adr_exist():
    usage = ROOT / "ESGInformationExtraction" / "docs" / "MODULE_USAGE_MAP_V1_5.md"
    adr = ROOT / "ESGInformationExtraction" / "docs" / "ADR_002_SCHEMA_ARCHITECTURE_HYGIENE_V1_5.md"
    assert usage.exists()
    assert adr.exists()
    usage_text = usage.read_text(encoding="utf-8")
    adr_text = adr.read_text(encoding="utf-8")
    assert "run_pdf_extraction.py" in usage_text
    assert "legacy_or_experimental" in usage_text
    assert "Instructions for future coding agents" in adr_text
    assert "run_pdf_extraction.py is the active engine" in adr_text

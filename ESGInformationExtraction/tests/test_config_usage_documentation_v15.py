from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_config_usage_documentation_exists_and_metric_catalog_not_imported():
    doc = ROOT / "ESGInformationExtraction" / "docs" / "CONFIG_USAGE_V1_5.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "metric_catalog_v0.yaml" in text
    assert "reserved for downstream ESG layers" in text
    assert "section_taxonomy_v0.yaml" in text
    engine = (ROOT / "ESGInformationExtraction" / "run_pdf_extraction.py").read_text(encoding="utf-8")
    assert "metric_catalog_v0.yaml" not in engine

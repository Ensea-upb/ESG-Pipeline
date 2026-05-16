from pathlib import Path


def test_release_docs_exist():
    root = Path(__file__).resolve().parents[2] / "ESGIndicatorValidation"
    assert (root / "README.md").exists()
    assert (root / "docs" / "INDICATOR_VALIDATION_CONTRACT_V0.md").exists()
    assert (root / "docs" / "RELEASE_NOTES_V1_0.md").exists()
    assert (root / "docs" / "ARCHITECTURE_OVERVIEW_V1_0.md").exists()
    assert (root / "docs" / "VALIDATION_COMMANDS_V1_0.md").exists()

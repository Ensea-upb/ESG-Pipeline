from pathlib import Path


def test_release_docs_exist():
    root = Path(__file__).resolve().parents[2] / "ESGManualReview"
    assert (root / "README.md").exists()
    assert (root / "docs" / "MANUAL_REVIEW_CONTRACT_V0.md").exists()
    assert (root / "docs" / "RELEASE_NOTES_V1_0.md").exists()
    assert (root / "docs" / "ARCHITECTURE_OVERVIEW_V1_0.md").exists()
    assert (root / "docs" / "VALIDATION_COMMANDS_V1_0.md").exists()
    assert (root / "docs" / "REVIEW_GUIDE_V1_0.md").exists()

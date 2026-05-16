from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "ESGTableExtraction"


def test_release_docs_exist():
    assert (ROOT / "README.md").exists()
    assert (ROOT / "docs" / "TABLE_OUTPUT_CONTRACT_V0.md").exists()
    assert (ROOT / "docs" / "RELEASE_NOTES_V1_0.md").exists()
    assert (ROOT / "docs" / "ARCHITECTURE_OVERVIEW_V1_0.md").exists()
    assert (ROOT / "docs" / "VALIDATION_COMMANDS_V1_0.md").exists()


def test_readme_states_no_scores():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "candidate-only" in text
    assert "does not produce scores" in text

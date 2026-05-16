from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_release_documentation_exists():
    docs = PROJECT_ROOT / "ESGCSVExtraction" / "docs"
    assert (docs / "RELEASE_NOTES_V1_0.md").exists()
    assert (docs / "ARCHITECTURE_OVERVIEW_V1_0.md").exists()
    assert (docs / "VALIDATION_COMMANDS_V1_0.md").exists()


def test_release_docs_state_candidate_only_scope():
    text = (PROJECT_ROOT / "ESGCSVExtraction" / "docs" / "RELEASE_NOTES_V1_0.md").read_text(encoding="utf-8")
    assert "Candidate-only" in text or "candidate-only" in text
    assert "No ESG score" in text
    assert "No modification" in text


def test_architecture_keeps_esg_validation_separate():
    text = (PROJECT_ROOT / "ESGCSVExtraction" / "docs" / "ARCHITECTURE_OVERVIEW_V1_0.md").read_text(encoding="utf-8")
    assert "Future ESG layer" in text
    assert "CSV candidates only" in text

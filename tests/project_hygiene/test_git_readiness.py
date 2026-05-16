from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_gitignore_contains_project_hygiene_patterns() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in [
        "__pycache__/",
        "*.py[cod]",
        ".pytest_cache/",
        ".pytest_tmp/",
        "ESGInformationExtraction/outputs/",
        "ESGProductionControlCenter/runs/",
        "ESGFinalCorpus/",
        "data/dossier_ingestion_0/",
    ]:
        assert pattern in text


def test_git_setup_guide_exists() -> None:
    text = (ROOT / "GIT_SETUP_GUIDE.md").read_text(encoding="utf-8")
    assert "git init" in text
    assert "Do Not Version" in text

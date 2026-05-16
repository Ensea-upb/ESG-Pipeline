from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_requirements_checker_passes() -> None:
    result = subprocess.run(
        [sys.executable, "tools/check_requirements.py", "--project-root", "."],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_requirements_notes_exist() -> None:
    text = (ROOT / "REQUIREMENTS_NOTES.md").read_text(encoding="utf-8")
    assert "Python 3.13" in text
    assert "pytest" in text

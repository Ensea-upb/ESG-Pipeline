from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "clean_python_artifacts.py"


def test_clean_python_artifacts_dry_run_does_not_delete(tmp_path: Path) -> None:
    cache_dir = tmp_path / "pkg" / "__pycache__"
    cache_dir.mkdir(parents=True)
    pyc = cache_dir / "module.pyc"
    pyc.write_bytes(b"cache")
    report = tmp_path / "cleanup.json"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(tmp_path), "--dry-run", "--report-path", str(report)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert cache_dir.exists()
    assert pyc.exists()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["total"] >= 1
    assert report.with_suffix(".md").exists()


def test_clean_python_artifacts_execute_is_limited_to_caches(tmp_path: Path) -> None:
    cache_dir = tmp_path / "pkg" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "module.pyc").write_bytes(b"cache")
    output_pdf = tmp_path / "ESGInformationExtraction" / "outputs" / "document.pdf"
    output_pdf.parent.mkdir(parents=True)
    output_pdf.write_bytes(b"%PDF fake")
    manifest = output_pdf.parent / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    report = tmp_path / "cleanup.json"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(tmp_path), "--execute", "--report-path", str(report)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not cache_dir.exists()
    assert output_pdf.exists()
    assert manifest.exists()

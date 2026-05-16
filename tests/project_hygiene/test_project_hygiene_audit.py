from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_project_hygiene_audit_produces_reports(tmp_path: Path) -> None:
    project = tmp_path / "project"
    test_dir = project / "SampleModule" / "tests"
    test_dir.mkdir(parents=True)
    (test_dir / "helpers.py").write_text("VALUE = 1\n", encoding="utf-8")
    (test_dir / "test_sample.py").write_text("from helpers import VALUE\n", encoding="utf-8")

    output_dir = tmp_path / "audit"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "project_hygiene_audit.py"),
            "--project-root",
            str(project),
            "--output-dir",
            str(output_dir),
            "--overwrite",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report_path = output_dir / "project_hygiene_report.json"
    findings_path = output_dir / "project_hygiene_findings.jsonl"
    markdown_path = output_dir / "project_hygiene_report.md"

    assert report_path.exists()
    assert findings_path.exists()
    assert markdown_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["test_helpers"]["helpers_py"]
    assert report["test_helpers"]["from_helpers_imports"]

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ESGInformationExtraction" / "tools" / "audit_engine_architecture.py"


def _hash_tree(path: Path) -> dict[str, str]:
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob("*")) if p.is_file()}


def test_architecture_audit_outputs(tmp_path: Path):
    project = ROOT / "ESGInformationExtraction"
    before = _hash_tree(project / "schemas")
    out = tmp_path / "architecture"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-root", str(ROOT), "--output-dir", str(out), "--overwrite"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout
    assert (out / "architecture_hygiene_report.json").exists()
    assert (out / "architecture_hygiene_findings.jsonl").exists()
    assert (out / "architecture_hygiene_report.md").exists()
    report = json.loads((out / "architecture_hygiene_report.json").read_text(encoding="utf-8"))
    assert report["active_engine"]["path"] == "run_pdf_extraction.py"
    assert any(item["path"] == "parsing/" for item in report["module_candidates"])
    assert before == _hash_tree(project / "schemas")

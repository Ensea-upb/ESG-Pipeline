from __future__ import annotations

import json
from pathlib import Path

from .conftest import run_cli


def test_jsonl_outputs_are_valid_one_object_per_line(require_pdfplumber, small_pdf: Path, tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_cli(small_pdf, output_dir)
    assert result.returncode == 0, result.stderr

    for filename in ("page_index.jsonl", "text_blocks.jsonl", "quality_report.jsonl"):
        path = output_dir / filename
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert lines, f"{filename} should not be empty"
        for line in lines:
            payload = json.loads(line)
            assert isinstance(payload, dict)

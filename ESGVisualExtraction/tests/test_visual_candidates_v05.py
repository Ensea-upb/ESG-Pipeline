from __future__ import annotations

import csv
from pathlib import Path

from .helpers import make_visual_input, run_visual


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_visual_candidates_are_candidate_only(tmp_path: Path):
    input_dir = make_visual_input(tmp_path)
    output_dir = tmp_path / "out"
    result = run_visual(input_dir, output_dir)
    assert result.returncode == 0, result.stdout
    assert (output_dir / "visual_candidates.csv").exists()
    assert (output_dir / "visual_candidates.jsonl").exists()
    rows = read_csv(output_dir / "visual_candidates.csv")
    assert rows
    assert {row["review_required"] for row in rows} == {"True"}
    assert {row["extraction_status"] for row in rows} == {"candidate_only"}
    assert all(float(row["confidence"]) <= 0.5 for row in rows)
    assert all("score" not in key.lower() for key in rows[0])
    assert "validated_metric" not in rows[0]

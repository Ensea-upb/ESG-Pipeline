from __future__ import annotations

import csv
import json
from pathlib import Path

from .helpers import CONTRACT, make_visual_input, run_validator, run_visual


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def test_visual_contract_validates_valid_output(tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_visual(make_visual_input(tmp_path), output_dir)
    assert result.returncode == 0, result.stdout
    validation = run_validator(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode == 0, validation.stdout
    assert payload["status"] == "success"
    assert payload["errors_count"] == 0
    assert CONTRACT.exists()


def test_visual_contract_fails_on_review_required_false(tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_visual(make_visual_input(tmp_path), output_dir)
    assert result.returncode == 0, result.stdout
    headers, rows = read_csv(output_dir / "visual_candidates.csv")
    rows[0]["review_required"] = "False"
    write_csv(output_dir / "visual_candidates.csv", headers, rows)
    validation = run_validator(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode != 0
    assert any("review_required" in error for error in payload["errors"])


def test_visual_contract_fails_on_confidence_above_limit(tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_visual(make_visual_input(tmp_path), output_dir)
    assert result.returncode == 0, result.stdout
    headers, rows = read_csv(output_dir / "visual_candidates.csv")
    rows[0]["confidence"] = "0.9"
    write_csv(output_dir / "visual_candidates.csv", headers, rows)
    validation = run_validator(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode != 0
    assert any("confidence" in error for error in payload["errors"])


def test_visual_contract_fails_on_score_column(tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_visual(make_visual_input(tmp_path), output_dir)
    assert result.returncode == 0, result.stdout
    headers, rows = read_csv(output_dir / "visual_candidates.csv")
    headers.append("visual_score")
    write_csv(output_dir / "visual_candidates.csv", headers, rows)
    validation = run_validator(output_dir)
    payload = json.loads(validation.stdout)
    assert validation.returncode != 0
    assert any("forbidden" in error for error in payload["errors"])

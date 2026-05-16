from __future__ import annotations

import csv
import json
from pathlib import Path

from .helpers import make_input, read_json, run_full


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_reuse_existing_sub_engine_outputs(tmp_path: Path):
    input_dir = make_input(tmp_path)
    output_dir = tmp_path / "out"
    first = run_full(input_dir, output_dir)
    assert first.returncode == 0, first.stdout

    second = run_full(input_dir, output_dir, "--overwrite", "--reuse-existing")
    assert second.returncode == 0, second.stdout
    payload = json.loads(second.stdout)
    manifest = payload["engine_run_manifest"]
    assert {item["status"] for item in manifest.values()} == {"reused_existing"}

    summary = read_json(output_dir / "full_extraction_summary.json")
    assert summary["reuse_existing"] is True
    assert summary["force_rerun"] is False


def test_force_rerun_and_reuse_existing_are_mutually_exclusive(tmp_path: Path):
    result = run_full(make_input(tmp_path), tmp_path / "out", "--reuse-existing", "--force-rerun")
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "cannot be used together" in payload["errors"][0]


def test_deduplication_outputs_are_audited_and_non_destructive(tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_full(make_input(tmp_path), output_dir)
    assert result.returncode == 0, result.stdout

    assert (output_dir / "consolidated_unique_candidates.csv").exists()
    assert (output_dir / "consolidated_unique_candidates.jsonl").exists()
    assert (output_dir / "consolidated_duplicate_groups.csv").exists()
    assert (output_dir / "consolidated_duplicate_groups.jsonl").exists()

    all_rows = read_csv(output_dir / "consolidated_candidates.csv")
    unique_rows = read_csv(output_dir / "consolidated_unique_candidates.csv")
    assert all_rows
    assert len(unique_rows) <= len(all_rows)
    assert all(row["deduplication_status"] in {"unique_candidate", "canonical_candidate", "duplicate_candidate"} for row in all_rows)
    assert "normalized_candidate_key" in all_rows[0]


def test_summary_contains_v11_deduplication_and_type_counters(tmp_path: Path):
    output_dir = tmp_path / "out"
    result = run_full(make_input(tmp_path), output_dir)
    assert result.returncode == 0, result.stdout
    summary = read_json(output_dir / "full_extraction_summary.json")
    assert "unique_candidates_count" in summary
    assert "duplicate_candidates_count" in summary
    assert "duplicate_groups_count" in summary
    assert "source_engine_information_type_distribution" in summary
    assert "deduplication_status_distribution" in summary

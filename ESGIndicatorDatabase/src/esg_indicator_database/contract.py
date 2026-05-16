from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def validate_indicator_database_outputs(output_dir: Path, contract_path: Path) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    checks = 0
    for name in contract.get("required_files", []):
        checks += 1
        if not (output_dir / name).exists():
            errors.append(f"required file missing: {name}")
    rows = _read_csv(output_dir / "indicator_preparation_database.csv")
    headers = list(rows[0].keys()) if rows else _headers(output_dir / "indicator_preparation_database.csv")
    missing = [field for field in contract.get("required_columns", []) if field not in headers]
    if missing:
        errors.append(f"missing columns: {missing}")
    forbidden = [h for h in headers if "score" in h.lower() and h != "score_produced"]
    if forbidden:
        errors.append(f"forbidden score columns: {forbidden}")
    links = _read_csv(output_dir / "indicator_evidence_links.csv")
    lineage = _read_jsonl(output_dir / "indicator_lineage.jsonl")
    link_ids = {row.get("preparation_indicator_id") for row in links}
    lineage_ids = {row.get("preparation_indicator_id") for row in lineage}
    for line_no, row in enumerate(rows, start=2):
        checks += 1
        if row.get("indicator_database_status") != "preparation_only":
            errors.append(f"{line_no}: indicator_database_status must be preparation_only")
        if row.get("is_final_indicator") != "False":
            errors.append(f"{line_no}: is_final_indicator must be False")
        if row.get("score_produced") != "False":
            errors.append(f"{line_no}: score_produced must be False")
        if row.get("preparation_indicator_id") not in link_ids:
            errors.append(f"{line_no}: missing evidence link")
        if row.get("preparation_indicator_id") not in lineage_ids:
            errors.append(f"{line_no}: missing lineage")
    return {"status": "success" if not errors else "failed", "contract_version": contract.get("contract_version", "unknown"), "output_dir": str(output_dir), "checks_count": checks, "errors_count": len(errors), "warnings_count": 0, "errors": errors, "warnings": []}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _headers(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file).fieldnames or [])


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

"""Contract validation for targeted_candidates_v2 outputs."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .io_utils import read_csv, read_json

_REQUIRED_COLS = [
    "candidate_id", "schema_version", "engine", "target_variable",
    "indicator_family", "document_id", "company", "company_slug",
    "fiscal_year", "official_doc_type", "page_number", "source_type",
    "raw_value", "raw_unit", "quote", "candidate_status",
]

_ALLOWED_STATUSES = {
    "candidate_found", "needs_review",
    "rejected_structural_noise", "rejected_unit_mismatch",
    "rejected_no_value", "rejected_no_evidence", "rejected_low_relevance",
}


def validate_candidates_against_contract(
    candidates: list[dict[str, Any]],
    contract_path: str | Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if contract_path:
        contract = read_json(contract_path)
        required_cols = contract.get("required_columns", _REQUIRED_COLS)
        allowed_statuses = set(contract.get("allowed_candidate_statuses", list(_ALLOWED_STATUSES)))
    else:
        required_cols = _REQUIRED_COLS
        allowed_statuses = _ALLOWED_STATUSES

    if not candidates:
        return {
            "status": "warning",
            "errors": [],
            "warnings": ["No candidates found — output is empty."],
            "total_candidates": 0,
            "valid_candidates": 0,
            "invalid_candidates": 0,
        }

    first = candidates[0]
    missing_cols = [c for c in required_cols if c not in first]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")

    valid = 0
    invalid = 0
    for i, cand in enumerate(candidates):
        row_errors: list[str] = []
        doc_id = cand.get("document_id", "")
        company = cand.get("company", "")
        fiscal_year = cand.get("fiscal_year", "")
        status = cand.get("candidate_status", "")
        quote = cand.get("quote", "")
        raw_value = cand.get("raw_value", "")

        if not doc_id:
            row_errors.append(f"Row {i}: document_id is empty")
        if not company:
            row_errors.append(f"Row {i}: company is empty")
        if not fiscal_year:
            row_errors.append(f"Row {i}: fiscal_year is empty")
        if status not in allowed_statuses:
            row_errors.append(f"Row {i}: invalid candidate_status '{status}'")
        if status in ("candidate_found", "needs_review") and not quote:
            row_errors.append(f"Row {i}: quote is empty for status '{status}'")
        if status == "candidate_found" and not raw_value:
            row_errors.append(f"Row {i}: raw_value is empty for candidate_found")

        if _is_iso_standard_value(raw_value):
            row_errors.append(f"Row {i}: raw_value looks like ISO standard number: '{raw_value}'")

        if row_errors:
            invalid += 1
            errors.extend(row_errors)
        else:
            valid += 1

    overall = "ok" if not errors else ("warning" if not [e for e in errors if "Row" not in e] else "failed")
    return {
        "status": overall,
        "errors": errors,
        "warnings": warnings,
        "total_candidates": len(candidates),
        "valid_candidates": valid,
        "invalid_candidates": invalid,
    }


def validate_output_dir(
    output_dir: str | Path,
    contract_path: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    candidates_path = output_dir / "targeted_candidates_v2.csv"

    if not candidates_path.exists():
        return {
            "status": "failed",
            "errors": [f"targeted_candidates_v2.csv not found in {output_dir}"],
            "warnings": [],
        }

    records = read_csv(candidates_path)
    result = validate_candidates_against_contract(records, contract_path)

    summary_path = output_dir / "extraction_v2_summary.json"
    if not summary_path.exists():
        result["warnings"].append("extraction_v2_summary.json not found")

    result["output_dir"] = str(output_dir)
    return result


_KNOWN_ISO_ESG = frozenset({
    "9001", "14001", "14004", "14006", "14025", "14031",
    "14040", "14044", "14046", "14064", "14067", "14068",
    "20121", "20400", "26000", "37001", "45001", "50001", "55001",
})

_ISO_PREFIX_PAT_V = re.compile(r"^ISO\s*(\d{4,5})$", re.IGNORECASE)
_ISO_BARE_PAT_V = re.compile(r"^\d{4,5}$")


def _is_iso_standard_value(value: str) -> bool:
    if not value:
        return False
    v = value.strip()
    if _ISO_PREFIX_PAT_V.match(v):
        return True
    if _ISO_BARE_PAT_V.match(v):
        return v in _KNOWN_ISO_ESG
    return False

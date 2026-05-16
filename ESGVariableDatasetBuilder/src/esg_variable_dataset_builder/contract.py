from __future__ import annotations

import json
from pathlib import Path

from .variable_dictionary import ALLOWED_STATUSES, FINAL_VARIABLES


def default_contract() -> dict[str, object]:
    return {
        "contract_name": "esg_variables_dataset_contract_v0",
        "schema_version": "v0",
        "unit_of_observation": "company_year",
        "main_dataset": "esg_variables_dataset.csv",
        "enriched_dataset": "esg_variables_dataset_enriched.csv",
        "long_dataset": "esg_variables_long.csv",
        "evidence_dataset": "esg_variables_evidence.csv",
        "quality_report": "esg_variables_quality_report.json",
        "variables": FINAL_VARIABLES,
        "allowed_statuses": sorted(ALLOWED_STATUSES),
        "forbidden_columns_contains": ["score"],
        "external_sources_allowed": False,
        "score_allowed": False,
        "found_requires_evidence": True,
    }


def write_default_contract(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default_contract(), indent=2) + "\n", encoding="utf-8")

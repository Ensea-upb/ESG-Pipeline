from __future__ import annotations

from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DICTIONARY_PATH = MODULE_DIR / "config" / "esg_variable_dictionary_v0.yaml"
DEFAULT_CONTRACT_PATH = MODULE_DIR / "contracts" / "esg_variables_dataset_contract_v0.json"

PRIORITY_INPUT_FILES = [
    "indicator_preparation_database.csv",
    "indicator_evidence_links.csv",
    "indicator_lineage.jsonl",
    "indicator_database_audit_summary.json",
    "indicator_database_summary.json",
]

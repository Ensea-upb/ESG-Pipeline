from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


FINAL_VARIABLES = [
    "co2_emissions", "carbon_intensity", "energy_consumption", "water_consumption", "waste",
    "biodiversity", "fossil_exposure", "turnover", "diversity", "work_accidents",
    "human_capital", "supply_chain", "human_rights", "board_independence",
    "ceo_chairman_separation", "remuneration", "shareholder_rights", "transparency",
    "esg_scandals", "fraud", "corruption", "pollution", "lawsuits", "social_controversies",
    "market_cap", "volatility", "leverage", "roa", "roe", "liquidity", "stock_returns",
]

ALLOWED_STATUSES = {
    "found",
    "missing_from_corpus",
    "needs_review",
    "qualitative_only",
    "conflicting_values",
    "not_disclosed",
}


def dictionary_path(project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    return root / "ESGVariableDatasetBuilder" / "config" / "esg_variable_dictionary_v0.yaml"


def load_variable_dictionary(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or dictionary_path()
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    variables = data.get("variables", [])
    return variables


def variable_by_name(path: Path | None = None) -> dict[str, dict[str, Any]]:
    return {item["variable_name"]: item for item in load_variable_dictionary(path)}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

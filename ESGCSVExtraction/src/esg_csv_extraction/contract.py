from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def default_contract_path() -> Path:
    return Path(__file__).resolve().parents[2] / "contracts" / "csv_output_contract_v0.json"


__all__ = ["default_contract_path", "load_contract"]

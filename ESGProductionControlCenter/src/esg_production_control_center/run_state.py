from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_run_state(run_dir: str | Path) -> dict[str, Any]:
    path = Path(run_dir) / "run_state.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def list_runs(runs_dir: str | Path) -> list[dict[str, Any]]:
    states = []
    root = Path(runs_dir)
    if not root.exists():
        return states
    for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        state = load_run_state(run_dir)
        if state:
            state["run_dir"] = str(run_dir)
            states.append(state)
    return states

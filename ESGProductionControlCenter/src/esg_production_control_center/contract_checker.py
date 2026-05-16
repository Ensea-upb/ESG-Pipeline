from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .command_builder import build_validation_command


def validate_contract(module_name: str, output_dir: str | Path, results_dir: str | Path, project_root: str | Path = ".", stop_on_contract_failure: bool = True) -> dict[str, Any]:
    plan = build_validation_command(module_name, output_dir, project_root)
    proc = subprocess.run(plan["command"], text=True, capture_output=True)
    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(proc.stdout)
    except Exception:
        parsed = {}
    result = {
        "module_name": module_name,
        "output_dir": str(output_dir),
        "contract_path": plan["contract_path"],
        "validation_status": parsed.get("status") or ("success" if proc.returncode == 0 else "failed"),
        "checks_count": parsed.get("checks_count", 0),
        "errors_count": parsed.get("errors_count", 0 if proc.returncode == 0 else 1),
        "warnings_count": parsed.get("warnings_count", 0),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
        "next_step_allowed": not (stop_on_contract_failure and proc.returncode != 0),
    }
    write_contract_results(results_dir, [result], overwrite=True)
    return result


def write_contract_results(results_dir: str | Path, results: list[dict[str, Any]], overwrite: bool = False) -> list[str]:
    out = Path(results_dir)
    out.mkdir(parents=True, exist_ok=True)
    jsonl = out / "contract_validation_results.jsonl"
    summary = out / "contract_validation_summary.json"
    if not overwrite and (jsonl.exists() or summary.exists()):
        raise FileExistsError("Refusing to overwrite contract validation results")
    jsonl.write_text("".join(json.dumps(r) + "\n" for r in results), encoding="utf-8")
    summary.write_text(json.dumps({
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validations_count": len(results),
        "failed_count": sum(1 for r in results if r.get("validation_status") != "success"),
    }, indent=2), encoding="utf-8")
    return [str(jsonl), str(summary)]

from __future__ import annotations

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_command(plan: dict[str, Any], runs_dir: str | Path, allow_execute: bool = False, timeout_seconds: int = 300) -> dict[str, Any]:
    run_id = f"{plan.get('module_name','command').lower()}_{uuid.uuid4().hex[:12]}"
    run_dir = Path(runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    started = _now()
    dry_run = bool(plan.get("dry_run", True))
    state = {
        "run_id": run_id,
        "module_name": plan.get("module_name"),
        "input_dir": plan.get("input_dir"),
        "output_dir": plan.get("output_dir"),
        "command": plan.get("command", []),
        "started_at": started,
        "finished_at": None,
        "status": "dry_run" if dry_run else "pending",
        "returncode": None,
        "dry_run": dry_run,
        "overwrite": bool(plan.get("overwrite", False)),
        "errors_count": 0,
        "warnings_count": 0,
    }
    (run_dir / "executed_command.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    if dry_run or not allow_execute:
        state["status"] = "dry_run"
        state["finished_at"] = _now()
        _write_run_files(run_dir, state, "", "")
        return state | {"run_dir": str(run_dir)}
    try:
        proc = subprocess.run(plan["command"], cwd=Path.cwd(), text=True, capture_output=True, timeout=timeout_seconds)
        stdout, stderr = proc.stdout, proc.stderr
        state["returncode"] = proc.returncode
        state["status"] = "success" if proc.returncode == 0 else "failed"
        state["errors_count"] = 0 if proc.returncode == 0 else 1
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\nTIMEOUT after {timeout_seconds}s"
        state["returncode"] = None
        state["status"] = "timeout"
        state["errors_count"] = 1
    state["finished_at"] = _now()
    _write_run_files(run_dir, state, stdout, stderr)
    return state | {"run_dir": str(run_dir)}


def _write_run_files(run_dir: Path, state: dict[str, Any], stdout: str, stderr: str) -> None:
    (run_dir / "run_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    (run_dir / "run_log.jsonl").write_text(json.dumps({"event": "run_finished", "state": state}) + "\n", encoding="utf-8")
    (run_dir / "command_stdout.txt").write_text(stdout, encoding="utf-8")
    (run_dir / "command_stderr.txt").write_text(stderr, encoding="utf-8")

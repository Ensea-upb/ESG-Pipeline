from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALLOWED_STATUSES = {"success", "failed", "timeout", "dry_run", "pending"}


def validate_control_center_output(output_dir: str | Path, contract_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(output_dir)
    errors: list[str] = []
    warnings: list[str] = []
    run_states = list(root.rglob("run_state.json"))
    for path in run_states:
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("status") not in ALLOWED_STATUSES:
            errors.append(f"invalid_status:{path}")
        if not (path.parent / "run_log.jsonl").exists():
            errors.append(f"missing_run_log:{path.parent}")
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".csv", ".json", ".jsonl", ".md", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            if (
                "validated_indicator=true" in text
                or "final_indicator=true" in text
                or '"final_indicator"=true' in text
                or '"validated_indicator": true' in text
                or '"final_indicator": true' in text
            ):
                errors.append(f"validated_or_final_indicator_detected:{path}")
            if "score_produced=true" in text or '"score_produced": true' in text:
                errors.append(f"score_detected:{path}")
    if not run_states:
        warnings.append("no_run_state_found")
    return {"status": "success" if not errors else "failed", "errors": errors, "warnings": warnings, "errors_count": len(errors), "warnings_count": len(warnings)}

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ALLOWED_DECISIONS = {"accept_candidate", "reject_candidate", "needs_more_evidence", "defer_decision", ""}


def load_workspace(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path) if Path(path).exists() else pd.DataFrame()


def validate_decisions(df: pd.DataFrame) -> list[dict[str, Any]]:
    findings = []
    for idx, row in df.iterrows():
        decision = str(row.get("proposed_decision", "") or "")
        if decision not in ALLOWED_DECISIONS:
            findings.append({"row": int(idx), "finding": "invalid_decision"})
        if decision == "accept_candidate":
            if not str(row.get("reviewer", "") or "").strip():
                findings.append({"row": int(idx), "finding": "accept_without_reviewer"})
            if not str(row.get("decision_reason", "") or "").strip():
                findings.append({"row": int(idx), "finding": "accept_without_decision_reason"})
    return findings


def export_decisions(df: pd.DataFrame, output_dir: str | Path, overwrite: bool = False) -> dict[str, Any]:
    findings = validate_decisions(df)
    if findings:
        return {"status": "failed", "findings": findings, "files_written": []}
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "review_decisions_filled.csv"
    summary_path = out / "review_decisions_export_summary.json"
    state_path = out / "review_editor_state.json"
    if not overwrite and any(p.exists() for p in [csv_path, summary_path, state_path]):
        raise FileExistsError("Refusing to overwrite review editor outputs")
    df.to_csv(csv_path, index=False)
    summary = {"status": "success", "decisions_count": int(len(df)), "accepted_candidate_is_not_validated_indicator": True}
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    state_path.write_text(json.dumps({"last_export": str(csv_path), "auto_acceptance": False}, indent=2), encoding="utf-8")
    return {"status": "success", "findings": [], "files_written": [str(csv_path), str(summary_path), str(state_path)]}

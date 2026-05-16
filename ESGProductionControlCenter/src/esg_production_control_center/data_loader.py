"""
data_loader.py — Load pilot run outputs for ESGProductionControlCenter v2.0.
Read-only. Never modifies source files.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

AUDIT_SUBDIR = "_review_quality_audit"
WORKSPACE_DIR = "04_review_workspace"
WORKSPACE_CSV = "manual_review_workspace.csv"


def load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_csv(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p, dtype=str, keep_default_na=False)
    except Exception:
        return pd.DataFrame()


def find_review_workspaces(run_root: str | Path) -> list[Path]:
    root = Path(run_root)
    if not root.exists():
        return []
    return sorted(root.rglob(WORKSPACE_DIR))


def load_pilot_summary(run_root: str | Path) -> dict[str, Any]:
    return load_json(Path(run_root) / "pilot_run_summary.json")


def load_review_quality_audit(run_root: str | Path) -> dict[str, Any]:
    return load_json(Path(run_root) / AUDIT_SUBDIR / "pilot_review_quality_summary.json")


def load_all_review_workspaces(run_root: str | Path) -> pd.DataFrame:
    ws_dirs = find_review_workspaces(run_root)
    root = Path(run_root)
    frames: list[pd.DataFrame] = []
    for ws_dir in ws_dirs:
        csv_path = ws_dir / WORKSPACE_CSV
        if not csv_path.exists():
            continue
        df = load_csv(csv_path)
        if df.empty:
            continue
        parts = ws_dir.relative_to(root).parts
        if len(parts) >= 4:
            df["_company_slug"] = parts[0]
            df["_fiscal_year"] = parts[1]
            df["_official_doc_type"] = parts[2]
            df["_document_id"] = parts[3]
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_top_possible_indicators(run_root: str | Path) -> pd.DataFrame:
    return load_csv(Path(run_root) / AUDIT_SUBDIR / "top_possible_indicators_all_docs.csv")


def load_false_positive_risks(run_root: str | Path) -> pd.DataFrame:
    return load_csv(Path(run_root) / AUDIT_SUBDIR / "false_positive_risk_samples.csv")


def load_candidate_counts_by_document(run_root: str | Path) -> pd.DataFrame:
    return load_csv(Path(run_root) / AUDIT_SUBDIR / "candidate_counts_by_document.csv")


def load_candidate_counts_by_family(run_root: str | Path) -> pd.DataFrame:
    return load_csv(Path(run_root) / AUDIT_SUBDIR / "candidate_counts_by_family.csv")


def load_candidate_counts_by_status(run_root: str | Path) -> pd.DataFrame:
    return load_csv(Path(run_root) / AUDIT_SUBDIR / "candidate_counts_by_status.csv")


def build_document_index(run_root: str | Path) -> pd.DataFrame:
    summary = load_pilot_summary(run_root)
    per_doc = summary.get("per_document", [])
    if not per_doc:
        return pd.DataFrame()
    return pd.DataFrame(per_doc)


def build_candidate_table(run_root: str | Path) -> pd.DataFrame:
    return load_all_review_workspaces(run_root)


def get_missing_files(run_root: str | Path) -> list[str]:
    """Return list of expected-but-missing files for user warnings."""
    root = Path(run_root)
    expected = [
        "pilot_run_summary.json",
        "selected_documents.csv",
        f"{AUDIT_SUBDIR}/pilot_review_quality_summary.json",
        f"{AUDIT_SUBDIR}/candidate_counts_by_document.csv",
        f"{AUDIT_SUBDIR}/candidate_counts_by_family.csv",
        f"{AUDIT_SUBDIR}/top_possible_indicators_all_docs.csv",
        f"{AUDIT_SUBDIR}/false_positive_risk_samples.csv",
    ]
    return [f for f in expected if not (root / f).exists()]

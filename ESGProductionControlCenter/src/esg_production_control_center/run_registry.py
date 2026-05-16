"""
run_registry.py — Discover available pilot runs for ESGProductionControlCenter v2.0.
"""
from __future__ import annotations

from pathlib import Path

KNOWN_RUN_ROOTS = [
    "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2",
    "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v1",
]

DEFAULT_RUN_ROOT = KNOWN_RUN_ROOTS[0]


def discover_runs(project_root: str | Path) -> list[str]:
    """Return relative paths of all available pilot run roots.

    Discovers:
    1. EXTERNAL_AUDIT_RUNS/ subdirs with pilot_run_summary.json (legacy format)
    2. audit_e2e_*/ and audit_batch_*/ dirs at project root with metric_candidates.jsonl
       or recall_report.json (new flat format from ESGInformationExtraction pipeline)
    """
    root = Path(project_root)
    runs: list[str] = []

    # Legacy: EXTERNAL_AUDIT_RUNS with pilot_run_summary.json
    audit_dir = root / "EXTERNAL_AUDIT_RUNS"
    if audit_dir.exists():
        for d in sorted(audit_dir.iterdir(), reverse=True):
            if d.is_dir() and (d / "pilot_run_summary.json").exists():
                runs.append(str(d.relative_to(root)).replace("\\", "/"))

    # New: audit_e2e_* and audit_batch_* dirs with metric extraction output
    for pattern in ("audit_e2e_*", "audit_batch_*"):
        for d in sorted(root.glob(pattern), reverse=True):
            if d.is_dir() and (
                (d / "metric_candidates.jsonl").exists()
                or (d / "recall_report.json").exists()
            ):
                rel = str(d.relative_to(root)).replace("\\", "/")
                if rel not in runs:
                    runs.append(rel)

    if not runs:
        for p in KNOWN_RUN_ROOTS:
            if (root / p).exists():
                runs.append(p)
    return runs


def get_default_run_root(project_root: str | Path) -> str:
    """Return the best available run root (prefers v2 runs)."""
    runs = discover_runs(project_root)
    for r in runs:
        if "v2" in r:
            return r
    return runs[0] if runs else DEFAULT_RUN_ROOT


def resolve_run_root(project_root: str | Path, run_root_input: str) -> Path:
    """Resolve a run_root string (relative or absolute) to an absolute Path."""
    p = Path(run_root_input)
    if p.is_absolute():
        return p
    return Path(project_root) / run_root_input

"""
export_utils.py — Safe export functions for ESGProductionControlCenter v2.0.
Writes ONLY to outputs/ or _control_center_exports/.
Never modifies any source pipeline file.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

MANUAL_BASELINE_COLUMNS = [
    "manual_indicator_id",
    "company_slug",
    "company_name",
    "fiscal_year",
    "official_doc_type",
    "document_id",
    "manual_indicator_label",
    "target_variable",
    "expected_family",
    "expected_value",
    "expected_unit",
    "expected_page",
    "expected_quote_or_context",
    "pipeline_found",
    "pipeline_candidate_id",
    "v1_error_type",
    "notes",
]

V1_ERROR_TYPES = [
    "true_positive",
    "false_positive",
    "missed_indicator",
    "wrong_family",
    "wrong_unit",
    "wrong_value",
    "wrong_year",
    "visual_missed",
    "table_parse_error",
    "section_number_false_positive",
    "iso_standard_false_positive",
    "unclear",
]

REVIEW_QUEUE_COLUMNS = [
    "review_item_id",
    "_company_slug",
    "_fiscal_year",
    "_official_doc_type",
    "page_number",
    "indicator_family",
    "label",
    "raw_value",
    "raw_unit",
    "normalized_value",
    "normalized_unit",
    "quote",
    "confidence",
    "review_priority",
    "suggested_review_action",
]


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_review_queue(df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = _ensure_dir(Path(output_dir))
    path = out / "review_queue_export.csv"
    cols = [c for c in REVIEW_QUEUE_COLUMNS if c in df.columns]
    df[cols].to_csv(path, index=False, encoding="utf-8")
    return path


def export_quality_decision_report(
    decision: str,
    metrics: dict,
    reasons: list[dict],
    output_dir: str | Path,
) -> Path:
    out = _ensure_dir(Path(output_dir))
    path = out / "quality_decision_report.md"

    lines = [
        "# Quality Decision Report",
        "",
        f"**Décision : {decision}**",
        "",
        "## Métriques clés",
        "",
        "| Métrique | Valeur |",
        "|----------|--------|",
    ]
    for k, v in metrics.items():
        if isinstance(v, float):
            lines.append(f"| {k} | {v:.2f} |")
        else:
            lines.append(f"| {k} | {v} |")

    lines += [
        "",
        "## Critères de décision",
        "",
        "| Critère | Résultat | Statut |",
        "|---------|----------|--------|",
    ]
    for r in reasons:
        crit = r.get("Critère", r.get("criterion", ""))
        res = r.get("Résultat", r.get("result", ""))
        stat = r.get("Statut", r.get("status", ""))
        lines.append(f"| {crit} | {res} | {stat} |")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def export_manual_baseline_template(output_dir: str | Path) -> Path:
    out = _ensure_dir(Path(output_dir))
    path = out / "manual_baseline_template.csv"
    pd.DataFrame(columns=MANUAL_BASELINE_COLUMNS).to_csv(path, index=False, encoding="utf-8")
    return path


def export_candidate_view(df: pd.DataFrame, output_dir: str | Path, filename: str = "candidate_view_export.csv") -> Path:
    out = _ensure_dir(Path(output_dir))
    path = out / filename
    df.to_csv(path, index=False, encoding="utf-8")
    return path

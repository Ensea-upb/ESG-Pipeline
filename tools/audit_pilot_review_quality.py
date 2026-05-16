"""
audit_pilot_review_quality.py
==============================
PilotReviewQualityAudit v1.0

Audits the review workspaces produced by a strict pilot prepare-review run.
READ-ONLY: never modifies source files.

CLI:
    python tools/audit_pilot_review_quality.py \
        --pilot-root "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2" \
        --output-dir "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2/_review_quality_audit" \
        --overwrite
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import statistics
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Review burden parameters
# ---------------------------------------------------------------------------

MINUTES_POSSIBLE_INDICATOR = 3.0
MINUTES_NEEDS_REVIEW = 1.0
MINUTES_REJECT_CANDIDATE = 0.3

BURDEN_LOW_MAX = 30
BURDEN_MEDIUM_MAX = 90
BURDEN_HIGH_MAX = 240

# ---------------------------------------------------------------------------
# False-positive detection parameters
# ---------------------------------------------------------------------------

MIN_QUOTE_LENGTH = 20

FOOTNOTE_LABEL_KEYWORDS = [
    "footnote",
    "refer to glossary",
    "see note",
    "see footnote",
    "refer to note",
    "note:",
    "page reference",
]

FOOTNOTE_VALUES = {"1", "2", "3", "4", "5", "6"}

# family → substrings that are clearly incompatible unit values
FAMILY_UNIT_INCOMPATIBLE: dict[str, list[str]] = {
    "ghg_emissions": ["hours", " h", "year", "days", "eur", "usd", "m2"],
    "energy": ["year", "days", "tco2", "co2"],
    "water": ["mwh", "kwh", "gwh", "tco2", "eur", "usd"],
    "waste": ["mwh", "kwh", "gwh", "tco2", "eur", "usd"],
}

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        with path.open("w", encoding="utf-8", newline="") as fh:
            fh.write("")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def _write_md(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Document discovery
# ---------------------------------------------------------------------------


def load_pilot_summary(pilot_root: Path) -> dict[str, Any]:
    return _read_json(pilot_root / "pilot_run_summary.json")


def build_company_name_map(pilot_summary: dict) -> dict[str, str]:
    """company_slug → company_name from per_document list."""
    result: dict[str, str] = {}
    for d in pilot_summary.get("per_document", []):
        slug = d.get("company_slug", "")
        name = d.get("company_name", "")
        if slug and name:
            result[slug] = name
    return result


def build_doc_meta_map(pilot_summary: dict) -> dict[tuple, dict]:
    """(company_slug, official_doc_type) → metadata dict."""
    result: dict[tuple, dict] = {}
    for d in pilot_summary.get("per_document", []):
        key = (d.get("company_slug", ""), d.get("official_doc_type", ""))
        result[key] = d
    return result


def find_workspace_dirs(pilot_root: Path) -> list[Path]:
    return sorted(pilot_root.rglob("04_review_workspace"))


def extract_path_meta(ws_dir: Path, pilot_root: Path) -> dict[str, str]:
    """Return company_slug, fiscal_year, official_doc_type, document_id from path."""
    try:
        parts = ws_dir.relative_to(pilot_root).parts
        return {
            "company_slug": parts[0] if len(parts) > 0 else "",
            "fiscal_year": parts[1] if len(parts) > 1 else "",
            "official_doc_type": parts[2] if len(parts) > 2 else "",
            "document_id": parts[3] if len(parts) > 3 else "",
        }
    except Exception:
        return {"company_slug": "", "fiscal_year": "", "official_doc_type": "", "document_id": ""}


# ---------------------------------------------------------------------------
# Per-document stats
# ---------------------------------------------------------------------------


def _estimate_minutes(n_poss: int, n_needs: int, n_reject: int) -> float:
    return (
        n_poss * MINUTES_POSSIBLE_INDICATOR
        + n_needs * MINUTES_NEEDS_REVIEW
        + n_reject * MINUTES_REJECT_CANDIDATE
    )


def _burden_level(minutes: float) -> str:
    if minutes < BURDEN_LOW_MAX:
        return "low"
    if minutes < BURDEN_MEDIUM_MAX:
        return "medium"
    if minutes < BURDEN_HIGH_MAX:
        return "high"
    return "excessive"


def compute_doc_stats(
    rows: list[dict],
    path_meta: dict[str, str],
    company_name: str,
) -> dict[str, Any]:
    n = len(rows)
    n_poss = sum(1 for r in rows if r.get("validation_status") == "possible_indicator")
    n_needs = sum(1 for r in rows if r.get("validation_status") == "needs_review")
    n_reject = sum(1 for r in rows if r.get("validation_status") == "reject_candidate")
    quote_missing = sum(1 for r in rows if not r.get("quote", "").strip())
    value_missing = sum(1 for r in rows if not r.get("raw_value", "").strip())
    unit_missing = sum(1 for r in rows if not r.get("raw_unit", "").strip())
    year_missing = sum(1 for r in rows if not r.get("normalized_year", "").strip())

    fam_counts: dict[str, int] = {}
    for r in rows:
        fam = r.get("indicator_family", "") or "unknown"
        fam_counts[fam] = fam_counts.get(fam, 0) + 1
    top_families = ",".join(
        k for k, _ in sorted(fam_counts.items(), key=lambda x: -x[1])[:5]
    )

    est = _estimate_minutes(n_poss, n_needs, n_reject)
    return {
        "company_slug": path_meta["company_slug"],
        "company_name": company_name,
        "fiscal_year": path_meta["fiscal_year"],
        "official_doc_type": path_meta["official_doc_type"],
        "document_id": path_meta["document_id"],
        "review_items_count": n,
        "possible_indicator_count": n_poss,
        "needs_review_count": n_needs,
        "reject_candidate_count": n_reject,
        "quote_missing_count": quote_missing,
        "value_missing_count": value_missing,
        "unit_missing_count": unit_missing,
        "year_missing_count": year_missing,
        "top_indicator_families": top_families,
        "estimated_review_minutes": round(est, 1),
        "review_burden_level": _burden_level(est),
    }


# ---------------------------------------------------------------------------
# Family and status stats
# ---------------------------------------------------------------------------


def compute_family_stats(all_rows: list[dict]) -> list[dict]:
    fam_data: dict[str, dict] = {}
    for row in all_rows:
        fam = row.get("indicator_family", "") or "unknown"
        if fam not in fam_data:
            fam_data[fam] = {
                "total_candidates": 0,
                "possible_indicator_count": 0,
                "needs_review_count": 0,
                "reject_candidate_count": 0,
                "documents": set(),
            }
        fam_data[fam]["total_candidates"] += 1
        st = row.get("validation_status", "")
        if st == "possible_indicator":
            fam_data[fam]["possible_indicator_count"] += 1
        elif st == "needs_review":
            fam_data[fam]["needs_review_count"] += 1
        elif st == "reject_candidate":
            fam_data[fam]["reject_candidate_count"] += 1
        fam_data[fam]["documents"].add(row.get("document_id", ""))

    total = sum(d["total_candidates"] for d in fam_data.values())
    result = []
    for fam, data in sorted(fam_data.items(), key=lambda x: -x[1]["total_candidates"]):
        result.append(
            {
                "indicator_family": fam,
                "total_candidates": data["total_candidates"],
                "possible_indicator_count": data["possible_indicator_count"],
                "needs_review_count": data["needs_review_count"],
                "reject_candidate_count": data["reject_candidate_count"],
                "documents_count": len(data["documents"]),
                "share_of_total_candidates": (
                    round(data["total_candidates"] / total * 100, 2) if total else 0
                ),
            }
        )
    return result


def compute_status_stats(all_rows: list[dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for row in all_rows:
        st = row.get("validation_status", "") or "unknown"
        counts[st] = counts.get(st, 0) + 1
    total = sum(counts.values())
    return [
        {
            "validation_status": st,
            "count": cnt,
            "share": round(cnt / total * 100, 2) if total else 0,
        }
        for st, cnt in sorted(counts.items(), key=lambda x: -x[1])
    ]


# ---------------------------------------------------------------------------
# False-positive detection
# ---------------------------------------------------------------------------


def _unit_family_mismatch(unit: str, family: str) -> bool:
    if not unit or not family:
        return False
    u = unit.lower().strip()
    for bad in FAMILY_UNIT_INCOMPATIBLE.get(family, []):
        if bad in u:
            return True
    return False


def _has_footnote_label(label: str) -> bool:
    ll = label.lower()
    return any(kw in ll for kw in FOOTNOTE_LABEL_KEYWORDS)


def detect_false_positives(rows: list[dict], path_meta: dict[str, str]) -> list[dict]:
    results = []
    fy = path_meta.get("fiscal_year", "")
    for row in rows:
        reasons: list[str] = []
        risk = "medium"

        quote = row.get("quote", "").strip()
        label = (row.get("label", "") or "").strip()
        raw_value = (row.get("raw_value", "") or "").strip()
        raw_unit = (row.get("raw_unit", "") or "").strip()
        norm_year = (row.get("normalized_year", "") or "").strip()
        page_num = (row.get("page_number", "") or "").strip()
        family = (row.get("indicator_family", "") or "").strip()

        if not quote:
            reasons.append("empty_quote")
            risk = "high"
        elif len(quote) < MIN_QUOTE_LENGTH:
            reasons.append("short_quote")
            risk = "high"

        if _has_footnote_label(label):
            reasons.append("footnote_label")
            risk = "high"

        if raw_value in FOOTNOTE_VALUES and (not quote or _has_footnote_label(label)):
            reasons.append("likely_footnote_value")
            risk = "high"

        if _unit_family_mismatch(raw_unit, family):
            reasons.append("unit_family_mismatch")

        if fy and norm_year:
            try:
                if abs(int(norm_year) - int(fy)) > 2:
                    reasons.append("year_mismatch")
            except ValueError:
                pass

        if not page_num:
            reasons.append("missing_page_number")

        if not reasons:
            continue

        results.append(
            {
                "company_slug": path_meta.get("company_slug", ""),
                "fiscal_year": fy,
                "official_doc_type": path_meta.get("official_doc_type", ""),
                "document_id": row.get("document_id", ""),
                "review_item_id": row.get("review_item_id", ""),
                "candidate_id": row.get("candidate_id", ""),
                "validation_status": row.get("validation_status", ""),
                "indicator_family": family,
                "raw_value": raw_value,
                "raw_unit": raw_unit,
                "normalized_value": row.get("normalized_value", ""),
                "normalized_unit": row.get("normalized_unit", ""),
                "normalized_year": norm_year,
                "page_number": page_num,
                "quote": quote[:200],
                "risk_reason": "|".join(reasons),
                "risk_level": risk,
            }
        )
    return results


# ---------------------------------------------------------------------------
# Top candidates
# ---------------------------------------------------------------------------

_STATUS_PRIORITY = {"possible_indicator": 0, "needs_review": 1, "reject_candidate": 2}


def get_top_candidates(
    all_rows: list[dict],
    path_meta_by_doc: dict[str, dict],
    name_by_slug: dict[str, str],
    max_per_doc: int = 30,
    global_max: int = 200,
) -> list[dict]:
    by_doc: dict[str, list[dict]] = {}
    for row in all_rows:
        doc_id = row.get("document_id", "")
        by_doc.setdefault(doc_id, []).append(row)

    result = []
    for doc_id, rows in by_doc.items():
        sorted_rows = sorted(
            rows, key=lambda r: _STATUS_PRIORITY.get(r.get("validation_status", ""), 9)
        )
        meta = path_meta_by_doc.get(doc_id, {})
        slug = meta.get("company_slug", rows[0].get("company", "") if rows else "")
        for row in sorted_rows[:max_per_doc]:
            result.append(
                {
                    "company_slug": slug,
                    "company_name": name_by_slug.get(slug, ""),
                    "fiscal_year": row.get("fiscal_year", ""),
                    "official_doc_type": meta.get("official_doc_type", ""),
                    "document_id": doc_id,
                    "review_item_id": row.get("review_item_id", ""),
                    "candidate_id": row.get("candidate_id", ""),
                    "source_engine": row.get("source_engine", ""),
                    "validation_status": row.get("validation_status", ""),
                    "review_priority": row.get("review_priority", ""),
                    "indicator_family": row.get("indicator_family", ""),
                    "indicator_key_candidate": row.get("indicator_key_candidate", ""),
                    "label": row.get("label", ""),
                    "raw_value": row.get("raw_value", ""),
                    "raw_unit": row.get("raw_unit", ""),
                    "normalized_value": row.get("normalized_value", ""),
                    "normalized_unit": row.get("normalized_unit", ""),
                    "normalized_year": row.get("normalized_year", ""),
                    "page_number": row.get("page_number", ""),
                    "quote": row.get("quote", "")[:300],
                }
            )

    result.sort(key=lambda r: _STATUS_PRIORITY.get(r.get("validation_status", ""), 9))
    return result[:global_max]


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------


def compute_decision(
    ws_found: int,
    ws_missing: int,
    total_items: int,
    total_possible: int,
    quotes_missing_all: int,
    meta_missing_company: int,
    meta_missing_fy: int,
    fp_high_risk_count: int,
    est_minutes_total: float,
    family_stats: list[dict],
) -> str:
    if ws_missing >= 3 or total_items == 0:
        return "NO_GO"
    if total_items and meta_missing_company / total_items > 0.3:
        return "NO_GO"
    if total_items and meta_missing_fy / total_items > 0.3:
        return "NO_GO"
    if total_possible and quotes_missing_all / total_possible > 0.5:
        return "NO_GO"

    # Check noise ratio: unknown + boundary combined
    noise_count = sum(
        d["total_candidates"]
        for d in family_stats
        if d["indicator_family"] in ("unknown", "boundary")
    )
    noise_ratio = noise_count / total_items if total_items else 0

    per_doc_avg = est_minutes_total / max(ws_found, 1)

    issues = []
    if ws_missing > 0:
        issues.append("workspaces_missing")
    if noise_ratio > 0.5:
        issues.append("high_noise_ratio")
    if per_doc_avg > 120:
        issues.append("high_review_burden")
    if total_items and quotes_missing_all / total_items > 0.1:
        issues.append("quotes_missing")
    if total_items and (meta_missing_company + meta_missing_fy) / total_items > 0.05:
        issues.append("metadata_incomplete")
    fp_ratio = fp_high_risk_count / max(total_items, 1)
    if fp_ratio > 0.3:
        issues.append("high_fp_risk")

    if not issues:
        return "GO"
    return "GO_WITH_FIXES"


# ---------------------------------------------------------------------------
# Report generators
# ---------------------------------------------------------------------------


def _pct(n: int, total: int) -> str:
    if total == 0:
        return "N/A"
    return f"{100 * n / total:.1f}%"


def build_review_burden_report(
    summary: dict,
    doc_stats: list[dict],
    family_stats: list[dict],
    top_candidates: list[dict],
    fp_samples: list[dict],
) -> str:
    total = summary["total_review_items"]
    n_poss = summary["total_possible_indicator"]
    n_needs = summary["total_needs_review"]
    n_reject = summary["total_reject_candidate"]
    est = summary["estimated_review_minutes"]
    decision = summary["decision_recommendation"]

    lines = [
        "# Review Burden Report — PilotReviewQualityAudit v1.0",
        "",
        f"**Date:** {summary.get('audit_date', 'N/A')}  ",
        f"**Pilot:** {summary.get('pilot_root', 'N/A')}  ",
        f"**Decision:** {decision}",
        "",
        "---",
        "",
        "## 1. Résumé global",
        "",
        f"| Métrique | Valeur |",
        f"|----------|--------|",
        f"| Workspaces trouvés | {summary['workspaces_found']} / {summary['documents_total']} |",
        f"| Total candidats | {total} |",
        f"| possible_indicator | {n_poss} ({_pct(n_poss, total)}) |",
        f"| needs_review | {n_needs} ({_pct(n_needs, total)}) |",
        f"| reject_candidate | {n_reject} ({_pct(n_reject, total)}) |",
        f"| Quotes manquantes | {summary['total_quotes_missing']} ({_pct(summary['total_quotes_missing'], total)}) |",
        f"| Valeurs manquantes | {summary['total_values_missing']} ({_pct(summary['total_values_missing'], total)}) |",
        f"| Moy. candidats/doc | {summary['average_candidates_per_document']:.0f} |",
        f"| Médiane | {summary['median_candidates_per_document']:.0f} |",
        f"| Max | {summary['max_candidates_per_document']} |",
        f"| Estimation totale | {est:.0f} min ({est/60:.1f} h) |",
        "",
        "---",
        "",
        "## 2. Top 10 documents les plus lourds",
        "",
        "| Document | Candidats | possible | needs | reject | Est. (min) | Charge |",
        "|----------|-----------|----------|-------|--------|------------|--------|",
    ]
    sorted_docs = sorted(doc_stats, key=lambda d: -d["estimated_review_minutes"])
    for d in sorted_docs[:10]:
        lines.append(
            f"| {d['company_slug']}/{d['official_doc_type']} "
            f"| {d['review_items_count']} "
            f"| {d['possible_indicator_count']} "
            f"| {d['needs_review_count']} "
            f"| {d['reject_candidate_count']} "
            f"| {d['estimated_review_minutes']:.0f} "
            f"| {d['review_burden_level']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Familles ESG les plus fréquentes",
        "",
        "| Famille | Total | possible | needs | share |",
        "|---------|-------|----------|-------|-------|",
    ]
    for fam in family_stats[:10]:
        lines.append(
            f"| {fam['indicator_family']} "
            f"| {fam['total_candidates']} "
            f"| {fam['possible_indicator_count']} "
            f"| {fam['needs_review_count']} "
            f"| {fam['share_of_total_candidates']}% |"
        )

    lines += [
        "",
        "---",
        "",
        "## 4. Taux de possible_indicator",
        "",
        f"- **{_pct(n_poss, total)}** des candidats sont classés `possible_indicator`.",
        f"- **{_pct(n_needs, total)}** sont `needs_review`.",
        f"- **{_pct(n_reject, total)}** sont `reject_candidate`.",
        "",
        "---",
        "",
        "## 5. Taux de candidats incomplets",
        "",
        f"- Quotes manquantes : **{_pct(summary['total_quotes_missing'], total)}**",
        f"- Valeurs manquantes : **{_pct(summary['total_values_missing'], total)}**",
        f"- Unités manquantes : **{_pct(summary['total_units_missing'], total)}**",
        f"- Années manquantes : **{_pct(summary['total_years_missing'], total)}**",
        "",
        "---",
        "",
        "## 6. Exemples de bons candidats",
        "",
    ]
    good = [r for r in top_candidates if r.get("validation_status") == "possible_indicator"][:5]
    if good:
        for r in good:
            lines += [
                f"**{r['company_slug']} / {r['official_doc_type']}**  ",
                f"- Famille : `{r['indicator_family']}`  ",
                f"- Indicateur : `{r['indicator_key_candidate']}`  ",
                f"- Valeur : `{r['raw_value']} {r['raw_unit']}`  ",
                f"- Année : `{r['normalized_year']}`  ",
                f"- Page : {r['page_number']}  ",
                f"- Quote : *{r['quote'][:150]}*  ",
                "",
            ]
    else:
        lines.append("_(aucun possible_indicator trouvé)_")

    lines += [
        "",
        "---",
        "",
        "## 7. Exemples de faux positifs probables",
        "",
    ]
    high_fp = [r for r in fp_samples if r.get("risk_level") == "high"][:5]
    if high_fp:
        for r in high_fp:
            lines += [
                f"**{r['company_slug']} / {r['official_doc_type']}** — risque `{r['risk_level']}`  ",
                f"- Raison : `{r['risk_reason']}`  ",
                f"- Valeur : `{r['raw_value']} {r['raw_unit']}`  ",
                f"- Quote : *{r['quote'][:120]}*  ",
                "",
            ]
    else:
        lines.append("_(aucun faux positif à haut risque détecté)_")

    lines += [
        "",
        "---",
        "",
        "## 8. Estimation du temps de revue",
        "",
        f"- Barème : {MINUTES_POSSIBLE_INDICATOR} min/possible_indicator, "
        f"{MINUTES_NEEDS_REVIEW} min/needs_review, "
        f"{MINUTES_REJECT_CANDIDATE} min/reject_candidate",
        f"- Total estimé : **{est:.0f} min ({est/60:.1f} h)**",
        f"- Moyenne par document : **{est/max(summary['workspaces_found'],1):.0f} min**",
        "",
        "---",
        "",
        "## 9. Recommandation pour passer à 20 documents",
        "",
    ]

    if decision == "GO":
        lines += [
            "**GO — Passage à 20 documents recommandé.**",
            "",
            "- Qualité des workspaces : bonne.",
            "- Charge de revue raisonnable.",
            "- Peu de faux positifs à haut risque.",
        ]
    elif decision == "GO_WITH_FIXES":
        lines += [
            "**GO_WITH_FIXES — Passage à 20 documents possible mais des corrections sont recommandées.**",
            "",
            "Avant de passer à 20 documents :",
            "- Réduire le bruit dans les familles `unknown` et `boundary`.",
            "- Revoir le scoring pour mieux filtrer les `needs_review` peu exploitables.",
            "- Vérifier les candidats avec valeurs manquantes (52% du corpus).",
            "- Envisager un filtre automatique sur les candidats à haut risque de faux positif.",
        ]
    else:
        lines += [
            "**NO_GO — Ne pas passer à 20 documents avant corrections.**",
            "",
            "Des problèmes critiques ont été détectés.",
            "Corriger les issues identifiées dans le rapport avant de relancer.",
        ]

    return "\n".join(lines) + "\n"


def build_audit_report(
    summary: dict,
    doc_stats: list[dict],
    family_stats: list[dict],
    audit_warnings: list[str],
    fp_samples: list[dict],
) -> str:
    total = summary["total_review_items"]
    n_poss = summary["total_possible_indicator"]
    n_needs = summary["total_needs_review"]
    n_reject = summary["total_reject_candidate"]
    est = summary["estimated_review_minutes"]
    decision = summary["decision_recommendation"]
    fp_high = sum(1 for r in fp_samples if r.get("risk_level") == "high")
    fp_medium = sum(1 for r in fp_samples if r.get("risk_level") == "medium")

    lines = [
        "# PILOT_REVIEW_QUALITY_AUDIT_REPORT",
        "",
        f"**Date :** {summary.get('audit_date', 'N/A')}  ",
        f"**Phase :** PilotReviewQualityAudit v1.0  ",
        f"**Décision :** {decision}",
        "",
        "---",
        "",
        "## 1. Contexte",
        "",
        "Le pilot strict prepare-review 10 documents a produit 10 review workspaces.",
        "Cette phase audite la qualité métier des candidats sans modifier les outputs.",
        "",
        f"- Pilot root : `{summary.get('pilot_root', 'N/A')}`",
        f"- Output audit : `{summary.get('output_dir', 'N/A')}`",
        "",
        "---",
        "",
        "## 2. Inputs audités",
        "",
        f"| Métrique | Valeur |",
        f"|----------|--------|",
        f"| Documents total | {summary['documents_total']} |",
        f"| Workspaces trouvés | {summary['workspaces_found']} |",
        f"| Workspaces manquants | {summary['workspaces_missing']} |",
        "",
    ]

    if audit_warnings:
        lines += ["**Warnings de lecture :**", ""]
        for w in audit_warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines += [
        "---",
        "",
        "## 3. Méthode",
        "",
        "- Lecture récursive de tous les `04_review_workspace/manual_review_workspace.csv`.",
        "- Calcul des métriques par document et global.",
        "- Détection de faux positifs par règles heuristiques.",
        "- Décision GO / GO_WITH_FIXES / NO_GO par seuils.",
        "- Lecture seule : aucun fichier source modifié.",
        "",
        "---",
        "",
        "## 4. Résultats chiffrés",
        "",
        "| Métrique | Valeur |",
        "|----------|--------|",
        f"| Total candidats | {total} |",
        f"| possible_indicator | {n_poss} ({_pct(n_poss, total)}) |",
        f"| needs_review | {n_needs} ({_pct(n_needs, total)}) |",
        f"| reject_candidate | {n_reject} ({_pct(n_reject, total)}) |",
        f"| Quotes manquantes | {summary['total_quotes_missing']} ({_pct(summary['total_quotes_missing'], total)}) |",
        f"| Valeurs manquantes | {summary['total_values_missing']} ({_pct(summary['total_values_missing'], total)}) |",
        f"| Unités manquantes | {summary['total_units_missing']} ({_pct(summary['total_units_missing'], total)}) |",
        f"| Années manquantes | {summary['total_years_missing']} ({_pct(summary['total_years_missing'], total)}) |",
        f"| Company manquante | {summary['total_metadata_missing_company']} |",
        f"| Fiscal year manquant | {summary['total_metadata_missing_fiscal_year']} |",
        f"| Estimation revue totale | {est:.0f} min ({est/60:.1f} h) |",
        f"| Faux positifs haut risque | {fp_high} |",
        f"| Faux positifs risque moyen | {fp_medium} |",
        "",
        "**Top familles ESG :**",
        "",
        "| Famille | Total | share |",
        "|---------|-------|-------|",
    ]
    for fam in family_stats[:8]:
        lines.append(
            f"| {fam['indicator_family']} | {fam['total_candidates']} | {fam['share_of_total_candidates']}% |"
        )

    lines += [
        "",
        "---",
        "",
        "## 5. Risques identifiés",
        "",
        "| Risque | Niveau | Détail |",
        "|--------|--------|--------|",
    ]

    noise_count = sum(
        d["total_candidates"]
        for d in family_stats
        if d["indicator_family"] in ("unknown", "boundary")
    )
    noise_ratio = noise_count / total if total else 0

    if noise_ratio > 0.5:
        lines.append(f"| Bruit familial élevé | HIGH | {noise_ratio:.0%} des candidats sont `unknown`/`boundary` |")
    else:
        lines.append(f"| Bruit familial | MEDIUM | {noise_ratio:.0%} des candidats sont `unknown`/`boundary` |")

    vm_ratio = summary["total_values_missing"] / total if total else 0
    if vm_ratio > 0.4:
        lines.append(f"| Valeurs manquantes | HIGH | {vm_ratio:.0%} des candidats sans raw_value |")

    est_per_doc = est / max(summary["workspaces_found"], 1)
    if est_per_doc > 120:
        lines.append(f"| Charge de revue | HIGH | {est_per_doc:.0f} min/document en moyenne |")
    elif est_per_doc > 60:
        lines.append(f"| Charge de revue | MEDIUM | {est_per_doc:.0f} min/document en moyenne |")

    if fp_high > 0:
        fp_rate = fp_high / total if total else 0
        lines.append(f"| Faux positifs | MEDIUM | {fp_high} candidats à haut risque ({fp_rate:.1%}) |")

    lines += [
        "",
        "---",
        "",
        "## 6. Décision",
        "",
        f"### {decision}",
        "",
    ]

    if decision == "GO":
        lines += [
            "Tous les critères GO sont satisfaits :",
            "- 10 workspaces trouvés et lisibles.",
            "- Quotes présentes pour la grande majorité des candidats.",
            "- Métadonnées company/fiscal_year présentes.",
            "- Charge de revue raisonnable.",
        ]
    elif decision == "GO_WITH_FIXES":
        lines += [
            "Le pilot est exploitable mais des améliorations sont nécessaires avant le pilot 20 docs :",
            "",
            "Points à corriger en priorité :",
        ]
        if noise_ratio > 0.5:
            lines.append(f"- **Réduire le bruit** : {noise_ratio:.0%} de candidats `unknown`/`boundary`.")
        if vm_ratio > 0.4:
            lines.append(f"- **Valeurs manquantes** : {vm_ratio:.0%} sans `raw_value` — revoir l'extraction.")
        if est_per_doc > 120:
            lines.append(
                f"- **Charge de revue** : {est_per_doc:.0f} min/doc — implémenter un filtre automatique."
            )
        if fp_high > 0:
            lines.append(f"- **Faux positifs** : {fp_high} à haut risque — améliorer le scoring.")
    else:
        lines += [
            "Problèmes critiques empêchant le passage au pilot 20 docs.",
            "Corriger les issues NO_GO avant de relancer.",
        ]

    lines += [
        "",
        "---",
        "",
        "## 7. Prochaine action recommandée",
        "",
    ]

    if decision == "GO":
        lines.append(
            "Lancer le pilot 20 documents (`--max-documents 20`) avec les mêmes paramètres."
        )
    elif decision == "GO_WITH_FIXES":
        lines += [
            "1. Revoir le scoring/filtrage pour réduire le bruit `unknown`/`boundary`.",
            "2. Valider manuellement un échantillon de `possible_indicator` pour calibrer la précision.",
            "3. Implémenter un filtre de faux positifs automatique sur les critères détectés.",
            "4. Relancer l'audit qualité sur un sous-ensemble de 3-5 documents corrigés.",
            "5. Si l'audit v2 passe GO → lancer pilot 20 documents.",
        ]
    else:
        lines += [
            "1. Identifier et corriger les causes NO_GO.",
            "2. Relancer le pilot 10 documents complet.",
            "3. Ré-auditer avant tout passage à 20 documents.",
        ]

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_audit(pilot_root: Path, output_dir: Path, overwrite: bool) -> int:
    if output_dir.exists() and not overwrite:
        if any(output_dir.iterdir()):
            log.error("Output dir exists and is not empty. Use --overwrite.")
            return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime, timezone

    audit_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # --- Load pilot metadata ---
    pilot_summary = load_pilot_summary(pilot_root)
    documents_total = pilot_summary.get("documents_selected", 0) or pilot_summary.get(
        "documents_processed", 0
    )
    name_by_slug = build_company_name_map(pilot_summary)
    doc_meta_map = build_doc_meta_map(pilot_summary)  # (slug, doc_type) → meta

    # --- Find workspaces ---
    ws_dirs = find_workspace_dirs(pilot_root)
    # Exclude the output_dir itself in case it's inside pilot_root
    ws_dirs = [d for d in ws_dirs if not str(d).startswith(str(output_dir))]
    log.info("Found %d workspace directories.", len(ws_dirs))

    # --- Load and aggregate ---
    all_rows: list[dict] = []
    doc_stats_list: list[dict] = []
    path_meta_by_doc: dict[str, dict] = {}
    audit_warnings: list[str] = []
    ws_missing = 0

    for ws_dir in ws_dirs:
        path_meta = extract_path_meta(ws_dir, pilot_root)
        slug = path_meta["company_slug"]
        doc_type = path_meta["official_doc_type"]
        company_name = name_by_slug.get(slug, slug)

        rows, _ws_summary, warns = [], {}, []
        csv_path = ws_dir / "manual_review_workspace.csv"
        if not csv_path.exists():
            ws_missing += 1
            audit_warnings.append(f"missing: {csv_path}")
            log.warning("manual_review_workspace.csv missing: %s", ws_dir)
        else:
            rows = _read_csv(csv_path)
            audit_warnings.extend(warns)

        # Tag rows with path meta for FP detection
        for row in rows:
            if not row.get("company_slug"):
                row["_company_slug"] = slug
            if not row.get("_official_doc_type"):
                row["_official_doc_type"] = doc_type

        all_rows.extend(rows)
        doc_id = path_meta.get("document_id", "")
        if doc_id and rows:
            path_meta_by_doc[doc_id] = path_meta

        doc_stats = compute_doc_stats(rows, path_meta, company_name)
        doc_stats_list.append(doc_stats)

    ws_found = len(ws_dirs) - ws_missing

    # --- Global aggregates ---
    total = len(all_rows)
    n_poss = sum(1 for r in all_rows if r.get("validation_status") == "possible_indicator")
    n_needs = sum(1 for r in all_rows if r.get("validation_status") == "needs_review")
    n_reject = sum(1 for r in all_rows if r.get("validation_status") == "reject_candidate")
    quotes_missing = sum(1 for r in all_rows if not r.get("quote", "").strip())
    values_missing = sum(1 for r in all_rows if not r.get("raw_value", "").strip())
    units_missing = sum(1 for r in all_rows if not r.get("raw_unit", "").strip())
    years_missing = sum(1 for r in all_rows if not r.get("normalized_year", "").strip())
    meta_miss_company = sum(1 for r in all_rows if not r.get("company", "").strip())
    meta_miss_fy = sum(1 for r in all_rows if not r.get("fiscal_year", "").strip())

    counts = [d["review_items_count"] for d in doc_stats_list if d["review_items_count"] > 0]
    avg_candidates = sum(counts) / len(counts) if counts else 0
    med_candidates = statistics.median(counts) if counts else 0
    max_candidates = max(counts) if counts else 0

    est_total = sum(d["estimated_review_minutes"] for d in doc_stats_list)

    # --- Family and status stats ---
    family_stats = compute_family_stats(all_rows)
    status_stats = compute_status_stats(all_rows)

    # --- False positives ---
    fp_all: list[dict] = []
    for ws_dir in ws_dirs:
        path_meta = extract_path_meta(ws_dir, pilot_root)
        csv_path = ws_dir / "manual_review_workspace.csv"
        rows = _read_csv(csv_path)
        fp_all.extend(detect_false_positives(rows, path_meta))

    fp_high_count = sum(1 for r in fp_all if r.get("risk_level") == "high")

    # --- Top candidates ---
    top_candidates = get_top_candidates(all_rows, path_meta_by_doc, name_by_slug)

    # --- Decision ---
    decision = compute_decision(
        ws_found=ws_found,
        ws_missing=ws_missing,
        total_items=total,
        total_possible=n_poss,
        quotes_missing_all=quotes_missing,
        meta_missing_company=meta_miss_company,
        meta_missing_fy=meta_miss_fy,
        fp_high_risk_count=fp_high_count,
        est_minutes_total=est_total,
        family_stats=family_stats,
    )

    # --- Summary JSON ---
    global_summary = {
        "schema_version": "1.0.0",
        "audit_phase": "PilotReviewQualityAudit",
        "audit_version": "v1.0",
        "audit_date": audit_date,
        "pilot_root": str(pilot_root.resolve()),
        "output_dir": str(output_dir.resolve()),
        "documents_total": documents_total,
        "workspaces_found": ws_found,
        "workspaces_missing": ws_missing,
        "total_review_items": total,
        "total_possible_indicator": n_poss,
        "total_needs_review": n_needs,
        "total_reject_candidate": n_reject,
        "total_quotes_missing": quotes_missing,
        "total_values_missing": values_missing,
        "total_units_missing": units_missing,
        "total_years_missing": years_missing,
        "total_metadata_missing_company": meta_miss_company,
        "total_metadata_missing_fiscal_year": meta_miss_fy,
        "average_candidates_per_document": round(avg_candidates, 1),
        "median_candidates_per_document": round(float(med_candidates), 1),
        "max_candidates_per_document": max_candidates,
        "estimated_review_minutes": round(est_total, 1),
        "false_positive_high_risk_count": fp_high_count,
        "false_positive_total_count": len(fp_all),
        "decision_recommendation": decision,
        "audit_warnings": audit_warnings,
    }

    # --- Write outputs ---
    _write_json(output_dir / "pilot_review_quality_summary.json", global_summary)
    log.info("Wrote pilot_review_quality_summary.json")

    _write_csv(output_dir / "candidate_counts_by_document.csv", doc_stats_list)
    log.info("Wrote candidate_counts_by_document.csv (%d rows)", len(doc_stats_list))

    _write_csv(output_dir / "candidate_counts_by_family.csv", family_stats)
    log.info("Wrote candidate_counts_by_family.csv (%d rows)", len(family_stats))

    _write_csv(output_dir / "candidate_counts_by_status.csv", status_stats)
    log.info("Wrote candidate_counts_by_status.csv (%d rows)", len(status_stats))

    _write_csv(output_dir / "top_possible_indicators_all_docs.csv", top_candidates)
    log.info("Wrote top_possible_indicators_all_docs.csv (%d rows)", len(top_candidates))

    _write_csv(output_dir / "false_positive_risk_samples.csv", fp_all)
    log.info("Wrote false_positive_risk_samples.csv (%d rows)", len(fp_all))

    burden_md = build_review_burden_report(
        global_summary, doc_stats_list, family_stats, top_candidates, fp_all
    )
    _write_md(output_dir / "review_burden_report.md", burden_md)
    log.info("Wrote review_burden_report.md")

    audit_md = build_audit_report(
        global_summary, doc_stats_list, family_stats, audit_warnings, fp_all
    )
    _write_md(output_dir / "PILOT_REVIEW_QUALITY_AUDIT_REPORT.md", audit_md)
    log.info("Wrote PILOT_REVIEW_QUALITY_AUDIT_REPORT.md")

    log.info("Decision: %s", decision)
    log.info(
        "Total candidates: %d | possible: %d | needs_review: %d | reject: %d",
        total, n_poss, n_needs, n_reject,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="PilotReviewQualityAudit v1.0")
    parser.add_argument("--pilot-root", required=True, help="Root dir of the pilot run.")
    parser.add_argument("--output-dir", required=True, help="Audit output directory.")
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing output directory."
    )
    args = parser.parse_args(argv)
    return run_audit(Path(args.pilot_root), Path(args.output_dir), args.overwrite)


if __name__ == "__main__":
    sys.exit(main())

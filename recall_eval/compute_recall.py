"""
compute_recall.py
=================
Calcule le recall du pipeline d'extraction ESG sur un document de référence.

Méthode :
  - Ground truth = métriques mandatoires ESRS (E1, S1, G1) + indicateurs
    SSI connus de Schneider Electric 2024. Ces métriques sont présentes
    dans TOUT rapport CSRD conforme.
  - Recall metric-level  = |found_ids| / |GT_ids|
  - Recall value-level   = |found_ids_with_value| / |GT_ids|
  - found_id = au moins 1 candidat dans metric_candidates.jsonl avec ce metric_id
  - found_id_with_value = idem + raw_value non vide

Usage :
  python compute_recall.py <output_dir>
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# Ground truth : métriques attendues dans le rapport CSRD Schneider 2024
# Basé sur les obligations ESRS E1, S1, G1 et les indicateurs SSI publiés.
# ---------------------------------------------------------------------------
GROUND_TRUTH: dict[str, dict] = {
    # ESRS E1 — Changement climatique
    "ghg_scope_1": {
        "label": "GHG Scope 1",
        "source": "ESRS E1 DR-E1-4 (mandatory)",
        "approximate_value": "~1.0-1.5 Mt CO2e",
    },
    "ghg_scope_2": {
        "label": "GHG Scope 2",
        "source": "ESRS E1 DR-E1-4 (mandatory)",
        "approximate_value": "market-based, near 0 (RE100)",
    },
    "ghg_scope_3": {
        "label": "GHG Scope 3",
        "source": "ESRS E1 DR-E1-4 (mandatory)",
        "approximate_value": "~200 Mt CO2e (use of products dominant)",
    },
    "total_energy_consumption": {
        "label": "Total energy consumption",
        "source": "ESRS E1 DR-E1-5 (mandatory)",
        "approximate_value": "~3-5 TWh",
    },
    "renewable_energy_share": {
        "label": "Renewable energy share",
        "source": "ESRS E1 + SSI indicator",
        "approximate_value": "~40-50%",
    },
    # ESRS E3 — Eau
    "water_withdrawal": {
        "label": "Water withdrawal",
        "source": "ESRS E3 (mandatory)",
        "approximate_value": "Mm3",
    },
    # ESRS E5 — Déchets
    "waste_generated": {
        "label": "Waste generated",
        "source": "ESRS E5 (mandatory)",
        "approximate_value": "kt",
    },
    "waste_recycling_rate": {
        "label": "Waste recycling rate",
        "source": "ESRS E5 + SSI",
        "approximate_value": ">80%",
    },
    # ESRS S1 — Main d'œuvre propre
    "total_employees": {
        "label": "Total employees",
        "source": "ESRS S1 DR-S1-6 (mandatory)",
        "approximate_value": "~150 000",
    },
    "gender_diversity_workforce": {
        "label": "Women in workforce",
        "source": "ESRS S1 DR-S1-9 (mandatory)",
        "approximate_value": "~29%",
    },
    "gender_diversity_board": {
        "label": "Women on board",
        "source": "ESRS G1 + loi PACTE",
        "approximate_value": ">40%",
    },
    "workplace_accidents": {
        "label": "Workplace accidents / LTIR",
        "source": "ESRS S1 DR-S1-14 (mandatory)",
        "approximate_value": "LTIR ~0.5",
    },
    "training_hours": {
        "label": "Training hours",
        "source": "ESRS S1 DR-S1-13",
        "approximate_value": "millions of hours or h/employee",
    },
    "employee_turnover_rate": {
        "label": "Employee turnover rate",
        "source": "ESRS S1 (voluntary/SSI)",
        "approximate_value": "%",
    },
    # ESRS G1 — Conduite des affaires
    "anti_corruption_training": {
        "label": "Anti-corruption training",
        "source": "ESRS G1 DR-G1-4",
        "approximate_value": "%",
    },
    "ethics_alerts": {
        "label": "Ethics alerts",
        "source": "ESRS G1 (mandatory)",
        "approximate_value": "number",
    },
    # Schneider SSI supplémentaires
    "carbon_intensity": {
        "label": "Carbon intensity",
        "source": "Schneider SSI #1",
        "approximate_value": "kgCO2e/€k revenue or similar",
    },
    "training_coverage": {
        "label": "Training coverage",
        "source": "Schneider SSI",
        "approximate_value": "%",
    },
    "fatal_accidents": {
        "label": "Fatal accidents",
        "source": "ESRS S1 DR-S1-14",
        "approximate_value": "number (ideally 0)",
    },
    "salary_gap": {
        "label": "Gender pay gap",
        "source": "ESRS S1 DR-S1-16",
        "approximate_value": "%",
    },
}

GT_IDS = set(GROUND_TRUTH.keys())


def load_candidates(output_dir: Path) -> list[dict]:
    f = output_dir / "metric_candidates.jsonl"
    if not f.exists():
        return []
    lines = f.read_text(encoding="utf-8").splitlines()
    return [json.loads(l) for l in lines if l.strip()]


def compute_recall(output_dir: Path) -> None:
    candidates = load_candidates(output_dir)
    stats_path = output_dir / "metric_statistics.json"
    stats = json.loads(stats_path.read_text()) if stats_path.exists() else {}

    # Group candidates by metric_id
    by_id: dict[str, list[dict]] = defaultdict(list)
    for c in candidates:
        mid = c.get("metric_id") or c.get("metric_label", "unknown")
        by_id[mid].append(c)

    found_ids: set[str] = set()
    found_ids_with_value: set[str] = set()
    found_ids_current_year: set[str] = set()

    for mid in GT_IDS:
        cands = by_id.get(mid, [])
        if cands:
            found_ids.add(mid)
        if any(c.get("raw_value") for c in cands):
            found_ids_with_value.add(mid)
        if any(c.get("is_current_year") is True for c in cands):
            found_ids_current_year.add(mid)

    missed_ids = GT_IDS - found_ids
    found_no_value = found_ids - found_ids_with_value

    recall_metric = len(found_ids) / len(GT_IDS)
    recall_value  = len(found_ids_with_value) / len(GT_IDS)
    recall_current = len(found_ids_current_year) / len(GT_IDS)

    print("=" * 60)
    print("RECALL EVALUATION — Schneider Electric CSRD 2024")
    print("=" * 60)
    print(f"Ground truth metrics  : {len(GT_IDS)}")
    print(f"Total candidates      : {len(candidates)}")
    print(f"  - regex             : {stats.get('regex_candidates_count', '?')}")
    print(f"  - GLiNER            : {stats.get('gliner_candidates_count', '?')}")
    print(f"  - docling_status    : {stats.get('docling_status', '?')}")
    print(f"  - ocr_available     : {stats.get('ocr_available', '?')}")
    print()
    print(f"Recall @ metric-level : {len(found_ids)}/{len(GT_IDS)} = {recall_metric:.1%}")
    print(f"Recall @ value-level  : {len(found_ids_with_value)}/{len(GT_IDS)} = {recall_value:.1%}")
    print(f"Recall @ current-year : {len(found_ids_current_year)}/{len(GT_IDS)} = {recall_current:.1%}")
    print()

    print("─── FOUND (avec valeur) ─────────────────────────────")
    for mid in sorted(found_ids_with_value):
        best = max(by_id[mid], key=lambda c: float(c.get("confidence", 0)))
        yr = best.get("year_in_context")
        curr = best.get("is_current_year")
        yr_tag = f" [year={yr}, current={curr}]" if yr else ""
        print(f"  ✓ {mid:<35} val={best.get('raw_value','')!r:>12} {best.get('raw_unit',''):6}{yr_tag}")

    if found_no_value:
        print()
        print("─── FOUND (sans valeur numérique) ───────────────────")
        for mid in sorted(found_no_value):
            snippet = by_id[mid][0].get("context_snippet", "")[:80]
            print(f"  ~ {mid:<35} context: {snippet!r}")

    if missed_ids:
        print()
        print("─── MANQUÉS (faux négatifs) ──────────────────────────")
        for mid in sorted(missed_ids):
            gt = GROUND_TRUTH[mid]
            print(f"  ✗ {mid:<35} attendu: {gt['approximate_value']}  ({gt['source']})")

    print()

    # Precision proxy metrics
    extra_ids = set(by_id.keys()) - GT_IDS
    gt_total_cands = sum(len(by_id[mid]) for mid in GT_IDS if mid in by_id)
    gt_cands_with_val = sum(
        sum(1 for c in by_id[mid] if c.get("raw_value"))
        for mid in GT_IDS if mid in by_id
    )
    extra_total_cands = sum(len(by_id[mid]) for mid in extra_ids)
    # Crude precision proxy: among GT candidates, what fraction carry a valid value?
    prec_proxy_gt = gt_cands_with_val / gt_total_cands if gt_total_cands else 0.0
    # Noise ratio: extra (non-GT) candidates as fraction of all candidates
    noise_ratio = extra_total_cands / len(candidates) if candidates else 0.0

    print(f"─── PRECISION PROXY ─────────────────────────────────")
    print(f"  GT candidates      : {gt_total_cands:6d}  ({gt_cands_with_val} with value  → {prec_proxy_gt:.1%} carry-value rate)")
    print(f"  Extra candidates   : {extra_total_cands:6d}  ({noise_ratio:.1%} of total — lower is better)")
    print(f"  Avg cands/GT metric: {gt_total_cands/len(GT_IDS):.1f}")
    print()

    print(f"─── HORS GROUND TRUTH ({len(extra_ids)} metric_ids supplémentaires) ──")
    for mid, n_cands in sorted(
        ((mid, len(by_id[mid])) for mid in extra_ids), key=lambda x: -x[1]
    )[:20]:  # top 20 only
        has_val = sum(1 for c in by_id[mid] if c.get("raw_value"))
        print(f"  + {mid:<35} {n_cands:5d} candidats, {has_val} avec valeur")
    if len(extra_ids) > 20:
        print(f"  ... ({len(extra_ids) - 20} autres)")

    print()
    print("═" * 60)
    print(f"RECALL FINAL : metric={recall_metric:.1%}  value={recall_value:.1%}  current_year={recall_current:.1%}")
    print(f"PRECISION    : carry-value={prec_proxy_gt:.1%}  noise={noise_ratio:.1%}")
    print("═" * 60)

    # Write JSON summary
    summary = {
        "ground_truth_count": len(GT_IDS),
        "total_candidates": len(candidates),
        "found_metric_ids": sorted(found_ids),
        "found_with_value": sorted(found_ids_with_value),
        "found_current_year": sorted(found_ids_current_year),
        "missed_metric_ids": sorted(missed_ids),
        "recall_metric_level": round(recall_metric, 4),
        "recall_value_level": round(recall_value, 4),
        "recall_current_year_level": round(recall_current, 4),
        "precision_proxy_carry_value": round(prec_proxy_gt, 4),
        "precision_proxy_noise_ratio": round(noise_ratio, 4),
        "gt_candidates_total": gt_total_cands,
        "extra_candidates_total": extra_total_cands,
        "extraction_stats": stats,
    }
    out_path = output_dir / "recall_report.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRapport JSON écrit : {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compute_recall.py <output_dir>")
        sys.exit(1)
    compute_recall(Path(sys.argv[1]))

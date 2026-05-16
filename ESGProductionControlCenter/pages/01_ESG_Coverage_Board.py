"""
Page 01 — ESG Coverage Board
Vue radar des indicateurs ESRS mandatoires :
quels metrics sont trouvés, avec valeur, pour l'année courante.
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from collections import defaultdict

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import pandas as pd

from ESGProductionControlCenter.src.esg_production_control_center.ui_components import setup_sidebar
from ESGProductionControlCenter.src.esg_production_control_center.styles import (
    get_global_css, badge_html, section_header_html,
)

st.set_page_config(page_title="ESG Coverage Board", layout="wide", page_icon="🎯")
st.markdown(get_global_css(), unsafe_allow_html=True)
run_root = setup_sidebar("ESG Coverage Board")

# ── Ground truth ESRS mandatoires ──────────────────────────────────────────────
ESRS_METRICS: dict[str, dict] = {
    # Environnement
    "ghg_scope_1":             {"label": "GHG Scope 1",              "family": "Environnement", "source": "ESRS E1"},
    "ghg_scope_2":             {"label": "GHG Scope 2",              "family": "Environnement", "source": "ESRS E1"},
    "ghg_scope_3":             {"label": "GHG Scope 3",              "family": "Environnement", "source": "ESRS E1"},
    "total_energy_consumption":{"label": "Énergie totale",           "family": "Environnement", "source": "ESRS E1"},
    "renewable_energy_share":  {"label": "Part énergie renouvelable","family": "Environnement", "source": "ESRS E1"},
    "carbon_intensity":        {"label": "Intensité carbone",        "family": "Environnement", "source": "SSI #1"},
    "water_withdrawal":        {"label": "Prélèvement eau",          "family": "Environnement", "source": "ESRS E3"},
    "waste_generated":         {"label": "Déchets générés",          "family": "Environnement", "source": "ESRS E5"},
    "waste_recycling_rate":    {"label": "Taux recyclage déchets",   "family": "Environnement", "source": "ESRS E5"},
    # Social
    "total_employees":         {"label": "Effectif total",           "family": "Social",        "source": "ESRS S1"},
    "gender_diversity_workforce":{"label":"Femmes effectif",         "family": "Social",        "source": "ESRS S1"},
    "gender_diversity_board":  {"label": "Femmes au conseil",        "family": "Social",        "source": "ESRS G1"},
    "workplace_accidents":     {"label": "Accidents travail / LTIR", "family": "Social",        "source": "ESRS S1"},
    "fatal_accidents":         {"label": "Accidents mortels",        "family": "Social",        "source": "ESRS S1"},
    "training_hours":          {"label": "Heures de formation",      "family": "Social",        "source": "ESRS S1"},
    "training_coverage":       {"label": "Taux couverture formation","family": "Social",        "source": "SSI"},
    "employee_turnover_rate":  {"label": "Taux de rotation",         "family": "Social",        "source": "ESRS S1"},
    "salary_gap":              {"label": "Écart salarial H/F",       "family": "Social",        "source": "ESRS S1"},
    # Gouvernance
    "anti_corruption_training":{"label": "Formation anticorruption", "family": "Gouvernance",   "source": "ESRS G1"},
    "ethics_alerts":           {"label": "Alertes éthiques",         "family": "Gouvernance",   "source": "ESRS G1"},
}

FAMILY_COLORS = {
    "Environnement": "#16A34A",
    "Social":        "#2563EB",
    "Gouvernance":   "#7C3AED",
}
FAMILY_BG = {
    "Environnement": "#F0FDF4",
    "Social":        "#EFF6FF",
    "Gouvernance":   "#F5F3FF",
}


@st.cache_data(ttl=120)
def _load_metric_candidates(run_root_str: str) -> list[dict]:
    """Load all metric_candidates.jsonl from every document workspace."""
    root = Path(run_root_str)
    candidates: list[dict] = []
    for f in root.rglob("metric_candidates.jsonl"):
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    # Tag with relative path info
                    parts = f.relative_to(root).parts
                    obj.setdefault("_company", parts[0] if len(parts) > 0 else "?")
                    obj.setdefault("_year", parts[1] if len(parts) > 1 else "?")
                    candidates.append(obj)
        except Exception:
            pass
    return candidates


@st.cache_data(ttl=120)
def _load_metric_stats(run_root_str: str) -> list[dict]:
    root = Path(run_root_str)
    stats = []
    for f in root.rglob("metric_statistics.json"):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
            parts = f.relative_to(root).parts
            obj["_company"] = parts[0] if len(parts) > 0 else "?"
            obj["_year"]    = parts[1] if len(parts) > 1 else "?"
            stats.append(obj)
        except Exception:
            pass
    return stats


# ── Load data ──────────────────────────────────────────────────────────────────
candidates = _load_metric_candidates(str(run_root))
stats_list = _load_metric_stats(str(run_root))

# Aggregate by metric_id
by_id: dict[str, list[dict]] = defaultdict(list)
for c in candidates:
    mid = c.get("metric_id") or ""
    if mid:
        by_id[mid].append(c)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("# 🎯 ESG Coverage Board")
st.caption("Couverture des indicateurs ESRS mandatoires — vue métier.")

if not candidates:
    st.warning(
        "Aucun fichier `metric_candidates.jsonl` trouvé dans ce run. "
        "Relancez l'extraction avec la version pipeline v3."
    )
    st.stop()

# ── Recall summary KPIs ────────────────────────────────────────────────────────
gt_ids = set(ESRS_METRICS.keys())
found_ids         = {mid for mid in gt_ids if by_id.get(mid)}
found_with_value  = {mid for mid in found_ids if any(c.get("raw_value") for c in by_id[mid])}
found_curr        = {mid for mid in found_ids if any(c.get("is_current_year") is True for c in by_id[mid])}
missed_ids        = gt_ids - found_ids

recall_m = len(found_ids) / len(gt_ids) * 100
recall_v = len(found_with_value) / len(gt_ids) * 100
recall_c = len(found_curr) / len(gt_ids) * 100

st.markdown(section_header_html("Recall ESRS mandatoires"), unsafe_allow_html=True)
r1, r2, r3, r4, r5 = st.columns(5)
r1.metric("Recall métrique",   f"{recall_m:.0f}%",  f"{len(found_ids)}/{len(gt_ids)} trouvés")
r2.metric("Recall valeur",     f"{recall_v:.0f}%",  f"{len(found_with_value)}/{len(gt_ids)} avec valeur")
r3.metric("Recall année cte",  f"{recall_c:.0f}%",  f"{len(found_curr)}/{len(gt_ids)} datés")
r4.metric("Total candidats",   f"{len(candidates):,}")
r5.metric("Manqués",           f"{len(missed_ids)}",
          delta=f"-{len(missed_ids)} indicateurs",
          delta_color="inverse" if missed_ids else "off")

# Progress bar
st.markdown(section_header_html("Progression recall"), unsafe_allow_html=True)
col_pb1, col_pb2, col_pb3 = st.columns(3)
with col_pb1:
    st.progress(recall_m / 100, text=f"Métrique : {recall_m:.0f}%")
with col_pb2:
    st.progress(recall_v / 100, text=f"Valeur : {recall_v:.0f}%")
with col_pb3:
    st.progress(recall_c / 100, text=f"Année courante : {recall_c:.0f}%")

# ── Precision proxy metrics ───────────────────────────────────────────────────
gt_cands_total = sum(len(by_id.get(mid, [])) for mid in gt_ids)
gt_cands_with_val = sum(
    sum(1 for c in by_id.get(mid, []) if c.get("raw_value"))
    for mid in gt_ids
)
extra_ids = set(by_id.keys()) - gt_ids
extra_cands_total = sum(len(by_id[mid]) for mid in extra_ids)
carry_value_rate = gt_cands_with_val / gt_cands_total * 100 if gt_cands_total else 0.0
noise_ratio = extra_cands_total / len(candidates) * 100 if candidates else 0.0

with st.expander("📊 Métriques de précision (proxy)", expanded=False):
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Candidats GT", f"{gt_cands_total:,}", help="Candidats pour les 20 métriques mandatoires")
    p2.metric("Candidats hors GT", f"{extra_cands_total:,}",
              delta=f"{noise_ratio:.0f}% de bruit", delta_color="inverse")
    p3.metric("Taux carry-value GT", f"{carry_value_rate:.1f}%",
              help="% des candidats GT qui portent une valeur numérique")
    p4.metric("Métriques extra", f"{len(extra_ids)}", help="Nbre de metric_ids hors ground truth")
    if extra_ids:
        top_extra = sorted(extra_ids, key=lambda m: -len(by_id[m]))[:8]
        st.caption("Top métriques hors GT (réduire = gain précision) : " +
                   ", ".join(f"{m} ({len(by_id[m])})" for m in top_extra))

st.divider()

# ── Coverage Grid — by family ──────────────────────────────────────────────────
st.markdown(section_header_html("Couverture par indicateur ESRS"), unsafe_allow_html=True)
st.caption(
    "🟢 Trouvé avec valeur  ·  🟡 Trouvé sans valeur  ·  🔴 Non trouvé  ·  "
    "Cliquez sur un badge pour voir les candidats."
)

# Build status per metric_id
def _status(mid: str) -> str:
    cands = by_id.get(mid, [])
    if not cands:
        return "missed"
    if any(c.get("raw_value") for c in cands):
        return "found_val"
    return "found_no"

def _best_candidate(mid: str) -> dict | None:
    cands = by_id.get(mid, [])
    if not cands:
        return None
    return max(cands, key=lambda c: float(c.get("confidence", 0)))

STATUS_ICON  = {"found_val": "🟢", "found_no": "🟡", "missed": "🔴"}
STATUS_LABEL = {"found_val": "Trouvé + valeur", "found_no": "Trouvé (sans valeur)", "missed": "Non trouvé"}
STATUS_COLOR = {
    "found_val": ("#DCFCE7", "#14532D", "#86EFAC"),
    "found_no":  ("#FEF3C7", "#78350F", "#FCD34D"),
    "missed":    ("#FEE2E2", "#7F1D1D", "#FCA5A5"),
}

for family in ["Environnement", "Social", "Gouvernance"]:
    fam_metrics = {mid: info for mid, info in ESRS_METRICS.items() if info["family"] == family}
    fc = FAMILY_COLORS[family]
    fb = FAMILY_BG[family]

    st.markdown(
        f'<div style="background:{fb};border-left:4px solid {fc};border-radius:0 8px 8px 0;'
        f'padding:0.4rem 1rem;margin:1rem 0 0.5rem;font-weight:700;font-size:0.85rem;color:{fc}">'
        f'{family} — {len(fam_metrics)} indicateurs</div>',
        unsafe_allow_html=True,
    )

    # Grid: 4 per row
    mids = list(fam_metrics.keys())
    for row_start in range(0, len(mids), 4):
        row_mids = mids[row_start:row_start + 4]
        cols = st.columns(4)
        for col, mid in zip(cols, row_mids):
            info = fam_metrics[mid]
            status = _status(mid)
            best = _best_candidate(mid)
            bg, fg, border = STATUS_COLOR[status]
            icon = STATUS_ICON[status]

            val_str = ""
            if best and best.get("raw_value"):
                val_str = f"{best['raw_value']} {best.get('raw_unit', '')}".strip()
            yr_str = ""
            if best and best.get("year_in_context"):
                yr_str = str(best["year_in_context"])
            conf_str = ""
            if best:
                conf_str = f"conf. {float(best.get('confidence', 0)):.0%}"

            col.markdown(
                f"""<div style="background:{bg};border:1px solid {border};border-radius:10px;
                padding:0.75rem;margin:3px;min-height:90px;">
                <div style="font-size:1.1rem;margin-bottom:2px">{icon}</div>
                <div style="font-weight:700;font-size:0.78rem;color:{fg};line-height:1.2">
                    {info['label']}</div>
                <div style="font-size:0.7rem;color:#6B7280;margin-top:2px">{info['source']}</div>
                {f'<div style="font-size:0.75rem;font-weight:600;color:#1E293B;margin-top:4px">{val_str}</div>' if val_str else ''}
                {f'<div style="font-size:0.68rem;color:#64748B">{yr_str} · {conf_str}</div>' if yr_str or conf_str else ''}
                </div>""",
                unsafe_allow_html=True,
            )

st.divider()

# ── Detailed table ─────────────────────────────────────────────────────────────
st.markdown(section_header_html("Détail par indicateur"), unsafe_allow_html=True)

rows = []
for mid, info in ESRS_METRICS.items():
    cands = by_id.get(mid, [])
    best = _best_candidate(mid)
    status = _status(mid)
    n_cands = len(cands)
    rows.append({
        "Famille":   info["family"],
        "Indicateur": info["label"],
        "Source ESRS": info["source"],
        "Statut":    STATUS_LABEL[status],
        "Candidats": n_cands,
        "Meilleure valeur": f"{best['raw_value']} {best.get('raw_unit','')}" if best and best.get("raw_value") else "",
        "Année":     best.get("year_in_context", "") if best else "",
        "Confiance": f"{float(best.get('confidence', 0)):.0%}" if best else "",
        "is_current_year": "✅" if best and best.get("is_current_year") is True else "",
    })

detail_df = pd.DataFrame(rows)
st.dataframe(
    detail_df,
    use_container_width=True,
    hide_index=True,
    height=420,
    column_config={
        "Confiance": st.column_config.TextColumn("Confiance"),
        "Candidats": st.column_config.NumberColumn("N candidats", format="%d"),
    },
)
st.download_button(
    "⬇️ Télécharger le rapport de couverture",
    detail_df.to_csv(index=False).encode("utf-8"),
    "esg_coverage_report.csv",
    "text/csv",
)

st.divider()

# ── Historical run comparison ──────────────────────────────────────────────────
_recall_report = run_root / "recall_report.json"
if _recall_report.exists():
    import plotly.graph_objects as go

    _rr = json.loads(_recall_report.read_text(encoding="utf-8"))
    st.markdown(section_header_html("Rapport recall/précision détaillé"), unsafe_allow_html=True)
    rr1, rr2, rr3, rr4, rr5 = st.columns(5)
    rr1.metric("Recall métrique",    f"{_rr.get('recall_metric_level', 0):.1%}")
    rr2.metric("Recall valeur",      f"{_rr.get('recall_value_level', 0):.1%}")
    rr3.metric("Recall année cte",   f"{_rr.get('recall_current_year_level', 0):.1%}")
    rr4.metric("Carry-value rate",   f"{_rr.get('precision_proxy_carry_value', 0):.1%}",
               help="% des candidats GT qui portent une valeur")
    rr5.metric("Bruit (noise ratio)", f"{_rr.get('precision_proxy_noise_ratio', 0):.1%}",
               help="% de candidats hors ground truth")

    missed = _rr.get("missed_metric_ids", [])
    if missed:
        st.warning(f"⚠️ Métriques manquées : {', '.join(missed)}")
    else:
        st.success("✅ Toutes les métriques ground truth sont trouvées.")

    st.divider()

# ── Stats pipeline ─────────────────────────────────────────────────────────────
if stats_list:
    st.markdown(section_header_html("Stats pipeline par document"), unsafe_allow_html=True)
    stats_df = pd.DataFrame(stats_list)
    display_cols = [c for c in [
        "_company", "_year",
        "regex_candidates_count", "gliner_candidates_count",
        "candidates_current_year", "candidates_historical",
        "docling_status", "ocr_available",
    ] if c in stats_df.columns]
    if display_cols:
        rename = {
            "_company": "Entreprise", "_year": "Année",
            "regex_candidates_count": "Regex", "gliner_candidates_count": "GLiNER",
            "candidates_current_year": "Année cte", "candidates_historical": "Historique",
            "docling_status": "Docling", "ocr_available": "OCR",
        }
        st.dataframe(
            stats_df[display_cols].rename(columns=rename),
            use_container_width=True, hide_index=True,
        )

"""
Page 02 — Pipeline Cockpit
Vue temps réel du pipeline ESG pour tous les documents de l'index.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import pandas as pd

from ESGProductionControlCenter.src.esg_production_control_center.pipeline_status import (
    get_all_statuses,
)
from ESGProductionControlCenter.src.esg_production_control_center.styles import (
    get_global_css,
    section_header_html,
)

st.set_page_config(page_title="Pipeline Cockpit", layout="wide", page_icon="🚀")
st.markdown(get_global_css(), unsafe_allow_html=True)

_INDEX = _ROOT / "DocumentPostProcessing/data/quality_audit_v2/extraction_index_strict_likely_valid.csv"

# ── CSS additionnel ───────────────────────────────────────────────────────────
st.markdown("""
<style>
.step-badge {
    display: inline-flex; align-items: center; justify-content: center;
    border-radius: 6px; padding: 3px 9px; font-size: 0.68rem; font-weight: 700;
    white-space: nowrap; border: 1.5px solid;
}
.step-done   { background:#DCFCE7; color:#15803D; border-color:#86EFAC; }
.step-ready  { background:#FEF3C7; color:#B45309; border-color:#FCD34D; }
.step-active { background:#DBEAFE; color:#1D4ED8; border-color:#93C5FD; }
.step-todo   { background:#F1F5F9; color:#94A3B8; border-color:#E2E8F0; }
.arrow       { color:#CBD5E1; font-size:0.75rem; margin:0 2px; }
.doc-card    { border-radius:12px; }
.status-pill {
    display:inline-block; border-radius:20px; padding:2px 10px;
    font-size:0.7rem; font-weight:700; border:1.5px solid;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=30)
def _load() -> list[dict]:
    df = pd.read_csv(_INDEX)
    return get_all_statuses(_ROOT, df)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🚀 Pipeline Cockpit")
st.caption("Statut en temps réel · Tous les documents · Index strict likely-valid")

col_refresh, _ = st.columns([1, 7])
with col_refresh:
    if st.button("⟳ Actualiser", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

statuses = _load()

# ── KPI globaux ───────────────────────────────────────────────────────────────
total        = len(statuses)
done_04      = sum(1 for s in statuses if s["steps"]["04"])
done_review  = sum(1 for s in statuses if s["steps"]["review"])
done_06      = sum(1 for s in statuses if s["steps"]["06"])
total_cands  = sum(s["review_progress"]["total"]   for s in statuses)
total_decided = sum(s["review_progress"]["decided"] for s in statuses)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Documents index",      total)
k2.metric("Extraction complète",  f"{done_04}/{total}",
          delta=f"{total-done_04} restants" if total-done_04 else "Tous faits",
          delta_color="off")
k3.metric("Revue humaine faite",  f"{done_review}/{total}")
k4.metric("Base finalisée",       f"{done_06}/{total}")
k5.metric("Candidats décidés",    f"{total_decided:,}/{total_cands:,}",
          delta=f"{total_cands-total_decided:,} restants" if total_cands else "—",
          delta_color="off")

st.divider()

# ── Filtre ────────────────────────────────────────────────────────────────────
companies = sorted({s["company_slug"] for s in statuses})
fc1, fc2 = st.columns([2, 4])
selected_co = fc1.selectbox("Filtrer par entreprise", ["Toutes"] + companies)
filter_map  = {
    "Tous états": None,
    "✅ Terminé": "done",
    "✍️ En attente de revue": "awaiting_review",
    "⬜ Non commencé": "not_started",
}
selected_state = fc2.selectbox("Filtrer par état", list(filter_map.keys()))

# ── Cards documents ────────────────────────────────────────────────────────────
st.markdown(section_header_html("Documents"), unsafe_allow_html=True)

STEP_DEF = [
    ("01", "Extraction"),
    ("02", "Orchestr."),
    ("03", "Validation"),
    ("04", "Workspace"),
    ("review", "✍️ Revue"),
    ("05", "Appliqué"),
    ("06", "Base DB"),
]


def _overall_state(doc: dict) -> str:
    if doc["steps"]["06"]:
        return "done"
    if doc["steps"]["review"]:
        return "review_done"
    if doc["steps"]["04"]:
        return "awaiting_review"
    if doc["steps"]["01"]:
        return "extracting"
    return "not_started"


_STATUS_LABELS = {
    "done":           ("TERMINÉ",               "#15803D", "#F0FDF4", "#86EFAC"),
    "review_done":    ("REVUE FAITE",            "#1D4ED8", "#EFF6FF", "#93C5FD"),
    "awaiting_review":("EN ATTENTE DE REVUE",   "#B45309", "#FFFBEB", "#FCD34D"),
    "extracting":     ("EXTRACTION INCOMPLÈTE", "#7C3AED", "#F5F3FF", "#C4B5FD"),
    "not_started":    ("NON COMMENCÉ",           "#64748B", "#F8FAFC", "#E2E8F0"),
}


for doc in statuses:
    # Filtres
    if selected_co != "Toutes" and doc["company_slug"] != selected_co:
        continue
    state = _overall_state(doc)
    if selected_state != "Tous états" and filter_map[selected_state] and state != filter_map[selected_state]:
        continue

    label, fc, bg, bc = _STATUS_LABELS.get(state, _STATUS_LABELS["not_started"])
    steps  = doc["steps"]
    prog   = doc["review_progress"]

    with st.container(border=True):
        col_info, col_timeline, col_btn = st.columns([2, 5, 1], gap="medium")

        # ── Info colonne ──────────────────────────────────────────────────────
        with col_info:
            st.markdown(f"**{doc['company_name']}**")
            st.caption(f"{doc['fiscal_year']} · `{doc['doc_type']}`")
            st.markdown(
                f'<span class="status-pill" style="color:{fc};background:{bg};border-color:{bc};">'
                f'{label}</span>',
                unsafe_allow_html=True,
            )

        # ── Timeline des étapes ───────────────────────────────────────────────
        with col_timeline:
            parts: list[str] = []
            for i, (sid, slabel) in enumerate(STEP_DEF):
                done = steps.get(sid, False)

                if sid == "review":
                    if done:
                        cls = "step-active"
                    elif steps.get("04"):
                        cls = "step-ready"
                    else:
                        cls = "step-todo"
                else:
                    cls = "step-done" if done else "step-todo"

                parts.append(f'<span class="step-badge {cls}">{slabel}</span>')
                if i < len(STEP_DEF) - 1:
                    parts.append('<span class="arrow">→</span>')

            st.markdown(
                '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:2px;margin-top:6px;">'
                + "".join(parts)
                + "</div>",
                unsafe_allow_html=True,
            )

            # Barre de progression revue
            if prog["total"] > 0:
                pct = prog["decided"] / prog["total"]
                st.markdown(
                    f'<div style="margin-top:5px;font-size:0.72rem;color:#64748B;">'
                    f'Revue&nbsp;: <b>{prog["decided"]}/{prog["total"]}</b> candidats '
                    f'— {prog["accepted"]} ✅ &nbsp;{prog["rejected"]} ❌ &nbsp;{prog["more_info"]} ⏳'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.progress(pct)

        # ── Bouton action ─────────────────────────────────────────────────────
        with col_btn:
            if steps.get("04"):
                btn_label = "✍️ Revue" if not steps.get("review") else "📝 Modifier"
                btn_key = f"btn_{doc['company_slug']}_{doc['fiscal_year']}_{doc['doc_type']}"
                if st.button(btn_label, key=btn_key, use_container_width=True):
                    st.session_state["review_company"]  = doc["company_slug"]
                    st.session_state["review_year"]     = doc["fiscal_year"]
                    st.session_state["review_doc_type"] = doc["doc_type"]
                    st.session_state["review_canonical"] = doc["canonical_id"]
                    st.session_state["review_doc_dir"]  = doc["doc_dir"]
                    st.switch_page("pages/03_Human_Review.py")
            else:
                st.markdown(
                    '<div style="color:#CBD5E1;font-size:0.75rem;text-align:center;margin-top:8px;">—</div>',
                    unsafe_allow_html=True,
                )

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
pct_global = total_decided / total_cands * 100 if total_cands else 0
st.markdown(
    f'<div style="text-align:center;color:#94A3B8;font-size:0.75rem;">'
    f'Progression globale revue : {pct_global:.1f}% — '
    f'{total_decided:,} décidés sur {total_cands:,} candidats'
    f'</div>',
    unsafe_allow_html=True,
)

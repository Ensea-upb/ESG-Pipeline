"""
Page 03 — Revue Humaine
Interface interactive : approuver / rejeter / corriger les candidats ESG.
Génère review_decisions_filled.csv dans 04_review_workspace/.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd
import streamlit as st

from ESGProductionControlCenter.src.esg_production_control_center.pipeline_status import (
    find_document_dir,
    load_review_progress,
)
from ESGProductionControlCenter.src.esg_production_control_center.styles import get_global_css

st.set_page_config(page_title="Revue Humaine", layout="wide", page_icon="✍️")
st.markdown(get_global_css(), unsafe_allow_html=True)

_INDEX = _ROOT / "DocumentPostProcessing/data/quality_audit_v2/extraction_index_strict_likely_valid.csv"
_AUDIT_ROOT = _ROOT / "EXTERNAL_AUDIT_RUNS"

DECISION_OPTIONS = {
    "": "— Non décidé —",
    "accept_candidate": "✅ Accepter",
    "reject_candidate": "❌ Rejeter",
    "needs_more_evidence": "⏳ Plus d'infos",
}

FAMILY_COLORS = {
    "ghg_emissions":    "#FEF3C7",
    "energy":           "#DBEAFE",
    "water":            "#DCFCE7",
    "waste":            "#F3E8FF",
    "biodiversity":     "#ECFDF5",
    "social":           "#FFF1F2",
    "governance":       "#F0F9FF",
}

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.review-header {
    background: linear-gradient(135deg,#1E293B 0%,#1D4ED8 100%);
    border-radius:12px; padding:20px 24px; margin-bottom:16px; color:#fff;
}
.review-header h2 { margin:0; font-size:1.4rem; }
.review-header p  { margin:4px 0 0; opacity:0.75; font-size:0.85rem; }
.candidate-card {
    border:1.5px solid #E2E8F0; border-radius:10px;
    padding:12px 16px; margin-bottom:8px;
    transition: border-color 0.2s;
}
.candidate-card:hover { border-color:#93C5FD; }
.card-accepted  { border-left:4px solid #16A34A !important; background:#F0FDF4; }
.card-rejected  { border-left:4px solid #DC2626 !important; background:#FFF5F5; }
.card-more-info { border-left:4px solid #D97706 !important; background:#FFFBEB; }
.card-pending   { border-left:4px solid #E2E8F0 !important; }
.fam-badge {
    display:inline-block; border-radius:4px; padding:1px 7px;
    font-size:0.68rem; font-weight:700; background:#F1F5F9; color:#475569;
}
.quote-box {
    background:#F8FAFC; border-left:3px solid #93C5FD;
    border-radius:0 6px 6px 0; padding:6px 10px;
    font-size:0.78rem; color:#475569; font-style:italic;
    white-space:pre-wrap; word-break:break-word;
}
.conf-bar { height:6px; border-radius:3px; background:#E2E8F0; }
.progress-ring { font-size:1.8rem; font-weight:800; color:#1D4ED8; }
</style>
""", unsafe_allow_html=True)


# ── Chargement index ──────────────────────────────────────────────────────────
@st.cache_data
def _load_index() -> pd.DataFrame:
    return pd.read_csv(_INDEX)


index_df = _load_index()


# ── Sélecteur de document ─────────────────────────────────────────────────────
st.markdown("# ✍️ Revue Humaine")

companies = sorted(index_df["company_slug"].unique())
years_all  = sorted(index_df["fiscal_year"].astype(str).unique())

c1, c2, c3 = st.columns(3)

default_co = st.session_state.get("review_company", companies[0])
default_yr = st.session_state.get("review_year", years_all[0])
default_dt = st.session_state.get("review_doc_type", "")

co_idx = companies.index(default_co) if default_co in companies else 0
company = c1.selectbox("Entreprise", companies, index=co_idx, key="sel_company")

years = sorted(index_df[index_df["company_slug"] == company]["fiscal_year"].astype(str).unique())
yr_idx = years.index(default_yr) if default_yr in years else 0
year = c2.selectbox("Année", years, index=yr_idx, key="sel_year")

doc_types = sorted(
    index_df[(index_df["company_slug"] == company) & (index_df["fiscal_year"].astype(str) == year)][
        "official_doc_type"
    ].unique()
)
dt_idx = doc_types.index(default_dt) if default_dt in doc_types else 0
doc_type = c3.selectbox("Type de document", doc_types, index=dt_idx, key="sel_doctype")

row = index_df[
    (index_df["company_slug"] == company)
    & (index_df["fiscal_year"].astype(str) == year)
    & (index_df["official_doc_type"] == doc_type)
].iloc[0]
canonical_id = row["selected_canonical_document_id"]

doc_dir = find_document_dir(_AUDIT_ROOT, company, year, doc_type, canonical_id)


# ── Vérification workspace ────────────────────────────────────────────────────
if doc_dir is None:
    st.error(
        "Aucun répertoire de travail trouvé pour ce document. "
        "Lancez d'abord les étapes 01-04 depuis le Pipeline Cockpit."
    )
    st.stop()

workspace_path  = Path(doc_dir) / "04_review_workspace" / "manual_review_workspace.csv"
template_path   = Path(doc_dir) / "04_review_workspace" / "review_decisions_template.csv"
decisions_path  = Path(doc_dir) / "04_review_workspace" / "review_decisions_filled.csv"

if not workspace_path.exists():
    st.error(f"Workspace introuvable : {workspace_path}")
    st.stop()


# ── Chargement données ────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def _load_workspace(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data(ttl=30)
def _load_template(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


workspace = _load_workspace(str(workspace_path))
template  = _load_template(str(template_path)) if template_path.exists() else pd.DataFrame()

# Chargement décisions existantes dans session_state
_state_key = f"decisions_{canonical_id}"
if _state_key not in st.session_state:
    if decisions_path.exists():
        existing = pd.read_csv(decisions_path)
        st.session_state[_state_key] = dict(
            zip(
                existing["review_item_id"],
                existing.get("proposed_decision", pd.Series(dtype=str)).fillna(""),
            )
        )
    else:
        st.session_state[_state_key] = {}

decisions: dict[str, str] = st.session_state[_state_key]


# ── Header avec progression ───────────────────────────────────────────────────
decided = sum(1 for v in decisions.values() if v)
total   = len(workspace)
accepted  = sum(1 for v in decisions.values() if v == "accept_candidate")
rejected  = sum(1 for v in decisions.values() if v == "reject_candidate")
more_info = sum(1 for v in decisions.values() if v == "needs_more_evidence")
pct = decided / total * 100 if total else 0

st.markdown(
    f"""
    <div class="review-header">
        <h2>📄 {row.get('company_name', company)} · {year}</h2>
        <p>{doc_type} · {canonical_id}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total candidats",  total)
m2.metric("Décidés",          f"{decided} ({pct:.0f}%)")
m3.metric("✅ Acceptés",       accepted)
m4.metric("❌ Rejetés",        rejected)
m5.metric("⏳ Plus d'infos",   more_info)
st.progress(pct / 100)

st.divider()


# ── Filtres ───────────────────────────────────────────────────────────────────
f1, f2, f3, f4 = st.columns(4)

families = ["Toutes"] + sorted(workspace["indicator_family"].dropna().unique().tolist())
sel_fam = f1.selectbox("Famille ESG", families, key="rev_fam")

decision_filter_map = {
    "Tous": "",
    "— Non décidés": "__pending__",
    "✅ Acceptés": "accept_candidate",
    "❌ Rejetés": "reject_candidate",
    "⏳ Plus d'infos": "needs_more_evidence",
}
sel_dec = f2.selectbox("Décision", list(decision_filter_map.keys()), key="rev_dec")

search_q = f3.text_input("🔍 Recherche (indicateur / valeur)", key="rev_search")

PAGE_SIZE = f4.selectbox("Candidats par page", [25, 50, 100, 200], index=1, key="rev_pagesize")


# ── Filtrage données ──────────────────────────────────────────────────────────
view = workspace.copy()

if sel_fam != "Toutes":
    view = view[view["indicator_family"] == sel_fam]

dec_filter = decision_filter_map[sel_dec]
if dec_filter == "__pending__":
    view = view[view["review_item_id"].map(lambda x: not decisions.get(x, ""))]
elif dec_filter:
    view = view[view["review_item_id"].map(lambda x: decisions.get(x, "") == dec_filter)]

if search_q:
    mask = (
        view["label"].str.contains(search_q, case=False, na=False)
        | view["raw_value"].astype(str).str.contains(search_q, case=False, na=False)
        | view["indicator_family"].str.contains(search_q, case=False, na=False)
    )
    view = view[mask]

total_filtered = len(view)
page_count = max(1, (total_filtered + PAGE_SIZE - 1) // PAGE_SIZE)

# Pagination
if "rev_page" not in st.session_state:
    st.session_state["rev_page"] = 0
if st.session_state["rev_page"] >= page_count:
    st.session_state["rev_page"] = 0

p_col1, p_col2, p_col3 = st.columns([1, 3, 1])
with p_col1:
    if st.button("← Précédent", disabled=st.session_state["rev_page"] == 0, use_container_width=True):
        st.session_state["rev_page"] -= 1
        st.rerun()
with p_col2:
    st.markdown(
        f'<div style="text-align:center;padding-top:8px;font-size:0.85rem;color:#64748B;">'
        f'Page {st.session_state["rev_page"]+1} / {page_count} — {total_filtered:,} candidats filtrés'
        f'</div>',
        unsafe_allow_html=True,
    )
with p_col3:
    if st.button("Suivant →", disabled=st.session_state["rev_page"] >= page_count - 1, use_container_width=True):
        st.session_state["rev_page"] += 1
        st.rerun()

start = st.session_state["rev_page"] * PAGE_SIZE
page_view = view.iloc[start : start + PAGE_SIZE]


# ── Rendu des candidats ───────────────────────────────────────────────────────
st.markdown(f"**{total_filtered:,} candidats** — page {st.session_state['rev_page']+1}/{page_count}")

for _, cand in page_view.iterrows():
    item_id = cand["review_item_id"]
    current_dec = decisions.get(item_id, "")

    card_cls = {
        "accept_candidate": "card-accepted",
        "reject_candidate": "card-rejected",
        "needs_more_evidence": "card-more-info",
    }.get(current_dec, "card-pending")

    fam_color = FAMILY_COLORS.get(cand.get("indicator_family", ""), "#F1F5F9")
    conf = float(cand.get("confidence", 0) or 0)
    conf_pct = int(conf * 100)

    with st.container():
        st.markdown(f'<div class="candidate-card {card_cls}">', unsafe_allow_html=True)

        row1, row2 = st.columns([5, 2])

        with row1:
            # Ligne principale
            fam = cand.get("indicator_family", "—")
            label = cand.get("label", "—")
            val = cand.get("raw_value", "—")
            unit = cand.get("raw_unit", "")
            page = cand.get("page_number", "?")
            engine = cand.get("source_engine", "")

            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
                f'<span class="fam-badge" style="background:{fam_color};">{fam}</span>'
                f'<span style="font-weight:700;font-size:0.9rem;color:#1E293B;">{label}</span>'
                f'<span style="color:#2563EB;font-weight:700;font-size:0.95rem;">{val} {unit}</span>'
                f'<span style="color:#94A3B8;font-size:0.75rem;">p.{page} · {engine}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Citation
            quote = str(cand.get("quote", "") or "").strip()
            if quote:
                short_quote = quote[:220] + ("…" if len(quote) > 220 else "")
                st.markdown(f'<div class="quote-box">{short_quote}</div>', unsafe_allow_html=True)

            # Confiance
            conf_color = "#16A34A" if conf >= 0.7 else "#D97706" if conf >= 0.4 else "#DC2626"
            st.markdown(
                f'<div style="margin-top:4px;font-size:0.72rem;color:#64748B;">'
                f'Confiance : <span style="color:{conf_color};font-weight:700;">{conf_pct}%</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with row2:
            # Boutons de décision
            cols_btn = st.columns(3)
            if cols_btn[0].button(
                "✅", key=f"acc_{item_id}", help="Accepter ce candidat",
                type="primary" if current_dec == "accept_candidate" else "secondary",
            ):
                decisions[item_id] = "accept_candidate"
                st.session_state[_state_key] = decisions
                st.rerun()
            if cols_btn[1].button(
                "❌", key=f"rej_{item_id}", help="Rejeter ce candidat",
                type="primary" if current_dec == "reject_candidate" else "secondary",
            ):
                decisions[item_id] = "reject_candidate"
                st.session_state[_state_key] = decisions
                st.rerun()
            if cols_btn[2].button(
                "⏳", key=f"more_{item_id}", help="Besoin de plus d'infos",
                type="primary" if current_dec == "needs_more_evidence" else "secondary",
            ):
                decisions[item_id] = "needs_more_evidence"
                st.session_state[_state_key] = decisions
                st.rerun()

            # Label décision courante
            dec_label = {
                "accept_candidate":    "✅ Accepté",
                "reject_candidate":    "❌ Rejeté",
                "needs_more_evidence": "⏳ Plus d'infos",
            }.get(current_dec, "— En attente —")
            st.markdown(
                f'<div style="text-align:center;font-size:0.75rem;color:#64748B;margin-top:4px;">'
                f'{dec_label}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)


# ── Barre de sauvegarde fixe en bas ──────────────────────────────────────────
st.divider()
save_col1, save_col2, save_col3 = st.columns([2, 2, 2])

reviewer_name = save_col1.text_input(
    "Votre nom (reviewer)", value="human_reviewer", key="reviewer_name"
)

with save_col2:
    n_undecided = total - sum(1 for v in decisions.values() if v)
    if n_undecided > 0:
        st.info(f"{n_undecided} candidats non décidés — ils seront ignorés à la sauvegarde.")

with save_col3:
    if st.button("💾 Sauvegarder les décisions", type="primary", use_container_width=True):
        if template.empty:
            st.error("Template de décisions introuvable.")
        else:
            out = template.copy()
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            for idx, trow in out.iterrows():
                iid = trow["review_item_id"]
                dec = decisions.get(iid, "")
                out.at[idx, "proposed_decision"] = dec if dec else None
                if dec:
                    out.at[idx, "reviewer"]    = reviewer_name
                    out.at[idx, "review_date"] = today

            # 1. Sauvegarde dans le workspace (pour tracking)
            out.to_csv(decisions_path, index=False)

            # 2. Sauvegarde dans la structure attendue par run_strict_index_pilot
            #    decisions_root/company/year/doc_type/review_decisions_filled.csv
            decisions_root_path = _ROOT / "DECISIONS" / company / year / doc_type
            decisions_root_path.mkdir(parents=True, exist_ok=True)
            out.to_csv(decisions_root_path / "review_decisions_filled.csv", index=False)

            st.cache_data.clear()
            n_decided = sum(1 for v in decisions.values() if v)
            st.success(f"✅ {n_decided} décisions sauvegardées.")
            st.toast("Fichier sauvegardé !", icon="✅")


# ── Bouton lancement pipeline ─────────────────────────────────────────────────
if decisions_path.exists():
    st.divider()
    launch_c1, launch_c2 = st.columns([3, 1])

    with launch_c1:
        st.markdown("### 🚀 Lancer les étapes 05 → 06 → 08")
        st.caption(
            "Applique les décisions, construit la base indicateurs et le dataset ESG final. "
            "Durée estimée : 1-3 minutes."
        )

    with launch_c2:
        run_root_choices = [
            str(d.relative_to(_ROOT)).replace("\\", "/")
            for d in (_ROOT / "EXTERNAL_AUDIT_RUNS").iterdir()
            if d.is_dir() and (d / "pilot_run_summary.json").exists()
        ]
        selected_run = st.selectbox("Run de sortie", run_root_choices, key="launch_run")

    if st.button("▶️ Lancer le pipeline (05→08)", type="primary", use_container_width=True):
        cmd = [
            sys.executable,
            str(_ROOT / "run_strict_index_pilot.py"),
            "--mode",            "apply-review-and-build-dataset",
            "--index-path",      str(_ROOT / "DocumentPostProcessing/data/quality_audit_v2/extraction_index_strict_likely_valid.csv"),
            "--output-root",     str(_ROOT / selected_run),
            "--decisions-root",  str(_ROOT / "DECISIONS"),
            "--company-slug",    company,
            "--fiscal-year",     year,
            "--doc-type",        doc_type,
            "--execute",
            "--max-documents",   "1",
            "--overwrite",
        ]
        with st.spinner("Pipeline en cours…"):
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, cwd=str(_ROOT), timeout=300
                )
                if result.returncode == 0:
                    st.success("Pipeline terminé avec succès !")
                    st.balloons()
                else:
                    st.error("Erreur dans le pipeline.")
                with st.expander("Logs pipeline"):
                    st.code(result.stdout[-4000:] + result.stderr[-2000:])
            except subprocess.TimeoutExpired:
                st.error("Timeout (5 min). Le pipeline tourne peut-être toujours en arrière-plan.")
            except Exception as exc:
                st.error(f"Erreur : {exc}")

"""
Page 12 — Base de données ESG finale
Affiche esg_values.csv + esg_lineage.csv depuis MASTER_ESG_OUTPUT/.
Permet de relancer le build depuis l'interface.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd
import streamlit as st

from ESGProductionControlCenter.src.esg_production_control_center.styles import (
    get_global_css,
    section_header_html,
)

st.set_page_config(page_title="Base ESG Finale", layout="wide", page_icon="🗄️")
st.markdown(get_global_css(), unsafe_allow_html=True)

_MASTER_DIR   = _ROOT / "MASTER_ESG_OUTPUT"
_VALUES_PATH  = _MASTER_DIR / "esg_values.csv"
_LINEAGE_PATH = _MASTER_DIR / "esg_lineage.csv"
_SUMMARY_PATH = _MASTER_DIR / "build_summary.json"
_BUILD_SCRIPT = _ROOT / "build_master_esg_dataset.py"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.db-header {
    background: linear-gradient(135deg,#0F172A 0%,#065F46 100%);
    border-radius:12px; padding:20px 24px; margin-bottom:20px; color:#fff;
}
.db-header h2 { margin:0; font-size:1.4rem; }
.db-header p  { margin:4px 0 0; opacity:0.7; font-size:0.85rem; }
.lineage-card {
    border:1.5px solid #E2E8F0; border-radius:8px;
    padding:10px 14px; margin-bottom:6px;
    border-left:4px solid #16A34A;
}
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="db-header">
  <h2>🗄️ Base de données ESG finale</h2>
  <p>esg_values.csv · esg_lineage.csv · MASTER_ESG_OUTPUT/</p>
</div>
""", unsafe_allow_html=True)


# ── Bouton build ──────────────────────────────────────────────────────────────
b1, b2, b3 = st.columns([2, 2, 4])

with b1:
    if st.button("🔨 (Re)construire le dataset", type="primary", use_container_width=True):
        with st.spinner("Construction en cours…"):
            result = subprocess.run(
                [sys.executable, str(_BUILD_SCRIPT), "--output-dir", str(_MASTER_DIR), "--overwrite"],
                capture_output=True, text=True, cwd=str(_ROOT),
            )
        if result.returncode == 0:
            st.toast("Dataset construit !", icon="✅")
            st.rerun()
        else:
            st.error("Erreur lors du build.")
            st.code(result.stderr[-2000:])

with b2:
    if st.button("⟳ Actualiser", use_container_width=True):
        st.rerun()

# ── Résumé du dernier build ───────────────────────────────────────────────────
if _SUMMARY_PATH.exists():
    summary = json.loads(_SUMMARY_PATH.read_text(encoding="utf-8"))
    built_at = summary.get("built_at", "—")[:19].replace("T", " ")
    st.caption(
        f"Dernier build : **{built_at} UTC** · "
        f"{summary.get('sources_scanned', 0)} sources scannées · "
        f"{summary.get('found_values', 0)} valeurs trouvées · "
        f"Complétion **{summary.get('completion_pct', 0):.1f}%**"
    )

if not _VALUES_PATH.exists():
    st.warning("Aucun dataset trouvé. Cliquez **Construire le dataset** pour générer les fichiers.")
    st.stop()


# ── Chargement données ────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def _load_values() -> pd.DataFrame:
    return pd.read_csv(_VALUES_PATH)

@st.cache_data(ttl=30)
def _load_lineage() -> pd.DataFrame:
    return pd.read_csv(_LINEAGE_PATH) if _LINEAGE_PATH.exists() else pd.DataFrame()


df_values  = _load_values()
df_lineage = _load_lineage()

META_COLS = {"company_name", "company_slug", "fiscal_year"}
var_cols  = [c for c in df_values.columns if c not in META_COLS]

# ── KPI globaux ───────────────────────────────────────────────────────────────
total_cells   = len(df_values) * len(var_cols)
found_cells   = int(df_values[var_cols].notna().sum().sum()) if var_cols else 0
missing_cells = total_cells - found_cells
completion    = found_cells / total_cells * 100 if total_cells else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Entreprises × années", len(df_values))
k2.metric("Variables ESG",        len(var_cols))
k3.metric("Valeurs trouvées",     found_cells)
k4.metric("Valeurs manquantes",   missing_cells)
k5.metric("Complétion",           f"{completion:.1f}%")
st.progress(completion / 100)

st.divider()

# ── Onglets ───────────────────────────────────────────────────────────────────
tab_values, tab_heatmap, tab_lineage, tab_var = st.tabs([
    "📊 Tableau wide",
    "🗺️ Heatmap",
    "🔍 Traçabilité",
    "🔎 Détail variable",
])

# ── Tab 1 : Tableau wide ──────────────────────────────────────────────────────
with tab_values:
    st.markdown(section_header_html("esg_values.csv — une ligne par entreprise × année"), unsafe_allow_html=True)

    f1, f2 = st.columns(2)
    search_var = f1.text_input("Filtrer variables", key="val_search")
    show_missing = f2.checkbox("Variables manquantes uniquement", key="val_missing")

    display_vars = var_cols
    if search_var:
        display_vars = [c for c in var_cols if search_var.lower() in c.lower()]
    if show_missing:
        display_vars = [c for c in display_vars if df_values[c].isna().all()]

    id_cols = [c for c in ["company_name", "company_slug", "fiscal_year"] if c in df_values.columns]
    st.dataframe(
        df_values[id_cols + display_vars],
        height=max(120, min(500, len(df_values) * 50 + 60)),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "⬇️ Télécharger esg_values.csv",
        df_values.to_csv(index=False).encode("utf-8"),
        "esg_values.csv", "text/csv",
        use_container_width=True,
    )

# ── Tab 2 : Heatmap ───────────────────────────────────────────────────────────
with tab_heatmap:
    st.markdown(section_header_html("Complétion par variable"), unsafe_allow_html=True)
    if not df_values.empty and var_cols:
        try:
            import plotly.express as px

            heat = df_values[var_cols].notna().astype(int)
            id_cols = [c for c in ["company_name", "company_slug", "fiscal_year"] if c in df_values.columns]
            if id_cols:
                heat.index = df_values[id_cols].astype(str).agg(" · ".join, axis=1)

            fig = px.imshow(
                heat,
                color_continuous_scale=[[0, "#F1F5F9"], [1, "#16A34A"]],
                aspect="auto",
                labels=dict(x="Variable ESG", y="Entreprise", color="Trouvé"),
                zmin=0, zmax=1,
            )
            fig.update_layout(
                height=max(160, len(df_values) * 60 + 100),
                margin=dict(t=20, b=10, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                coloraxis_showscale=False,
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        except ImportError:
            st.dataframe(df_values[var_cols].notna().astype(int), use_container_width=True)
    else:
        st.info("Aucune donnée à afficher.")

# ── Tab 3 : Traçabilité ───────────────────────────────────────────────────────
with tab_lineage:
    st.markdown(section_header_html("esg_lineage.csv — d'où vient chaque valeur"), unsafe_allow_html=True)

    if df_lineage.empty:
        st.info("Aucune ligne de traçabilité disponible.")
    else:
        # Filtres
        l1, l2 = st.columns(2)
        companies_l = ["Toutes"] + sorted(df_lineage["company_slug"].dropna().unique().tolist()) if "company_slug" in df_lineage.columns else ["Toutes"]
        sel_co = l1.selectbox("Entreprise", companies_l, key="lin_co")
        vars_l = ["Toutes"] + sorted(df_lineage["variable"].dropna().unique().tolist()) if "variable" in df_lineage.columns else ["Toutes"]
        sel_var = l2.selectbox("Variable", vars_l, key="lin_var")

        view = df_lineage.copy()
        if sel_co != "Toutes" and "company_slug" in view.columns:
            view = view[view["company_slug"] == sel_co]
        if sel_var != "Toutes" and "variable" in view.columns:
            view = view[view["variable"] == sel_var]

        st.caption(f"{len(view)} lignes de traçabilité")

        # Affichage par carte
        for _, row in view.iterrows():
            quote = str(row.get("source_quote", "") or "")[:200]
            st.markdown(
                f"""
                <div class="lineage-card">
                  <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;">
                    <strong>{row.get('company_slug','—')}</strong>
                    <span style="color:#64748B">{row.get('fiscal_year','—')}</span>
                    <span style="background:#DCFCE7;color:#15803D;border-radius:4px;padding:1px 7px;font-size:0.75rem;font-weight:700;">
                      {row.get('variable','—')}
                    </span>
                    <span style="font-size:1rem;font-weight:700;color:#1D4ED8;">
                      {row.get('value','—')} {row.get('unit','') or ''}
                    </span>
                    <span style="color:#94A3B8;font-size:0.75rem;">p.{row.get('source_page','?')}</span>
                    <span style="color:#94A3B8;font-size:0.75rem;">par {row.get('reviewer','—')}</span>
                  </div>
                  {"<div style='margin-top:6px;font-style:italic;font-size:0.78rem;color:#475569;border-left:3px solid #93C5FD;padding-left:8px;'>" + quote + "</div>" if quote else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.download_button(
            "⬇️ Télécharger esg_lineage.csv",
            df_lineage.to_csv(index=False).encode("utf-8"),
            "esg_lineage.csv", "text/csv",
            use_container_width=True,
        )

# ── Tab 4 : Détail variable ───────────────────────────────────────────────────
with tab_var:
    st.markdown(section_header_html("Zoom sur une variable"), unsafe_allow_html=True)
    sel_v = st.selectbox("Variable ESG", var_cols if var_cols else ["—"], key="db_var_zoom")
    if sel_v and sel_v in df_values.columns:
        id_cols_z = [c for c in ["company_name", "company_slug", "fiscal_year"] if c in df_values.columns]
        vdf = df_values[id_cols_z + [sel_v]].copy()
        vdf["Statut"] = vdf[sel_v].apply(
            lambda v: "✅ Trouvé" if pd.notna(v) and str(v).strip() not in ("", "nan") else "❌ Manquant"
        )
        st.dataframe(vdf, use_container_width=True, hide_index=True)

        # Traçabilité pour cette variable
        if not df_lineage.empty and "variable" in df_lineage.columns:
            lin_v = df_lineage[df_lineage["variable"] == sel_v]
            if not lin_v.empty:
                st.markdown("**Sources :**")
                for _, r in lin_v.iterrows():
                    st.markdown(f"- `{r.get('company_slug','?')}` · {r.get('fiscal_year','?')} · p.{r.get('source_page','?')} · **{r.get('value','?')} {r.get('unit','') or ''}** · reviewer: {r.get('reviewer','?')}")

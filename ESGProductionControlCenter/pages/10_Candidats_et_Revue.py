"""
Page 10 — Candidats & Revue v3.0
Explorer les candidats ESG avec charts Plotly interactifs.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import pandas as pd

from ESGProductionControlCenter.src.esg_production_control_center.data_loader import (
    build_candidate_table, build_document_index,
)
from ESGProductionControlCenter.src.esg_production_control_center.filters import (
    apply_all_filters, get_priority_queue, add_human_labels, get_unique_values,
)
from ESGProductionControlCenter.src.esg_production_control_center.ui_components import setup_sidebar
from ESGProductionControlCenter.src.esg_production_control_center.styles import (
    get_global_css, badge_html, section_header_html,
)

st.set_page_config(page_title="Candidats & Revue", layout="wide", page_icon="🔬")
st.markdown(get_global_css(), unsafe_allow_html=True)
run_root = setup_sidebar("Candidats & Revue")

st.markdown("# 🔬 Candidats & Revue")
st.caption("Explorer les candidats ESG extraits · Préparer la file de revue humaine.")

@st.cache_data(ttl=60)
def _load(rr: str):
    return build_candidate_table(Path(rr))

df = _load(str(run_root))

if df.empty:
    st.warning("Aucun candidat trouvé. Vérifiez le run sélectionné dans la barre latérale.")
    st.stop()

n_docs = df["_document_id"].nunique() if "_document_id" in df.columns else "?"

# ── KPI banner ─────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total candidats", f"{len(df):,}")
k2.metric("Documents couverts", n_docs)
n_pos = int((df.get("validation_status", pd.Series()) == "possible_indicator").sum()) if "validation_status" in df.columns else 0
n_nr  = int((df.get("validation_status", pd.Series()) == "needs_review").sum()) if "validation_status" in df.columns else 0
n_rej = int((df.get("validation_status", pd.Series()) == "reject_candidate").sum()) if "validation_status" in df.columns else 0
k3.metric("Utiles (possible)", n_pos, f"{n_pos/len(df)*100:.0f}%" if len(df) else "")
k4.metric("A vérifier", n_nr, f"{n_nr/len(df)*100:.0f}%" if len(df) else "")
k5.metric("Bruit", n_rej, f"{n_rej/len(df)*100:.0f}%" if len(df) else "")

st.divider()

tab_all, tab_charts, tab_priority, tab_doc = st.tabs([
    "🔍 Tous les candidats",
    "📊 Analyse visuelle",
    "⭐ File de revue prioritaire",
    "📄 Par document",
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — Tous les candidats
# ══════════════════════════════════════════════════════════════
with tab_all:
    col1, col2, col3 = st.columns(3)
    status_map = {
        "Tous": "", "🟢 Utiles": "possible_indicator",
        "🟡 À vérifier": "needs_review", "🔴 Bruit": "reject_candidate",
    }
    status_f  = col1.selectbox("Statut", list(status_map.keys()))
    family_f  = col2.selectbox("Famille ESG", ["Toutes"] + get_unique_values(df, "indicator_family"))
    company_f = col3.selectbox("Entreprise",  ["Toutes"] + get_unique_values(df, "_company_slug"))

    col4, col5 = st.columns(2)
    quote_q = col4.text_input("Recherche dans la citation")
    label_q = col5.text_input("Recherche dans le label")

    view = apply_all_filters(
        df,
        status=status_map[status_f],
        family="" if family_f == "Toutes" else family_f,
        company="" if company_f == "Toutes" else company_f,
        quote_query=quote_q,
        label_query=label_q,
    )
    view = add_human_labels(view)
    pct = len(view) / len(df) * 100 if len(df) else 0

    if len(view) == len(df):
        st.success(f"{len(view):,} candidats — aucun filtre actif")
    else:
        st.info(f"{len(view):,} candidats ({pct:.1f}% du total)")

    COLS = [c for c in ["_company_slug", "_fiscal_year", "page_number", "Statut",
                         "Famille", "label", "raw_value", "raw_unit", "quote"] if c in view.columns]
    RENAME = {
        "_company_slug": "Entreprise", "_fiscal_year": "Année",
        "page_number": "Page", "label": "Indicateur",
        "raw_value": "Valeur", "raw_unit": "Unité", "quote": "Citation",
    }
    st.dataframe(
        view[COLS].rename(columns=RENAME).head(2000),
        height=450, use_container_width=True, hide_index=True,
    )
    if len(view) > 2000:
        st.caption("2 000 premiers affichés. Affinez les filtres ou téléchargez.")
    st.download_button(
        "⬇️ Télécharger vue CSV",
        view[COLS].to_csv(index=False).encode("utf-8"),
        "candidats_export.csv", "text/csv",
    )

# ══════════════════════════════════════════════════════════════
# TAB 2 — Analyse visuelle
# ══════════════════════════════════════════════════════════════
with tab_charts:
    try:
        import plotly.express as px
        import plotly.graph_objects as go

        chart_col1, chart_col2 = st.columns(2)

        # Donut statut
        with chart_col1:
            st.markdown(section_header_html("Répartition par statut"), unsafe_allow_html=True)
            if "validation_status" in df.columns:
                vc_s = df["validation_status"].value_counts().reset_index()
                vc_s.columns = ["Statut", "N"]
                label_map_s = {
                    "possible_indicator": "Utiles",
                    "needs_review":       "À vérifier",
                    "reject_candidate":   "Bruit",
                }
                color_map_s = {"Utiles": "#16A34A", "À vérifier": "#D97706", "Bruit": "#DC2626"}
                vc_s["Statut"] = vc_s["Statut"].map(label_map_s).fillna(vc_s["Statut"])
                fig_s = px.pie(vc_s, values="N", names="Statut",
                               color="Statut", color_discrete_map=color_map_s, hole=0.55)
                fig_s.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10),
                                    paper_bgcolor="rgba(0,0,0,0)",
                                    showlegend=True,
                                    legend=dict(orientation="h", y=-0.15, x=0.1))
                fig_s.update_traces(textinfo="percent+value", textfont_size=11)
                st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False})

        # Bar famille
        with chart_col2:
            st.markdown(section_header_html("Candidats par famille ESG"), unsafe_allow_html=True)
            if "indicator_family" in df.columns:
                vc_f = (df["indicator_family"]
                        .value_counts()
                        .reset_index()
                        .rename(columns={"indicator_family": "Famille", "count": "N"}))
                fig_f = px.bar(
                    vc_f.sort_values("N", ascending=True).tail(15),
                    x="N", y="Famille", orientation="h",
                    color="N", color_continuous_scale="Blues",
                )
                fig_f.update_layout(
                    height=280, margin=dict(t=10, b=10, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_f, use_container_width=True, config={"displayModeBar": False})

        st.divider()

        chart_col3, chart_col4 = st.columns(2)

        # Distribution de confiance
        with chart_col3:
            st.markdown(section_header_html("Distribution de la confiance"), unsafe_allow_html=True)
            if "confidence" in df.columns:
                conf_vals = pd.to_numeric(df["confidence"], errors="coerce").dropna()
                fig_conf = px.histogram(
                    conf_vals, x=conf_vals, nbins=20,
                    color_discrete_sequence=["#2563EB"],
                    labels={"x": "Confiance", "y": "Candidats"},
                )
                fig_conf.update_layout(
                    height=260, margin=dict(t=10, b=10, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    bargap=0.05, showlegend=False,
                )
                fig_conf.update_xaxes(range=[0, 1])
                st.plotly_chart(fig_conf, use_container_width=True, config={"displayModeBar": False})

        # Candidats par page (top 30)
        with chart_col4:
            st.markdown(section_header_html("Pages les plus riches"), unsafe_allow_html=True)
            if "page_number" in df.columns:
                page_df = (df[df["page_number"].astype(str).str.strip() != ""]
                           .groupby("page_number").size()
                           .sort_values(ascending=False)
                           .reset_index(name="Candidats")
                           .rename(columns={"page_number": "Page"})
                           .head(20))
                try:
                    page_df["Page"] = page_df["Page"].astype(int)
                    page_df = page_df.sort_values("Page")
                except Exception:
                    pass
                fig_pg = px.bar(page_df, x="Page", y="Candidats",
                                color_discrete_sequence=["#7C3AED"])
                fig_pg.update_layout(
                    height=260, margin=dict(t=10, b=10, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_pg, use_container_width=True, config={"displayModeBar": False})

        st.divider()

        # Heatmap famille × statut
        st.markdown(section_header_html("Heatmap famille × statut de validation"), unsafe_allow_html=True)
        if "indicator_family" in df.columns and "validation_status" in df.columns:
            heat_data = (df.groupby(["indicator_family", "validation_status"])
                         .size()
                         .reset_index(name="N"))
            pivot = heat_data.pivot(
                index="indicator_family", columns="validation_status", values="N"
            ).fillna(0)
            # Rename columns for display
            pivot.columns = [{"possible_indicator": "Utiles",
                              "needs_review": "À vérifier",
                              "reject_candidate": "Bruit"}.get(c, c) for c in pivot.columns]

            fig_heat = px.imshow(
                pivot,
                color_continuous_scale="RdYlGn",
                aspect="auto",
                labels=dict(x="Statut", y="Famille", color="N"),
                text_auto=True,
            )
            fig_heat.update_layout(
                height=max(200, len(pivot) * 30),
                margin=dict(t=20, b=10, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            fig_heat.update_traces(textfont_size=11)
            st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})

    except ImportError:
        st.info("Installez `plotly` pour activer les graphiques interactifs : `pip install plotly`")
        if "validation_status" in df.columns:
            st.bar_chart(df["validation_status"].value_counts())

# ══════════════════════════════════════════════════════════════
# TAB 3 — File prioritaire
# ══════════════════════════════════════════════════════════════
with tab_priority:
    priority_df = get_priority_queue(df)
    st.markdown(f"**{len(priority_df):,} candidats prioritaires** — `possible_indicator` + valeur + citation + famille connue")

    if priority_df.empty:
        st.info("Aucun candidat ne satisfait tous les critères de priorité.")
    else:
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Prioritaires",     len(priority_df))
        p2.metric("% du total",       f"{len(priority_df)/len(df)*100:.1f}%")
        p3.metric("Charge estimée",   f"{len(priority_df)*3/60:.0f}h")
        nd = priority_df["_document_id"].nunique() if "_document_id" in priority_df.columns else "?"
        p4.metric("Documents couverts", nd)

        c_f   = st.selectbox("Entreprise", ["Toutes"] + get_unique_values(priority_df, "_company_slug"), key="pq_co")
        fam_f = st.selectbox("Famille ESG", ["Toutes les familles"] + get_unique_values(priority_df, "indicator_family"), key="pq_fam")
        pview = priority_df.copy()
        if c_f != "Toutes" and "_company_slug" in pview.columns:
            pview = pview[pview["_company_slug"] == c_f]
        if fam_f != "Toutes les familles" and "indicator_family" in pview.columns:
            pview = pview[pview["indicator_family"] == fam_f]
        pview = add_human_labels(pview)

        PCOLS = [c for c in ["review_item_id", "_company_slug", "_fiscal_year",
                              "page_number", "Famille", "label",
                              "raw_value", "raw_unit", "normalized_value", "normalized_unit",
                              "quote", "confidence"] if c in pview.columns]
        PRENAME = {
            "review_item_id": "ID", "_company_slug": "Entreprise",
            "_fiscal_year": "Année", "page_number": "Page",
            "label": "Indicateur", "raw_value": "Valeur", "raw_unit": "Unité",
            "normalized_value": "Val. norm.", "normalized_unit": "Unit. norm.",
            "quote": "Citation", "confidence": "Conf.",
        }
        st.caption(f"{len(pview):,} candidats prioritaires affichés.")
        st.dataframe(
            pview[PCOLS].rename(columns=PRENAME),
            height=450, use_container_width=True, hide_index=True,
        )
        st.download_button(
            "⬇️ Télécharger file prioritaire",
            pview[PCOLS].to_csv(index=False).encode("utf-8"),
            "review_queue.csv", "text/csv",
        )

# ══════════════════════════════════════════════════════════════
# TAB 4 — Par document
# ══════════════════════════════════════════════════════════════
with tab_doc:
    if "_company_slug" not in df.columns:
        st.info("Données de document non disponibles.")
        st.stop()

    d1, d2, d3, d4 = st.columns(4)
    companies = sorted(df["_company_slug"].dropna().unique())
    co  = d1.selectbox("Entreprise", companies, key="di_co")
    years_doc = sorted(df[df["_company_slug"] == co]["_fiscal_year"].dropna().unique()) if co else []
    yr  = d2.selectbox("Année", years_doc, key="di_yr")
    dtypes = sorted(df[(df["_company_slug"] == co) & (df["_fiscal_year"] == yr)]["_official_doc_type"].dropna().unique()) if yr else []
    dt  = d3.selectbox("Type", dtypes, key="di_dt")
    doc_ids = sorted(df[(df["_company_slug"] == co) & (df["_fiscal_year"] == yr) & (df["_official_doc_type"] == dt)]["_document_id"].dropna().unique()) if dt else []
    did = d4.selectbox("Document ID", doc_ids, key="di_did")

    if not did:
        st.info("Sélectionnez un document.")
    else:
        doc_df = df[df["_document_id"] == did].copy()
        n_pos_d = int((doc_df.get("validation_status", pd.Series()) == "possible_indicator").sum()) if "validation_status" in doc_df.columns else 0
        n_nr_d  = int((doc_df.get("validation_status", pd.Series()) == "needs_review").sum()) if "validation_status" in doc_df.columns else 0
        n_rej_d = int((doc_df.get("validation_status", pd.Series()) == "reject_candidate").sum()) if "validation_status" in doc_df.columns else 0

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Total", len(doc_df))
        s2.metric("Utiles", n_pos_d)
        s3.metric("À vérifier", n_nr_d)
        s4.metric("Bruit", n_rej_d)

        sub = st.radio("Afficher", ["🟢 Utiles", "🟡 À vérifier", "🔴 Bruit", "Tous"],
                       horizontal=True, key="di_filter")
        sub_map = {"🟢 Utiles": "possible_indicator", "🟡 À vérifier": "needs_review",
                   "🔴 Bruit": "reject_candidate"}
        if sub in sub_map and "validation_status" in doc_df.columns:
            sub_df = doc_df[doc_df["validation_status"] == sub_map[sub]]
        else:
            sub_df = doc_df

        DCOLS = [c for c in ["page_number", "indicator_family", "label", "raw_value",
                              "raw_unit", "quote", "confidence", "source_engine"] if c in sub_df.columns]
        st.dataframe(add_human_labels(sub_df)[DCOLS],
                     height=420, use_container_width=True, hide_index=True)

        if "page_number" in doc_df.columns:
            try:
                import plotly.express as px
                page_counts = (doc_df[doc_df["page_number"].astype(str).str.strip() != ""]
                               .groupby("page_number").size()
                               .sort_values(ascending=False)
                               .reset_index(name="Candidats")
                               .rename(columns={"page_number": "Page"})
                               .head(30))
                with st.expander("Distribution par page", expanded=False):
                    fig_pg_doc = px.bar(
                        page_counts.sort_values("Page"),
                        x="Page", y="Candidats",
                        color_discrete_sequence=["#2563EB"],
                    )
                    fig_pg_doc.update_layout(
                        height=220, margin=dict(t=10, b=10, l=10, r=10),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_pg_doc, use_container_width=True,
                                    config={"displayModeBar": False})
            except ImportError:
                with st.expander("Distribution par page"):
                    page_counts = (doc_df.groupby("page_number").size()
                                   .sort_values(ascending=False).head(30))
                    st.bar_chart(page_counts)

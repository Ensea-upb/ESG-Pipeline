"""
Page 11 — Analyse & Décision v3.0
Décision GO/NO_GO avec gauges Plotly, critères visuels, next steps.
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
    load_pilot_summary, build_candidate_table, load_false_positive_risks,
    load_top_possible_indicators, load_candidate_counts_by_family,
)
from ESGProductionControlCenter.src.esg_production_control_center.metrics import compute_all_metrics
from ESGProductionControlCenter.src.esg_production_control_center.decision_rules import (
    compute_decision, get_decision_reasons, GO_EXPLANATION, NEXT_STEPS,
)
from ESGProductionControlCenter.src.esg_production_control_center.ui_components import (
    setup_sidebar, format_rate, format_hours,
)
from ESGProductionControlCenter.src.esg_production_control_center.export_utils import (
    export_quality_decision_report, export_manual_baseline_template,
    MANUAL_BASELINE_COLUMNS, V1_ERROR_TYPES,
)
from ESGProductionControlCenter.src.esg_production_control_center.styles import (
    get_global_css, decision_hero_html, badge_html, section_header_html,
)

st.set_page_config(page_title="Analyse & Décision", layout="wide", page_icon="📊")
st.markdown(get_global_css(), unsafe_allow_html=True)
run_root = setup_sidebar("Analyse & Décision")

st.markdown("# 📊 Analyse & Décision")
st.caption("Décision qualité GO/NO_GO · Métriques pipeline · Comparaison V1/V2")

@st.cache_data(ttl=60)
def _load(rr: str):
    rp = Path(rr)
    ps = load_pilot_summary(rp)
    df = build_candidate_table(rp)
    fp = load_false_positive_risks(rp)
    return ps, df, fp

pilot_summary, df, fp_df = _load(str(run_root))
metrics  = compute_all_metrics(pilot_summary, df, fp_df)
decision = compute_decision(metrics)
reasons  = get_decision_reasons(metrics)

tab_dec, tab_bench, tab_base = st.tabs([
    "📊 Décision qualité",
    "⚖️ V1 vs V2",
    "📖 Baseline manuelle",
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — DÉCISION
# ══════════════════════════════════════════════════════════════
with tab_dec:
    hero_col, explain_col = st.columns([1, 2], gap="large")

    with hero_col:
        subtitle = GO_EXPLANATION.get(decision, "")[:80]
        st.markdown(decision_hero_html(decision, subtitle), unsafe_allow_html=True)

    with explain_col:
        st.markdown(section_header_html("Signification"), unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;'
            f'padding:1rem 1.25rem;font-size:0.9rem;color:#374151;line-height:1.6">'
            f'{GO_EXPLANATION.get(decision, "")}</div>',
            unsafe_allow_html=True,
        )

        st.markdown(section_header_html("Prochaines étapes"), unsafe_allow_html=True)
        for i, step in enumerate(NEXT_STEPS.get(decision, []), 1):
            color = "#16A34A" if decision == "GO" else ("#D97706" if decision == "GO_WITH_FIXES" else "#DC2626")
            st.markdown(
                f'<div style="display:flex;gap:0.75rem;align-items:flex-start;'
                f'margin-bottom:0.5rem;">'
                f'<div style="background:{color};color:white;border-radius:9999px;'
                f'width:22px;height:22px;display:flex;align-items:center;justify-content:center;'
                f'font-size:0.7rem;font-weight:700;flex-shrink:0;margin-top:1px">{i}</div>'
                f'<div style="font-size:0.875rem;color:#374151;padding-top:1px">{step}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Critères avec gauges ──────────────────────────────────
    st.markdown(section_header_html("Critères de décision — détail"), unsafe_allow_html=True)

    try:
        import plotly.graph_objects as go

        gauge_specs = [
            ("Taux de succès",       metrics.get("documents_success_rate", 0),  100,  100,  True,  "%"),
            ("Quotes présentes",     100 - metrics.get("missing_quote_rate", 0), 95,   100,  True,  "%"),
            ("Valeurs présentes",    100 - metrics.get("missing_value_rate", 0), 70,   100,  True,  "%"),
            ("Signal famille",       100 - metrics.get("unknown_boundary_rate", 0), 70, 100, True,  "%"),
            ("Charge de revue (inv)",100 - min(metrics.get("review_burden_hours", 0) / 100 * 100, 100), 60, 100, True, ""),
            ("Faux positifs (inv)",  100 - metrics.get("high_risk_rate", 0),     99,   100,  True,  "%"),
        ]

        gauge_cols = st.columns(3)
        for i, (name, value, warn_th, ok_th, higher_is_better, unit) in enumerate(gauge_specs):
            col = gauge_cols[i % 3]
            color = "#16A34A" if value >= ok_th else ("#D97706" if value >= warn_th else "#DC2626")
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=value,
                title={"text": name, "font": {"size": 12, "color": "#374151"}},
                number={"suffix": unit, "font": {"size": 18, "color": color}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#CBD5E1"},
                    "bar": {"color": color, "thickness": 0.7},
                    "bgcolor": "#F8FAFC",
                    "bordercolor": "#E2E8F0",
                    "steps": [
                        {"range": [0, warn_th],  "color": "#FEE2E2"},
                        {"range": [warn_th, ok_th], "color": "#FEF3C7"},
                        {"range": [ok_th, 100],  "color": "#DCFCE7"},
                    ],
                    "threshold": {
                        "line": {"color": "#374151", "width": 2},
                        "thickness": 0.8,
                        "value": ok_th,
                    },
                },
            ))
            fig.update_layout(
                height=180, margin=dict(t=30, b=10, l=20, r=20),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif"),
            )
            col.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    except ImportError:
        # Fallback : tableau simple
        st.dataframe(pd.DataFrame(reasons), use_container_width=True, hide_index=True)

    st.divider()

    # ── KPI table ───────────────────────────────────────────────
    st.markdown(section_header_html("Tableau des critères"), unsafe_allow_html=True)

    reason_df = pd.DataFrame(reasons)
    # Style: vert si ✅, rouge si ❌
    def _highlight(row):
        if row.get("Statut") == "✅":
            return ["background-color:#F0FDF4;color:#14532D"] * len(row)
        return ["background-color:#FFF7ED;color:#7C2D12"] * len(row)

    st.dataframe(
        reason_df.style.apply(_highlight, axis=1),
        use_container_width=True, hide_index=True, height=260,
    )

    st.divider()

    # ── Export ─────────────────────────────────────────────────
    st.markdown(section_header_html("Exporter"), unsafe_allow_html=True)
    export_dir = run_root / "_control_center_exports"
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("💾 Exporter rapport qualité (Markdown)"):
            try:
                p = export_quality_decision_report(decision, metrics, reasons, export_dir)
                st.success(f"Rapport exporté : `{p}`")
            except Exception as e:
                st.error(str(e))
    with col_b:
        lines = ["# Quality Decision Report", "", f"**Décision : {decision}**", "",
                 GO_EXPLANATION.get(decision, ""), "", "## Critères"]
        for r in reasons:
            lines.append(f"- {r.get('Statut','')} {r.get('Critère','')} : {r.get('Résultat','')}")
        lines += ["", "## KPIs"]
        for k, v in metrics.items():
            lines.append(f"- {k}: {v:.2f}" if isinstance(v, float) else f"- {k}: {v}")
        st.download_button(
            "⬇️ Télécharger rapport (Markdown)",
            "\n".join(lines).encode("utf-8"),
            "quality_decision_report.md", "text/markdown",
        )

# ══════════════════════════════════════════════════════════════
# TAB 2 — V1 vs V2
# ══════════════════════════════════════════════════════════════
with tab_bench:
    st.markdown(section_header_html("Métriques V1 — pilot 10 documents"), unsafe_allow_html=True)

    V1 = {
        "Documents traités": ("10 / 10", "10 / 10"),
        "Total candidats":   ("6 027",   "—"),
        "possible_indicator":("1 020 (16.9%)", "—"),
        "needs_review":      ("4 412 (73.2%)", "—"),
        "Valeurs manquantes":("52.3%", "< 15%"),
        "Bruit unknown/boundary":("62.2%", "< 10%"),
        "Charge de revue":   ("127.5h", "< 40h"),
        "Précision estimée": ("~50–55%", "> 75%"),
        "Rappel estimé":     ("~45–50%", "> 60%"),
        "Recall ESRS metric":("—", "95%"),
        "Recall ESRS valeur":("—", "85%"),
    }

    try:
        import plotly.graph_objects as go

        rows_v1 = list(V1.keys())
        vals_v1 = [v[0] for v in V1.values()]
        vals_v2 = [v[1] for v in V1.values()]

        fig_bench = go.Figure(data=[
            go.Table(
                header=dict(
                    values=["<b>KPI</b>", "<b>V1 (actuel)</b>", "<b>V2 (cible)</b>"],
                    fill_color="#0F172A",
                    font=dict(color="white", size=12),
                    align="left",
                    height=36,
                ),
                cells=dict(
                    values=[rows_v1, vals_v1, vals_v2],
                    fill_color=[
                        ["#F8FAFC"] * len(rows_v1),
                        ["#FEF3C7"] * len(rows_v1),
                        ["#DCFCE7"] * len(rows_v1),
                    ],
                    align="left",
                    font=dict(size=12, color="#374151"),
                    height=30,
                ),
            )
        ])
        fig_bench.update_layout(
            margin=dict(t=10, b=10, l=0, r=0),
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_bench, use_container_width=True, config={"displayModeBar": False})
    except ImportError:
        bench_df = pd.DataFrame(
            [(k, v[0], v[1]) for k, v in V1.items()],
            columns=["KPI", "V1 actuel", "V2 cible"],
        )
        st.dataframe(bench_df, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown(section_header_html("Erreurs V1 identifiées"), unsafe_allow_html=True)
    V1_ERRORS = pd.DataFrame([
        ("section_number_false_positive", "Numéros de section (2.1) comme valeurs", "🔴 Élevé"),
        ("iso_standard_false_positive",   "Normes ISO (50001, 14001) comme valeurs", "🔴 Élevé"),
        ("wrong_family_ghg",              "CO2 → famille unknown au lieu de ghg_emissions", "🔴 Élevé"),
        ("table_unit_not_propagated",     "Unité colonne non propagée aux cellules", "🟡 Moyen"),
        ("visual_infographic_missed",     "Tableaux infographiques non capturés", "🟡 Moyen"),
        ("year_as_value",                 "Années (2024) extraites comme valeur numérique", "🟢 Corrigé v3"),
        ("implausible_values",            "Valeurs hors bornes physiques", "🟢 Corrigé v3"),
    ], columns=["Type", "Description", "Impact"])
    st.dataframe(V1_ERRORS, use_container_width=True, hide_index=True)

    with st.expander("Distribution des familles V1", expanded=False):
        fam_df = load_candidate_counts_by_family(run_root)
        if not fam_df.empty:
            try:
                import plotly.express as px
                if "indicator_family" in fam_df.columns and "count" in fam_df.columns:
                    fig_fam = px.bar(
                        fam_df.sort_values("count", ascending=True).tail(15),
                        x="count", y="indicator_family",
                        orientation="h",
                        color_discrete_sequence=["#2563EB"],
                        labels={"count": "Candidats", "indicator_family": "Famille"},
                    )
                    fig_fam.update_layout(
                        height=350, margin=dict(t=10, b=10, l=10, r=10),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_fam, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.dataframe(fam_df, use_container_width=True, hide_index=True)
            except ImportError:
                st.dataframe(fam_df, use_container_width=True, hide_index=True)
        else:
            st.info("candidate_counts_by_family.csv introuvable.")

    with st.expander("Top candidats V1 (possible_indicator)", expanded=False):
        top = load_top_possible_indicators(run_root)
        if not top.empty:
            TOPCOLS = [c for c in ["document_id", "indicator_family", "label",
                                   "raw_value", "raw_unit", "page_number"] if c in top.columns]
            st.dataframe(top[TOPCOLS], use_container_width=True, hide_index=True, height=280)
        else:
            st.info("top_possible_indicators_all_docs.csv introuvable.")

# ══════════════════════════════════════════════════════════════
# TAB 3 — BASELINE MANUELLE
# ══════════════════════════════════════════════════════════════
with tab_base:
    st.caption("Indicateurs identifiés manuellement sur Schneider TCFD 2023 (36 pages).")

    MANUAL = [
        (3,  "SSI score",                        "governance",   "6.59/10",  "score",   "true_positive"),
        (3,  "CO2 savings cumulatif (client)",    "ghg_emissions","632",      "MtCO2e",  "true_positive"),
        (3,  "Revenue portfolio durable",         "boundary",     "74%",      "%",       "wrong_family"),
        (3,  "Accès à l'énergie (bénéficiaires)","workforce",    "49M",      "people",  "missed_indicator"),
        (9,  "CO2 avoided (produits)",            "ghg_emissions","108",      "MtCO2e",  "wrong_family"),
        (9,  "Électricité renouvelable (ops)",    "energy",       "53%",      "%",       "true_positive"),
        (9,  "Taux de fuite SF6",                 "ghg_emissions","0.3%",     "%",       "true_positive"),
        (9,  "Sites Zero-CO2",                    "ghg_emissions","68",       "sites",   "true_positive"),
        (10, "Scope 1+2 GHG absolu",              "ghg_emissions","457",      "ktCO2e",  "true_positive"),
        (10, "Réduction Scope 1+2 vs 2017",       "ghg_emissions","59%",      "%",       "true_positive"),
        (10, "Intensité Scope 3 upstream",         "ghg_emissions","24%",      "%",       "true_positive"),
        (11, "Objectif Net-Zero",                 "methodology",  "2040",     "year",    "wrong_family"),
        (12, "Investissements efficacité énergie","energy",       "90",       "M€",      "section_number_fp"),
        (14, "Couverture RE100",                  "energy",       "53%",      "%",       "true_positive"),
        (17, "Scope 3 cat 1 supply chain",        "ghg_emissions","4.7",      "MtCO2e",  "true_positive"),
        (17, "Réduction Scope 3 supply chain 2025","ghg_emissions","20%",     "%",       "true_positive"),
        (23, "CO2 évité downstream (produits)",   "ghg_emissions","632",      "MtCO2e",  "true_positive"),
    ]
    manual_df = pd.DataFrame(MANUAL, columns=["Page", "Indicateur", "Famille", "Valeur", "Unité", "Erreur V1"])

    n_tp     = (manual_df["Erreur V1"] == "true_positive").sum()
    n_missed = (manual_df["Erreur V1"] == "missed_indicator").sum()
    n_wf     = (manual_df["Erreur V1"] == "wrong_family").sum()
    n_fp     = (manual_df["Erreur V1"].str.contains("fp|false_positive")).sum()

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Vrais positifs V1",  n_tp,    f"{n_tp/len(manual_df)*100:.0f}%")
    b2.metric("Manqués V1",         n_missed)
    b3.metric("Mauvaise famille",   n_wf)
    b4.metric("Faux positifs",      n_fp)

    try:
        import plotly.express as px
        err_counts = manual_df["Erreur V1"].value_counts().reset_index()
        err_counts.columns = ["Type", "N"]
        color_map = {
            "true_positive":     "#16A34A",
            "missed_indicator":  "#DC2626",
            "wrong_family":      "#D97706",
            "section_number_fp": "#7C3AED",
        }
        fig_base = px.pie(
            err_counts, values="N", names="Type",
            color="Type", color_discrete_map=color_map,
            hole=0.5,
            title="Répartition qualité V1 (baseline Schneider TCFD)",
        )
        fig_base.update_layout(
            height=280, margin=dict(t=40, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        col_chart, col_table = st.columns([1, 2])
        col_chart.plotly_chart(fig_base, use_container_width=True, config={"displayModeBar": False})
        col_table.dataframe(manual_df, use_container_width=True, hide_index=True, height=280)
    except ImportError:
        st.dataframe(manual_df, use_container_width=True, hide_index=True, height=400)

    st.divider()
    ex1, ex2 = st.columns(2)
    with ex1:
        if st.button("💾 Exporter template vide"):
            try:
                p = export_manual_baseline_template(run_root / "_control_center_exports")
                st.success(f"Template exporté : `{p}`")
            except Exception as e:
                st.error(str(e))
    with ex2:
        st.download_button(
            "⬇️ Télécharger baseline Schneider TCFD",
            manual_df.to_csv(index=False).encode("utf-8"),
            "baseline_schneider_tcfd.csv", "text/csv",
        )

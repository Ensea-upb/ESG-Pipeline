"""
ESGProductionControlCenter — app.py v3.0
Executive Cockpit : décision GO/NO_GO + KPIs pipeline + navigation guidée.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import streamlit as st
    import pandas as pd
    _HAS_ST = True
except Exception:  # pragma: no cover
    st = None      # type: ignore[assignment]
    pd = None      # type: ignore[assignment]
    _HAS_ST = False

SAFETY_TEXT = (
    "Aucun indicateur ESG final validé / aucun score produit. "
    "Interface de pilotage lecture seule — v3.0. "
    "accepted_candidate != validated_indicator."
)


def render_app() -> None:
    if not _HAS_ST:
        raise RuntimeError("Streamlit est requis pour lancer l'interface graphique.")

    st.set_page_config(
        page_title="ESG Decision Center",
        layout="wide",
        page_icon="🎯",
        initial_sidebar_state="expanded",
    )

    from ESGProductionControlCenter.src.esg_production_control_center.ui_components import setup_sidebar
    from ESGProductionControlCenter.src.esg_production_control_center.styles import (
        get_global_css, decision_hero_html, badge_html, section_header_html,
        DECISION_COLORS,
    )

    st.markdown(get_global_css(), unsafe_allow_html=True)
    run_root = setup_sidebar()

    # ── Charge les données ──────────────────────────────────────
    metrics, decision, reasons, df_candidates = None, None, None, None
    data_ok = False
    try:
        from ESGProductionControlCenter.src.esg_production_control_center.data_loader import (
            load_pilot_summary, build_candidate_table, load_false_positive_risks,
        )
        from ESGProductionControlCenter.src.esg_production_control_center.metrics import compute_all_metrics
        from ESGProductionControlCenter.src.esg_production_control_center.decision_rules import (
            compute_decision, get_decision_reasons,
        )

        @st.cache_data(ttl=120)
        def _load(rr: str):
            rp = Path(rr)
            ps = load_pilot_summary(rp)
            df = build_candidate_table(rp)
            fp = load_false_positive_risks(rp)
            m  = compute_all_metrics(ps, df, fp)
            d  = compute_decision(m)
            r  = get_decision_reasons(m)
            return m, d, r, df

        metrics, decision, reasons, df_candidates = _load(str(run_root))
        data_ok = True
    except Exception:
        pass

    # ══════════════════════════════════════════════════════════
    # HERO — Décision + résumé
    # ══════════════════════════════════════════════════════════
    col_hero, col_nav = st.columns([3, 2], gap="large")

    with col_hero:
        st.markdown('<p style="font-size:0.75rem;font-weight:700;text-transform:uppercase;'
                    'letter-spacing:0.1em;color:#64748B;margin-bottom:0.25rem;">ESG Decision Center — v3.0</p>',
                    unsafe_allow_html=True)
        st.markdown("# Pilotage pipeline ESG")
        st.caption("Extraction · Qualité · Couverture ESRS · Décision GO/NO_GO")

        if data_ok and decision:
            subtitle_map = {
                "GO":           "Pipeline stable — prêt pour extension 20 documents.",
                "GO_WITH_FIXES":"Pipeline fonctionnel — corrections requises avant extension.",
                "NO_GO":        "Problèmes critiques — ne pas étendre avant résolution.",
            }
            st.markdown(
                decision_hero_html(decision, subtitle_map.get(decision, "")),
                unsafe_allow_html=True,
            )
        else:
            st.info("Sélectionnez un run dans la barre latérale pour afficher la décision.")

    with col_nav:
        st.markdown(section_header_html("Navigation rapide"), unsafe_allow_html=True)
        pages = [
            ("🚀", "Pipeline Cockpit",      "État de chaque document · Lancer la revue.",            "pages/02_Pipeline_Cockpit.py"),
            ("✍️", "Revue Humaine",          "Approuver / rejeter les candidats ESG extraits.",        "pages/03_Human_Review.py"),
            ("🗄️", "Base ESG Finale",        "Tableau wide des variables ESG validées.",               "pages/12_ESG_Database.py"),
            ("🎯", "ESG Coverage Board",    "Couverture ESRS — quels indicateurs sont trouvés ?",     "pages/01_ESG_Coverage_Board.py"),
            ("🔬", "Candidats & Revue",     "Explorer et filtrer les candidats extraits.",            "pages/10_Candidats_et_Revue.py"),
            ("📊", "Analyse & Décision",    "Critères GO/NO_GO et métriques de qualité détaillées.", "pages/11_Analyse_et_Decision.py"),
        ]
        for icon, title, desc, _page in pages:
            with st.container(border=True):
                c1, c2 = st.columns([1, 5])
                c1.markdown(f"<div style='font-size:1.8rem;text-align:center;padding-top:4px'>{icon}</div>",
                            unsafe_allow_html=True)
                c2.markdown(f"**{title}**")
                c2.caption(desc)

    st.divider()

    # ══════════════════════════════════════════════════════════
    # KPI BAR — 6 indicateurs clés
    # ══════════════════════════════════════════════════════════
    st.markdown(section_header_html("Indicateurs clés du run"), unsafe_allow_html=True)

    if data_ok and metrics:
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("Documents traités",
                  f"{metrics.get('documents_success', 0)}/{metrics.get('documents_selected', 0)}",
                  help="Workspaces produits avec succès")
        k2.metric("Total candidats",
                  f"{metrics.get('candidate_count_total', 0):,}",
                  help="Toutes sources confondues")
        k3.metric("Candidats utiles",
                  f"{metrics.get('possible_indicator_count', 0):,}",
                  help="Statut possible_indicator")
        k4.metric("Valeurs manquantes",
                  f"{metrics.get('missing_value_rate', 0):.0f}%",
                  delta=f"{metrics.get('missing_value_rate', 0) - 30:.0f}pp vs seuil",
                  delta_color="inverse",
                  help="Objectif < 30%")
        k5.metric("Bruit (unknown/boundary)",
                  f"{metrics.get('unknown_boundary_rate', 0):.0f}%",
                  delta=f"{metrics.get('unknown_boundary_rate', 0) - 30:.0f}pp vs seuil",
                  delta_color="inverse",
                  help="Objectif < 30%")
        k6.metric("Charge revue",
                  f"{metrics.get('review_burden_hours', 0):.0f}h",
                  delta=f"{metrics.get('review_burden_hours', 0) - 40:.0f}h vs seuil",
                  delta_color="inverse",
                  help="Objectif < 40h")
    else:
        st.info("Chargez un run pour voir les KPIs.")

    st.divider()

    # ══════════════════════════════════════════════════════════
    # CRITÈRES DE DÉCISION — tableau compact
    # ══════════════════════════════════════════════════════════
    if data_ok and reasons:
        col_crit, col_dist = st.columns([3, 2], gap="large")

        with col_crit:
            st.markdown(section_header_html("Critères de décision"), unsafe_allow_html=True)
            for r in reasons:
                ok = r.get("Statut") == "✅"
                bg = "#F0FDF4" if ok else "#FFF7ED"
                border = "#86EFAC" if ok else "#FCD34D"
                icon = "✅" if ok else "❌"
                st.markdown(
                    f"""<div style="background:{bg};border:1px solid {border};border-radius:8px;
                    padding:0.6rem 1rem;margin-bottom:6px;display:flex;justify-content:space-between;
                    align-items:center;">
                    <span style="font-weight:600;font-size:0.85rem;color:#1E293B">{r.get('Critère','')}</span>
                    <span style="font-size:0.85rem;color:#475569">{r.get('Résultat','')} {icon}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )

        with col_dist:
            st.markdown(section_header_html("Distribution des candidats"), unsafe_allow_html=True)
            if df_candidates is not None and not df_candidates.empty and "validation_status" in df_candidates.columns:
                try:
                    import plotly.express as px
                    counts = df_candidates["validation_status"].value_counts().reset_index()
                    counts.columns = ["Statut", "N"]
                    label_map = {
                        "possible_indicator": "Utiles",
                        "needs_review":       "À vérifier",
                        "reject_candidate":   "Bruit",
                    }
                    color_map = {
                        "Utiles":      "#16A34A",
                        "À vérifier":  "#D97706",
                        "Bruit":       "#DC2626",
                    }
                    counts["Statut"] = counts["Statut"].map(label_map).fillna(counts["Statut"])
                    fig = px.pie(
                        counts, values="N", names="Statut",
                        color="Statut", color_discrete_map=color_map,
                        hole=0.55,
                    )
                    fig.update_layout(
                        margin=dict(t=10, b=10, l=10, r=10),
                        height=230,
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, x=0.1),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter, sans-serif", size=12),
                    )
                    fig.update_traces(textinfo="percent+value", textfont_size=11)
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                except ImportError:
                    vc = df_candidates["validation_status"].value_counts()
                    for s, n in vc.items():
                        st.metric(s, n)
            else:
                st.info("Données candidates non disponibles.")

    st.divider()

    # ── Footer ──────────────────────────────────────────────────
    st.markdown(
        f'<div style="text-align:center;color:#94A3B8;font-size:0.75rem;padding:1rem 0">'
        f'🔒 {SAFETY_TEXT}'
        f'</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    render_app()

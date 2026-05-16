"""
ui_components.py — Reusable Streamlit UI helpers for ESGProductionControlCenter v2.0.
Conditional Streamlit import so this module can be imported in non-Streamlit tests.
"""
from __future__ import annotations

from pathlib import Path

try:
    import streamlit as st
    _HAS_ST = True
except Exception:
    st = None  # type: ignore[assignment]
    _HAS_ST = False

DECISION_ICON = {"GO": "🟢", "GO_WITH_FIXES": "🟡", "NO_GO": "🔴"}

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN_ROOT = "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2"

# Thresholds for KPI coloring
_THRESHOLDS = {
    "documents_success_rate":   {"good": 100.0, "bad": 80.0,  "higher_is_better": True},
    "possible_indicator_rate":  {"good": 20.0,  "bad": 5.0,   "higher_is_better": True},
    "missing_value_rate":       {"good": 20.0,  "bad": 40.0,  "higher_is_better": False},
    "missing_unit_rate":        {"good": 30.0,  "bad": 60.0,  "higher_is_better": False},
    "missing_quote_rate":       {"good": 5.0,   "bad": 30.0,  "higher_is_better": False},
    "unknown_boundary_rate":    {"good": 20.0,  "bad": 50.0,  "higher_is_better": False},
    "high_risk_rate":           {"good": 0.5,   "bad": 5.0,   "higher_is_better": False},
    "review_burden_hours":      {"good": 40.0,  "bad": 120.0, "higher_is_better": False},
}

_KPI_INTERPRETATIONS = {
    "documents_success_rate": {
        "good":    "Excellent — tous les documents traités avec succès.",
        "warning": "Attention — certains documents ont échoué.",
        "bad":     "Problème — plus de 20 % de documents en échec.",
    },
    "missing_value_rate": {
        "good":    "Bon — la plupart des candidats ont une valeur numérique.",
        "warning": "À surveiller — beaucoup de candidats sans valeur.",
        "bad":     "Problème — plus de 40 % des candidats n'ont pas de valeur. Bruit important.",
    },
    "unknown_boundary_rate": {
        "good":    "Bon — peu de candidats dans les familles bruyantes.",
        "warning": "Élevé — les familles unknown/boundary génèrent du bruit.",
        "bad":     "Critique — plus de 50 % des candidats sont du bruit familial.",
    },
    "review_burden_hours": {
        "good":    "Gérable — une revue humaine complète est faisable.",
        "warning": "Charge élevée — prioriser les possible_indicator.",
        "bad":     "Excessive — impossible à réviser manuellement sans filtrage automatique.",
    },
    "missing_quote_rate": {
        "good":    "Excellent — presque tous les candidats ont une citation source.",
        "warning": "À surveiller — citations manquantes pour certains candidats.",
        "bad":     "Problème — sans citation, les candidats ne peuvent pas être vérifiés.",
    },
    "high_risk_rate": {
        "good":    "Excellent — très peu de faux positifs à haut risque.",
        "warning": "Acceptable — quelques faux positifs à inspecter.",
        "bad":     "Problème — trop de candidats clairement erronés.",
    },
    "possible_indicator_rate": {
        "good":    "Bon — proportion saine de candidats probablement utiles.",
        "warning": "Faible — peu de candidats atteignent le statut 'probable'.",
        "bad":     "Très faible — le pipeline peine à identifier des indicateurs fiables.",
    },
}


def _kpi_level(metric_name: str, value: float) -> str:
    """Return 'good', 'warning', or 'bad' based on thresholds."""
    t = _THRESHOLDS.get(metric_name)
    if t is None:
        return "neutral"
    if t["higher_is_better"]:
        if value >= t["good"]:
            return "good"
        if value <= t["bad"]:
            return "bad"
        return "warning"
    else:
        if value <= t["good"]:
            return "good"
        if value >= t["bad"]:
            return "bad"
        return "warning"


def _level_color(level: str) -> str:
    return {"good": "#28a745", "warning": "#e6a817", "bad": "#dc3545", "neutral": "#6c757d"}.get(level, "#6c757d")


def _level_icon(level: str) -> str:
    return {"good": "✅", "warning": "⚠️", "bad": "❌", "neutral": "ℹ️"}.get(level, "ℹ️")


def metric_with_status(label: str, value: str, metric_name: str, raw_value: float) -> None:
    """Display a st.metric with a colored interpretation line below it."""
    if not _HAS_ST:
        return
    level = _kpi_level(metric_name, raw_value)
    color = _level_color(level)
    icon = _level_icon(level)
    interp = _KPI_INTERPRETATIONS.get(metric_name, {}).get(level, "")
    st.metric(label, value)
    if interp:
        st.markdown(
            f"<p style='color:{color};font-size:0.78em;margin-top:-12px;margin-bottom:4px;'>"
            f"{icon} {interp}</p>",
            unsafe_allow_html=True,
        )


def decision_badge(decision: str) -> str:
    icon = DECISION_ICON.get(decision, "⚪")
    return f"{icon} **{decision}**"


def status_icon(status: str) -> str:
    return {"success": "✅", "failed": "❌", "warning": "⚠️", "pending": "⏳"}.get(status, "⚪")


def human_label(technical: str) -> str:
    mapping = {
        "possible_indicator": "Probablement utile",
        "needs_review": "À vérifier",
        "reject_candidate": "Probablement bruit",
        "manual_review_workspace.csv": "Table de revue humaine",
        "unknown": "Famille inconnue",
        "boundary": "Limite système",
        "ghg_emissions": "Émissions GHG",
        "energy": "Énergie",
        "water": "Eau",
        "workforce": "Effectifs",
        "governance": "Gouvernance",
        "policy": "Politique",
        "risk": "Risque",
        "methodology": "Méthodologie",
    }
    return mapping.get(technical, technical)


def setup_sidebar(page_title: str = "ESG Decision Center v3.0") -> "Path":
    """Display common sidebar with auto-discovered run selector. Returns run_root Path."""
    if not _HAS_ST:
        return _PROJECT_ROOT / DEFAULT_RUN_ROOT

    from ESGProductionControlCenter.src.esg_production_control_center.run_registry import discover_runs
    from ESGProductionControlCenter.src.esg_production_control_center.data_loader import find_review_workspaces

    st.sidebar.markdown("## 🎯 ESG Decision Center")
    st.sidebar.caption("v3.0 — lecture seule")
    st.sidebar.divider()

    # Auto-discover runs
    available_runs = discover_runs(_PROJECT_ROOT)
    current = st.session_state.get("run_root", DEFAULT_RUN_ROOT)

    if available_runs:
        # Ensure current value is in the list
        options = available_runs if current in available_runs else [current] + available_runs
        idx = options.index(current) if current in options else 0
        selected = st.sidebar.selectbox(
            "📁 Choisir un run pilot",
            options,
            index=idx,
            help="Les runs disponibles sont détectés automatiquement dans EXTERNAL_AUDIT_RUNS/",
        )
        st.session_state["run_root"] = selected
        run_root = _PROJECT_ROOT / selected
    else:
        # Fallback: manual text input
        selected = st.sidebar.text_input(
            "📁 Chemin du run (relatif)",
            value=current,
            help="Chemin relatif depuis la racine ESG vers le dossier pilot_run_summary.json",
        )
        st.session_state["run_root"] = selected
        run_root = _PROJECT_ROOT / selected

    # Status feedback
    if run_root.exists():
        n_ws = len(find_review_workspaces(run_root))
        st.sidebar.success(f"✅ {n_ws} workspace(s) chargé(s)")
        pilot_json = run_root / "pilot_run_summary.json"
        if pilot_json.exists():
            st.sidebar.caption(f"Run : `{run_root.name}`")
    else:
        st.sidebar.error("❌ Dossier de run introuvable")
        st.sidebar.caption(f"Chemin : `{run_root}`")

    st.sidebar.divider()
    st.sidebar.caption("🔒 Lecture seule — aucun fichier source modifié.")
    return run_root


def section_header(title: str, subtitle: str = "") -> None:
    """Render a consistent section header."""
    if not _HAS_ST:
        return
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def info_card(title: str, body: str, icon: str = "ℹ️") -> None:
    """Render a bordered info card."""
    if not _HAS_ST:
        return
    with st.container(border=True):
        st.markdown(f"**{icon} {title}**")
        st.markdown(body)


def format_rate(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f} %"


def format_hours(hours: float) -> str:
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m:02d}min"


def show_missing_files_warning(missing: list[str]) -> None:
    if not _HAS_ST or not missing:
        return
    with st.expander(f"⚠️ {len(missing)} fichier(s) optionnel(s) absent(s)", expanded=False):
        st.caption("Ces fichiers sont générés par l'audit qualité. Lancez l'audit pour les produire.")
        for f in missing:
            st.caption(f"• {f}")

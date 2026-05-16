"""
styles.py — ESG Control Center design system v3.0
Inject with: st.markdown(get_global_css(), unsafe_allow_html=True)
"""
from __future__ import annotations


# ── Palette ───────────────────────────────────────────────────
GREEN   = "#16A34A"
BLUE    = "#2563EB"
AMBER   = "#D97706"
RED     = "#DC2626"
SLATE   = "#0F172A"
MUTED   = "#64748B"
SURFACE = "#FFFFFF"
BG      = "#F1F5F9"

DECISION_COLORS = {
    "GO":           {"bg": "#DCFCE7", "border": "#16A34A", "text": "#14532D", "badge_bg": "#16A34A"},
    "GO_WITH_FIXES":{"bg": "#FEF3C7", "border": "#D97706", "text": "#78350F", "badge_bg": "#D97706"},
    "NO_GO":        {"bg": "#FEE2E2", "border": "#DC2626", "text": "#7F1D1D", "badge_bg": "#DC2626"},
}


def get_global_css() -> str:
    return """
<style>
/* ── Reset & base ────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
}

/* Main container */
.main .block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 1400px;
}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0F172A !important;
}
[data-testid="stSidebar"] * {
    color: #E2E8F0 !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label {
    color: #94A3B8 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stSidebar"] hr {
    border-color: #1E293B !important;
}

/* ── Metric cards ─────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1rem 1.25rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
}
[data-testid="stMetric"]:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.10);
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #64748B !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: #0F172A !important;
}

/* ── Containers / cards ───────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

/* ── Tabs ─────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #F8FAFC;
    border-radius: 8px;
    padding: 4px;
    gap: 4px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 6px;
    font-weight: 500;
    color: #64748B !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: #FFFFFF !important;
    color: #0F172A !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* ── Buttons ──────────────────────────────────────────────── */
[data-testid="stButton"] > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    border: 1px solid #E2E8F0 !important;
    transition: all 0.15s !important;
}
[data-testid="stButton"] > button:hover {
    border-color: #2563EB !important;
    color: #2563EB !important;
    background: #EFF6FF !important;
}

/* ── Dataframe ────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 8px !important;
    overflow: hidden;
    border: 1px solid #E2E8F0 !important;
}

/* ── Alerts ───────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    border-left-width: 4px !important;
}

/* ── Custom badges (injected via markdown) ────────────────── */
.esg-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.esg-badge-green  { background: #DCFCE7; color: #14532D; border: 1px solid #86EFAC; }
.esg-badge-amber  { background: #FEF3C7; color: #78350F; border: 1px solid #FCD34D; }
.esg-badge-red    { background: #FEE2E2; color: #7F1D1D; border: 1px solid #FCA5A5; }
.esg-badge-blue   { background: #DBEAFE; color: #1E3A8A; border: 1px solid #93C5FD; }
.esg-badge-gray   { background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; }

/* ── KPI Hero cards ───────────────────────────────────────── */
.kpi-hero {
    background: linear-gradient(135deg, #1E3A5F 0%, #0F172A 100%);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    color: white;
    margin-bottom: 1rem;
}
.kpi-hero h1 { color: white !important; margin: 0; font-size: 2.5rem; font-weight: 800; }
.kpi-hero p  { color: #94A3B8; margin: 0.25rem 0 0; font-size: 0.95rem; }

/* ── Decision hero ────────────────────────────────────────── */
.decision-go {
    background: linear-gradient(135deg, #14532D, #16A34A);
    border-radius: 16px; padding: 2rem; color: white; text-align: center;
}
.decision-go_with_fixes {
    background: linear-gradient(135deg, #78350F, #D97706);
    border-radius: 16px; padding: 2rem; color: white; text-align: center;
}
.decision-no_go {
    background: linear-gradient(135deg, #7F1D1D, #DC2626);
    border-radius: 16px; padding: 2rem; color: white; text-align: center;
}
.decision-hero-label { font-size: 0.85rem; font-weight: 600; text-transform: uppercase;
                        letter-spacing: 0.1em; opacity: 0.8; margin-bottom: 0.5rem; }
.decision-hero-value { font-size: 3.5rem; font-weight: 900; letter-spacing: -0.02em;
                        margin: 0; line-height: 1; }
.decision-hero-sub   { font-size: 0.9rem; opacity: 0.75; margin-top: 0.75rem; }

/* ── Section headers ──────────────────────────────────────── */
.section-header {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #64748B;
    margin: 1.5rem 0 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #E2E8F0;
}

/* ── Coverage grid (ESG metrics) ──────────────────────────── */
.coverage-cell {
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
    margin: 3px;
    font-size: 0.75rem;
    font-weight: 600;
    text-align: center;
    border: 1px solid transparent;
}
.coverage-found-val { background: #DCFCE7; color: #14532D; border-color: #86EFAC; }
.coverage-found-no  { background: #FEF3C7; color: #78350F; border-color: #FCD34D; }
.coverage-missed    { background: #FEE2E2; color: #7F1D1D; border-color: #FCA5A5; }

/* Hide default Streamlit footer */
footer { display: none !important; }
#MainMenu { display: none !important; }
</style>
"""


def decision_hero_html(decision: str, subtitle: str = "") -> str:
    css_class = f"decision-{decision.lower()}"
    icon = {"GO": "✅", "GO_WITH_FIXES": "⚠️", "NO_GO": "🚫"}.get(decision, "")
    return f"""
<div class="{css_class}">
  <div class="decision-hero-label">Décision pipeline</div>
  <div class="decision-hero-value">{icon} {decision.replace("_", " ")}</div>
  {"<div class='decision-hero-sub'>" + subtitle + "</div>" if subtitle else ""}
</div>
"""


def badge_html(text: str, color: str = "gray") -> str:
    return f'<span class="esg-badge esg-badge-{color}">{text}</span>'


def section_header_html(text: str) -> str:
    return f'<div class="section-header">{text}</div>'

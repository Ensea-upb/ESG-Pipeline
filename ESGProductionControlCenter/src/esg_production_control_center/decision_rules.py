"""
decision_rules.py — GO / GO_WITH_FIXES / NO_GO logic for ESGProductionControlCenter v2.0.
No Streamlit dependency.
"""
from __future__ import annotations


def compute_decision(metrics: dict) -> str:
    """Return GO, GO_WITH_FIXES, or NO_GO based on pipeline KPIs."""
    success_rate = metrics.get("documents_success_rate", 0.0)
    docs_selected = metrics.get("documents_selected", 0)

    # Hard NO_GO
    if docs_selected > 0 and success_rate < 50.0:
        return "NO_GO"
    if metrics.get("missing_quote_rate", 0.0) > 50.0:
        return "NO_GO"
    if metrics.get("documents_success", 0) == 0 and docs_selected > 0:
        return "NO_GO"

    # Full GO — all thresholds met
    workspace_ok = success_rate >= 100.0
    quote_ok = metrics.get("missing_quote_rate", 100.0) < 5.0
    burden_ok = metrics.get("review_burden_hours", 9999.0) < 40.0
    noise_ok = metrics.get("unknown_boundary_rate", 100.0) < 30.0
    value_ok = metrics.get("missing_value_rate", 100.0) < 30.0

    if workspace_ok and quote_ok and burden_ok and noise_ok and value_ok:
        return "GO"

    return "GO_WITH_FIXES"


def get_decision_reasons(metrics: dict) -> list[dict]:
    """Return per-criterion evaluation for the Decision Board table."""
    success_rate = metrics.get("documents_success_rate", 0.0)
    docs_s = metrics.get("documents_success", 0)
    docs_sel = metrics.get("documents_selected", 0)
    missing_q = metrics.get("missing_quote_rate", 0.0)
    missing_v = metrics.get("missing_value_rate", 0.0)
    noise = metrics.get("unknown_boundary_rate", 0.0)
    burden = metrics.get("review_burden_hours", 0.0)
    high_risk = metrics.get("high_risk_rate", 0.0)

    def _ok(condition: bool) -> str:
        return "✅" if condition else "❌"

    return [
        {
            "Critère": "Workspaces produits (100 %)",
            "Résultat": f"{docs_s}/{docs_sel} ({success_rate:.0f} %)",
            "Statut": _ok(success_rate >= 100.0),
        },
        {
            "Critère": "Quotes présentes (< 5 % manquantes)",
            "Résultat": f"{missing_q:.1f} % manquantes",
            "Statut": _ok(missing_q < 5.0),
        },
        {
            "Critère": "Valeurs présentes (< 30 % manquantes)",
            "Résultat": f"{missing_v:.1f} % manquantes",
            "Statut": _ok(missing_v < 30.0),
        },
        {
            "Critère": "Bruit familial < 30 % (unknown/boundary)",
            "Résultat": f"{noise:.1f} %",
            "Statut": _ok(noise < 30.0),
        },
        {
            "Critère": "Charge de revue < 40 h",
            "Résultat": f"{burden:.1f} h",
            "Statut": _ok(burden < 40.0),
        },
        {
            "Critère": "Faux positifs haut risque < 1 %",
            "Résultat": f"{high_risk:.2f} %",
            "Statut": _ok(high_risk < 1.0),
        },
    ]


GO_EXPLANATION = {
    "GO": (
        "Le pipeline est stable, les workspaces sont complets, "
        "la charge de revue est gérable et la qualité extracteurs est suffisante."
    ),
    "GO_WITH_FIXES": (
        "Le pipeline fonctionne et les workspaces sont exploitables, "
        "mais la qualité des extracteurs doit être améliorée avant extension : "
        "trop de candidats unknown/boundary, trop de valeurs manquantes, "
        "charge de revue excessive."
    ),
    "NO_GO": (
        "Des problèmes critiques empêchent d'avancer : "
        "workspaces manquants, quotes absentes, ou pipeline non fonctionnel."
    ),
}

NEXT_STEPS = {
    "GO": [
        "Lancer le pilot 20 documents.",
        "Démarrer la revue humaine sur les possible_indicator.",
    ],
    "GO_WITH_FIXES": [
        "Réduire le bruit unknown/boundary (target < 30 %).",
        "Corriger les valeurs manquantes pour les familles quantitatives (GHG, energy, water).",
        "Implémenter un filtre automatique pour needs_review sans valeur ni unité.",
        "Valider manuellement 20-30 possible_indicator des familles clés.",
        "Relancer l'audit qualité après corrections → si GO, lancer 20 docs.",
    ],
    "NO_GO": [
        "Diagnostiquer les workspaces manquants.",
        "Corriger les erreurs pipeline avant toute extension.",
    ],
}

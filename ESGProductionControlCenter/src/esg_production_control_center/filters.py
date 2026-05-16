"""
filters.py — DataFrame filtering utilities for ESGProductionControlCenter v2.0.
No Streamlit dependency.
"""
from __future__ import annotations

import pandas as pd

HUMAN_LABELS = {
    "possible_indicator": "Probablement utile",
    "needs_review": "À vérifier",
    "reject_candidate": "Probablement bruit",
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

NOISY_FAMILIES = {"unknown", "boundary"}
PRIORITY_FAMILIES = {"ghg_emissions", "energy", "water", "workforce", "governance"}


def filter_by_status(df: pd.DataFrame, status: str) -> pd.DataFrame:
    if not status or "validation_status" not in df.columns:
        return df
    return df[df["validation_status"] == status]


def filter_by_family(df: pd.DataFrame, family: str) -> pd.DataFrame:
    if not family or "indicator_family" not in df.columns:
        return df
    return df[df["indicator_family"] == family]


def filter_by_company(df: pd.DataFrame, company: str) -> pd.DataFrame:
    if not company or "_company_slug" not in df.columns:
        return df
    return df[df["_company_slug"] == company]


def filter_by_engine(df: pd.DataFrame, engine: str) -> pd.DataFrame:
    if not engine or "source_engine" not in df.columns:
        return df
    return df[df["source_engine"] == engine]


def filter_has_value(df: pd.DataFrame) -> pd.DataFrame:
    if "raw_value" not in df.columns:
        return df
    return df[df["raw_value"].str.strip() != ""]


def filter_has_quote(df: pd.DataFrame) -> pd.DataFrame:
    if "quote" not in df.columns:
        return df
    return df[df["quote"].str.len() >= 10]


def filter_text_in_quote(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query or "quote" not in df.columns:
        return df
    return df[df["quote"].str.contains(query, case=False, na=False)]


def filter_text_in_label(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query or "label" not in df.columns:
        return df
    return df[df["label"].str.contains(query, case=False, na=False)]


def filter_by_risk_level(df: pd.DataFrame, risk_level: str) -> pd.DataFrame:
    if not risk_level or "risk_level" not in df.columns:
        return df
    return df[df["risk_level"] == risk_level]


def apply_all_filters(
    df: pd.DataFrame,
    status: str = "",
    family: str = "",
    company: str = "",
    engine: str = "",
    fiscal_year: str = "",
    doc_type: str = "",
    has_value: bool = False,
    has_quote: bool = False,
    quote_query: str = "",
    label_query: str = "",
) -> pd.DataFrame:
    if status:
        df = filter_by_status(df, status)
    if family:
        df = filter_by_family(df, family)
    if company:
        df = filter_by_company(df, company)
    if engine:
        df = filter_by_engine(df, engine)
    if fiscal_year and "_fiscal_year" in df.columns:
        df = df[df["_fiscal_year"] == fiscal_year]
    if doc_type and "_official_doc_type" in df.columns:
        df = df[df["_official_doc_type"] == doc_type]
    if has_value:
        df = filter_has_value(df)
    if has_quote:
        df = filter_has_quote(df)
    if quote_query:
        df = filter_text_in_quote(df, quote_query)
    if label_query:
        df = filter_text_in_label(df, label_query)
    return df


def get_priority_queue(df: pd.DataFrame) -> pd.DataFrame:
    """Return high-priority candidates for human review."""
    if df.empty:
        return df
    mask = pd.Series(True, index=df.index)
    if "validation_status" in df.columns:
        mask &= df["validation_status"] == "possible_indicator"
    if "indicator_family" in df.columns:
        mask &= ~df["indicator_family"].isin(NOISY_FAMILIES)
    if "raw_value" in df.columns:
        mask &= df["raw_value"].str.strip() != ""
    if "quote" in df.columns:
        mask &= df["quote"].str.len() >= 10
    return df[mask].reset_index(drop=True)


def add_human_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add human-readable columns alongside technical ones."""
    out = df.copy()
    if "validation_status" in out.columns:
        out["Statut"] = out["validation_status"].map(lambda x: HUMAN_LABELS.get(x, x))
    if "indicator_family" in out.columns:
        out["Famille"] = out["indicator_family"].map(lambda x: HUMAN_LABELS.get(x, x))
    return out


def get_unique_values(df: pd.DataFrame, col: str) -> list[str]:
    if col not in df.columns:
        return []
    return sorted(df[col].dropna().astype(str).unique().tolist())

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .csv_viewer import filter_dataframe, load_csv

BUSINESS_COLUMNS = {
    "company": "Entreprise",
    "fiscal_year": "Année",
    "information_type": "Type d’information",
    "esg_category": "Thème ESG",
    "label": "Information détectée",
    "raw_value": "Valeur",
    "raw_unit": "Unité",
    "year": "Année de reporting",
    "normalized_year": "Année de reporting",
    "page_number": "Page",
    "quote": "Extrait justificatif",
    "validation_status": "Statut",
    "review_priority": "Priorité de revue",
    "source_engine": "Source",
}

TECHNICAL_COLUMNS = ["candidate_id", "evidence_id", "table_id", "cell_id", "figure_id", "module_name", "output_dir", "section_id"]


def load_first_available_csv(root: str | Path, names: list[str]) -> tuple[Path | None, pd.DataFrame]:
    base = Path(root)
    for name in names:
        matches = list(base.rglob(name)) if base.exists() else []
        if matches:
            return matches[0], load_csv(matches[0], max_rows=10000)
    return None, pd.DataFrame()


def to_business_results(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=list(BUSINESS_COLUMNS.values()))
    out = pd.DataFrame()
    for raw, label in BUSINESS_COLUMNS.items():
        if raw in df.columns and label not in out.columns:
            out[label] = df[raw]
    return out


def filter_business_results(df: pd.DataFrame, **filters: Any) -> pd.DataFrame:
    reverse = {v: k for k, v in BUSINESS_COLUMNS.items()}
    technical_filters = {reverse.get(k, k): v for k, v in filters.items()}
    return to_business_results(filter_dataframe(df, **technical_filters))

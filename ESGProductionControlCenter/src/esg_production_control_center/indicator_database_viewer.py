from __future__ import annotations

from pathlib import Path
import pandas as pd


def load_indicator_database(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(p)


def database_status_message(df: pd.DataFrame) -> str:
    if df.empty:
        return "indicator_preparation_database.csv is empty; status remains preparation_only."
    if "indicator_database_status" in df.columns:
        return "indicator_database_status=preparation_only"
    return "indicator_database_status column not found"

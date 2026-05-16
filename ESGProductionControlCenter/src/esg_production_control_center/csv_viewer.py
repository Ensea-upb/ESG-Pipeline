from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError, ParserError


def load_csv(path: str | Path, max_rows: int = 1000) -> pd.DataFrame:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(p).head(max_rows)
    except (EmptyDataError, ParserError, UnicodeDecodeError):
        return pd.DataFrame()


def filter_dataframe(df: pd.DataFrame, **filters: Any) -> pd.DataFrame:
    out = df.copy()
    for key, value in filters.items():
        if value in (None, "") or key == "quote_search":
            continue
        if key in out.columns:
            out = out[out[key].astype(str) == str(value)]
    quote_search = filters.get("quote_search")
    if quote_search and "quote" in out.columns:
        out = out[out["quote"].astype(str).str.contains(str(quote_search), case=False, na=False)]
    return out


def write_viewer_state(output_dir: str | Path, state: dict[str, Any]) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = [out / "csv_viewer_state.json", out / "csv_viewer_summary.json"]
    files[0].write_text(json.dumps(state, indent=2), encoding="utf-8")
    files[1].write_text(json.dumps({"rows_loaded": state.get("rows_loaded", 0), "preparation_only_visible": True}, indent=2), encoding="utf-8")
    return [str(p) for p in files]

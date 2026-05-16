from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd


def parse_csv_env(name: str) -> Optional[set[str]]:
    value = os.getenv(name)
    if not value:
        return None
    items = {item.strip() for item in value.split(",") if item.strip()}
    return items or None


def get_scope_from_env() -> tuple[Optional[set[str]], Optional[set[int]]]:
    if os.getenv("ESG_POSTPROCESS_SCOPE", "global").lower() == "global":
        return None, None

    company_slugs = parse_csv_env("ESG_POSTPROCESS_COMPANY_SLUGS")
    year_values = parse_csv_env("ESG_POSTPROCESS_YEARS")
    years = {int(year) for year in year_values} if year_values else None
    return company_slugs, years


def get_output_root_from_env(project_root: Path) -> Path:
    value = os.getenv("ESG_POSTPROCESS_OUTPUT_ROOT")
    if value:
        return Path(value).resolve()
    return (project_root / "data").resolve()


def get_input_root_from_env() -> Optional[Path]:
    value = os.getenv("ESG_POSTPROCESS_INPUT_ROOT")
    if value:
        return Path(value).resolve()
    return None


def get_output_dir_from_env(project_root: Path, subdir: str) -> Path:
    return get_output_root_from_env(project_root) / subdir


def get_corpus_root_from_env(env_name: str, default_root: Path) -> Path:
    value = os.getenv(env_name)
    if value:
        return Path(value).resolve()
    return default_root.resolve()


def row_in_scope(
    company_slug,
    fiscal_year,
    company_slugs: Optional[set[str]] = None,
    years: Optional[set[int]] = None,
) -> bool:
    if company_slugs is not None:
        if str(company_slug) not in company_slugs:
            return False

    if years is not None:
        try:
            parsed_year = int(float(fiscal_year))
        except (TypeError, ValueError):
            return False
        if parsed_year not in years:
            return False

    return True


def filter_dataframe_scope(
    df: pd.DataFrame,
    company_slugs: Optional[set[str]] = None,
    years: Optional[set[int]] = None,
) -> pd.DataFrame:
    if company_slugs is None and years is None:
        return df

    mask = pd.Series([True] * len(df), index=df.index)
    if company_slugs is not None and "company_slug" in df.columns:
        mask &= df["company_slug"].astype(str).isin(company_slugs)
    if years is not None and "fiscal_year" in df.columns:
        parsed_years = pd.to_numeric(df["fiscal_year"], errors="coerce")
        mask &= parsed_years.isin(years)
    return df[mask].copy()

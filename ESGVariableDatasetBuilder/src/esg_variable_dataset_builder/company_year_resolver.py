from __future__ import annotations

from typing import Any


def resolve_company_year(row: dict[str, Any], fallback_company: str = "", fallback_year: str = "") -> tuple[str, str]:
    company = str(row.get("company") or row.get("company_name") or fallback_company).strip()
    year = str(row.get("fiscal_year") or row.get("year_prepared") or row.get("year") or fallback_year).strip()
    return company, year

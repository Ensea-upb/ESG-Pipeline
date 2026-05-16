from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import PRIORITY_INPUT_FILES
from .io_utils import read_csv, read_json, write_csv, write_json, write_jsonl


def _company_year_from_dir(output_dir: Path) -> tuple[str, str]:
    rows = read_csv(output_dir / "indicator_preparation_database.csv")
    for row in rows:
        company = row.get("company", "").strip()
        year = row.get("fiscal_year", "").strip() or row.get("year", "").strip()
        if company and year:
            return company, year
    summary = read_json(output_dir / "indicator_database_summary.json")
    company = str(summary.get("company") or summary.get("company_name") or "").strip()
    year = str(summary.get("fiscal_year") or summary.get("year") or "").strip()
    if company and year:
        return company, year
    name = output_dir.name.lower()
    guessed_company = "LVMH" if "lvmh" in name else output_dir.name
    guessed_year = "2024" if "2024" in name or "lvmh" in name else ""
    return guessed_company, guessed_year


def discover_inputs(input_root: Path) -> list[dict[str, Any]]:
    sources = []
    for output_dir in sorted(input_root.glob("*")):
        if not output_dir.is_dir():
            continue
        prep_path = output_dir / "indicator_preparation_database.csv"
        if not prep_path.exists():
            continue
        company, year = _company_year_from_dir(output_dir)
        available = sorted(path.name for path in output_dir.iterdir() if path.is_file())
        rows = read_csv(prep_path)
        document_ids = sorted({row.get("document_id", "") for row in rows if row.get("document_id", "")})
        if not document_ids:
            document_ids = [""]
        sources.append(
            {
                "company": company,
                "year": year,
                "document_ids": document_ids,
                "source_output_dir": str(output_dir),
                "available_files": available,
                "preparation_database_present": prep_path.exists(),
                "evidence_links_present": (output_dir / "indicator_evidence_links.csv").exists(),
                "lineage_present": (output_dir / "indicator_lineage.jsonl").exists(),
                "manual_review_present": any("review" in file_name for file_name in available),
                "empty_preparation_database": len(rows) == 0,
            }
        )
    return sources


def group_company_year(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for source in sources:
        key = (source["company"], str(source["year"]))
        item = grouped.setdefault(
            key,
            {
                "company": source["company"],
                "year": str(source["year"]),
                "source_output_dirs": [],
                "document_ids": set(),
                "sources_count": 0,
                "empty_preparation_database": True,
            },
        )
        item["source_output_dirs"].append(source["source_output_dir"])
        item["document_ids"].update(source["document_ids"])
        item["sources_count"] += 1
        item["empty_preparation_database"] = item["empty_preparation_database"] and source["empty_preparation_database"]
    return [
        {**item, "document_ids": sorted(doc for doc in item["document_ids"] if doc)}
        for item in grouped.values()
    ]


def write_input_discovery_outputs(input_root: Path, output_dir: Path) -> dict[str, Any]:
    sources = discover_inputs(input_root)
    inventory = group_company_year(sources)
    write_json(output_dir / "company_year_input_inventory.json", {"company_years": inventory})
    write_jsonl(output_dir / "company_year_input_sources.jsonl", sources)
    summary = {
        "input_root": str(input_root),
        "sources_count": len(sources),
        "company_year_count": len(inventory),
        "empty_preparation_database_count": sum(1 for item in inventory if item["empty_preparation_database"]),
    }
    write_json(output_dir / "input_discovery_summary.json", summary)
    return {"sources": sources, "inventory": inventory, "summary": summary}

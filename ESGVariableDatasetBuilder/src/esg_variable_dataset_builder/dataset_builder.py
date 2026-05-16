from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path
from typing import Any

from .config import DEFAULT_DICTIONARY_PATH
from .evidence_builder import build_traceability_outputs
from .input_discovery import group_company_year, write_input_discovery_outputs
from .io_utils import write_csv, write_json
from .preparation_loader import load_preparation_output, write_preparation_loading_outputs
from .quality_report import build_quality_report
from .value_selector import write_selection_outputs, select_values
from .variable_dictionary import FINAL_VARIABLES
from .variable_mapper import map_records, write_mapping_outputs

logger = logging.getLogger(__name__)


def build_dataset(
    input_root: Path,
    output_dir: Path,
    company: str | None = None,
    year: str | None = None,
    dictionary_path: Path = DEFAULT_DICTIONARY_PATH,
    overwrite: bool = False,
    override_empty_company_from_cli: bool = False,
    override_empty_year_from_cli: bool = False,
    single_document_mode: bool = False,
) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"Output directory already exists and is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    discovery = write_input_discovery_outputs(input_root, output_dir)
    sources = discovery["sources"]
    if company:
        sources = [item for item in sources if item["company"].lower() == company.lower()]
    if year:
        sources = [item for item in sources if str(item["year"]) == str(year)]
    if not sources and company and year:
        sources = [{
            "company": company,
            "year": str(year),
            "source_output_dir": "",
            "document_ids": [],
            "empty_preparation_database": True,
        }]

    company_year_items = group_company_year(sources)
    company_years = [(item["company"], str(item["year"])) for item in company_year_items]
    if not company_years and company and year:
        company_years = [(company, str(year))]

    # Early override safety check — fail before loading if multiple source dirs present
    if (override_empty_company_from_cli or override_empty_year_from_cli) and not single_document_mode:
        real_sources = [s for s in sources if s.get("source_output_dir")]
        if len(real_sources) > 1:
            source_dirs = [s["source_output_dir"] for s in real_sources]
            raise ValueError(
                "override_empty_company_from_cli/override_empty_year_from_cli requires single-document-mode "
                f"(multiple source directories found: {source_dirs}). "
                "Pass --single-document-mode explicitly to allow this."
            )

    all_records: list[dict[str, Any]] = []
    all_evidence: list[dict[str, Any]] = []
    all_lineage: list[dict[str, Any]] = []
    all_findings: list[dict[str, Any]] = []
    ignored_records_count = 0
    ignored_reasons: list[str] = []

    for source in sources:
        source_dir = Path(source.get("source_output_dir", ""))
        if not source_dir.exists():
            logger.warning("Source directory does not exist, skipping: %s", source_dir)
            ignored_records_count += 1
            ignored_reasons.append("source_dir_missing")
            continue
        loaded = load_preparation_output(source_dir)
        # Log (never silently ignore) records that have findings
        for finding in loaded.get("findings", []):
            logger.warning(
                "Preparation record ignored: category=%s preparation_indicator_id=%s",
                finding.get("category", "unknown"),
                finding.get("preparation_indicator_id", ""),
            )
            ignored_records_count += 1
            ignored_reasons.append(finding.get("category", "unknown"))
        all_records.extend(loaded["records"])
        all_evidence.extend(loaded["evidence_links"])
        all_lineage.extend(loaded["lineage"])
        all_findings.extend(loaded.get("findings", []))

    # Metadata quality counts
    metadata_missing_company_count = sum(1 for r in all_records if not str(r.get("company", "")).strip())
    metadata_missing_fiscal_year_count = sum(1 for r in all_records if not str(r.get("fiscal_year", "")).strip())

    # Override flags — only allowed in single-document mode or when all records share same document_id
    if override_empty_company_from_cli or override_empty_year_from_cli:
        all_doc_ids = {r.get("document_id", "") for r in all_records if r.get("document_id")}
        is_single_doc = len(all_doc_ids) <= 1
        if not is_single_doc and not single_document_mode:
            raise ValueError(
                "override_empty_company_from_cli/override_empty_year_from_cli requires single-document-mode "
                f"(multiple document_ids found: {sorted(all_doc_ids)}). "
                "Pass --single-document-mode explicitly to allow this."
            )
        if override_empty_company_from_cli and company:
            for r in all_records:
                if not str(r.get("company", "")).strip():
                    r["company"] = company
            logger.info("override_empty_company_from_cli applied: company=%s", company)
        if override_empty_year_from_cli and year:
            for r in all_records:
                if not str(r.get("fiscal_year", "")).strip():
                    r["fiscal_year"] = year
            logger.info("override_empty_year_from_cli applied: year=%s", year)

    if metadata_missing_company_count > 0:
        logger.warning(
            "metadata_missing_company: %d/%d loaded records have empty company",
            metadata_missing_company_count, len(all_records),
        )
    if metadata_missing_fiscal_year_count > 0:
        logger.warning(
            "metadata_missing_fiscal_year: %d/%d loaded records have empty fiscal_year",
            metadata_missing_fiscal_year_count, len(all_records),
        )

    loaded_all = {
        "records": all_records,
        "evidence_links": all_evidence,
        "lineage": all_lineage,
        "findings": all_findings,
        "empty_database_warning": len(all_records) == 0,
    }
    write_preparation_loading_outputs(loaded_all, output_dir)

    mapping_candidates = map_records(all_records, dictionary_path)
    write_mapping_outputs(mapping_candidates, output_dir)

    selected = select_values(mapping_candidates, company_years)
    write_selection_outputs(selected, output_dir)
    _write_wide_datasets(selected, output_dir)
    traceability = build_traceability_outputs(selected, output_dir)
    quality = build_quality_report(output_dir)

    ignored_reason_distribution = dict(Counter(ignored_reasons))
    summary = {
        "input_root": str(input_root),
        "output_dir": str(output_dir),
        "company_year_rows_count": len(set(company_years)),
        "variables_count": len(FINAL_VARIABLES),
        "selected_rows_count": len(selected),
        "ignored_records_count": ignored_records_count,
        "ignored_records_reason_distribution": ignored_reason_distribution,
        "metadata_missing_company_count": metadata_missing_company_count,
        "metadata_missing_fiscal_year_count": metadata_missing_fiscal_year_count,
        **traceability,
        "quality": quality,
        "no_external_sources_used": True,
        "score_produced": False,
    }
    write_json(output_dir / "esg_variables_dataset_summary.json", summary)
    return summary


def _write_wide_datasets(selected: list[dict[str, Any]], output_dir: Path) -> None:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    enriched: dict[tuple[str, str], dict[str, Any]] = {}
    for row in selected:
        key = (row.get("company", ""), str(row.get("year", "")))
        base = grouped.setdefault(key, {"company": key[0], "year": key[1], **{name: "" for name in FINAL_VARIABLES}})
        rich = enriched.setdefault(key, _empty_enriched_row(key[0], key[1]))
        variable = row.get("variable_name", "")
        if variable not in FINAL_VARIABLES:
            continue
        base[variable] = row.get("selected_value", "") if row.get("selected_status") == "found" else ""
        rich[f"{variable}_value"] = row.get("selected_value", "")
        rich[f"{variable}_unit"] = row.get("selected_unit", "")
        rich[f"{variable}_status"] = row.get("selected_status", "")
        rich[f"{variable}_source_document"] = row.get("selected_source_document", "")
        rich[f"{variable}_page_number"] = row.get("selected_page_number", "")
        rich[f"{variable}_confidence"] = row.get("selected_confidence", "")

    main_fields = ["company", "year", *FINAL_VARIABLES]
    enriched_fields = ["company", "year"]
    for variable in FINAL_VARIABLES:
        enriched_fields.extend([
            f"{variable}_value", f"{variable}_unit", f"{variable}_status",
            f"{variable}_source_document", f"{variable}_page_number", f"{variable}_confidence",
        ])
    write_csv(output_dir / "esg_variables_dataset.csv", list(grouped.values()), main_fields)
    write_csv(output_dir / "esg_variables_dataset_enriched.csv", list(enriched.values()), enriched_fields)


def _empty_enriched_row(company: str, year: str) -> dict[str, Any]:
    row: dict[str, Any] = {"company": company, "year": year}
    for variable in FINAL_VARIABLES:
        row[f"{variable}_value"] = ""
        row[f"{variable}_unit"] = ""
        row[f"{variable}_status"] = "missing_from_corpus"
        row[f"{variable}_source_document"] = ""
        row[f"{variable}_page_number"] = ""
        row[f"{variable}_confidence"] = ""
    return row

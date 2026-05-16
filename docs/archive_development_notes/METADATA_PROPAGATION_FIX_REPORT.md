# MetadataPropagationFix v1.0 — Implementation Report

## Summary

Implemented full metadata propagation fix across the ESG pipeline. The root cause was
that `company` and `fiscal_year` were never written by `ESGInformationExtraction` (no CLI args),
not propagated by `ESGVisualExtraction` (no fields in output), and lost during
`ESGExtractionOrchestrator` consolidation, ultimately causing `ESGVariableDatasetBuilder`
to produce 0 found values for TotalEnergies 2024 (real E2E bug).

## Baseline

- **406 tests passing**, 0 failures before any changes.

## Changes Made

### v0.0 — Baseline Report
- Created `METADATA_BASELINE_REPORT.md`

### v0.1 — run_project_validation.py + audit tool
- **Fixed** `tools/run_project_validation.py`: now uses `tempfile.mkdtemp()` instead of fixed `.pytest_tmp`. Added `--basetemp-root` CLI option.
- **Created** `tools/audit_metadata_propagation.py`: inspects E2E run output root, produces `metadata_propagation_report.json`, `metadata_propagation_findings.jsonl`, `metadata_propagation_report.md`.
- **Created** `tests/test_metadata_propagation_audit_v01.py` (6 tests)

### v0.2 — Metadata Contract Documentation
- **Created** `docs/METADATA_PROPAGATION_CONTRACT_V1.md`: defines all 12 metadata fields, authority order, fiscal_year vs year_raw distinction, rules for missing/contradicting metadata.

### v0.3 — ESGInformationExtraction metadata CLI args
- **Backed up** `run_pdf_extraction.py` and `output_contract_v1.json` to `backups/metadata_fix_v0_3_pre_implementation/`
- **Modified** `ESGInformationExtraction/run_pdf_extraction.py`:
  - Added 9 optional CLI args: `--company`, `--company-name`, `--company-slug`, `--fiscal-year`, `--official-doc-type`, `--document-family`, `--final-path`, `--source-index-path`, `--corpus-run-id`
  - Added fields to `ExtractionOptions` dataclass (all default None)
  - Injects `_cli_metadata` additively into `document_record.json`, `document_inventory.json`, `evidence_store.jsonl`, `multimodal_evidence_index.jsonl`
  - 100% backward compatible — absent args = unchanged behavior
- **Created** `ESGInformationExtraction/tests/test_metadata_propagation_v03.py` (7 tests)

### v0.4 — ESGVisualExtraction + Orchestrator
- **Modified** `ESGVisualExtraction/src/esg_visual_extraction/loader.py`:
  - Added `_resolve_company_year()` using authority order: `document_record.json` → `document_inventory.json` → path inference
  - `load_visual_inputs()` now returns `company` and `fiscal_year`
- **Modified** `ESGVisualExtraction/src/esg_visual_extraction/candidate_extractor.py`:
  - Added `company` and `fiscal_year` to `CANDIDATE_FIELDS`
  - `_build_candidates()` now accepts and writes `company`/`fiscal_year` to each candidate
  - `visual_extraction_summary.json` includes `company` and `fiscal_year`
- **Modified** `ESGExtractionOrchestrator/src/esg_extraction_orchestrator/candidate_consolidator.py`:
  - Added `company` and `fiscal_year` to `CONSOLIDATED_FIELDS`
  - All three source engines (csv, visual, table) now pass through `company`/`fiscal_year`
  - Backfill logic: visual candidates without `company`/`fiscal_year` are filled from CSV/Table candidates sharing same `document_id`
- **Created** `ESGVisualExtraction/tests/test_metadata_propagation_v04_visual.py` (7 tests)
- **Created** `ESGExtractionOrchestrator/tests/test_metadata_propagation_v04_orchestrator.py` (6 tests)

### v0.5 — ESGIndicatorValidation + ESGManualReview (verified, no code change needed)
- Both modules already had `company`/`fiscal_year` in their output field lists and pass-through logic.
- `ESGIndicatorValidation` normalizer does NOT overwrite `fiscal_year` (verified).
- **Created** `ESGIndicatorValidation/tests/test_metadata_propagation_v05_validation.py` (5 tests)
- **Created** `ESGManualReview/tests/test_metadata_propagation_v05_review.py` (3 tests)

### v0.6 — ESGIndicatorDatabase
- **Modified** `ESGIndicatorDatabase/src/esg_indicator_database/database_builder.py`:
  - Added `metadata_missing_company_count` and `metadata_missing_fiscal_year_count` warnings via `logging`
  - Added `reporting_year_vs_extracted_year_difference_count` (info level)
  - Added these counts to `indicator_database_summary.json`
- **Created** `ESGIndicatorDatabase/tests/test_metadata_propagation_v06_database.py` (6 tests)

### v0.7 — ESGVariableDatasetBuilder
- **Modified** `ESGVariableDatasetBuilder/src/esg_variable_dataset_builder/dataset_builder.py`:
  - Added `override_empty_company_from_cli`, `override_empty_year_from_cli`, `single_document_mode` parameters
  - Override flags only allowed in single-document mode or when all records share same `document_id`; raises explicit `ValueError` otherwise
  - Added `ignored_records_count`, `ignored_records_reason_distribution`, `metadata_missing_company_count`, `metadata_missing_fiscal_year_count` to summary
  - Records with findings are logged (not silently dropped)
- **Modified** `ESGVariableDatasetBuilder/scripts/build_esg_variables_dataset.py`:
  - Added `--override-empty-company-from-cli`, `--override-empty-year-from-cli`, `--single-document-mode` CLI args
- **Created** `ESGVariableDatasetBuilder/tests/test_metadata_propagation_v07_builder.py` (8 tests)

### v0.8 — Regression Fixtures + E2E Tests
- **Created** `tests/fixtures/metadata_regression_totalenergies_2024/indicator_preparation_database_with_metadata.csv`
- **Created** `tests/fixtures/metadata_regression_totalenergies_2024/indicator_preparation_database_missing_company.csv`
- **Created** `tests/test_e2e_metadata_regression_v08.py` (8 tests)

## Files Modified

| File | Nature of Change |
|---|---|
| `tools/run_project_validation.py` | tempfile.mkdtemp(), --basetemp-root |
| `ESGInformationExtraction/run_pdf_extraction.py` | +9 optional CLI metadata args, additive injection |
| `ESGVisualExtraction/src/esg_visual_extraction/loader.py` | _resolve_company_year(), company/fiscal_year in outputs |
| `ESGVisualExtraction/src/esg_visual_extraction/candidate_extractor.py` | company/fiscal_year in CANDIDATE_FIELDS and records |
| `ESGExtractionOrchestrator/src/esg_extraction_orchestrator/candidate_consolidator.py` | company/fiscal_year in CONSOLIDATED_FIELDS, backfill logic |
| `ESGIndicatorDatabase/src/esg_indicator_database/database_builder.py` | metadata warning logging, summary counts |
| `ESGVariableDatasetBuilder/src/esg_variable_dataset_builder/dataset_builder.py` | override flags, summary counts, improved logging |
| `ESGVariableDatasetBuilder/scripts/build_esg_variables_dataset.py` | new CLI flags |

## Constraints Respected

- All changes additive and backward compatible
- No PDF files modified
- No ESGFinalCorpus modified
- No existing output files overwritten
- No ESG scoring logic added
- `fiscal_year` never overwritten by `year_raw`
- Override flags require explicit `single_document_mode` for multi-doc safety

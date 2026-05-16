# Metadata Baseline Report — MetadataPropagationFix v1.0

## Baseline State

- **Test count**: 406 tests passing, 0 failures
- **Python version**: 3.13.12
- **OS**: Windows 11 Pro
- **Date captured**: 2026-05-14

## Known Root Causes

1. `ESGInformationExtraction/run_pdf_extraction.py` has NO `--company`, `--fiscal-year` CLI args
2. `ESGVisualExtraction` does NOT write `company`/`fiscal_year` to `visual_candidates.csv`
3. `ESGExtractionOrchestrator` consolidation LOSES `company`/`fiscal_year` when merging (visual candidates have no company/fiscal_year, so the merge produces empty values)
4. `ESGCSVExtraction` and `ESGTableExtraction` infer `company`/`fiscal_year` from file path via `infer_company_year()` — works IF path contains `ESGFinalCorpus/COMPANY/YEAR/` pattern, fails otherwise
5. `ESGVariableDatasetBuilder` has `--company` and `--year` CLI args but they are optional and the guessing fallback in `input_discovery.py` is fragile

## Bug Reproduced

- End-to-end test on TotalEnergies 2024
- `ESGIndicatorDatabase` produced 2 rows (human_capital=102887 employees, water_consumption=92 Mm3)
- `company` was EMPTY in `indicator_preparation_database.csv`
- `ESGVariableDatasetBuilder` produced 0 found values
- After manual patch setting `company=TotalEnergies`, `fiscal_year=2024` → builder produced correct results

## Modules to be Modified

| Module | Change |
|---|---|
| `ESGInformationExtraction/run_pdf_extraction.py` | Add optional metadata CLI args |
| `ESGVisualExtraction/src/esg_visual_extraction/candidate_extractor.py` | Write company/fiscal_year to visual candidates |
| `ESGVisualExtraction/src/esg_visual_extraction/loader.py` | Load company/fiscal_year from document_inventory |
| `ESGExtractionOrchestrator/src/esg_extraction_orchestrator/candidate_consolidator.py` | Preserve and backfill company/fiscal_year |
| `ESGIndicatorDatabase/src/esg_indicator_database/database_builder.py` | Add metadata-missing warnings |
| `ESGVariableDatasetBuilder/src/esg_variable_dataset_builder/dataset_builder.py` | Add override flags and summary counts |
| `tools/run_project_validation.py` | Use tempfile.mkdtemp() |

## Files to be Created

- `tools/audit_metadata_propagation.py`
- `docs/METADATA_PROPAGATION_CONTRACT_V1.md`
- `tests/test_metadata_propagation_audit_v01.py`
- `ESGInformationExtraction/tests/test_metadata_propagation_v03.py`
- `ESGVisualExtraction/tests/test_metadata_propagation_v04_visual.py`
- `ESGExtractionOrchestrator/tests/test_metadata_propagation_v04_orchestrator.py`
- `ESGIndicatorValidation/tests/test_metadata_propagation_v05_validation.py`
- `ESGManualReview/tests/test_metadata_propagation_v05_review.py`
- `ESGIndicatorDatabase/tests/test_metadata_propagation_v06_database.py`
- `ESGVariableDatasetBuilder/tests/test_metadata_propagation_v07_builder.py`
- `tests/fixtures/metadata_regression_totalenergies_2024/`
- `tests/test_e2e_metadata_regression_v08.py`

## Authority Order for Metadata

1. CLI explicit argument
2. document_record.json
3. document_inventory.json
4. evidence_store.jsonl / multimodal_evidence_index.jsonl
5. PDF content (never for company/fiscal_year)

## Critical Rule

`fiscal_year` = reporting year (company-level metadata)
`year_raw` / `year_prepared` = year found in content of a quote
NEVER overwrite `fiscal_year` with `year_raw`

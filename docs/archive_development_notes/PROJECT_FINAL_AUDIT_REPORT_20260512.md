# Project Final Audit Report

Date: 2026-05-12

## Overall Status

- Status: passed
- Global pytest: passed
- Project validation runner: passed
- Compileall: passed
- Helper import collision check: passed
- ESGVariableDatasetBuilder contract: passed
- Onyxia quality-audit integration: passed

## Validation Commands Executed

- `python tools/project_hygiene_audit.py --project-root . --output-dir project_hygiene_outputs --overwrite`
- `python tools/check_test_helper_imports.py --project-root .`
- `python -m compileall -q ESGInformationExtraction ESGCSVExtraction ESGVisualExtraction ESGTableExtraction ESGExtractionOrchestrator ESGIndicatorValidation ESGManualReview ESGIndicatorDatabase ESGProductionControlCenter ESGVariableDatasetBuilder DocumentPostProcessing ESGOrchestrator`
- `python -m pytest ESGVariableDatasetBuilder/tests DocumentPostProcessing/tests ESGOrchestrator/tests --basetemp .pytest_tmp/final_audit_focused`
- `python tools/run_project_validation.py --project-root . --full`
- `python -m pytest --basetemp .pytest_tmp/final_audit_global`
- `python ESGVariableDatasetBuilder/scripts/validate_esg_variables_dataset.py --output-dir ESGVariableDatasetBuilder/outputs/lvmh_2024_variables_dataset_v10_test --contract-path ESGVariableDatasetBuilder/contracts/esg_variables_dataset_contract_v0.json`
- `python tools/clean_python_artifacts.py --project-root . --dry-run --report-path python_artifacts_cleanup_report.json`

## Results

- Focused tests: 22 passed
- Global tests: 406 passed
- Project validation: 14/14 steps passed
- Dataset contract validation: passed, 0 errors
- `from helpers import ...` collisions: none detected
- Requirements hygiene: bounded and readable
- Compileall: no errors

## Module Coverage Confirmed

Validated by global pytest:

- AnnualReportRetriever
- DocumentPostProcessing
- ESGCSVExtraction
- ESGExtractionOrchestrator
- ESGIndicatorDatabase
- ESGIndicatorValidation
- ESGInformationExtraction
- ESGManualReview
- ESGOrchestrator
- ESGProductionControlCenter
- ESGTableExtraction
- ESGVariableDatasetBuilder
- ESGVisualExtraction
- Project hygiene tests

## ESGVariableDatasetBuilder Audit

- Final variable dictionary: present
- Required variables: 31
- Main CSV contract: present
- Enriched/status/evidence outputs: present
- Contract validator: passed
- Score produced: no
- External source detected: no
- LVMH 2024 test output:
  - company_year_rows_count: 1
  - found_values_count: 0
  - missing_values_count: 31
  - found_without_evidence_count: 0

The LVMH source preparation database is empty, so `missing_from_corpus` for all
31 variables is expected and contract-compliant.

## Onyxia / Post-Processing Audit

- Onyxia execution report documented in `docs/ONYXIA_CAC40_5Y_EXECUTION_REPORT_20260510.md`
- Local integration status documented in `docs/ONYXIA_LOCAL_INTEGRATION_STATUS_20260512.md`
- `audit_selected_documents.py` is now wired into `ESGOrchestrator` post-processing
- Quality audit v2 outputs include:
  - `extraction_index_strict_likely_valid.csv`
  - `extraction_index_usable_excluding_quarantine.csv`
  - `exclusion_index_quarantine_wrong_company.csv`
  - `quality_summary_by_company.csv`
  - `quality_summary_by_doc_type.csv`
  - `quality_audit_report.md`
- Markdown generation does not depend on `tabulate`
- `final_path` existence is checked

Rule confirmed: raw `ESGFinalCorpus` must not be used directly for extraction.
Extraction should start from `extraction_index_strict_likely_valid.csv`.

## Hygiene Findings

- Git available: yes
- Git repository initialized: no
- `.gitignore`: present
- Python caches: present after validation runs
- Cache cleanup: dry-run completed
- Legacy scripts: documented
- Requirements: no unbounded requirements found by audit
- Retriever test coverage: partial outside the current prioritized retriever core

Python caches are expected after compile/test runs and can be removed with:

```powershell
python tools/clean_python_artifacts.py --project-root . --execute
```

## Remaining Risks

- The workspace is not currently a Git repository, so no Git diff-based proof is available.
- Large corpus runs can still duplicate PDFs physically unless `copy_mode = copy | hardlink | symlink` is implemented.
- Disk-space preflight before heavy post-processing remains to be added.
- Several retriever families still need broader mocked tests.
- Retriever hardening is still needed for non-HTML/binary responses observed on Onyxia.
- Short policy documents remain fragile for company-document validation.

## Recommendation

The project is validation-ready for controlled extraction tests. Start the next
real extraction phase on 10 to 20 documents from the strict Onyxia index only,
then expand to 100 strict documents after evidence fields and extraction quality
are manually checked.

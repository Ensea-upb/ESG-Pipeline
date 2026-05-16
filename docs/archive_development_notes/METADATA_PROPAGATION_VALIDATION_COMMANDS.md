# Metadata Propagation Validation Commands

## 1. Compile check (all modified modules)

```powershell
python -m compileall -q `
  C:/Users/hp/Desktop/ESG/ESGInformationExtraction `
  C:/Users/hp/Desktop/ESG/ESGCSVExtraction `
  C:/Users/hp/Desktop/ESG/ESGVisualExtraction `
  C:/Users/hp/Desktop/ESG/ESGTableExtraction `
  C:/Users/hp/Desktop/ESG/ESGExtractionOrchestrator `
  C:/Users/hp/Desktop/ESG/ESGIndicatorValidation `
  C:/Users/hp/Desktop/ESG/ESGManualReview `
  C:/Users/hp/Desktop/ESG/ESGIndicatorDatabase `
  C:/Users/hp/Desktop/ESG/ESGVariableDatasetBuilder
```

Expected: no output (clean compile).

## 2. Full test suite

```powershell
cd C:/Users/hp/Desktop/ESG
python -m pytest --basetemp=C:/Windows/Temp/esg_pytest_metadata_fix -p no:cacheprovider -q --tb=short 2>&1
```

Expected: 406 + new tests, 0 failures.

## 3. Run audit tool on an E2E output root

```powershell
python C:/Users/hp/Desktop/ESG/tools/audit_metadata_propagation.py `
  --input-root <path-to-e2e-output-root> `
  --output-dir C:/Users/hp/Desktop/ESG/project_hygiene_outputs/metadata_audit `
  --overwrite
```

Check `metadata_propagation_report.md` for findings.

## 4. Run ESGInformationExtraction with metadata args

```powershell
python C:/Users/hp/Desktop/ESG/ESGInformationExtraction/run_pdf_extraction.py `
  --pdf-path <path-to.pdf> `
  --document-id totalenergies_2024_urd `
  --output-dir <output-dir> `
  --company TotalEnergies `
  --fiscal-year 2024 `
  --official-doc-type URD
```

Check `document_record.json` contains `company` and `fiscal_year`.

## 5. Run ESGVariableDatasetBuilder with override flags (single-document mode)

```powershell
python C:/Users/hp/Desktop/ESG/ESGVariableDatasetBuilder/scripts/build_esg_variables_dataset.py `
  --input-root <path-to-indicator-db-output> `
  --output-dir <output-dir> `
  --company TotalEnergies `
  --year 2024 `
  --override-empty-company-from-cli `
  --override-empty-year-from-cli `
  --single-document-mode `
  --overwrite
```

Check `esg_variables_dataset_summary.json` for `metadata_missing_company_count`.

## 6. Verify fiscal_year vs year_raw never confused

```powershell
python -c "
import csv
with open('tests/fixtures/metadata_regression_totalenergies_2024/indicator_preparation_database_with_metadata.csv') as f:
    rows = list(csv.DictReader(f))
for r in rows:
    assert r['fiscal_year'] == '2024', f'fiscal_year wrong: {r}'
    print(f'indicator_key={r[\"indicator_key\"]} fiscal_year={r[\"fiscal_year\"]} year_raw={r[\"year_raw\"]} year_prepared={r[\"year_prepared\"]}')
print('OK: fiscal_year is always 2024 regardless of year_raw')
"
```

## 7. Regression: reproduce original bug scenario

```powershell
cd C:/Users/hp/Desktop/ESG
python -m pytest tests/test_e2e_metadata_regression_v08.py -v --tb=short
```

Expected: all 8 tests pass, including:
- `test_builder_produces_human_capital_found_when_metadata_present`
- `test_found_values_count_equals_two_when_metadata_present`
- `test_fiscal_year_stays_2024_despite_year_raw_2015`
- `test_builder_missing_company_produces_no_found_values` (reproduces the original bug)

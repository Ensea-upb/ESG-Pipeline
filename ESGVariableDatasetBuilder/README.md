# ESGVariableDatasetBuilder

Builds a company x year CSV of ESG, controversy, and financial variables from
the preparation-only outputs of `ESGIndicatorDatabase`.

This module does not produce ESG scores, ratings, or final validated
indicators. It does not fetch external sources. All values must come from the
PDF-derived corpus pipeline or be marked with an absence/status.

Main output:

- `esg_variables_dataset.csv`

Enriched audit outputs include statuses, evidence, lineage, missing reports,
and quality reports.

## Build

```powershell
python ESGVariableDatasetBuilder/scripts/build_esg_variables_dataset.py `
  --input-root "ESGIndicatorDatabase/outputs" `
  --company "LVMH" `
  --year "2024" `
  --output-dir "ESGVariableDatasetBuilder/outputs/lvmh_2024_variables_dataset_v10_test" `
  --overwrite
```

## Validate

```powershell
python ESGVariableDatasetBuilder/scripts/validate_esg_variables_dataset.py `
  --output-dir "ESGVariableDatasetBuilder/outputs/lvmh_2024_variables_dataset_v10_test" `
  --contract-path "ESGVariableDatasetBuilder/contracts/esg_variables_dataset_contract_v0.json"
```

No source outputs, PDFs, external data, ESG scores, or ESG ratings are produced
or modified by this module.

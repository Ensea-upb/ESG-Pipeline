# Validation Commands V1.0

```powershell
python -m compileall -q ESGVariableDatasetBuilder ESGInformationExtraction ESGCSVExtraction ESGVisualExtraction ESGTableExtraction ESGExtractionOrchestrator ESGIndicatorValidation ESGManualReview ESGIndicatorDatabase ESGProductionControlCenter
python -m pytest ESGVariableDatasetBuilder/tests --basetemp .pytest_tmp/esg_variable_dataset_builder
python -m pytest --basetemp .pytest_tmp/global
python tools/run_project_validation.py --project-root . --full
```

Manual LVMH build:

```powershell
python ESGVariableDatasetBuilder/scripts/build_esg_variables_dataset.py `
  --input-root "ESGIndicatorDatabase/outputs" `
  --company "LVMH" `
  --year "2024" `
  --output-dir "ESGVariableDatasetBuilder/outputs/lvmh_2024_variables_dataset_v10_test" `
  --overwrite
```

Contract validation:

```powershell
python ESGVariableDatasetBuilder/scripts/validate_esg_variables_dataset.py `
  --output-dir "ESGVariableDatasetBuilder/outputs/lvmh_2024_variables_dataset_v10_test" `
  --contract-path "ESGVariableDatasetBuilder/contracts/esg_variables_dataset_contract_v0.json"
```

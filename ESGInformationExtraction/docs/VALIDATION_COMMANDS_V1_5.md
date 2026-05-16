# Validation Commands v1.5

```powershell
python -m compileall -q ESGInformationExtraction ESGCSVExtraction ESGVisualExtraction ESGTableExtraction ESGExtractionOrchestrator ESGIndicatorValidation ESGManualReview ESGIndicatorDatabase
```

```powershell
$bt = Join-Path $env:TEMP ('pytest_info_' + [guid]::NewGuid().ToString())
python -m pytest ESGInformationExtraction\tests --basetemp $bt
```

```powershell
python ESGInformationExtraction/tools/validate_output_contract.py `
  --output-dir "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test" `
  --contract-path "ESGInformationExtraction/contracts/output_contract_v1.json"
```

```powershell
python ESGInformationExtraction/tools/audit_engine_architecture.py `
  --project-root "." `
  --output-dir "ESGInformationExtraction/outputs/architecture_hygiene_v15" `
  --overwrite
```

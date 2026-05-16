# ESGIndicatorValidation v1.0 - Validation Commands

```powershell
python -m compileall -q ESGIndicatorValidation ESGExtractionOrchestrator ESGTableExtraction ESGVisualExtraction ESGCSVExtraction ESGInformationExtraction
```

```powershell
$bt = Join-Path $env:TEMP ('pytest_indicator_' + [guid]::NewGuid().ToString())
python -m pytest ESGIndicatorValidation\tests --basetemp $bt
```

```powershell
python ESGIndicatorValidation/scripts/run_indicator_validation.py `
  --input-dir "ESGExtractionOrchestrator/outputs/lvmh_full_v11_test" `
  --output-dir "ESGIndicatorValidation/outputs/lvmh_indicator_validation_v10_test" `
  --overwrite
```

```powershell
python ESGIndicatorValidation/scripts/validate_indicator_validation_outputs.py `
  --output-dir "ESGIndicatorValidation/outputs/lvmh_indicator_validation_v10_test" `
  --contract-path "ESGIndicatorValidation/contracts/indicator_validation_contract_v0.json"
```

```powershell
python ESGIndicatorValidation/scripts/run_multi_document_indicator_validation.py `
  --input-root "ESGExtractionOrchestrator/outputs" `
  --output-dir "ESGIndicatorValidation/outputs/multi_document_indicator_validation_v10" `
  --overwrite
```

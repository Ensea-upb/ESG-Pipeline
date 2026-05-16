# ESGManualReview v1.0 - Validation Commands

```powershell
python -m compileall -q ESGManualReview ESGIndicatorValidation ESGExtractionOrchestrator ESGTableExtraction ESGVisualExtraction ESGCSVExtraction ESGInformationExtraction
```

```powershell
$bt = Join-Path $env:TEMP ('pytest_manual_' + [guid]::NewGuid().ToString())
python -m pytest ESGManualReview\tests --basetemp $bt
```

```powershell
python ESGManualReview/scripts/build_review_workspace.py `
  --input-dir "ESGIndicatorValidation/outputs/lvmh_indicator_validation_v10_test" `
  --output-dir "ESGManualReview/outputs/lvmh_manual_review_v10_test" `
  --overwrite
```

```powershell
python ESGManualReview/scripts/apply_review_decisions.py `
  --workspace-dir "ESGManualReview/outputs/lvmh_manual_review_v10_test" `
  --decisions-file "ESGManualReview/outputs/lvmh_manual_review_v10_test/review_decisions_template.csv" `
  --output-dir "ESGManualReview/outputs/lvmh_manual_review_applied_v10_test" `
  --overwrite
```

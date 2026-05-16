# ESGIndicatorDatabase v1.0 - Validation Commands

```powershell
python -m compileall -q ESGIndicatorDatabase ESGManualReview ESGIndicatorValidation ESGExtractionOrchestrator ESGTableExtraction ESGVisualExtraction ESGCSVExtraction ESGInformationExtraction
```

```powershell
$bt = Join-Path $env:TEMP ('pytest_db_' + [guid]::NewGuid().ToString())
python -m pytest ESGIndicatorDatabase\tests --basetemp $bt
```

```powershell
python ESGIndicatorDatabase/scripts/build_indicator_database.py `
  --input-dir "ESGManualReview/outputs/lvmh_manual_review_applied_v10_test" `
  --output-dir "ESGIndicatorDatabase/outputs/lvmh_indicator_database_v10_test" `
  --overwrite
```

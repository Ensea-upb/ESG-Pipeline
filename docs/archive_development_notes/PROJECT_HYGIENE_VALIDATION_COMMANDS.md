# Project Hygiene Validation Commands

## Audit

```powershell
python tools/project_hygiene_audit.py --project-root . --output-dir project_hygiene_outputs --overwrite
```

## Helper Imports

```powershell
python tools/check_test_helper_imports.py --project-root .
```

## Requirements

```powershell
python tools/check_requirements.py --project-root .
```

## Cache Cleanup Dry Run

```powershell
python tools/clean_python_artifacts.py --project-root . --dry-run --report-path python_artifacts_cleanup_report.json
```

## Compile

```powershell
python -m compileall -q ESGInformationExtraction ESGCSVExtraction ESGVisualExtraction ESGTableExtraction ESGExtractionOrchestrator ESGIndicatorValidation ESGManualReview ESGIndicatorDatabase ESGProductionControlCenter
```

## Isolated Tests

```powershell
python -m pytest ESGInformationExtraction/tests --basetemp .pytest_tmp/final_info
python -m pytest ESGCSVExtraction/tests --basetemp .pytest_tmp/final_csv
python -m pytest ESGVisualExtraction/tests --basetemp .pytest_tmp/final_visual
python -m pytest ESGTableExtraction/tests --basetemp .pytest_tmp/final_table
python -m pytest ESGExtractionOrchestrator/tests --basetemp .pytest_tmp/final_fullorch
python -m pytest ESGIndicatorValidation/tests --basetemp .pytest_tmp/final_validation
python -m pytest ESGManualReview/tests --basetemp .pytest_tmp/final_manual
python -m pytest ESGIndicatorDatabase/tests --basetemp .pytest_tmp/final_db
python -m pytest ESGProductionControlCenter/tests --basetemp .pytest_tmp/final_control
python -m pytest AnnualReportRetriever/tests --basetemp .pytest_tmp/final_retriever
```

## Global Test

```powershell
python -m pytest --basetemp .pytest_tmp/final_global_cache
```

## CI-Ready Validation

```powershell
python tools/run_project_validation.py --project-root . --full
```

Final observed status:

- Global pytest: `384 passed`
- Project validation: `14/14 passed`

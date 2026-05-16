# Project Validation Report

- Status: `failed`
- Steps: `13/14` passed

## Steps

- **failed** `check_test_helper_imports`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe tools/check_test_helper_imports.py --project-root .`

```text
.pytest_tmp_run/test_project_hygiene_audit_pro0/project/SampleModule/tests has helpers.py but no __init__.py
.pytest_tmp_run/test_project_hygiene_audit_pro0/project/SampleModule/tests/test_sample.py:1 uses absolute helpers import
.pytest_tmp_robustness/test_project_hygiene_audit_pro0/project/SampleModule/tests has helpers.py but no __init__.py
.pytest_tmp_robustness/test_project_hygiene_audit_pro0/project/SampleModule/tests/test_sample.py:1 uses absolute helpers import
.pytest_tmp_fresh/test_project_hygiene_audit_pro0/project/SampleModule/tests has helpers.py but no __init__.py
.pytest_tmp_fresh/test_project_hygiene_audit_pro0/project/SampleModule/tests/test_sample.py:1 uses absolute helpers import

```

- **passed** `check_requirements`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe tools/check_requirements.py --project-root .`
- **passed** `compileall_core_modules`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m compileall -q ESGInformationExtraction ESGCSVExtraction ESGVisualExtraction ESGTableExtraction ESGExtractionOrchestrator ESGIndicatorValidation ESGManualReview ESGIndicatorDatabase ESGProductionControlCenter`
- **passed** `pytest_ESGInformationExtraction`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m pytest ESGInformationExtraction/tests --basetemp C:\Users\hp\AppData\Local\Temp\esg_pytest_validation_tvb096gn\validation_ESGInformationExtraction`
- **passed** `pytest_ESGCSVExtraction`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m pytest ESGCSVExtraction/tests --basetemp C:\Users\hp\AppData\Local\Temp\esg_pytest_validation_tvb096gn\validation_ESGCSVExtraction`
- **passed** `pytest_ESGVisualExtraction`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m pytest ESGVisualExtraction/tests --basetemp C:\Users\hp\AppData\Local\Temp\esg_pytest_validation_tvb096gn\validation_ESGVisualExtraction`
- **passed** `pytest_ESGTableExtraction`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m pytest ESGTableExtraction/tests --basetemp C:\Users\hp\AppData\Local\Temp\esg_pytest_validation_tvb096gn\validation_ESGTableExtraction`
- **passed** `pytest_ESGExtractionOrchestrator`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m pytest ESGExtractionOrchestrator/tests --basetemp C:\Users\hp\AppData\Local\Temp\esg_pytest_validation_tvb096gn\validation_ESGExtractionOrchestrator`
- **passed** `pytest_ESGIndicatorValidation`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m pytest ESGIndicatorValidation/tests --basetemp C:\Users\hp\AppData\Local\Temp\esg_pytest_validation_tvb096gn\validation_ESGIndicatorValidation`
- **passed** `pytest_ESGManualReview`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m pytest ESGManualReview/tests --basetemp C:\Users\hp\AppData\Local\Temp\esg_pytest_validation_tvb096gn\validation_ESGManualReview`
- **passed** `pytest_ESGIndicatorDatabase`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m pytest ESGIndicatorDatabase/tests --basetemp C:\Users\hp\AppData\Local\Temp\esg_pytest_validation_tvb096gn\validation_ESGIndicatorDatabase`
- **passed** `pytest_ESGProductionControlCenter`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m pytest ESGProductionControlCenter/tests --basetemp C:\Users\hp\AppData\Local\Temp\esg_pytest_validation_tvb096gn\validation_ESGProductionControlCenter`
- **passed** `pytest_retrievers`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m pytest AnnualReportRetriever/tests --basetemp C:\Users\hp\AppData\Local\Temp\esg_pytest_validation_tvb096gn\validation_retrievers`
- **passed** `pytest_global`: `C:\Users\hp\AppData\Local\Programs\Python\Python313\python.exe -m pytest --basetemp C:\Users\hp\AppData\Local\Temp\esg_pytest_validation_tvb096gn\validation_global`

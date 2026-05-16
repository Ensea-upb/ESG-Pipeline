# Validation Commands - ESGProductionControlCenter v1.1

```powershell
python -m compileall -q ESGProductionControlCenter ESGInformationExtraction ESGCSVExtraction ESGVisualExtraction ESGTableExtraction ESGExtractionOrchestrator ESGIndicatorValidation ESGManualReview ESGIndicatorDatabase
python -m pytest ESGProductionControlCenter/tests --basetemp <tmp>
python -m pytest ESGInformationExtraction/tests --basetemp <tmp>
python -m pytest ESGCSVExtraction/tests --basetemp <tmp>
python -m pytest ESGVisualExtraction/tests --basetemp <tmp>
python -m pytest ESGTableExtraction/tests --basetemp <tmp>
python -m pytest ESGExtractionOrchestrator/tests --basetemp <tmp>
python -m pytest ESGIndicatorValidation/tests --basetemp <tmp>
python -m pytest ESGManualReview/tests --basetemp <tmp>
python -m pytest ESGIndicatorDatabase/tests --basetemp <tmp>
streamlit run ESGProductionControlCenter/app.py
```

# ESGExtractionOrchestrator v1.0 - Validation Commands

```powershell
python -m compileall -q ESGExtractionOrchestrator ESGTableExtraction ESGVisualExtraction ESGCSVExtraction ESGInformationExtraction
python -m pytest ESGExtractionOrchestrator/tests --basetemp <tmp>
python -m pytest ESGTableExtraction/tests --basetemp <tmp>
python -m pytest ESGVisualExtraction/tests --basetemp <tmp>
python -m pytest ESGCSVExtraction/tests --basetemp <tmp>
python -m pytest ESGInformationExtraction/tests --basetemp <tmp>
python ESGExtractionOrchestrator/scripts/run_full_extraction.py `
  --input-dir "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test" `
  --output-dir "ESGExtractionOrchestrator/outputs/lvmh_full_v10_test" `
  --overwrite
python ESGExtractionOrchestrator/scripts/validate_full_extraction_outputs.py `
  --output-dir "ESGExtractionOrchestrator/outputs/lvmh_full_v10_test" `
  --contract-path "ESGExtractionOrchestrator/contracts/full_extraction_output_contract_v0.json"
```

# ESGTableExtraction v1.0 - Validation Commands

```powershell
python -m compileall -q ESGTableExtraction ESGVisualExtraction ESGCSVExtraction ESGInformationExtraction
python -m pytest ESGTableExtraction/tests --basetemp <tmp>
python -m pytest ESGVisualExtraction/tests --basetemp <tmp>
python -m pytest ESGCSVExtraction/tests --basetemp <tmp>
python -m pytest ESGInformationExtraction/tests --basetemp <tmp>
python ESGTableExtraction/scripts/run_table_extraction.py `
  --input-dir "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test" `
  --output-dir "ESGTableExtraction/outputs/lvmh_table_v10_test" `
  --overwrite
python ESGTableExtraction/scripts/validate_table_outputs.py `
  --output-dir "ESGTableExtraction/outputs/lvmh_table_v10_test" `
  --contract-path "ESGTableExtraction/contracts/table_output_contract_v0.json"
```

# ESGProductionControlCenter Validation Commands v1.0

```powershell
python -m compileall -q ESGProductionControlCenter ESGInformationExtraction ESGCSVExtraction ESGVisualExtraction ESGTableExtraction ESGExtractionOrchestrator ESGIndicatorValidation ESGManualReview ESGIndicatorDatabase
python -m pytest ESGProductionControlCenter/tests --basetemp <tmp>
python ESGProductionControlCenter/scripts/run_control_center.py --input-dir "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test" --output-dir "ESGProductionControlCenter/outputs/lvmh_control_center_v10_test" --dry-run --overwrite
python ESGProductionControlCenter/scripts/validate_control_center_outputs.py --output-dir "ESGProductionControlCenter/outputs/lvmh_control_center_v10_test" --contract-path "ESGProductionControlCenter/contracts/control_center_output_contract_v0.json"
streamlit run ESGProductionControlCenter/app.py
```

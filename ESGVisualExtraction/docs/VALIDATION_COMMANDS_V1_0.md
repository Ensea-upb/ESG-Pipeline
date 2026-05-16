# ESGVisualExtraction v1.0 - Validation Commands

## Compile

```powershell
python -m compileall -q ESGVisualExtraction ESGCSVExtraction ESGInformationExtraction
```

## Tests

```powershell
python -m pytest ESGVisualExtraction/tests --basetemp <tmp>
python -m pytest ESGCSVExtraction/tests --basetemp <tmp>
python -m pytest ESGInformationExtraction/tests --basetemp <tmp>
```

## Manual LVMH Run

```powershell
python ESGVisualExtraction/scripts/run_visual_extraction.py `
  --input-dir "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test" `
  --output-dir "ESGVisualExtraction/outputs/lvmh_visual_v10_test" `
  --overwrite
```

## Contract Validation

```powershell
python ESGVisualExtraction/scripts/validate_visual_outputs.py `
  --output-dir "ESGVisualExtraction/outputs/lvmh_visual_v10_test" `
  --contract-path "ESGVisualExtraction/contracts/visual_output_contract_v0.json"
```

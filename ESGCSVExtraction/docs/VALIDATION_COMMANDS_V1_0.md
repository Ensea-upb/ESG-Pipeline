# ESGCSVExtraction v1.0 - Validation Commands

## Compile

```powershell
python -m compileall -q ESGCSVExtraction ESGInformationExtraction
```

## Test ESGCSVExtraction

```powershell
$bt = Join-Path (Resolve-Path .pytest_tmp).Path ('pytest_csv_' + [guid]::NewGuid().ToString())
python -m pytest ESGCSVExtraction/tests --basetemp $bt
```

## Test ESGInformationExtraction Regression Suite

```powershell
$bt = Join-Path (Resolve-Path .pytest_tmp).Path ('pytest_info_' + [guid]::NewGuid().ToString())
python -m pytest ESGInformationExtraction/tests --basetemp $bt
```

## Manual LVMH Candidate Extraction

```powershell
python ESGCSVExtraction/scripts/run_csv_extraction.py `
  --input-dir "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test" `
  --output-dir "ESGCSVExtraction/outputs/lvmh_v10_csv_test" `
  --overwrite
```

## CSV Contract Validation

```powershell
python ESGCSVExtraction/scripts/validate_csv_outputs.py `
  --output-dir "ESGCSVExtraction/outputs/lvmh_v10_csv_test" `
  --contract-path "ESGCSVExtraction/contracts/csv_output_contract_v0.json"
```

## Multi-document Audit

```powershell
python ESGCSVExtraction/scripts/run_multi_document_audit.py `
  --input-root "ESGInformationExtraction/outputs" `
  --output-dir "ESGCSVExtraction/outputs/multi_document_v10" `
  --overwrite
```

## Non-destructive Check

Hash the input directory before and after manual runs. The hash must stay identical because the engine writes only to `ESGCSVExtraction/outputs`.

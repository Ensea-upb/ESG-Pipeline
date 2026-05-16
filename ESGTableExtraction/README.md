# ESGTableExtraction

`ESGTableExtraction` is a separate candidate-only table extraction module.

It reads `table_index.jsonl` and `table_cells.jsonl` produced by `ESGInformationExtraction`, reconstructs tables, detects simple structure, classifies ESG-relevant rows, and exports table metric candidates.

It does not modify source outputs, PDFs, manifests, or other ESG modules. It does not produce scores or validated ESG indicators.

## Run

```powershell
python ESGTableExtraction/scripts/run_table_extraction.py `
  --input-dir "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test" `
  --output-dir "ESGTableExtraction/outputs/lvmh_table_v10_test" `
  --overwrite
```

## Validate

```powershell
python ESGTableExtraction/scripts/validate_table_outputs.py `
  --output-dir "ESGTableExtraction/outputs/lvmh_table_v10_test" `
  --contract-path "ESGTableExtraction/contracts/table_output_contract_v0.json"
```

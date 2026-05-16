# Table Output Contract v0

`ESGTableExtraction` reads table outputs from `ESGInformationExtraction` and creates candidate-only table metrics.

## Required Rules

- All rows are `candidate_only`.
- All rows have `review_required=true`.
- Confidence is capped at `0.6`.
- No score or validated metric is produced.
- Each candidate keeps `document_id`, `table_id`, `cell_id`, `page_number`, `row_index`, and `column_index`.

## Validation

```powershell
python ESGTableExtraction/scripts/validate_table_outputs.py `
  --output-dir "ESGTableExtraction/outputs/lvmh_table_v10_test" `
  --contract-path "ESGTableExtraction/contracts/table_output_contract_v0.json"
```

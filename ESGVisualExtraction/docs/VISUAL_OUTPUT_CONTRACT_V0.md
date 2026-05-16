# Visual Output Contract v0

`ESGVisualExtraction` produces candidate-only visual outputs from `ESGInformationExtraction` figures and page-level visuals.

## Required Outputs

- `visual_input_inventory.json`
- `visual_items.jsonl`
- `visual_crops_index.jsonl`
- `visual_ocr_outputs.jsonl`
- `visual_ocr_summary.json`
- `visual_classification.jsonl`
- `visual_classification_summary.json`
- `visual_candidates.csv`
- `visual_candidates.jsonl`
- `visual_audit_summary.json`
- `visual_audit_findings.jsonl`
- `visual_audit_samples.csv`
- `visual_extraction_summary.json`

## Candidate Rules

- `review_required` must be `True`.
- `extraction_status` must be `candidate_only`.
- `confidence` must be less than or equal to `0.5`.
- Every candidate must retain `document_id`, `figure_id`, `page_number`, and `source_image_path`.
- No score or validated ESG metric is produced.

## Validation

```powershell
python ESGVisualExtraction/scripts/validate_visual_outputs.py `
  --output-dir "ESGVisualExtraction/outputs/lvmh_visual_v10_test" `
  --contract-path "ESGVisualExtraction/contracts/visual_output_contract_v0.json"
```

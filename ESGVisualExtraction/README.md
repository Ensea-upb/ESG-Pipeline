# ESGVisualExtraction

`ESGVisualExtraction` is a separate candidate-only visual layer for the ESG project.

It reads figures and visual page candidates already detected by `ESGInformationExtraction`, creates non-destructive crops when possible, applies optional OCR, classifies visual objects, and exports visual ESG candidates for human review.

It does not validate ESG indicators, produce scores, run RAG, require an LLM, modify PDFs, or modify source documentary outputs.

## Command

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

## Scope

All results are `candidate_only`, all rows have `review_required=true`, and all visual confidence values are capped at `0.5`.

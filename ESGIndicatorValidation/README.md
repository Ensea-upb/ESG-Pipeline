# ESGIndicatorValidation

Candidate-only validation layer for consolidated ESG extraction outputs.

This module reads `ESGExtractionOrchestrator` outputs and produces an audited pre-validation table. It does not create validated ESG indicators, scores, ratings, or final metrics. Every row remains `candidate_only` and `review_required=true`.

## v1.0

Input:

- `consolidated_unique_candidates.csv` when available
- fallback: `consolidated_candidates.csv`

Outputs:

- `indicator_candidate_validations.csv`
- `indicator_candidate_validations.jsonl`
- `indicator_validation_audit_summary.json`
- `indicator_validation_audit_findings.jsonl`
- `indicator_validation_summary.json`
- `possible_indicators.csv`
- `rejected_candidates.csv`
- `validation_review_queue.csv/jsonl`
- `normalized_indicator_candidates.csv`
- `indicator_duplicate_groups.jsonl`
- `indicator_candidate_validations_deduplicated.csv/jsonl`

`possible_indicator` is not a validated ESG indicator. It only means the candidate is structured enough for human review.

Example:

```powershell
python ESGIndicatorValidation/scripts/run_indicator_validation.py `
  --input-dir "ESGExtractionOrchestrator/outputs/lvmh_full_v11_test" `
  --output-dir "ESGIndicatorValidation/outputs/lvmh_indicator_v01_test" `
  --overwrite
```

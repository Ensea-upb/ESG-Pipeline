# ESGIndicatorDatabase

Preparation-only ESG indicator database builder.

This module reads `ESGManualReview` outputs and builds a structured preparation database from `accepted_candidate_inputs.csv`. It does not produce final validated ESG indicators, ESG scores, ratings, or a final indicator database.

`accepted_candidate` is not `validated_final_indicator`.

## v1.0

```powershell
python ESGIndicatorDatabase/scripts/build_indicator_database.py `
  --input-dir "ESGManualReview/outputs/lvmh_manual_review_applied_v10_test" `
  --output-dir "ESGIndicatorDatabase/outputs/lvmh_indicator_database_v10_test" `
  --overwrite
```

```powershell
python ESGIndicatorDatabase/scripts/validate_indicator_database_outputs.py `
  --output-dir "ESGIndicatorDatabase/outputs/lvmh_indicator_database_v10_test" `
  --contract-path "ESGIndicatorDatabase/contracts/indicator_database_contract_v0.json"
```

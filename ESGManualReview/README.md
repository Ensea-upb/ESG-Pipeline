# ESGManualReview

Human-in-the-loop review workspace for `ESGIndicatorValidation` outputs.

This module does not produce final ESG indicators, ESG scores, ratings, or a final indicator database. It only builds auditable review workspaces and applies explicit reviewer decisions while preserving source traceability.

## v1.0

Main commands:

```powershell
python ESGManualReview/scripts/build_review_workspace.py `
  --input-dir "ESGIndicatorValidation/outputs/lvmh_indicator_validation_v10_test" `
  --output-dir "ESGManualReview/outputs/lvmh_manual_review_v10_test" `
  --overwrite
```

```powershell
python ESGManualReview/scripts/apply_review_decisions.py `
  --workspace-dir "ESGManualReview/outputs/lvmh_manual_review_v10_test" `
  --decisions-file "ESGManualReview/outputs/lvmh_manual_review_v10_test/review_decisions_template.csv" `
  --output-dir "ESGManualReview/outputs/lvmh_manual_review_applied_v10_test" `
  --overwrite
```

`accept_candidate` means accepted for a future preparation layer. It is not a validated ESG indicator.

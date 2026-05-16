# Full Extraction Output Contract v0

The full orchestrator consolidates candidate-only outputs from:

- `ESGCSVExtraction`
- `ESGVisualExtraction`
- `ESGTableExtraction`

All consolidated rows must keep traceability fields and remain:

- `review_required=True`
- `extraction_status=candidate_only`

No ESG score or validated indicator is produced.

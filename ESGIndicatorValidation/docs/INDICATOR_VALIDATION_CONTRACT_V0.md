# Indicator Validation Contract v0

`ESGIndicatorValidation v1.0` is a pre-validation layer for consolidated ESG candidates.

It does **not** produce validated ESG indicators, final metrics, ESG scores, ratings, RAG, OCR, or LLM output.

Required outputs:

- `indicator_candidate_validations.csv/jsonl`
- `possible_indicators.csv`
- `rejected_candidates.csv`
- `validation_review_queue.csv/jsonl`
- `normalized_indicator_candidates.csv`
- `indicator_duplicate_groups.jsonl`
- `indicator_candidate_validations_deduplicated.csv/jsonl`
- `indicator_validation_audit_summary.json`
- `indicator_validation_audit_findings.jsonl`
- `indicator_validation_audit_samples.csv`
- `indicator_validation_summary.json`

Hard invariants:

- `review_required=True`
- `extraction_status=candidate_only`
- `validation_status` is one of `needs_review`, `possible_indicator`, `reject_candidate`
- `is_validated_indicator=False`
- `score_produced=False`
- `confidence <= 0.5`
- `possible_indicator` means candidate for human review, not validated indicator

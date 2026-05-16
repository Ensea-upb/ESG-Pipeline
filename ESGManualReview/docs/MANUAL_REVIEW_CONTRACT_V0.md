# Manual Review Contract v0

`ESGManualReview v1.0` creates a human review workspace and applies explicit reviewer decisions.

Hard rules:

- no final ESG indicator is produced;
- `accepted_candidate` is not `validated_indicator`;
- `validated_indicator=False` everywhere;
- `score_produced=False` everywhere;
- raw values and corrected values are stored separately;
- traceability fields are required: `candidate_id`, `document_id`, `page_number`, `quote`.

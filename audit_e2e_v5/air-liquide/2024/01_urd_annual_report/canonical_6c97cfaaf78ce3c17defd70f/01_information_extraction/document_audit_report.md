# Document Audit Report

## 1. Document identity
- document_id: canonical_6c97cfaaf78ce3c17defd70f
- pdf_path: C:\Users\hp\Desktop\ESG\ESGFinalCorpus\air-liquide\2024\01_urd_annual_report\document.pdf
- sha256: 6b522790fa357c4e454cafb605fad1ad3a448ff405985db5ac3e7de01014ab1f
- pages_processed / page_count: 57 / 57

## 2. Extraction status
- status: success
- errors_count: 0
- warnings_count: 176
- extraction_readiness_status: partially_ready
- extraction_readiness_reasons: ['many_review_or_quarantined_evidences']

## 3. Document structure
- pages: 57
- text blocks: 4077
- sections: 35
- suspicious sections: 0

## 4. Evidence overview
- total evidences: 879
- evidences by modality: {'text': 516, 'table': 74, 'figure': 289}
- evidences by type: {'section_heading': 35, 'paragraph': 481, 'table': 74, 'figure': 289}
- evidence_policy_distribution: {'normal': 878, 'review_required': 1}
- downstream_use_policy_distribution: {'eligible_for_future_extraction': 334, 'review_before_extraction': 518, 'exclude_from_automatic_extraction': 27}

Clarification: normal_evidence_count corresponds to evidence_policy = normal. review_required_evidence_count corresponds to the review_required flag. These categories can overlap. quarantine means retained for traceability but excluded from automatic extraction.

## 5. Tables audit
- tables_count: 105
- parsed_tables_count: 33
- low_confidence_tables_count: 58
- empty_tables_count: 14
- table_artifact_suspected_count: 26
- failed_tables_count: 0
Tables are detected as documentary objects only; cell values are not interpreted.

## 6. Figures audit
- figures_count: 289
- page_level_visual_count: 0
- embedded_visual_count: 289
- captioned_figure_count: 0
- failed_figures_count: 0
Figures and visual pages are localized or flagged only; graph values are not read.

## 7. Suspicious sections
No suspicious section detected.

## 8. Readiness decision
Decision: **partially_ready**.
Reasons: ['many_review_or_quarantined_evidences'].
For partially_ready documents, usable evidence exists but some zones remain under human review.

## 9. Limitations
- No ESG extraction was performed.
- No ESG value was validated.
- No graph value was read.
- No table cell was interpreted.
- No ESG scoring was produced.

## 10. Recommended next step
Review critical and major findings first, then inspect suspicious sections before any future ESG extraction prototype.

## Audit summary
- audit_overall_status: warning
- findings_count: 9

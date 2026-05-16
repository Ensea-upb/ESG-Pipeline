# Document Audit Report

## 1. Document identity
- document_id: e2e_v09_totalenergies_2024
- pdf_path: C:\Users\hp\Desktop\ESG\ESGFinalCorpus\totalenergies\2024\02_sustainability_statement_csrd_esrs\document.pdf
- sha256: c0294fa903042125e9347c0592847defd97f5da88182a640162598828d33b4f0
- pages_processed / page_count: 50 / 680

## 2. Extraction status
- status: success
- errors_count: 0
- warnings_count: 212
- extraction_readiness_status: partially_ready
- extraction_readiness_reasons: ['many_review_or_quarantined_evidences']

## 3. Document structure
- pages: 50
- text blocks: 2858
- sections: 25
- suspicious sections: 0

## 4. Evidence overview
- total evidences: 1163
- evidences by modality: {'text': 579, 'table': 94, 'figure': 490}
- evidences by type: {'section_heading': 25, 'paragraph': 554, 'table': 94, 'figure': 490}
- evidence_policy_distribution: {'normal': 1163}
- downstream_use_policy_distribution: {'review_before_extraction': 689, 'eligible_for_future_extraction': 446, 'exclude_from_automatic_extraction': 28}

Clarification: normal_evidence_count corresponds to evidence_policy = normal. review_required_evidence_count corresponds to the review_required flag. These categories can overlap. quarantine means retained for traceability but excluded from automatic extraction.

## 5. Tables audit
- tables_count: 113
- parsed_tables_count: 24
- low_confidence_tables_count: 71
- empty_tables_count: 18
- table_artifact_suspected_count: 30
- failed_tables_count: 0
Tables are detected as documentary objects only; cell values are not interpreted.

## 6. Figures audit
- figures_count: 490
- page_level_visual_count: 0
- embedded_visual_count: 490
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

# Document Audit Report

## 1. Document identity
- document_id: e2e_lvmh_2024_sustain
- pdf_path: C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf
- sha256: 4e67ffaaae7f880fd24e837c30f10c08b0a087ca1b4314dade86e7b5d32c12cb
- pages_processed / page_count: 30 / 484

## 2. Extraction status
- status: success
- errors_count: 0
- warnings_count: 85
- extraction_readiness_status: partially_ready
- extraction_readiness_reasons: ['suspicious_sections_present']

## 3. Document structure
- pages: 30
- text blocks: 1467
- sections: 5
- suspicious sections: 1

## 4. Evidence overview
- total evidences: 283
- evidences by modality: {'text': 250, 'table': 29, 'figure': 4}
- evidences by type: {'section_heading': 5, 'paragraph': 245, 'table': 29, 'figure': 4}
- evidence_policy_distribution: {'quarantine': 10, 'normal': 273}
- downstream_use_policy_distribution: {'exclude_from_automatic_extraction': 13, 'eligible_for_future_extraction': 206, 'review_before_extraction': 64}

Clarification: normal_evidence_count corresponds to evidence_policy = normal. review_required_evidence_count corresponds to the review_required flag. These categories can overlap. quarantine means retained for traceability but excluded from automatic extraction.

## 5. Tables audit
- tables_count: 37
- parsed_tables_count: 13
- low_confidence_tables_count: 17
- empty_tables_count: 7
- table_artifact_suspected_count: 16
- failed_tables_count: 0
Tables are detected as documentary objects only; cell values are not interpreted.

## 6. Figures audit
- figures_count: 4
- page_level_visual_count: 4
- embedded_visual_count: 0
- captioned_figure_count: 0
- failed_figures_count: 0
Figures and visual pages are localized or flagged only; graph values are not read.

## 7. Suspicious sections
- section_id: e2e_lvmh_2024_sustain_section_0001
- section_title: REPORT ON THE CERTIFICATION OF SUSTAINABILITY REPORTING
- reasons: ['unknown_section_type', 'front_matter_section', 'title_content_mismatch']
- evidence_policy: quarantine
- sample quotes: ['As table totals are based on unrounded figures, there may be discrepancies between these totals and the sum of their rounded component figures.', 'This document is a free translation into English of the original French “Document d’enregistrement universel”, hereafter referred to as the “Universal Registration Document”. It is not a binding docum', 'Although the history of the LVMH Group began in 1987 with the merger of Moët Hennessy and Louis Vuitton, the roots of the Group actually stretch back much further, to eighteenth‑century Champagne, whe', 'global Group in which the historic companies share their expertise with the newer brands, and continue to cultivate the art of growing while transcending time, without losing their soul or their image', 'From the 14th century to the present']

## 8. Readiness decision
Decision: **partially_ready**.
Reasons: ['suspicious_sections_present'].
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
- audit_overall_status: fail
- findings_count: 13

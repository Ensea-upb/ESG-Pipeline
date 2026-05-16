# Document Audit Report

## 1. Document identity
- document_id: schneider_electric_2024_csrd_v5
- pdf_path: C:\Users\hp\Desktop\ESG\ESGFinalCorpus\schneider-electric\2024\02_sustainability_statement_csrd_esrs\document.pdf
- sha256: 89d162c4a20b0b532fd6c15021ed8bf6cf65551b34fa5c5a0b757b0fa03ce25d
- pages_processed / page_count: 676 / 676

## 2. Extraction status
- status: success
- errors_count: 0
- warnings_count: 2202
- extraction_readiness_status: partially_ready
- extraction_readiness_reasons: ['many_review_or_quarantined_evidences']

## 3. Document structure
- pages: 676
- text blocks: 46439
- sections: 324
- suspicious sections: 2

## 4. Evidence overview
- total evidences: 10307
- evidences by modality: {'text': 8717, 'table': 1088, 'figure': 502}
- evidences by type: {'section_heading': 324, 'paragraph': 8393, 'table': 1088, 'figure': 502}
- evidence_policy_distribution: {'review_required': 853, 'normal': 9454}
- downstream_use_policy_distribution: {'review_before_extraction': 4044, 'eligible_for_future_extraction': 6010, 'exclude_from_automatic_extraction': 253}

Clarification: normal_evidence_count corresponds to evidence_policy = normal. review_required_evidence_count corresponds to the review_required flag. These categories can overlap. quarantine means retained for traceability but excluded from automatic extraction.

## 5. Tables audit
- tables_count: 1148
- parsed_tables_count: 331
- low_confidence_tables_count: 763
- empty_tables_count: 54
- table_artifact_suspected_count: 126
- failed_tables_count: 0
Tables are detected as documentary objects only; cell values are not interpreted.

## 6. Figures audit
- figures_count: 502
- page_level_visual_count: 0
- embedded_visual_count: 498
- captioned_figure_count: 4
- failed_figures_count: 0
Figures and visual pages are localized or flagged only; graph values are not read.

## 7. Suspicious sections
- section_id: schneider_electric_2024_csrd_v5_section_0092
- section_title: 83 000 heures de
- reasons: ['unknown_section_type', 'high_evidence_density', 'weak_heading_confidence', 'section_too_long']
- evidence_policy: review_required
- sample quotes: ['se.com Life Is On | Schneider Electric 233', 'Les principaux programmes axés sur la mise à niveau des compétences essentielles incluent : Intitulé du Description du Description du programme et Impact quantitatif et programme public cible avantage', 'pour tous les Achèvement et numérique de l’entreprise et la durabilité de l’emploi conduites appropriées dans un employés progression à des collaborateurs. Il repose sur un programme environnement num', 'portant sur les permettant aux collaborateurs d’être informés des mondiale de la solution de perfectionnement six compétences tendances numériques décisives et de découvrir des compétences du Groupe a', 'compétences dans des résultats de l’évaluation individuelle afin de responsables hiérarchiques et la Direction, ce domaine. faciliter le perfectionnement continu des en les aidant à cibler les actions']

- section_id: schneider_electric_2024_csrd_v5_section_0134
- section_title: 404-1 Répartition des heures par catégorie
- reasons: ['unknown_section_type', 'high_evidence_density', 'weak_heading_confidence', 'section_too_long']
- evidence_policy: review_required
- sample quotes: ['Cols blancs % 55 % 57 % 57 % 53 % Cols bleus % 45 % 43 % 43 % 47 %', "2-24 Pourcentage de salariés formés à la Charte de 99 % 99 % 98 % 96 % confiance, le Code de conduite de Schneider 2-24 Pourcentage de l'effectif éligible ayant reçu une % 99 % 98 % 97 % 97 % formatio", "Produits, Solutions et Services % 13 % 13 % 14 % 12 % Chaîne d'approvisionnement % 7 % 9 % 9 % 12 %", 'Dépenses totales pour le développement et la million € 105,7 91,1 75,6 56,8', 'Dépenses totales pour le développement et la €/employé 718,2 660,8 560,8 425,8']

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
- findings_count: 10

# ESGInformationExtraction v1.4 - Release Notes

## Resume

La release v1.4 stabilise le moteur documentaire PDF et ses outils d'audit batch jusqu'a la production d'une checklist d'execution humaine.

Cette version reste strictement documentaire. Elle transforme des PDFs en objets audites, verifie la coherence des outputs, controle leur compatibilite avec le contrat v1.0, propose un plan de remediation et produit une checklist ordonnee. Elle ne fait aucune extraction ESG metier.

## Fonctionnalites principales

- Extraction documentaire PDF en lecture seule.
- Production d'outputs structures : pages, blocs de texte, sections, evidences documentaires, tableaux, figures, inventaire multimodal.
- Audit inter-fichiers et rapport humain.
- Validation du contrat de sortie v1.0.
- Audit standalone sans reparser le PDF.
- Compatibilite des anciens outputs.
- Scanner batch de compatibilite.
- Plan de remediation batch.
- Checklist d'execution batch avec priorites humaines.

## Fichiers produits par le moteur documentaire

- `document_record.json`
- `page_index.jsonl`
- `text_blocks.jsonl`
- `text_block_statistics.json`
- `section_candidates.jsonl`
- `section_index.jsonl`
- `section_statistics.json`
- `suspicious_sections.jsonl`
- `evidence_store.jsonl`
- `evidence_statistics.json`
- `table_index.jsonl`
- `table_cells.jsonl`
- `table_statistics.json`
- `figure_index.jsonl`
- `figure_statistics.json`
- `document_inventory.json`
- `multimodal_evidence_index.jsonl`
- `multimodal_statistics.json`
- `consistency_report.json`
- `audit_findings.jsonl`
- `document_audit_report.md`
- `quality_report.jsonl`
- `extraction_summary.json`

## Fichiers batch v1.4

Dans `ESGInformationExtraction/outputs/batch_compatibility_report/` :

- `batch_compatibility_summary.json`
- `batch_compatibility_table.csv`
- `batch_compatibility_report.md`
- `batch_remediation_plan.json`
- `batch_remediation_plan.csv`
- `batch_remediation_plan.md`
- `batch_execution_checklist.json`
- `batch_execution_checklist.csv`
- `batch_execution_checklist.md`

## Garanties non destructives

- Les PDFs sources ne sont jamais modifies.
- `ESGFinalCorpus` n'est pas modifie.
- Les manifests sources ne sont pas modifies.
- Les outils batch ne modifient pas les outputs scannes.
- Les commandes recommandees dans la checklist ne sont jamais executees automatiquement.
- Aucune regeneration d'output n'est lancee par le batch.

## Tests actuels

Derniere validation connue :

- `228 passed`
- `0 failed`
- `0 errors`

Un avertissement pytest peut apparaitre si le cache `.pytest_cache` n'est pas accessible. Il ne concerne pas le moteur.

## Limites restantes

- Les tableaux sont structures, mais leurs valeurs ne sont pas interpretees.
- Les figures et graphiques sont localises, mais les valeurs graphiques ne sont pas lues.
- Les sections suspectes sont conservees et marquees, pas corrigees automatiquement.
- Les outputs incompatibles doivent etre regeneres manuellement si necessaire.
- Les commandes de remediation restent consultatives.

## Ce que le moteur ne fait pas encore

- Pas d'extraction ESG.
- Pas de metriques ESG validees.
- Pas d'indicateurs.
- Pas de scoring.
- Pas de RAG.
- Pas de base vectorielle.
- Pas de LLM.
- Pas d'OCR massif.
- Pas d'interpretation metier des tableaux ou figures.

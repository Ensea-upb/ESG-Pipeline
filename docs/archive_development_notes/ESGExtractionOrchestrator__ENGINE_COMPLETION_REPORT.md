# ESGExtractionOrchestrator - Engine Completion Report

## Version Finale Atteinte

Version finale : v1.1.

Statut : passed avec un warning d'audit consolide non bloquant.

## Fichiers Crees / Modifies

- `ESGExtractionOrchestrator/README.md`
- `ESGExtractionOrchestrator/AGENT_DELIVERY_REPORT.md`
- `ESGExtractionOrchestrator/ENGINE_COMPLETION_REPORT.md`
- `ESGExtractionOrchestrator/scripts/run_full_extraction.py`
- `ESGExtractionOrchestrator/scripts/validate_full_extraction_outputs.py`
- `ESGExtractionOrchestrator/scripts/run_multi_document_full_extraction.py`
- `ESGExtractionOrchestrator/src/esg_extraction_orchestrator/*`
- `ESGExtractionOrchestrator/contracts/full_extraction_output_contract_v0.json`
- `ESGExtractionOrchestrator/docs/*`
- `ESGExtractionOrchestrator/tests/test_full_orchestrator_v10.py`
- `ESGExtractionOrchestrator/tests/test_full_orchestrator_v11.py`

## v1.1 - Stabilisation Entree Consolidee

La v1.1 ajoute un cache controle des sous-moteurs et une deduplication auditee :

- `--reuse-existing` reutilise les outputs `csv/`, `visual/`, `table/` deja presents.
- `--force-rerun` force une nouvelle execution.
- `consolidated_candidates.csv/jsonl` conserve tous les candidats.
- `consolidated_unique_candidates.csv/jsonl` expose la vue canonique candidate-only.
- `consolidated_duplicate_groups.csv/jsonl` documente chaque groupe de doublons.
- Aucun candidat n'est supprime silencieusement.

## Tests Executes

- `python -m compileall -q ESGExtractionOrchestrator ESGTableExtraction ESGVisualExtraction ESGCSVExtraction ESGInformationExtraction` : OK.
- `ESGExtractionOrchestrator/tests` : 10 passed.
- `ESGTableExtraction/tests` : 13 passed.
- `ESGVisualExtraction/tests` : 14 passed.
- `ESGCSVExtraction/tests` : 31 passed.
- `ESGInformationExtraction/tests` : 228 passed.

Warnings : cache pytest inaccessible uniquement.

## Test Manuel LVMH

Commande :

```powershell
python ESGExtractionOrchestrator/scripts/run_full_extraction.py `
  --input-dir "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test" `
  --output-dir "ESGExtractionOrchestrator/outputs/lvmh_full_v10_test" `
  --overwrite
```

Resultats :

- candidats texte / CSV : 109
- candidats visuels : 3
- candidats tableaux : 2
- candidats consolides : 114
- candidats uniques canoniques : 112
- candidats doublons retenus pour audit : 2
- groupes de doublons : 2
- erreurs audit consolide : 0
- warnings audit consolide : 2
- second run `--reuse-existing` : `csv`, `visual`, `table` reutilises depuis les sous-dossiers existants.

## Audit Consolide

Distribution source :

```text
csv: 109
visual: 3
table: 2
```

Distribution information_type :

```text
boundary_context: 37
observed_metric: 26
policy_or_commitment: 16
methodology_context: 3
target: 7
risk_statement: 2
visual_evidence: 18
visual_metric_candidate: 2
visual_context_evidence: 1
table_metric_candidate: 2
```

Checks :

```text
review_required_missing_or_false: 0
extraction_status_not_candidate_only: 0
confidence_above_allowed_threshold: 0
score_column_detected: 0
validated_indicator_detected: 0
probable_duplicates: 4
deduplicated_duplicate_candidates: 2
source_engine_information_type_mismatch: 0
candidates_without_source: 0
candidates_without_quote: 0
```

## Validation Contrat

```text
status: success
contract_version: 0.6.0
checks_count: 124
errors_count: 0
warnings_count: 0
```

## Preuve Non Destructive

```text
files_hashed: 23
digest_before: 0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee
digest_after:  0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee
```

v1.1 :

```text
files_hashed: 23
digest_before: b51286fa9b0cccd970a478a8a94e9700d5a528f5dae528fb09c01faf6fb0d652
digest_after:  b51286fa9b0cccd970a478a8a94e9700d5a528f5dae528fb09c01faf6fb0d652
```

## Limites Restantes

- Le run complet peut relancer les moteurs sous-jacents ; utiliser `--reuse-existing` pour les executions d'audit rapides.
- Les candidats restent bruts et a revue humaine.
- Les doublons probables sont marques et une vue canonique est produite, mais aucune fusion metier definitive n'est faite.
- Aucun indicateur ESG n'est valide.

## Recommandation

Prochaine etape : v1.1 avec cache optionnel des sous-moteurs, reutilisation d'outputs deja generes, et deduplication candidate-only auditee.

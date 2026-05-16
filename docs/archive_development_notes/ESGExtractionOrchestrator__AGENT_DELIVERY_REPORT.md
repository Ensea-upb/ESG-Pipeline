# ESGExtractionOrchestrator - Agent Delivery Report

## Versions Validees

- v0.1 : runner simple `ESGCSVExtraction`.
- v0.2 : runner complet `csv/`, `visual/`, `table/`.
- v0.3 : consolidation `consolidated_candidates.csv/jsonl`.
- v0.4 : audit consolide.
- v0.5 : rapport humain `full_extraction_report.md`.
- v0.6 : contrat de sortie et validateur.
- v0.7 : multi-document.
- v1.0 : release stable documentee.
- v1.1 : cache optionnel des sous-moteurs, reutilisation controlee, deduplication candidate-only auditee.

## Fichiers Crees

- `scripts/run_full_extraction.py`
- `scripts/validate_full_extraction_outputs.py`
- `scripts/run_multi_document_full_extraction.py`
- `src/esg_extraction_orchestrator/*`
- `contracts/full_extraction_output_contract_v0.json`
- `docs/FULL_EXTRACTION_OUTPUT_CONTRACT_V0.md`
- `docs/RELEASE_NOTES_V1_0.md`
- `docs/ARCHITECTURE_OVERVIEW_V1_0.md`
- `docs/VALIDATION_COMMANDS_V1_0.md`
- `tests/test_full_orchestrator_v10.py`
- `tests/test_full_orchestrator_v11.py`

## v1.1 - Changements

- Ajout de `--reuse-existing` pour reutiliser les sous-dossiers `csv/`, `visual/`, `table/` quand les fichiers attendus existent.
- Ajout de `--force-rerun` pour forcer la reexecution des sous-moteurs.
- Ajout d'un `engine_run_manifest` dans `full_extraction_summary.json`.
- Ajout des champs `source_information_type`, `normalized_candidate_key`, `deduplication_group_id`, `deduplication_status`, `canonical_candidate_id`, `duplicate_reason`.
- Ajout de `consolidated_unique_candidates.csv/jsonl`.
- Ajout de `consolidated_duplicate_groups.csv/jsonl`.
- Les doublons restent dans `consolidated_candidates.csv/jsonl` et sont seulement marques pour audit.

## Tests Executes

- `compileall` : passed.
- `ESGExtractionOrchestrator/tests` : 10 passed.
- `ESGTableExtraction/tests` : 13 passed.
- `ESGVisualExtraction/tests` : 14 passed.
- `ESGCSVExtraction/tests` : 31 passed.
- `ESGInformationExtraction/tests` : 228 passed.

## Test Manuel LVMH

Output :

```text
ESGExtractionOrchestrator/outputs/lvmh_full_v10_test
```

Resultats :

- CSV candidates : 109
- Visual candidates : 3
- Table candidates : 2
- Consolidated candidates : 114
- Audit errors : 0
- Audit warnings : 1

Distribution source :

```text
csv: 109
visual: 3
table: 2
```

v1.1 reuse/cache :

```text
consolidated_candidates_count: 114
unique_candidates_count: 112
duplicate_candidates_count: 2
duplicate_groups_count: 2
engine statuses after second --reuse-existing run:
  csv: reused_existing
  visual: reused_existing
  table: reused_existing
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

## Validation Contrat

```text
status: success
contract_version: 0.6.0
checks_count: 124
errors_count: 0
warnings_count: 0
```

## Preuve Non Destructive

Input LVMH :

```text
files_hashed: 23
digest_before: 0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee
digest_after:  0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee
```

v1.1 LVMH input hash :

```text
files_hashed: 23
digest_before: b51286fa9b0cccd970a478a8a94e9700d5a528f5dae528fb09c01faf6fb0d652
digest_after:  b51286fa9b0cccd970a478a8a94e9700d5a528f5dae528fb09c01faf6fb0d652
```

## Decision

v1.1 est validee techniquement. Les resultats restent `candidate_only`, `review_required=true`, sans score ni indicateur valide.

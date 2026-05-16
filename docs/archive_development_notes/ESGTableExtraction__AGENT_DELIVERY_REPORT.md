# ESGTableExtraction - Agent Delivery Report

## Phase 0 - Inspection

Input reel inspecte :

```text
ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test
```

Fichiers consommes :

- `document_inventory.json`
- `extraction_summary.json`
- `table_index.jsonl`
- `table_cells.jsonl`
- `table_statistics.json`

Observation LVMH :

- tables : 28
- cellules : 4659
- statuts : `parsed`, `low_confidence`, `empty_table`
- nombreuses tables artefacts, front matter, organigrammes et cellules fragmentees.

## Versions Validees

### v0.1 - Loader table

Statut : passed.

Sorties :

- `table_input_inventory.json`
- `table_items.jsonl`
- `table_cells_loaded.jsonl`
- `table_extraction_summary.json`

### v0.2 - Reconstruction

Statut : passed.

Sorties :

- `reconstructed_tables.jsonl`
- `table_reconstruction_audit.jsonl`
- `table_reconstruction_summary.json`

### v0.3 - Structure table

Statut : passed.

Sorties :

- `table_structure_index.jsonl`
- `table_structure_summary.json`

### v0.4 - Classification lignes ESG

Statut : passed.

Sorties :

- `table_row_classification.jsonl`
- `table_row_classification_summary.json`

### v0.5 - Candidats metriques table

Statut : passed avec warnings metier.

Sorties :

- `table_metric_candidates.csv`
- `table_metric_candidates.jsonl`
- `table_candidate_extraction_summary.json`

### v0.6 - Audit table

Statut : passed.

Sorties :

- `table_audit_summary.json`
- `table_audit_findings.jsonl`
- `table_audit_samples.csv`

### v0.7 - CSV types table

Statut : passed.

Sorties :

- `table_observed_metrics.csv`
- `table_targets.csv`
- `table_contexts.csv`
- `table_rejected_candidates.csv`

### v0.8 - Contrat table

Statut : passed.

Sorties :

- `contracts/table_output_contract_v0.json`
- `docs/TABLE_OUTPUT_CONTRACT_V0.md`
- `scripts/validate_table_outputs.py`

### v0.9 - Audit multi-documents table

Statut : passed.

Sorties :

- `multi_document_table_audit_summary.json`
- `multi_document_table_audit.csv`
- `multi_document_table_audit.md`

### v1.0 - Release stable

Statut : passed avec warnings qualite.

## Tests Executes

- `python -m compileall -q ESGTableExtraction ESGVisualExtraction ESGCSVExtraction ESGInformationExtraction` : passed.
- `python -m pytest ESGTableExtraction/tests --basetemp <tmp>` : 13 passed, 1 warning cache pytest.
- `python -m pytest ESGVisualExtraction/tests --basetemp <tmp>` : 14 passed, 1 warning cache pytest.
- `python -m pytest ESGCSVExtraction/tests --basetemp <tmp>` : 31 passed, 1 warning cache pytest.
- `python -m pytest ESGInformationExtraction/tests --basetemp <tmp>` : 228 passed, 1 warning cache pytest.

## Test Manuel LVMH

Output :

```text
ESGTableExtraction/outputs/lvmh_table_v10_test
```

Resultats :

- tables lues : 28
- cellules lues : 4659
- tables reconstruites : 28
- candidats produits : 2
- `candidate_only`: true
- `review_required_count`: 2
- erreurs audit : 0
- warnings audit : 3

Distribution `metric_family` :

```text
unknown: 2
```

CSV types :

```text
table_observed_metrics.csv: 0
table_targets.csv: 0
table_contexts.csv: 2
table_rejected_candidates.csv: 0
```

Validation contrat :

```text
status: success
contract_version: 0.8.0
checks_count: 26
errors_count: 0
warnings_count: 0
```

## Audit Multi-documents

Output :

```text
ESGTableExtraction/outputs/multi_document_table_v10
```

Resultats :

- documents traites : 7
- tables totales : 196
- cellules totales : 32679
- candidats totaux : 14
- distribution : `unknown: 14`
- candidats sans unite : 7
- candidats sans annee : 0
- candidats depuis tables low-confidence : 6

## Preuve Non Destructive

Input LVMH :

```text
files_hashed: 23
digest_before: 0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee
digest_after:  0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee
```

## Warnings

- `quality_warning=true`
- `real_world_table_audit_pending=true`
- Les tableaux LVMH disponibles dans les 20 premieres pages sont majoritairement non metriques ou artefactuels.
- Les candidats produits sont conservateurs et classes `unknown`.

## Decision

v1.0 est validee techniquement. Continuer seulement avec un corpus contenant de vrais tableaux ESG numeriques bien structures.

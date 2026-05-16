# ESGCSVExtraction - Agent Delivery Report

## Phase 0 - Inspection

Inspection effectuee sur le repo local `C:\Users\hp\Desktop\ESG`.

Modules observes :

- `ESGInformationExtraction` : moteur documentaire PDF stabilise en v1.4.
- `ESGCSVExtraction` : nouveau module separe cree pour produire des CSV candidats.
- `ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test` : output LVMH disponible et exploitable pour test manuel.

Documentation lue :

- `ESGInformationExtraction/docs/RELEASE_NOTES_V1_4.md`
- `ESGInformationExtraction/docs/ARCHITECTURE_OVERVIEW_V1_4.md`
- `ESGInformationExtraction/README.md`

Inputs reels identifies :

- `document_inventory.json`
- `extraction_summary.json`
- `multimodal_evidence_index.jsonl`

Fichier principal retenu :

- `multimodal_evidence_index.jsonl`

Raison :

- contient toutes les evidences normalisees texte/table/figure ;
- expose `source_modality`, `evidence_type`, `page_number`, `section_id`, `evidence_id`, `quote`, `review_required`, `downstream_use_policy` ;
- permet de produire un CSV sans relire les PDFs ni toucher a `ESGInformationExtraction`.

Inputs secondaires :

- `document_inventory.json` pour `document_id`, `pdf_path`, readiness et contexte documentaire ;
- `extraction_summary.json` comme fallback pour `document_id`, `pdf_path`, statut et compteurs.

## Architecture minimale retenue

```text
ESGCSVExtraction/
  README.md
  AGENT_DELIVERY_REPORT.md
  scripts/
    run_csv_extraction.py
  src/
    esg_csv_extraction/
      __init__.py
      extractor.py
  tests/
    test_csv_extraction_v01.py
  outputs/
```

Flux :

```text
ESGInformationExtraction output dir
  -> document_inventory.json
  -> extraction_summary.json
  -> multimodal_evidence_index.jsonl
  -> rule-based candidate detection
  -> CSV/JSONL candidates
  -> audit CSV/JSON/JSONL
```

## Versions realisees

### v0.1 minimale

Fichiers produits :

- `esg_information_candidates.csv`
- `esg_information_candidates.jsonl`
- `extraction_audit.csv`
- `extraction_summary.json`

Regles :

- tous les candidats sont `candidate_only` ;
- tous les candidats sont `review_required=true` ;
- aucune metrique ESG n'est validee ;
- aucun score n'est produit.

Types detectes :

- `observed_metric`
- `target`
- `policy_or_commitment`
- `risk_statement`
- `boundary_context`
- `methodology_context`
- `visual_evidence`

### Auto-audit v0.1

Fichiers ajoutes :

- `candidate_audit_summary.json`
- `candidate_audit_findings.jsonl`
- `candidate_audit_samples.csv`

Checks :

- distribution par `information_type` ;
- candidats sans quote ;
- `observed_metric` sans valeur ;
- `observed_metric` sans unite ;
- `target` sans annee cible ;
- `visual_evidence` a faible confiance ;
- `confidence > 0.6` ;
- `review_required` manquant ou faux.

## Gate v0.2

Statut : passed.

Raison :

- l'audit v0.1 ne detecte aucune erreur critique ;
- `confidence_above_0_6`: 0 ;
- `review_required_missing_or_false`: 0 ;
- `candidates_without_quote`: 0 ;
- `observed_metric_without_value`: 0.

Problemes non bloquants :

- `observed_metric_without_unit`: 5 sur le test LVMH ;
- `visual_evidence_low_confidence`: 23 sur le test LVMH.

## Validation locale

Commandes executees :

- `python -m compileall -q ESGCSVExtraction ESGInformationExtraction`
- `python -m pytest ESGCSVExtraction\tests --basetemp <tmp>`
- `python -m pytest ESGInformationExtraction\tests --basetemp <tmp>`
- test manuel sur `ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test`

Resultats :

- `ESGCSVExtraction` : 8 tests passes.
- `ESGInformationExtraction` : 228 tests passes.
- Aucune erreur de compilation.
- Warning pytest uniquement lie au cache `.pytest_cache` inaccessible.

## Test manuel LVMH

Input :

```text
ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test
```

Output :

```text
ESGCSVExtraction/outputs/lvmh_v01_test
```

Resultats :

- `source_evidences_count`: 189
- `candidates_count`: 118

Distribution :

```text
boundary_context: 39
observed_metric: 28
policy_or_commitment: 16
methodology_context: 3
target: 7
risk_statement: 2
visual_evidence: 23
```

Audit v0.1 :

```text
candidates_without_quote: 0
observed_metric_without_value: 0
observed_metric_without_unit: 5
target_without_target_year: 0
visual_evidence_low_confidence: 23
confidence_above_0_6: 0
review_required_missing_or_false: 0
```

Conclusion :

- v0.1 est stable pour produire des candidats revus humainement.
- Les principaux points a surveiller sont les `observed_metric` sans unite et les `visual_evidence` faibles.

## Version courante v0.3 - Audit multi-documents

Statut : passed avec reserve.

Objectif :

Tester `ESGCSVExtraction` sur plusieurs dossiers d'outputs `ESGInformationExtraction` disponibles, puis produire un audit agrege.

Fichiers crees/modifies :

- `ESGCSVExtraction/src/esg_csv_extraction/multi_document_audit.py`
- `ESGCSVExtraction/scripts/run_multi_document_audit.py`
- `ESGCSVExtraction/tests/test_multi_document_audit_v03.py`
- `ESGCSVExtraction/src/esg_csv_extraction/extractor.py`
- `ESGCSVExtraction/README.md`
- `ESGCSVExtraction/AGENT_DELIVERY_REPORT.md`

Sorties produites :

- `ESGCSVExtraction/outputs/multi_document_v03/multi_document_candidate_audit_summary.json`
- `ESGCSVExtraction/outputs/multi_document_v03/multi_document_candidate_audit.csv`
- `ESGCSVExtraction/outputs/multi_document_v03/multi_document_candidate_audit.md`

Tests executes :

- `python -m compileall -q ESGCSVExtraction ESGInformationExtraction` : passed.
- `python -m pytest ESGCSVExtraction/tests` : premier lancement bloque par permission sur le dossier temporaire systeme.
- Relance avec `TEMP=.pytest_tmp` : 14 passed.
- `python -m pytest ESGInformationExtraction\tests --basetemp <tmp>` : 228 passed.

Test manuel multi-documents :

Input root :

```text
ESGInformationExtraction/outputs
```

Outputs detectes :

```text
pdf_v07_lvmh_2024_sustainability_test
pdf_v08_lvmh_2024_sustainability_test
pdf_v10_lvmh_2024_sustainability_test
```

Resultats :

- `documents_tested_count`: 3
- `total_candidates_count`: 354

Distribution agregee :

```text
boundary_context: 117
observed_metric: 84
policy_or_commitment: 48
methodology_context: 9
target: 21
risk_statement: 6
visual_evidence: 69
```

Audit agrege :

```text
observed_metric_without_unit_total: 15
target_without_target_year_total: 0
visual_evidence_low_confidence_total: 69
confidence_above_0_6_total: 0
review_required_missing_or_false_total: 0
```

Preuve non destructive :

```text
dirs_hashed: 3
files_hashed: 66
digest_before: 9f3477148426e001f7e5fa820b0bb3afc53079bef5adf1ec1e0e7793fd09d2c4
digest_after:  9f3477148426e001f7e5fa820b0bb3afc53079bef5adf1ec1e0e7793fd09d2c4
```

Decision :

Continuer est techniquement possible, mais il est recommande de s'arreter avant v0.4 tant que le test multi-documents ne couvre pas plusieurs entreprises ou plusieurs types documentaires. Les trois outputs disponibles sont des versions du meme document LVMH. La v0.3 est donc validee techniquement, mais la gate metier demande une revue humaine ou davantage d'outputs diversifies avant CSV types v0.4.

## Version courante v0.4 - CSV types

Statut : passed.

Objectif :

Separer le CSV global en CSV par type d'information, tout en conservant `esg_information_candidates.csv` et `esg_information_candidates.jsonl`.

Fichiers crees/modifies :

- `ESGCSVExtraction/src/esg_csv_extraction/extractor.py`
- `ESGCSVExtraction/tests/test_typed_csv_outputs_v04.py`
- `ESGCSVExtraction/README.md`
- `ESGCSVExtraction/AGENT_DELIVERY_REPORT.md`

Sorties ajoutees :

- `observed_metrics.csv`
- `targets.csv`
- `policies.csv`
- `risks.csv`
- `boundary_contexts.csv`
- `methodology_contexts.csv`
- `visual_evidences.csv`

Schema :

Les CSV types conservent le meme schema stable que le CSV global :

```text
document_id, company, fiscal_year, information_type, esg_category, label,
raw_value, raw_unit, year, source_modality, page_number, section_id,
evidence_id, quote, confidence, review_required, extraction_status
```

Regles conservees :

- `review_required=true` pour toutes les lignes ;
- `extraction_status=candidate_only` pour toutes les lignes ;
- aucune metrique validee ;
- aucun indicateur final ;
- aucun score ESG.

Tests executes :

- `python -m compileall -q ESGCSVExtraction ESGInformationExtraction` : passed.
- `python -m pytest ESGCSVExtraction/tests` avec `TEMP=.pytest_tmp` : 17 passed.
- `python -m pytest ESGInformationExtraction\tests --basetemp <tmp>` : 228 passed.

Test manuel LVMH :

Input :

```text
ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test
```

Output :

```text
ESGCSVExtraction/outputs/lvmh_v04_test
```

Resultats :

- `source_evidences_count`: 189
- `candidates_count`: 118

Distribution :

```text
boundary_context: 39
observed_metric: 28
policy_or_commitment: 16
methodology_context: 3
target: 7
risk_statement: 2
visual_evidence: 23
```

CSV types :

```text
observed_metrics.csv: 28
targets.csv: 7
policies.csv: 16
risks.csv: 2
boundary_contexts.csv: 39
methodology_contexts.csv: 3
visual_evidences.csv: 23
```

Preuve non destructive :

```text
files_hashed: 23
digest_before: 0223bdcefe8650dd19cdc8b2f627020a2e96734d7c9f2758e5a280c0f40e0bdb
digest_after:  0223bdcefe8650dd19cdc8b2f627020a2e96734d7c9f2758e5a280c0f40e0bdb
```

Decision :

v0.4 est validee techniquement. La prochaine version logique est v0.5, mais elle doit etre abordee prudemment car elle modifie la logique de detection des `observed_metric` pour reduire les faux positifs.

## Versions v0.5 a v1.0 - Stabilisation CSV candidate-only

Statut global : passed avec warnings metier.

Versions validees :

- v0.5 `observed_metrics.csv` : champs metriques ajoutes, detection prudente valeur/unite/annee, exclusion des phrases target-like.
- v0.6 `targets.csv` : champs target ajoutes, detection `target_year`, `baseline_year`, `target_status=candidate_only`.
- v0.7 policies/risks : policies sans obligation de valeur numerique, risks descriptifs sans score.
- v0.8 boundary/methodology : separation des contextes de perimetre et de methode.
- v0.9 contrat CSV : `csv_output_contract_v0.json`, documentation et validateur CLI.
- v1.0 release : docs de release, architecture et commandes de validation.

Fichiers crees/modifies :

- `ESGCSVExtraction/src/esg_csv_extraction/extractor.py`
- `ESGCSVExtraction/src/esg_csv_extraction/typed_csv_exporter.py`
- `ESGCSVExtraction/src/esg_csv_extraction/audit.py`
- `ESGCSVExtraction/src/esg_csv_extraction/validators.py`
- `ESGCSVExtraction/src/esg_csv_extraction/contract.py`
- `ESGCSVExtraction/scripts/validate_csv_outputs.py`
- `ESGCSVExtraction/contracts/csv_output_contract_v0.json`
- `ESGCSVExtraction/docs/CSV_OUTPUT_CONTRACT_V0.md`
- `ESGCSVExtraction/docs/RELEASE_NOTES_V1_0.md`
- `ESGCSVExtraction/docs/ARCHITECTURE_OVERVIEW_V1_0.md`
- `ESGCSVExtraction/docs/VALIDATION_COMMANDS_V1_0.md`
- tests v0.5 a v1.0 dans `ESGCSVExtraction/tests/`
- `ESGCSVExtraction/README.md`
- `ESGCSVExtraction/AGENT_DELIVERY_REPORT.md`
- `ESGCSVExtraction/ENGINE_COMPLETION_REPORT.md`

Tests executes :

- `python -m compileall -q ESGCSVExtraction ESGInformationExtraction` : passed.
- `python -m pytest ESGCSVExtraction/tests --basetemp <tmp>` : 31 passed, 1 warning cache pytest.
- `python -m pytest ESGInformationExtraction/tests --basetemp <tmp>` : 228 passed, 1 warning cache pytest.

Test manuel LVMH v1.0 :

Input :

```text
ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test
```

Output :

```text
ESGCSVExtraction/outputs/lvmh_v10_csv_test
```

Resultats :

- `source_evidences_count`: 189
- `candidates_count`: 109
- `review_required_count`: 109
- `candidate_audit_error_count`: 0
- `candidate_audit_warning_count`: 3

Distribution :

```text
boundary_context: 37
observed_metric: 26
policy_or_commitment: 16
methodology_context: 3
target: 7
risk_statement: 2
visual_evidence: 18
```

Audit qualite :

```text
candidates_without_quote: 0
observed_metric_without_value: 0
observed_metric_without_unit: 4
target_without_target_year: 5
visual_evidence_low_confidence: 18
confidence_above_0_6: 0
review_required_missing_or_false: 0
duplicate_evidence_type_label: 0
ineligible_evidence_candidates: 0
```

Validation contrat CSV :

```text
status: success
contract_version: 0.9.0
checks_count: 240
errors_count: 0
warnings_count: 0
```

Audit multi-documents :

```text
documents_tested_count: 3
total_candidates_count: 327
boundary_context: 111
observed_metric: 78
policy_or_commitment: 48
methodology_context: 9
target: 21
risk_statement: 6
visual_evidence: 54
```

Preuve non destructive :

```text
LVMH input files_hashed: 23
LVMH digest_before: 0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee
LVMH digest_after:  0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee

ESGInformationExtraction outputs files_hashed: 276
global digest_before: 1ab643ab37810064c3e44f9411c279d151ccf3d88e04758984820d3c5ab5ec90
global digest_after:  1ab643ab37810064c3e44f9411c279d151ccf3d88e04758984820d3c5ab5ec90
```

Warnings metier :

- `quality_warning=true`
- `real_world_audit_pending=true`
- certains targets n'ont pas encore de `target_year` explicite ;
- certaines evidences visuelles restent faibles et doivent etre revues humainement ;
- le multi-document local couvre surtout plusieurs versions du meme document LVMH.

Decision :

v1.0 est validee techniquement. Continuer vers une future v1.1 seulement apres revue metier des samples et enrichissement du corpus de test multi-entreprises.

# ESGCSVExtraction

`ESGCSVExtraction` est une brique separee de `ESGInformationExtraction`.

Son role est de lire des outputs documentaires deja produits et de generer des CSV de candidats d'information ESG exploitables pour revue humaine.

## Perimetre v0.1

La v0.1 est volontairement conservative :

- aucune extraction ESG validee ;
- aucun indicateur final ;
- aucun score ;
- aucune modification des outputs sources ;
- aucun acces aux PDFs ;
- tous les resultats sont `candidate_only` ;
- tous les resultats ont `review_required=true`.

## Sources consommees

Fichiers prioritaires :

- `document_inventory.json` : identite documentaire et chemin source ;
- `multimodal_evidence_index.jsonl` : evidences normalisees texte/table/figure ;
- `extraction_summary.json` : metadonnees et fallback document.

## Sorties

Dans `--output-dir` :

- `esg_information_candidates.csv`
- `esg_information_candidates.jsonl`
- `extraction_audit.csv`
- `candidate_audit_summary.json`
- `candidate_audit_findings.jsonl`
- `candidate_audit_samples.csv`
- `extraction_summary.json`

## Commande

```powershell
python ESGCSVExtraction/scripts/run_csv_extraction.py `
  --input-dir "ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test" `
  --output-dir "ESGCSVExtraction/outputs/lvmh_v01_test" `
  --overwrite
```

## Types d'information detectes

- `observed_metric`
- `target`
- `policy_or_commitment`
- `risk_statement`
- `boundary_context`
- `methodology_context`
- `visual_evidence`

Ces types restent des candidats bruts. Ils doivent etre verifies avant toute utilisation metier.

## Auto-audit v0.1

Le module produit aussi un auto-audit des candidats :

- distribution par `information_type` ;
- candidats sans quote ;
- `observed_metric` sans valeur ;
- `observed_metric` sans unite ;
- `target` sans annee cible ;
- `visual_evidence` a faible confiance ;
- `confidence > 0.6` ;
- `review_required` manquant ou faux.

Si l'audit montre trop de faux positifs grossiers, il faut corriger la v0.1 avant de produire des CSV types v0.2.

## v0.3 - Audit multi-documents

La v0.3 applique l'extraction candidate-only a plusieurs outputs `ESGInformationExtraction` et agrege les resultats.

Commande :

```powershell
python ESGCSVExtraction/scripts/run_multi_document_audit.py `
  --input-root "ESGInformationExtraction/outputs" `
  --output-dir "ESGCSVExtraction/outputs/multi_document_v03" `
  --overwrite
```

Sorties :

- `multi_document_candidate_audit_summary.json`
- `multi_document_candidate_audit.csv`
- `multi_document_candidate_audit.md`

Le multi-document audit ne modifie aucun input. Il cree des sorties candidates dans `ESGCSVExtraction/outputs/.../documents/<input_name>/`.

## v0.4 - CSV types

La v0.4 conserve le CSV global et ajoute des CSV separes par type d'information.

Sorties ajoutees :

- `observed_metrics.csv`
- `targets.csv`
- `policies.csv`
- `risks.csv`
- `boundary_contexts.csv`
- `methodology_contexts.csv`
- `visual_evidences.csv`

Chaque CSV type garde le meme schema stable que le CSV global. Les lignes restent `candidate_only` et `review_required=true`.

Ces fichiers ne sont pas des indicateurs ESG valides. Ils servent uniquement a faciliter la revue humaine et les futurs traitements separes.

## v0.5 - Observed metrics

La v0.5 enrichit `observed_metrics.csv` avec des champs prudents :

- `metric_key`
- `metric_label`
- `normalized_value`
- `normalized_unit`
- `reported_year`
- `boundary`
- `segment`
- `geography`
- `methodology`
- `value_kind`

Les valeurs restent candidates. Les phrases d'objectif evidentes sont dirigees vers `targets.csv`, pas vers `observed_metrics.csv`.

## v0.6 - Targets

La v0.6 enrichit `targets.csv` avec :

- `target_key`
- `target_label`
- `target_value`
- `target_unit`
- `target_year`
- `baseline_value`
- `baseline_year`
- `metric_related`
- `target_status`

`target_status` reste toujours `candidate_only`.

## v0.7 - Policies et risks

La v0.7 stabilise les exports qualitatifs :

- `policies.csv` garde les claims, topics et standards associes ;
- `risks.csv` garde des descriptions de risque sans produire de score.

Aucun `risk_score` n'est produit.

## v0.8 - Boundary et methodology

La v0.8 separe les contextes :

- `boundary_contexts.csv` pour perimetres, geographies, inclusions et exclusions ;
- `methodology_contexts.csv` pour standards et methodes comme `GHG Protocol`, `ESRS`, `GRI`, `market-based` ou `location-based`.

Ces lignes sont des contextes documentaires, pas des metriques finales.

## v0.9 - Contrat CSV

La v0.9 ajoute un contrat stable et un validateur :

- `contracts/csv_output_contract_v0.json`
- `docs/CSV_OUTPUT_CONTRACT_V0.md`
- `scripts/validate_csv_outputs.py`

Commande :

```powershell
python ESGCSVExtraction/scripts/validate_csv_outputs.py `
  --output-dir "ESGCSVExtraction/outputs/lvmh_v10_csv_test" `
  --contract-path "ESGCSVExtraction/contracts/csv_output_contract_v0.json"
```

## v1.0 - Release stable ESGCSVExtraction

Documentation de release :

- `docs/RELEASE_NOTES_V1_0.md`
- `docs/ARCHITECTURE_OVERVIEW_V1_0.md`
- `docs/VALIDATION_COMMANDS_V1_0.md`

La v1.0 fige une premiere couche CSV exploitable pour revue humaine. Elle ne valide aucune metrique ESG, ne produit aucun indicateur final et ne produit aucun score.

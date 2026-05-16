# Audit complet du projet ESG pour ChatGPT

## 1. Resume executif

Le projet ESG est une chaine documentaire avancee visant a construire un corpus ESG fiable, traceable et pret pour une future extraction d'indicateurs. Le projet couvre deja l'ingestion documentaire, le post-processing, la deduplication, l'organisation taxonomique, la validation documentaire, la selection finale, puis un moteur PDF documentaire audite dans `ESGInformationExtraction`.

L'etat actuel est solide cote infrastructure documentaire. Le pipeline sait construire un `ESGFinalCorpus`, isoler les runs par `run_id`, tourner sur Onyxia, et transformer un PDF en objets documentaires structures : pages, blocs, sections, evidences, tableaux, figures, inventaire multimodal, rapports d'audit, validation de contrat, compatibilite batch, plan de remediation et checklist humaine.

Le projet ne fait pas encore d'extraction ESG metier. Il ne produit pas encore d'indicateurs, de metriques validees, de score, de RAG, de base vectorielle ou d'analyse LLM. La prochaine grande phase devra etre une couche ESG separee, qui lit les outputs documentaires sans les modifier.

## 2. Objectif du projet

Objectif final :

```text
CAC40 x 5 annees
  -> ingestion documentaire
  -> corpus final ESG propre
  -> extraction future d'indicateurs ESG
  -> base d'evidences
  -> controle qualite
  -> scoring ESG eventuel
```

Objectif actuel :

```text
stabiliser la chaine documentaire
  -> recuperer les documents
  -> dedupliquer
  -> organiser
  -> valider
  -> selectionner
  -> structurer les PDFs
  -> auditer les outputs
```

Ce projet est donc encore dans une phase documentaire, pas dans une phase d'interpretation ESG.

## 3. Architecture generale

Arborescence principale observee :

```text
ESG/
  AGMRetriever/
  AnnualReportRetriever/
  AssuranceReportRetriever/
  CDPResponseRetriever/
  ClimateReportRetriever/
  CorporatePolicyRetriever/
  EarningsCallRetriever/
  GovernanceReportRetriever/
  HalfYearReportRetriever/
  InvestorPresentationRetriever/
  RemunerationReportRetriever/
  SBTiRetriever/
  SustainabilityReportRetriever/
  VigilancePlanRetriever/
  DocumentPostProcessing/
  ESGOrchestrator/
  ESGInformationExtraction/
  ESGCorpus/
  ESGCorpusTaxonomy/
  ESGFinalCorpus/
  data/
  docs/
  scripts/
```

Flux global :

```text
Retrievers
  -> data/dossier_ingestion_0
  -> DocumentPostProcessing
  -> central registry
  -> deduplication
  -> canonical registry
  -> ESGCorpus
  -> ESGCorpusTaxonomy
  -> validation documentaire
  -> selection finale
  -> ESGFinalCorpus
  -> ESGInformationExtraction
  -> outputs documentaires audites
```

## 4. Modules principaux

### 4.1 Retrievers documentaires

Le projet contient 14 retrievers :

- `AnnualReportRetriever`
- `SustainabilityReportRetriever`
- `ClimateReportRetriever`
- `GovernanceReportRetriever`
- `RemunerationReportRetriever`
- `VigilancePlanRetriever`
- `AGMRetriever`
- `AssuranceReportRetriever`
- `CDPResponseRetriever`
- `CorporatePolicyRetriever`
- `EarningsCallRetriever`
- `HalfYearReportRetriever`
- `InvestorPresentationRetriever`
- `SBTiRetriever`

Role :

- chercher des documents ;
- scorer les candidats ;
- telecharger les PDFs ;
- produire des manifests ;
- alimenter `data/dossier_ingestion_0`.

Points forts :

- separation par type documentaire ;
- logique modulaire ;
- compatibilite avec orchestration par subprocess ;
- corrections deja faites pour encodage Windows/Linux et robustesse HTML.

Risques :

- dependance aux moteurs de recherche et sites web ;
- formats de manifests implicites ;
- comportements variables selon les sites ;
- certains types officiels n'ont pas encore de retriever configure.

### 4.2 DocumentPostProcessing

Role :

- lire les manifests et PDFs existants ;
- construire un registre central ;
- dedupliquer par SHA-256 ;
- construire un registre canonique ;
- organiser le corpus ;
- mapper vers une taxonomie officielle ;
- valider techniquement les PDFs ;
- selectionner les documents finaux.

Sorties typiques :

```text
central_registry/
deduplication/
organized_corpus/
organized_corpus_taxonomy/
validation/
selection/
```

Points forts :

- fonctionne offline ;
- ne modifie pas les PDFs sources ;
- copie les documents au lieu de les deplacer ;
- produit des index CSV/JSON ;
- support du scope company/year pour les runs.

Risques :

- les anciens outputs globaux peuvent contenir de l'historique ;
- il faut privilegier les sorties isolees par `run_id` ;
- la qualite depend des manifests produits par les retrievers.

### 4.3 ESGOrchestrator

Role :

- lire les entreprises, annees et types documentaires ;
- construire la matrice de taches ;
- lancer les retrievers ;
- gerer les statuts ;
- lancer le post-processing ;
- produire les sorties run-scoped.

Sortie cible :

```text
ESGOrchestrator/runs/<run_id>/
  postprocessing/
  ESGCorpus/
  ESGCorpusTaxonomy/
  ESGFinalCorpus/
  task_log.csv
  run_state.json
  coverage_matrix.csv
  final_summary.json
```

Profils importants :

- `pilot` : LVMH + TotalEnergies, 2024-2025.
- `onyxia_pilot_5x2` : 5 entreprises, 2024-2025.
- `onyxia_cac40_5y` : CAC40 complet, 2021-2025.

Etat Onyxia signale :

```text
run_id: onyxia_cac40_5y_full_20260510_085527
task_log exists: True
rows: 4400

status distribution:
pending: 2431
skipped_not_applicable: 1000
success: 954
failed: 15
```

Interpretation :

- le run complet Onyxia est en cours ou incomplet ;
- `skipped_not_applicable` est normal pour les types sans retriever ;
- les `15 failed` doivent etre audites separement ;
- les `2431 pending` indiquent que le run n'est pas termine.

### 4.4 ESGInformationExtraction

Role actuel :

Transformer un PDF en representation documentaire structuree et auditee.

Version actuelle :

```text
v1.4
```

Derniere validation connue :

```text
228 passed
0 failed
0 errors
```

Le module produit notamment :

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

Outils disponibles :

- `audit_text_blocks.py`
- `run_document_audit.py`
- `validate_output_contract.py`
- `check_output_compatibility.py`
- `batch_check_outputs.py`

Etat batch local observe :

```text
outputs_scanned_count: 26
compatible: 1
compatible_with_warnings: 1
migration_required: 9
incompatible: 15
```

Plan de remediation observe :

```text
no_action_needed: 1
annotate_summary_only: 1
rerun_audit_standalone: 9
regenerate_with_current_engine: 15
```

## 5. Contrats et garanties

Contrat stable :

```text
ESGInformationExtraction/contracts/output_contract_v1.json
ESGInformationExtraction/docs/OUTPUT_CONTRACT_V1.md
```

Garanties importantes :

- les PDFs sources ne sont pas modifies ;
- `ESGFinalCorpus` n'est pas modifie par le moteur PDF ;
- les manifests sources ne sont pas modifies ;
- les outputs sont ecrits dans `--output-dir` ;
- les outils batch ne modifient pas les outputs scannes ;
- les commandes de remediation ne sont pas executees automatiquement ;
- aucune extraction ESG n'est faite dans v1.4.

## 6. Points solides

- Architecture separee entre ingestion, post-processing, orchestration et moteur PDF.
- Isolation par `run_id` dans `ESGOrchestrator`.
- Preparation Windows et Onyxia/Linux.
- `ESGInformationExtraction` tres bien teste : 228 tests.
- Contrat de sortie v1.0 documente et machine-readable.
- Audit standalone possible sans reparser le PDF.
- Batch compatibility, remediation plan et execution checklist non destructifs.
- Bonne discipline de non-modification des PDFs/manifests.
- Separation claire entre evidence documentaire et future extraction ESG.

## 7. Risques actuels

### 7.1 Run Onyxia incomplet

Le run CAC40 x 5 ans montre encore beaucoup de `pending` et 15 `failed`.

Priorite :

- terminer ou reprendre le run ;
- auditer les 15 failures ;
- produire un rapport final Onyxia ;
- verifier la couverture par entreprise/annee/type documentaire.

### 7.2 Outputs historiques incompatibles

Dans `ESGInformationExtraction/outputs`, beaucoup d'anciens outputs sont incompatibles avec le contrat v1.0.

Ce n'est pas forcement un bug : beaucoup datent d'avant les versions stabilisees. Le plan v1.4 recommande de regenerer ou auditer selon les cas.

### 7.3 Future extraction ESG non encore construite

Le plus gros risque reste a venir :

- extraction des valeurs dans les tableaux ;
- reconnaissance des unites ;
- association a la bonne annee ;
- distinction scope groupe / filiale / segment ;
- validation de l'evidence ;
- gestion multilingue ;
- controle qualite metier.

### 7.4 Tableaux et figures

Le moteur sait localiser et structurer des tableaux/figures, mais ne les interprete pas.

Ce choix est sain pour l'instant, mais la future extraction ESG dependra fortement de cette couche.

## 8. Ce qu'il ne faut pas faire maintenant

Ne pas :

- brancher directement un LLM sur tout le corpus ;
- faire du RAG avant stabilisation des evidences ;
- produire un score ESG avant d'avoir des indicateurs fiables ;
- modifier les retrievers pendant un run Onyxia sans raison critique ;
- modifier les manifests historiques ;
- ecraser les outputs globaux sans run_id ;
- confondre `evidence_store.jsonl` avec des indicateurs ESG valides.

## 9. Prochaines priorites recommandees

### Priorite 1 - Finaliser le run Onyxia

Actions :

- surveiller le run `onyxia_cac40_5y_full_20260510_085527` ;
- auditer les 15 `failed` ;
- relancer en resume si necessaire ;
- verifier que le post-processing final produit bien un `ESGFinalCorpus` isole.

### Priorite 2 - Auditer le corpus final Onyxia

Actions :

- lancer l'audit de run ESGOrchestrator ;
- produire coverage matrix finale ;
- verifier documents manquants par entreprise/annee/type ;
- identifier les trous documentaires.

### Priorite 3 - Regenerer quelques outputs PDF v1.4 propres

Actions :

- choisir 5 a 10 PDFs representatifs ;
- lancer `run_pdf_extraction.py` ;
- valider avec `validate_output_contract.py` ;
- comparer les rapports humains.

### Priorite 4 - Specifier la couche ESG metier

Avant de coder :

- definir les indicateurs prioritaires ;
- definir les schemas `MetricCandidate`, `ValidatedMetric`, `ESGEvidenceLink` ;
- definir les regles d'unite, annee, perimetre ;
- definir les criteres de validation.

### Priorite 5 - Prototyper l'extraction ESG sur un petit perimetre

Perimetre conseille :

```text
LVMH + TotalEnergies
2024
2 types documentaires :
  - sustainability statement
  - annual report / URD
5 a 10 indicateurs seulement
```

## 10. Recommandation d'architecture future

Creer un module separe :

```text
ESGMetricExtraction/
  README.md
  schemas/
  config/
  extractors/
  validators/
  evidence_linking/
  quality_control/
  outputs/
  tests/
```

Flux futur :

```text
ESGInformationExtraction outputs
  -> metric candidate detection
  -> table-aware extraction
  -> unit normalization
  -> year/scope alignment
  -> evidence linking
  -> confidence scoring
  -> human review queue
  -> validated indicator database
```

Important :

Cette couche doit lire les outputs documentaires, pas les modifier.

## 11. Questions ouvertes pour la suite

- Quels indicateurs ESG prioritaires extraire en premier ?
- Faut-il commencer par climat uniquement ou par un socle E/S/G ?
- Comment gerer les tableaux multi-annees ?
- Quelle granularite de perimetre : groupe, pays, segment, activite ?
- Quel format cible pour la base d'indicateurs ?
- Quelle part d'extraction par regles vs modele ?
- Quel processus de revue humaine ?
- Quels seuils de confiance rendent une valeur exploitable ?
- Comment versionner les indicateurs extraits ?

## 12. Prompt court a donner a ChatGPT

```text
Tu analyses un projet ESG documentaire avance.

Le projet construit un corpus ESG CAC40 x 5 ans. Il contient des retrievers, DocumentPostProcessing, ESGOrchestrator et ESGInformationExtraction.

Etat actuel :
- ingestion et post-processing existent ;
- ESGOrchestrator lance des runs Onyxia avec isolation par run_id ;
- un run complet Onyxia est en cours : 4400 taches, 954 success, 1000 skipped_not_applicable, 15 failed, 2431 pending ;
- ESGInformationExtraction est stabilise en v1.4 ;
- le moteur PDF produit pages, blocs, sections, evidences, tableaux, figures, inventaire multimodal, audits, contrat v1.0, compatibilite batch, remediation plan et checklist ;
- tests v1.4 : 228 passed, 0 failed, 0 errors ;
- aucune extraction ESG metier n'est encore faite.

Objectif prochain :
1. terminer et auditer le run Onyxia ;
2. stabiliser le corpus final ;
3. specifier une couche ESG separee ;
4. prototyper l'extraction d'indicateurs sur un petit perimetre.

Contraintes :
- ne pas modifier les PDFs ou manifests ;
- ne pas confondre evidence documentaire et indicateur ESG ;
- ne pas faire de scoring avant validation des indicateurs ;
- garder la couche ESG separee du moteur PDF.
```

## 13. Conclusion

Le projet est a un bon niveau de maturite documentaire. Il a depasse le stade du simple prototype PDF : il dispose maintenant d'une chaine corpus + orchestration + moteur documentaire audite.

La note globale actuelle est autour de 8/10 pour atteindre l'objectif documentaire. Pour atteindre l'objectif final ESG complet, il reste la phase la plus delicate : extraction metier, validation des valeurs, gestion des tableaux, controle des unites et construction d'une base d'indicateurs fiable.

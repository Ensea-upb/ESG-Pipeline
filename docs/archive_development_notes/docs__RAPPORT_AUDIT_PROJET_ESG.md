# Rapport d'audit du projet ESG

## 1. Resume executif

Le projet ESG est aujourd'hui une chaine documentaire avancee dont l'objectif est de construire un corpus ESG propre, structure, deduplique, valide techniquement et pret pour une extraction d'information future. Le systeme couvre deja l'ingestion de plusieurs familles documentaires, le post-processing centralise, l'organisation taxonomique, la validation documentaire legere et la selection finale vers un `ESGFinalCorpus`.

Le niveau de maturite est celui d'un prototype industriel en cours de stabilisation. La separation entre ingestion, post-processing et corpus final est claire. L'orchestrateur permet de lancer des profils pilotes et des profils plus larges, avec isolation par `run_id`. Une preparation Onyxia a ete amorcee via `ESG_PROJECT_ROOT`, `ESG_POSTPROCESS_INPUT_ROOT`, des profils dedies et un script de lancement.

Les points d'attention principaux sont la stabilite des contrats implicites entre retrievers et post-processing, la compatibilite des chemins entre Windows et Linux, la dependance aux formats de manifests, la reprise de run encore minimale, et la necessite de ne pas modifier les retrievers pendant un run Onyxia long.

## 2. Objectif fonctionnel du projet

Le but metier du projet est de produire un corpus documentaire ESG fiable pour les entreprises du CAC40 sur plusieurs annees. Ce corpus doit etre suffisamment traceable pour permettre, dans une phase ulterieure, l'extraction controlee d'indicateurs ESG, la constitution d'une base d'evidences, puis eventuellement des scores de risque ESG.

L'objectif actuel n'est pas l'extraction d'information ESG. La phase courante vise uniquement la stabilisation documentaire :

- rechercher et telecharger des documents ESG et financiers pertinents ;
- centraliser les manifests produits par les retrievers ;
- dedupliquer par hash ;
- construire un registre canonique ;
- organiser les documents par entreprise, annee et famille documentaire ;
- classer les documents selon une taxonomie officielle ;
- valider legerement les PDFs ;
- selectionner un corpus final par entreprise, annee et type documentaire.

Le livrable cible de cette phase est `ESGFinalCorpus`, isole par `run_id`, et pret pour une extraction future.

## 3. Architecture generale observee

Arborescence principale observee :

```text
ESG/
├── AGMRetriever/
├── AnnualReportRetriever/
├── AssuranceReportRetriever/
├── CDPResponseRetriever/
├── ClimateReportRetriever/
├── CorporatePolicyRetriever/
├── EarningsCallRetriever/
├── GovernanceReportRetriever/
├── HalfYearReportRetriever/
├── InvestorPresentationRetriever/
├── RemunerationReportRetriever/
├── SBTiRetriever/
├── SustainabilityReportRetriever/
├── VigilancePlanRetriever/
├── data/
│   └── dossier_ingestion_0/
├── DocumentPostProcessing/
├── ESGCorpus/
├── ESGCorpusTaxonomy/
├── ESGFinalCorpus/
├── ESGOrchestrator/
├── scripts/
├── requirements_all.txt
└── ONYXIA_RUN.md
```

Schema textuel du pipeline :

```text
Retrievers documentaires
  -> ingestion dans data/dossier_ingestion_0
  -> manifests JSON + PDFs candidats
  -> DocumentPostProcessing / registre central
  -> deduplication exacte par SHA-256
  -> registre canonique
  -> ESGCorpus
  -> ESGCorpusTaxonomy
  -> validation documentaire legere
  -> selection finale
  -> ESGOrchestrator/runs/<run_id>/ESGFinalCorpus
```

L'orchestrateur coordonne les retrievers et le post-processing. Les sorties run-scoped sont prevues dans :

```text
ESGOrchestrator/runs/<run_id>/
├── postprocessing/
├── ESGCorpus/
├── ESGCorpusTaxonomy/
└── ESGFinalCorpus/
```

## 4. Analyse des modules principaux

### 4.1 Retrievers documentaires

Les 14 retrievers ont une structure similaire : `search.py`, `scorer.py`, `retriever.py`, `downloader.py`, `storage.py`, `html_resolver.py`, `models.py`, `utils.py`, et des scripts de lancement. Leur responsabilite generale est de produire des candidats documentaires, les scorer, telecharger les fichiers retenus, puis ecrire des manifests JSON et des PDFs dans une arborescence d'ingestion.

Retrievers observes :

- `AnnualReportRetriever` : rapports annuels, URD, documents d'enregistrement universel.
- `SustainabilityReportRetriever` : rapports de durabilite, ESG, RSE, CSRD/ESRS potentiels.
- `ClimateReportRetriever` : rapports climat, TCFD, transition plan, emissions.
- `GovernanceReportRetriever` : documents de gouvernance, souvent sections ou documents proches des URD.
- `RemunerationReportRetriever` : rapports de remuneration ou compensation.
- `VigilancePlanRetriever` : plans de vigilance et due diligence droits humains.
- `AGMRetriever` : documents d'assemblee generale, avis, resolutions, minutes.
- `AssuranceReportRetriever` : rapports d'assurance tierce partie, assurance limitee ou raisonnable.
- `CDPResponseRetriever` : reponses CDP.
- `CorporatePolicyRetriever` : codes et politiques corporate, avec sous-types `code_of_conduct`, `anticorruption`, `human_rights`, `dei`, `environmental`, `supplier_code`.
- `EarningsCallRetriever` : transcriptions ou documents d'appels de resultats.
- `HalfYearReportRetriever` : rapports semestriels.
- `InvestorPresentationRetriever` : presentations investisseurs.
- `SBTiRetriever` : engagements ou validations SBTi.

Les retrievers utilisent DDGS pour la recherche web selon les fichiers `requirements.txt`. Les dependances communes sont `ddgs`, `requests`, `pydantic`, `pyyaml`, `beautifulsoup4`, `lxml`, `pdfplumber`.

### 4.2 DocumentPostProcessing

`DocumentPostProcessing` est la couche de consolidation offline. Elle ne doit pas appeler le reseau. Elle lit les manifests et PDFs deja produits.

Modules principaux :

- `models.py` : modele `IngestedDocument` et resultats de construction du registre.
- `registry_builder.py` : lit les manifests et produit `documents_registry.csv/json`.
- `deduplicator.py` : groupe les documents par SHA-256.
- `canonical_registry.py` : selectionne un document canonique par hash unique.
- `corpus_organizer.py` : copie les documents dans `ESGCorpus`.
- `taxonomy_corpus_organizer.py` : mappe les familles techniques vers les types documentaires officiels.
- `validator.py` : validation PDF legere, header PDF, pages, extraction limitee des premieres pages.
- `document_selector.py` : selection finale d'un document principal par entreprise, annee et type officiel.
- `scope.py` : lecture des variables de scope et filtrage `company_slug` / `fiscal_year`.

Sorties globales historiques observees :

```text
DocumentPostProcessing/data/central_registry/
DocumentPostProcessing/data/deduplication/
DocumentPostProcessing/data/organized_corpus/
DocumentPostProcessing/data/organized_corpus_taxonomy/
DocumentPostProcessing/data/validation/
DocumentPostProcessing/data/selection/
```

En mode orchestre, ces sorties sont redirigees vers `ESGOrchestrator/runs/<run_id>/postprocessing/`.

### 4.3 ESGOrchestrator

`ESGOrchestrator` coordonne la construction du corpus. Il lit :

- `config/companies_cac40.yaml` : 40 entreprises observees ;
- `config/document_types.yaml` : 22 types documentaires officiels ;
- `config/pipeline.yaml` : annees par defaut, seuil de score, scope et etapes post-processing ;
- `config/run_profiles.yaml` : profils `pilot`, `full_cac40_5y`, `onyxia_pilot_5x2`, `onyxia_cac40_5y`.

Modules principaux :

- `company_universe.py` : selection d'entreprises.
- `task_builder.py` : construit la matrice `company x year x document_type`.
- `retriever_runner.py` : lance les subprocess retrievers.
- `postprocessing_runner.py` : lance les scripts offline de post-processing.
- `pipeline_orchestrator.py` : coordonne l'ensemble.
- `run_state.py` : ecrit `run_state.json` et `task_log.csv`.
- `reporting.py` : ecrit `coverage_matrix.csv` et `final_summary.json`.

Les profils observes :

- `pilot` : LVMH, TotalEnergies, 2024-2025, 88 taches.
- `onyxia_pilot_5x2` : 5 entreprises, 2024-2025, 220 taches.
- `onyxia_cac40_5y` : CAC40 complet, 2021-2025.

### 4.4 ESGCorpus

`ESGCorpus` est un corpus lisible humainement, organise par :

```text
ESGCorpus/<company_slug>/<fiscal_year>/<document_family>/<canonical_document_id>/
├── document.pdf
├── manifest.json
└── references.json
```

Un meme document canonique peut etre copie dans plusieurs familles documentaires si plusieurs roles sont detectes. Cela cree volontairement des copies physiques pour rendre le corpus comprehensible par un humain.

### 4.5 ESGCorpusTaxonomy

`ESGCorpusTaxonomy` applique une taxonomie documentaire officielle. La structure cible est :

```text
ESGCorpusTaxonomy/<company_slug>/<year>/<official_doc_type>/<canonical_document_id>/
├── document.pdf
├── manifest.json
└── references.json
```

La taxonomie inclut notamment :

- `01_urd_annual_report`
- `02_sustainability_statement_csrd_esrs`
- `03_climate_report_tcfd_transition_plan`
- `04_vigilance_plan`
- `05_half_year_financial_report`
- `07_code_ethique`
- `08_anticorruption_policy`
- `09_human_rights_policy`
- `12_supplier_code_of_conduct`
- `16_agm_minutes_resolutions`
- `17_cdp_response`
- `18_sbti_validation`
- `19_third_party_assurance_report`

Certains types sont configures mais sans retriever actif : SEC filings, communiques ESG, controverses, contentieux, critical coverage.

### 4.6 ESGFinalCorpus

`ESGFinalCorpus` est la sortie documentaire finale. Sa vocation est de fournir un corpus plus restreint, par entreprise, annee et type documentaire officiel, pret pour une future extraction ESG.

Structure attendue :

```text
ESGFinalCorpus/<company_slug>/<year>/<official_doc_type>/
├── document.pdf
├── manifest.json
└── references.json
```

En mode orchestre, la source principale doit etre :

```text
ESGOrchestrator/runs/<run_id>/ESGFinalCorpus/
```

Le dossier global `ESGFinalCorpus/` peut exister localement, mais ne doit pas etre considere comme la sortie principale d'un run Onyxia.

## 5. Flux de donnees et contrats implicites

### Structure des dossiers

Contrat actuel d'ingestion orchestree :

```text
data/dossier_ingestion_0/<storage_folder>/...
```

Le post-processing orchestre lit ce dossier via :

```text
ESG_POSTPROCESS_INPUT_ROOT=<ESG_PROJECT_ROOT>/data/dossier_ingestion_0
```

Les anciens dossiers internes aux retrievers existent encore :

```text
<Retriever>/data/dossier_ingestion_0/
```

Ils restent utiles pour historique ou usage manuel, mais le mode orchestre doit privilegier le dossier racine.

### Noms de fichiers attendus

Les manifests sont recherches avec le motif :

```text
*manifest.json
```

Les corpus organises attendent :

```text
document.pdf
manifest.json
references.json
```

### Champs de manifests et registres

Champs importants du registre central :

```text
document_id, retriever_name, document_family, company_name, company_slug,
fiscal_year, source_url, source_title, source_name, score, decision,
local_path, manifest_path, sha256, file_size_mb, document_type,
storage_role, candidate_rank, stored_at, source_manifest_path
```

Le champ `fiscal_year` est central pour les rapports annuels et assimiles. Pour les politiques corporate, `reference_year` peut etre utilise dans les manifests et normalise en `fiscal_year` dans le registre central.

Champs importants du registre canonique :

```text
canonical_document_id, sha256, company_name, company_slug, fiscal_year,
canonical_retriever_name, canonical_document_family, canonical_local_path,
canonical_manifest_path, canonical_source_url, canonical_source_title,
canonical_score, document_families_detected, retrievers_detected,
source_urls_detected, source_titles_detected, duplicate_count,
is_duplicate_group, all_references
```

Champs importants de l'index taxonomique :

```text
canonical_document_id, sha256, company_name, company_slug, fiscal_year,
technical_document_family, official_doc_type, official_doc_type_label,
doc_type_stratum, doc_subtype, period_type, regulatory_status,
status, taxonomy_notes, source_document_path, taxonomy_document_path,
taxonomy_manifest_path, taxonomy_references_path
```

Champs importants de la selection finale :

```text
company_name, company_slug, fiscal_year, official_doc_type,
official_doc_type_label, selected_canonical_document_id, sha256,
source_title, source_url, source_path, final_path, validation_status,
selection_status, selection_reason, selection_score, page_count,
detected_years, company_name_detected_in_text
```

### Variables d'environnement

Variables importantes :

```text
ESG_PROJECT_ROOT=/home/onyxia/work/ESG
ESG_POSTPROCESS_INPUT_ROOT=/home/onyxia/work/ESG/data/dossier_ingestion_0
ESG_POSTPROCESS_OUTPUT_ROOT=<run_dir>/postprocessing
ESG_POSTPROCESS_SCOPE=run
ESG_POSTPROCESS_COMPANY_SLUGS=...
ESG_POSTPROCESS_YEARS=...
PYTHONIOENCODING=utf-8
PYTHONUNBUFFERED=1
```

### Conventions d'identification

Les entites sont identifiees par `company_slug`, `fiscal_year`, `document_family`, `official_doc_type`, `sha256`, `canonical_document_id`.

Le hash SHA-256 est le pivot de deduplication exacte. Le `canonical_document_id` est derive du document canonique et sert de reference stable dans les corpus organises.

## 6. Etat de robustesse actuel

Elements solides observes :

- Les retrievers sont separes par famille documentaire.
- L'orchestrateur construit une matrice explicite `company x year x document_type`.
- Les types sans retriever sont marques `skipped_not_applicable`.
- Les sorties par `run_id` existent.
- Le mode `postprocessing_scope: run` limite les sorties a un perimetre donne.
- `ESG_POSTPROCESS_INPUT_ROOT` permet au post-processing de lire le dossier d'ingestion racine.
- Le pilot local LVMH / TotalEnergies 2024-2025 a atteint 68 success, 20 skipped, 0 failed apres corrections.
- La chaine DocumentPostProcessing produit des artefacts lisibles : CSV, JSON, summaries.
- La deduplication exacte par SHA-256 donne une base solide pour eviter les doublons physiques.
- La validation documentaire est volontairement legere et bornee.

Indicateurs historiques observes localement :

- registre central global : 296 documents charges ;
- documents uniques : 229 ;
- groupes de doublons exacts : 48 ;
- documents organises dans `ESGCorpus` : 240 ;
- documents classes dans `ESGCorpusTaxonomy` : 197 ;
- documents finaux globaux selectionnes : 37 ;
- manifests dans `data/dossier_ingestion_0` : 276 ;
- manifests dans les dossiers internes des retrievers : 296.

## 7. Risques techniques identifies

### Dependances fortes aux formats de manifests

Le post-processing suppose que les manifests conservent certains champs et structures : `company`, `company_slug`, `fiscal_year` ou `reference_year`, `source`, `scoring`, `file`, `sha256`. Changer ce format sans versionner casserait la chaine.

### Risques de chemins locaux / Onyxia

Le projet a historiquement utilise deux emplacements d'ingestion : les dossiers internes des retrievers et le dossier racine `data/dossier_ingestion_0`. Sur Onyxia, il faut privilegier le dossier racine et verifier que `ESG_POSTPROCESS_INPUT_ROOT` est bien defini.

### Compatibilite entre modules

Les retrievers, le registry builder, les organisateurs de corpus, le validator et le selector communiquent par fichiers. Les contrats ne sont pas encore formalises dans un schema versionne. Cela rend les evolutions fragiles.

### Duplication documentaire

La duplication physique est parfois volontaire dans `ESGCorpus` et `ESGCorpusTaxonomy`, mais elle doit rester tracee par `sha256`, `canonical_document_id` et `all_references`.

### Selection finale ambigue

La selection finale utilise des heuristiques. Les documents `selected_needs_review`, `needs_review` et `likely_wrong_company` indiquent que la sortie finale doit etre auditee avant usage d'extraction ESG.

### Types documentaires non applicables

Certains types officiels sont configures sans retriever. Ils apparaissent comme `skipped_not_applicable`. Cela est sain techniquement, mais la couverture documentaire finale restera incomplete pour ces categories.

### Modifications pendant un run distant

Modifier un retriever ou un format de manifest pendant un run Onyxia peut produire des donnees heterogenes dans un meme `run_id`. Il faut geler les contrats pendant les runs longs.

### PDFs absents ou mal classes

La validation legere peut detecter fichiers manquants, non PDF, illisibles ou mauvaises entreprises. Le risque principal apres selection est la presence de documents plausibles mais mal classes.

### Reprise de run

Le champ `resume` existe dans la configuration, mais la reprise doit etre consideree comme minimale tant qu'un mecanisme explicite de relecture des statuts et de skip effectif n'est pas durci.

## 8. Recommandations immediates sans casser Onyxia

Actions recommandees pendant ou juste apres le run Onyxia, sans modifier les retrievers :

1. Geler les retrievers et les formats de manifests pendant le run.
2. Conserver tous les artefacts de run dans `ESGOrchestrator/runs/<run_id>/`.
3. Produire un rapport de coherence par run :
   - nombre de taches attendues ;
   - nombre de success / failed / skipped ;
   - nombre de manifests lus ;
   - repartition par entreprise, annee et type documentaire ;
   - nombre de PDFs manquants ;
   - nombre de documents finaux.
4. Comparer attendu / observe pour `onyxia_pilot_5x2` avant le CAC40 complet.
5. Auditer les `selected_needs_review`, `likely_wrong_company` et `needs_review`.
6. Documenter les schemas actuels des CSV et JSON comme contrats v1.
7. Eviter toute modification des scorers, downloaders, storages et retrievers pendant le run distant.
8. Ne pas brancher d'extraction ESG tant que `ESGFinalCorpus` n'est pas stabilise.

## 9. Architecture recommandee apres ESGFinalCorpus

Architecture future recommandee, a developper comme chaine independante :

```text
ESGFinalCorpus
  -> ESGDocumentBase
  -> ESGParsing
  -> ESGSectionIndex
  -> ESGMetricExtraction
  -> ESGEvidenceStore
  -> ESGQualityControl
  -> ESGIndicatorDatabase
  -> ESGRiskScoring
```

Description des couches :

- `ESGDocumentBase` : registre stable des documents finaux selectionnes, avec liens vers manifests, references et hashes.
- `ESGParsing` : extraction texte/pages/tableaux depuis PDFs, sans modifier les documents sources.
- `ESGSectionIndex` : detection des sections pertinentes : climat, emissions, gouvernance, vigilance, remuneration, risques.
- `ESGMetricExtraction` : extraction controlee d'indicateurs quantitatifs et qualitatifs.
- `ESGEvidenceStore` : stockage des preuves, citations, pages, bounding boxes si disponibles.
- `ESGQualityControl` : controles d'unites, annees, coherence temporelle, source, entreprise.
- `ESGIndicatorDatabase` : base normalisee des indicateurs.
- `ESGRiskScoring` : couche separee de scoring, uniquement apres stabilisation des donnees.

## 10. Proposition de futurs modules

Architecture future possible :

```text
ESGInformationExtraction/
├── schemas/
│   ├── document_record.py
│   ├── page_record.py
│   ├── section_record.py
│   ├── metric_record.py
│   ├── evidence_record.py
│   └── quality_check_record.py
├── parsing/
├── section_detection/
├── extraction/
├── quality_control/
├── outputs/
└── README.md
```

Cette architecture ne doit pas etre branchee au pipeline actuel tant que `ESGFinalCorpus` n'est pas stabilise et audite. Elle doit lire le corpus final comme entree immuable.

## 11. Schemas de donnees a preparer

### DocumentRecord

Champs recommandes :

- `document_id`
- `canonical_document_id`
- `sha256`
- `company_name`
- `company_slug`
- `fiscal_year`
- `official_doc_type`
- `official_doc_type_label`
- `document_path`
- `manifest_path`
- `references_path`
- `source_url`
- `source_title`
- `selection_status`
- `validation_status`
- `created_at`

### PageRecord

Champs recommandes :

- `page_id`
- `document_id`
- `page_number`
- `text`
- `char_count`
- `language`
- `extraction_status`
- `has_tables`
- `has_images`
- `parser_version`

### SectionRecord

Champs recommandes :

- `section_id`
- `document_id`
- `page_start`
- `page_end`
- `section_title`
- `section_type`
- `section_path`
- `confidence`
- `detection_method`

### MetricRecord

Champs recommandes :

- `metric_id`
- `company_slug`
- `fiscal_year`
- `metric_name`
- `metric_category`
- `value_raw`
- `value_normalized`
- `unit`
- `period`
- `scope`
- `source_document_id`
- `evidence_id`
- `confidence`

### EvidenceRecord

Champs recommandes :

- `evidence_id`
- `document_id`
- `page_number`
- `section_id`
- `quote`
- `table_id`
- `bbox`
- `source_url`
- `extraction_method`
- `confidence`

### QualityCheckRecord

Champs recommandes :

- `quality_check_id`
- `target_type`
- `target_id`
- `check_name`
- `status`
- `severity`
- `message`
- `created_at`
- `review_required`

## 12. Feuille de route recommandee

### Phase 1 - Stabilisation documentaire

Finaliser les runs pilotes, verifier les sorties run-scoped, et geler les contrats v1.

### Phase 2 - Audit des sorties Onyxia

Analyser `task_log.csv`, `final_summary.json`, les summaries post-processing, la couverture par entreprise/annee/type.

### Phase 3 - Documentation des contrats

Documenter les schemas actuels de manifests, registres, index taxonomique, validation et selection.

### Phase 4 - Prototypes de parsing isoles

Tester plusieurs parseurs sur une copie de quelques documents selectionnes, sans brancher au pipeline principal.

### Phase 5 - Section detection

Construire une detection de sections ESG robuste, multilingue et auditable.

### Phase 6 - Extraction metrique controlee

Extraire quelques indicateurs pilotes avec preuves, unites, annees et controle de source.

### Phase 7 - Controle qualite

Ajouter des controles automatiques et une file de revue humaine.

### Phase 8 - Base d'indicateurs ESG

Normaliser les indicateurs dans une base versionnee et traçable.

### Phase 9 - Scoring ESG

Construire les scores uniquement apres stabilisation de la base d'indicateurs.

## 13. Questions ouvertes

- Quels types documentaires sont prioritaires pour la future extraction ?
- Faut-il commencer par URD, sustainability statement, climate report, vigilance plan ou assurance report ?
- Quel niveau de parsing est necessaire : page, section, paragraphe, tableau ?
- L'extraction doit-elle etre par regles, modeles, LLM, ou approche hybride ?
- Comment traiter les tableaux et les unites ?
- Comment gerer le multilingue francais / anglais ?
- Comment gerer les versions de documents et les corrections d'entreprise ?
- Quelle granularite d'evidence est requise : page, citation, bounding box ?
- Quel format de stockage final choisir : CSV, Parquet, SQLite, PostgreSQL ?
- Quelle gouvernance de validation humaine mettre en place ?
- Comment versionner les schemas et les sorties ?

## 14. Conclusion

Le projet ESG dispose deja d'une architecture documentaire solide pour passer de la recherche web a un corpus final exploitable. La separation entre retrievers, post-processing, corpus taxonomique, validation et selection finale est claire. L'isolation par `run_id` et la preparation Onyxia vont dans le bon sens pour industrialiser les runs longs.

La priorite immediate est de stabiliser les sorties Onyxia, d'auditer le pilot intermediaire, puis seulement ensuite de lancer le CAC40 complet. Il faut eviter toute modification des retrievers et des manifests pendant le run. L'extraction ESG doit rester une phase separee, construite sur `ESGFinalCorpus` comme entree stable et auditee.


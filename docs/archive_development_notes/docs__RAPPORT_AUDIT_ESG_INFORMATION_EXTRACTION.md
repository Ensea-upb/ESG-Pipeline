# Rapport d'audit de ESGInformationExtraction

## 1. Resume executif

`ESGInformationExtraction` est un module prototype destine a preparer la future extraction d'informations ESG a partir de `ESGFinalCorpus`. Il est separe du pipeline documentaire principal, ce qui est une bonne decision d'architecture : il ne depend pas des retrievers et ses sorties sont rangees dans `ESGInformationExtraction/outputs/<run_id>/`.

L'etat actuel correspond a une premiere maquette fonctionnelle : schemas Pydantic, scan du corpus final, extraction de texte avec `pdfplumber`, detection de sections par regles, extraction de candidats metriques par mots-cles/regex, evidence store et controles qualite simples.

Le module n'est pas encore pret pour produire une base d'indicateurs ESG fiable. Les sorties observees contiennent des candidats bruts, des faux positifs probables, des ranges de sections invalides, et des chemins Windows globaux pointant vers `C:\Users\hp\Desktop\ESG\ESGFinalCorpus`. Il faut donc le traiter comme un prototype experimental isole, pas comme une couche de production.

## 2. Perimetre audite

Chemin audite :

```text
C:\Users\hp\Desktop\ESG\ESGInformationExtraction
```

Fichiers et dossiers inspectes :

- `README.md`
- `requirements.txt`
- `config/extraction_config.yaml`
- `config/metric_catalog_v0.yaml`
- `config/section_taxonomy_v0.yaml`
- `schemas/*.py`
- `document_base/build_document_base.py`
- `parsing/pdf_text_parser.py`
- `parsing/page_index_builder.py`
- `section_detection/heading_detector.py`
- `section_detection/section_index_builder.py`
- `extraction/metric_candidate_extractor.py`
- `extraction/unit_normalizer.py`
- `evidence/evidence_store.py`
- `quality_control/quality_checks.py`
- `tests/test_schemas.py`
- `outputs/*/*.jsonl`

Commandes legeres executees :

- lecture de fichiers ;
- comptage des lignes JSONL ;
- compilation Python legere avec `python -m compileall -q ESGInformationExtraction` ;
- tentative de `python -m pytest ESGInformationExtraction\tests`, non executee car `pytest` n'est pas installe.

## 3. Architecture observee

Structure principale :

```text
ESGInformationExtraction/
├── config/
├── document_base/
├── evidence/
├── extraction/
├── outputs/
├── parsing/
├── quality_control/
├── schemas/
├── section_detection/
├── tests/
├── README.md
└── requirements.txt
```

Flux conceptuel attendu :

```text
ESGFinalCorpus
→ document_base.jsonl
→ page_index.jsonl
→ section_index.jsonl
→ metric_candidates / MetricRecord
→ evidence_store.jsonl
→ quality_report.jsonl
```

Le flux est bien separe du pipeline d'ingestion documentaire. C'est important : la future extraction ESG doit rester une phase independante, lancee seulement apres stabilisation du corpus final.

## 4. Analyse des composants

### 4.1 Schemas

Les schemas Pydantic existent :

- `DocumentRecord`
- `PageRecord`
- `SectionRecord`
- `MetricRecord`
- `EvidenceRecord`
- `QualityCheckRecord`

Points solides :

- Les objets de base sont clairement separes.
- `schema_version` existe dans chaque record.
- Les champs principaux de tracabilite sont presents : `document_id`, `company_slug`, `fiscal_year`, `official_doc_type`.
- Les records restent simples et lisibles.

Points fragiles :

- `DocumentRecord.selection_status` accepte seulement `selected`, `candidate`, `unknown`, alors que le pipeline documentaire produit des statuts plus riches comme `selected_needs_review`.
- `DocumentRecord.validation_status` accepte `validated`, `pending`, `rejected`, `unknown`, mais le post-processing produit des statuts comme `likely_valid`, `needs_review`, `likely_wrong_company`.
- `MetricRecord` existe, mais aucune sortie `metric_candidates.jsonl` ou `metric_records.jsonl` n'a ete observee dans le dernier output.
- Le lien complet `MetricRecord -> EvidenceRecord -> SectionRecord -> PageRecord -> DocumentRecord` n'est pas encore materialise dans les sorties.

### 4.2 Document base

Module : `document_base/build_document_base.py`

Role :

- scanner un dossier `ESGFinalCorpus` ;
- detecter les `document.pdf` ;
- lire le `manifest.json` voisin ;
- produire un `DocumentRecord` par document.

Points solides :

- lecture seule du corpus source ;
- ecriture separee dans `outputs/<run_id>/`;
- fallback si le manifest est absent ou illisible.

Points fragiles :

- les sorties inspectees pointent vers le corpus global Windows `C:\Users\hp\Desktop\ESG\ESGFinalCorpus`, pas vers un `ESGOrchestrator/runs/<run_id>/ESGFinalCorpus`;
- `document_id` est regenere avec `uuid4` a chaque run, donc il n'est pas stable entre deux executions ;
- `selection_status` est force a `candidate`, ce qui perd l'information issue du `DocumentSelector`;
- `validation_status` reste souvent `unknown`.

### 4.3 Parsing PDF

Module : `parsing/pdf_text_parser.py`

Role :

- extraire le texte page par page via `pdfplumber`;
- detecter si des tables existent ;
- fournir une version iterative pour les grands PDFs.

Points solides :

- implementation simple ;
- lecture seule ;
- erreur explicite si `pdfplumber` manque ;
- version iterative utile pour limiter la memoire.

Points fragiles :

- `parse_pdf_pages()` charge toutes les pages en memoire ;
- pas de limite effective `max_pages_per_doc` appliquee par le parser ;
- pas de resume d'erreurs par PDF ;
- pas de gestion fine des PDFs chiffrés, corrompus, scannes ou tres volumineux ;
- pas d'OCR, ce qui est acceptable pour v0 mais doit etre documente dans les outputs.

### 4.4 Page index

Module : `parsing/page_index_builder.py`

Role :

- convertir les pages brutes en `PageRecord`.

Points solides :

- structure de page claire ;
- `extraction_status` distingue `ok` et `empty`.

Points fragiles :

- `write_page_index()` ouvre le fichier en mode append (`"a"`), donc une relance sur le meme output peut dupliquer les pages ;
- pas de garde contre les doublons de `page_id` ou de `(document_id, page_number)`;
- pas de hash ou signature de page.

### 4.5 Detection de sections

Modules :

- `section_detection/heading_detector.py`
- `section_detection/section_index_builder.py`

Role :

- detecter des titres candidats par heuristiques ;
- classifier les titres via `section_taxonomy_v0.yaml`;
- produire des `SectionRecord`.

Points solides :

- approche simple, interpretable, sans LLM ;
- taxonomy separee dans YAML ;
- score de confiance rudimentaire.

Probleme important detecte :

Dans la sortie `outputs/20260510_071351/section_index.jsonl`, un grand nombre de sections ont `page_end < page_start`.

Exemple observe :

```json
{
  "section_title": "OUR MODEL",
  "page_start": 2,
  "page_end": 1
}
```

Cause probable :

- plusieurs headings detectes sur la meme page ;
- `page_end` est calcule comme `page_start du heading suivant - 1`;
- si le heading suivant est sur la meme page, alors `page_end = page_start - 1`.

Impact :

- association evidence -> section faussee ;
- sections invalides ;
- extraction aval difficilement fiable.

Autre signal :

- beaucoup de titres semblent venir de tables des matieres ou de lignes courtes non structurelles.

### 4.6 Extraction de candidats metriques

Modules :

- `extraction/metric_candidate_extractor.py`
- `extraction/unit_normalizer.py`

Role :

- detecter des lignes contenant des mots-cles ESG ;
- extraire une valeur numerique proche ;
- normaliser quelques unites.

Points solides :

- catalogue metrique externe ;
- extraction volontairement prudente avec confiance faible ;
- normalisation d'unites separee.

Points fragiles :

- regex trop generale : elle peut capturer des numeros de page, annees, references ou valeurs non ESG ;
- pas de validation du contexte ;
- pas de distinction claire entre valeur, annee, page, note, rang ou pourcentage ;
- `unit_normalizer.normalize_unit()` n'est pas encore relie a une production persistante de `MetricRecord`;
- aucun fichier `metric_candidates.jsonl` n'a ete trouve dans les outputs inspectes alors que `extraction_config.yaml` le declare.

### 4.7 Evidence store

Module : `evidence/evidence_store.py`

Role :

- transformer des candidats metriques en `EvidenceRecord`;
- associer chaque evidence a une section si possible.

Points solides :

- evidence textuelle tracee par page ;
- lien possible vers `section_id`;
- methode d'extraction indiquee.

Points fragiles :

- l'evidence ne porte pas le `metric_id`, donc il faut une autre table pour relier evidence et metrique ;
- comme les sections peuvent avoir des ranges invalides, l'association evidence -> section peut etre fausse ;
- les sorties contiennent de nombreux extraits courts issus de sommaires ou de lignes non metriques.

### 4.8 Quality control

Module : `quality_control/quality_checks.py`

Role :

- verifier l'existence des PDF ;
- verifier la coherence fiscal_year document/pages ;
- detecter pages vides ;
- detecter absence d'evidence ;
- controler la confiance minimale.

Points solides :

- bonnes briques conceptuelles ;
- checks separes ;
- severite et `review_required`.

Points fragiles :

- le dernier output inspecte `20260510_071351` ne contient pas `quality_report.jsonl`;
- les checks ne semblent pas encore orchestras dans un script de pipeline complet ;
- pas encore de controle structurel sur les sections invalides ;
- pas encore de controle sur les valeurs metriques incoherentes.

## 5. Sorties observees

Runs presents dans `outputs/` :

| Run | document_base | page_index | section_index | evidence_store | quality_report |
|---|---:|---:|---:|---:|---:|
| 20260510_064251 | 2 | 100 | 5203 | 0 | 5 |
| 20260510_064721 | 1 | 484 | 9972 | 0 | 10 |
| 20260510_065556 | 2 | 1360 | 3236 | 0 | 18 |
| 20260510_065921 | 2 | 1360 | 3236 | 0 | 18 |
| 20260510_070940 | 1 | 680 | 1618 | 1428 | 9 |
| 20260510_071351 | 37 | environ 4 000 pages | plus de 12 000 sections | 5517 | absent |

Dernier run observe : `20260510_071351`

Repartition des documents par entreprise :

| company_slug | documents |
|---|---:|
| air-liquide | 1 |
| bnp-paribas | 1 |
| lvmh | 12 |
| schneider-electric | 11 |
| totalenergies | 12 |

Repartition des documents par type officiel :

| official_doc_type | documents |
|---|---:|
| 01_urd_annual_report | 5 |
| 02_sustainability_statement_csrd_esrs | 3 |
| 03_climate_report_tcfd_transition_plan | 3 |
| 04_vigilance_plan | 2 |
| 05_half_year_financial_report | 3 |
| 07_code_ethique | 1 |
| 08_anticorruption_policy | 3 |
| 11_environmental_policy | 1 |
| 12_supplier_code_of_conduct | 1 |
| 13_investor_presentations | 2 |
| 14_earnings_call_transcripts | 1 |
| 16_agm_minutes_resolutions | 3 |
| 17_cdp_response | 3 |
| 18_sbti_validation | 3 |
| 19_third_party_assurance_report | 3 |

Point d'attention majeur :

- les documents du dernier run semblent correspondre au profil intermediaire 5 entreprises x 2 annees, mais les chemins contenus dans `document_base.jsonl` pointent vers le dossier global `ESGFinalCorpus`, pas vers un corpus final isole par `run_id`.

## 6. Etat de robustesse

Ce qui est robuste :

- architecture isolee du pipeline documentaire ;
- aucune dependance directe aux retrievers ;
- schemas Pydantic presents ;
- config YAML separee ;
- approche non LLM et interpretable ;
- compilation Python OK ;
- sorties JSONL lisibles ;
- dependances simples : `pydantic`, `pdfplumber`, `pyyaml`.

Ce qui est immature :

- pas de script CLI/pipeline unique clairement identifie ;
- pas de resume d'execution `extraction_summary.json` observe ;
- pas de selection explicite d'un `ESGFinalCorpus` run-scoped ;
- pas de persistance des `MetricRecord`;
- pas de controle qualite complet dans le dernier run ;
- append mode dans plusieurs writers, donc risque de doublons ;
- identifiants UUID non stables entre executions ;
- section detection trop bruitee ;
- ranges de sections invalides ;
- extraction metrique encore trop faible pour tout usage analytique.

## 7. Risques techniques principaux

### CRITICAL

1. **Risque de corpus source non maitrise**

   Les outputs inspectes pointent vers `C:\Users\hp\Desktop\ESG\ESGFinalCorpus`, c'est-a-dire le corpus global local, pas necessairement le `ESGFinalCorpus` isole du run Onyxia.

2. **Sections invalides**

   Le calcul de `page_end` produit de nombreux cas `page_end < page_start`, ce qui casse le contrat logique d'une section.

3. **Candidats non fiables**

   Les evidences ne doivent pas etre interpretees comme indicateurs ESG. Elles sont des candidats faibles, souvent contextuels ou issus de sommaires.

### WARNING

1. **Pas de pipeline executable standard**

   Aucun script principal de type `run_extraction.py` n'a ete observe.

2. **Pas de `metric_candidates.jsonl` observe**

   Le fichier est declare dans la config mais absent dans les outputs inspectes.

3. **Qualite non produite dans le dernier run**

   Le dernier dossier d'output ne contient pas `quality_report.jsonl`.

4. **Encodage a verifier**

   Des sequences comme `Ã©`, `â€™`, `Â` apparaissent dans plusieurs lectures. Une partie peut venir de l'affichage PowerShell, mais certaines sequences apparaissent aussi dans les JSONL. Il faut verifier l'encodage reel avant de construire une base textuelle.

5. **Risque de duplication**

   Plusieurs writers utilisent le mode append. Relancer une etape sur le meme output peut ajouter des doublons.

## 8. Recommandations immediates

Ne pas brancher ce module au pipeline Onyxia tant que `ESGFinalCorpus` n'est pas stabilise et audite.

Actions recommandees sans changer la logique documentaire :

1. Ajouter un script d'audit specifique des outputs `ESGInformationExtraction`.
2. Ajouter un script CLI unique plus tard, mais seulement apres stabilisation du contrat d'entree.
3. Imposer un `--corpus-path` explicite pointant vers un `ESGOrchestrator/runs/<run_id>/ESGFinalCorpus`.
4. Produire systematiquement un `extraction_summary.json`.
5. Corriger le calcul des ranges de sections avant toute extraction metrique serieuse.
6. Ajouter un controle qualite sur les sections :
   - `page_start <= page_end` si `page_end` existe ;
   - section non vide ;
   - section non issue du sommaire si detectee.
7. Remplacer les writes append par une strategie explicite :
   - soit nouveau output_dir a chaque run ;
   - soit overwrite controle ;
   - soit append avec deduplication.
8. Ne pas produire de score ESG a partir de ces outputs.

## 9. Architecture cible recommandee

Avant toute extraction massive, stabiliser une sequence stricte :

```text
ESGFinalCorpus run-scoped
→ build_document_base
→ parse_pages_limited_or_full
→ page_index
→ section_detection_v1
→ section_quality_checks
→ metric_candidate_extraction
→ metric_record_building
→ evidence_linking
→ quality_report
→ human_review_queue
```

Sorties attendues a terme :

```text
outputs/<run_id>/
├── document_base.jsonl
├── page_index.jsonl
├── section_index.jsonl
├── metric_candidates.jsonl
├── metric_records.jsonl
├── evidence_store.jsonl
├── quality_report.jsonl
└── extraction_summary.json
```

## 10. Priorites de correction futures

1. Stabiliser l'entree : utiliser uniquement `ESGOrchestrator/runs/<run_id>/ESGFinalCorpus`.
2. Creer un `run_extraction.py` non ambigu avec `--corpus-path`, `--output-dir`, `--max-docs`, `--max-pages`.
3. Corriger `section_index_builder` pour eviter `page_end < page_start`.
4. Ajouter un filtre anti-table-des-matieres dans `heading_detector`.
5. Produire des `MetricRecord` persistants.
6. Relier explicitement `MetricRecord.evidence_id`.
7. Ajouter `extraction_summary.json`.
8. Ajouter des tests unitaires pour :
   - ranges de sections ;
   - normalisation d'unites ;
   - extraction regex ;
   - scan de corpus minimal ;
   - non regression sur chemins run-scoped.

## 11. Decision recommandee

Le module doit rester en **sandbox de recherche** pour l'instant.

Il est utile pour prototyper :

- parsing PDF ;
- detection de sections ;
- extraction de candidats ;
- schemas de donnees ;
- controles qualite.

Il ne doit pas encore etre considere comme :

- une base d'indicateurs ESG ;
- un moteur d'extraction fiable ;
- un composant production du pipeline Onyxia ;
- une source de scoring ESG.

## 12. Conclusion

`ESGInformationExtraction` est une bonne premiere brique d'architecture pour la phase apres `ESGFinalCorpus`. Sa separation avec les retrievers et le post-processing est saine. Les schemas sont utiles et la chaine conceptuelle est claire.

Mais le niveau actuel est celui d'un prototype exploratoire. Les sorties montrent que la detection de sections est trop bruitee, que les preuves extraites sont des candidats faibles, et que le lien avec le corpus final isole par run n'est pas encore garanti.

La priorite immediate est de ne pas accelerer vers le scoring ou l'extraction massive. Il faut d'abord stabiliser le corpus final Onyxia, puis durcir ce module avec un contrat d'entree explicite, un pipeline CLI reproductible, un resume d'execution, et des controles qualite structurels.

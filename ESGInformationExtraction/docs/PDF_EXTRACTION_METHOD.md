# Methode cible d'extraction PDF

## 1. Objectif

Ce document specifie la methode cible pour construire un moteur generique d'extraction PDF dans `ESGInformationExtraction`.

L'objectif n'est pas encore d'extraire des indicateurs ESG. L'objectif est d'abord de transformer un PDF en representation documentaire structuree, traçable et exploitable par des moteurs aval.

Le moteur PDF doit extraire separement :

- les pages ;
- les blocs de texte ;
- les titres ;
- les paragraphes ;
- les listes ;
- les notes ;
- les tableaux ;
- les cellules de tableaux ;
- les figures ;
- les graphiques ;
- les legendes ;
- l'ordre de lecture ;
- les sections ;
- les preuves localisees.

Le moteur doit rester strictement non destructif :

- lecture seule du PDF ;
- aucune modification du PDF source ;
- aucune modification des manifests originaux ;
- aucune interpretation ESG definitive ;
- aucune production de score ESG.

## 2. Principe fondamental

Il faut separer deux couches :

```text
PDF brut
→ moteur documentaire PDF
→ representation structuree
→ moteur d'extraction ESG
→ candidats metriques
→ validation / controle qualite
→ indicateurs valides plus tard
```

Le moteur documentaire PDF decrit la structure du document. Il ne decide pas si une valeur est un indicateur ESG fiable.

Le moteur ESG interprete ensuite cette structure pour produire des candidats. Ces candidats ne doivent jamais etre consideres comme des indicateurs valides sans controle qualite.

## 3. Moteur documentaire PDF vs moteur d'extraction ESG

### 3.1 Moteur documentaire PDF

Le moteur documentaire PDF repond a la question :

> Que contient physiquement et logiquement le PDF ?

Il extrait :

- pages ;
- zones de texte ;
- titres ;
- paragraphes ;
- listes ;
- notes ;
- tableaux ;
- cellules ;
- figures ;
- graphiques ;
- legendes ;
- ordre de lecture ;
- sections ;
- preuves localisables.

Il doit conserver les coordonnees `bbox` autant que possible.

Il produit des objets structurels, par exemple :

- `PageRecord`
- `TextBlockRecord`
- `TableRecord`
- `TableCellRecord`
- `FigureRecord`
- `SectionRecord`
- `EvidenceRecord`
- `QualityCheckRecord`

### 3.2 Moteur d'extraction ESG

Le moteur d'extraction ESG repond a la question :

> Quels candidats d'information ESG peut-on proposer a partir de la structure documentaire ?

Il peut produire :

- `MetricCandidateRecord`
- liens vers les preuves ;
- contexte textuel ;
- unite brute ;
- valeur brute ;
- score de confiance faible ou moyen ;
- statut de revue humaine.

Il ne doit pas produire directement un score ESG.

Il ne doit pas transformer un candidat en indicateur valide sans couche de validation.

## 4. Architecture cible

Architecture cible du moteur PDF :

```text
pdf_engine/
├── pdf_loader.py
├── pdf_classifier.py
├── layout_extractor.py
├── text_block_extractor.py
├── table_extractor.py
├── figure_extractor.py
├── reading_order_builder.py
└── extraction_diagnostics.py
```

### 4.1 `pdf_loader.py`

Responsabilites :

- ouvrir le PDF en lecture seule ;
- detecter les erreurs d'ouverture ;
- detecter le nombre de pages ;
- identifier les PDFs proteges, corrompus ou vides ;
- fournir un objet de lecture au reste du moteur.

### 4.2 `pdf_classifier.py`

Responsabilites :

- classifier techniquement le PDF ;
- distinguer PDF texte, PDF image, PDF mixte, PDF probablement scanne ;
- estimer si une extraction texte directe suffit ;
- signaler si OCR futur necessaire.

### 4.3 `layout_extractor.py`

Responsabilites :

- extraire la mise en page ;
- detecter les zones ;
- conserver les coordonnees ;
- produire une representation page par page.

### 4.4 `text_block_extractor.py`

Responsabilites :

- extraire les blocs de texte ;
- distinguer titres, paragraphes, listes, notes, footers et headers si possible ;
- conserver `bbox`, page, ordre local et contenu brut.

### 4.5 `table_extractor.py`

Responsabilites :

- detecter les tableaux ;
- extraire les cellules ;
- conserver lignes, colonnes, spans et coordonnees ;
- signaler les tableaux detectes mais non parsables.

### 4.6 `figure_extractor.py`

Responsabilites :

- detecter les figures, graphiques et images ;
- extraire les legendes candidates ;
- conserver les coordonnees ;
- ne pas interpreter les graphiques comme donnees chiffrees en v0.

### 4.7 `reading_order_builder.py`

Responsabilites :

- reconstruire l'ordre de lecture ;
- ordonner blocs, tableaux, figures et legendes ;
- gerer les colonnes ;
- produire un ordre stable par page et par document.

### 4.8 `extraction_diagnostics.py`

Responsabilites :

- produire les diagnostics ;
- compter les pages vides ;
- signaler les erreurs ;
- evaluer la couverture texte/tableaux ;
- produire les `QualityCheckRecord`.

## 5. Sorties attendues

Le moteur documentaire PDF doit produire :

```text
outputs/<run_id>/
├── page_index.jsonl
├── text_blocks.jsonl
├── table_index.jsonl
├── figure_index.jsonl
├── section_index.jsonl
├── evidence_store.jsonl
├── quality_report.jsonl
└── extraction_summary.json
```

### 5.1 `page_index.jsonl`

Une ligne par page extraite.

### 5.2 `text_blocks.jsonl`

Une ligne par bloc textuel.

### 5.3 `table_index.jsonl`

Une ligne par tableau detecte, avec cellules associees ou references vers `TableCellRecord`.

### 5.4 `figure_index.jsonl`

Une ligne par figure, graphique ou image detectee.

### 5.5 `section_index.jsonl`

Une ligne par section documentaire detectee.

### 5.6 `evidence_store.jsonl`

Une ligne par preuve localisee. Une preuve est un extrait reutilisable par un moteur ESG, mais elle n'est pas encore une conclusion.

### 5.7 `quality_report.jsonl`

Une ligne par controle qualite.

### 5.8 `extraction_summary.json`

Un resume global de l'extraction :

- nombre de documents ;
- nombre de pages ;
- nombre de pages parsees ;
- nombre de pages en erreur ;
- nombre de blocs ;
- nombre de tableaux ;
- nombre de figures ;
- nombre de sections ;
- nombre d'alertes ;
- duree d'execution ;
- version du moteur ;
- parametres utilises.

## 6. Objets de donnees cibles

### 6.1 `DocumentRecord`

Role :

Representer un document source issu de `ESGFinalCorpus`.

Champs obligatoires :

- `document_id`
- `canonical_document_id`
- `sha256`
- `company_name`
- `company_slug`
- `fiscal_year`
- `official_doc_type`
- `document_path`

Champs de tracabilite :

- `manifest_path`
- `references_path`
- `source_url`
- `source_title`
- `run_id`
- `created_at`
- `schema_version`

Niveau de confiance :

- `extraction_ready`
- `document_quality_status`
- `confidence`

Liens :

- parent de `PageRecord`
- parent indirect de `TextBlockRecord`, `TableRecord`, `FigureRecord`, `SectionRecord`, `EvidenceRecord`

### 6.2 `PageRecord`

Role :

Representer une page physique du PDF.

Champs obligatoires :

- `page_id`
- `document_id`
- `page_number`
- `width`
- `height`
- `rotation`
- `extraction_status`

Champs de tracabilite :

- `company_slug`
- `fiscal_year`
- `official_doc_type`
- `parser_name`
- `parser_version`
- `created_at`

Niveau de confiance :

- `text_extraction_confidence`
- `layout_extraction_confidence`
- `has_text`
- `has_tables`
- `has_figures`

Liens :

- enfant de `DocumentRecord`
- parent de `TextBlockRecord`, `TableRecord`, `FigureRecord`

### 6.3 `TextBlockRecord`

Role :

Representer une unite textuelle localisee : titre, paragraphe, liste, note, header, footer ou legende.

Champs obligatoires :

- `text_block_id`
- `document_id`
- `page_id`
- `page_number`
- `block_type`
- `text`
- `bbox`
- `reading_order`

Types possibles :

- `title`
- `paragraph`
- `list_item`
- `note`
- `caption`
- `header`
- `footer`
- `unknown`

Champs de tracabilite :

- `source_extractor`
- `created_at`
- `schema_version`

Niveau de confiance :

- `block_type_confidence`
- `reading_order_confidence`

Liens :

- enfant de `PageRecord`
- peut etre rattache a `SectionRecord`
- peut servir de source a `EvidenceRecord`

### 6.4 `TableRecord`

Role :

Representer un tableau detecte sur une ou plusieurs pages.

Champs obligatoires :

- `table_id`
- `document_id`
- `page_id`
- `page_number`
- `bbox`
- `row_count`
- `column_count`
- `extraction_status`

Champs de tracabilite :

- `caption_text`
- `source_extractor`
- `created_at`
- `schema_version`

Niveau de confiance :

- `table_detection_confidence`
- `structure_confidence`

Liens :

- enfant de `PageRecord`
- parent de `TableCellRecord`
- peut etre rattache a `SectionRecord`
- peut servir de source a `EvidenceRecord`

### 6.5 `TableCellRecord`

Role :

Representer une cellule de tableau.

Champs obligatoires :

- `cell_id`
- `table_id`
- `document_id`
- `page_id`
- `row_index`
- `column_index`
- `text`
- `bbox`

Champs de tracabilite :

- `row_span`
- `column_span`
- `is_header`
- `created_at`
- `schema_version`

Niveau de confiance :

- `cell_extraction_confidence`
- `cell_type_confidence`

Liens :

- enfant de `TableRecord`
- peut servir de source a `EvidenceRecord`
- peut alimenter `MetricCandidateRecord`

### 6.6 `FigureRecord`

Role :

Representer une figure, image, graphique ou schema.

Champs obligatoires :

- `figure_id`
- `document_id`
- `page_id`
- `page_number`
- `figure_type`
- `bbox`
- `extraction_status`

Types possibles :

- `image`
- `chart`
- `diagram`
- `logo`
- `map`
- `unknown`

Champs de tracabilite :

- `caption_text`
- `source_extractor`
- `created_at`
- `schema_version`

Niveau de confiance :

- `figure_detection_confidence`
- `figure_type_confidence`

Liens :

- enfant de `PageRecord`
- peut etre rattache a `SectionRecord`
- peut produire une `EvidenceRecord` si une legende est exploitable

### 6.7 `SectionRecord`

Role :

Representer une section logique du document.

Champs obligatoires :

- `section_id`
- `document_id`
- `section_title`
- `section_type`
- `page_start`
- `page_end`
- `start_element_id`
- `end_element_id`

Champs de tracabilite :

- `parent_section_id`
- `source_heading_block_id`
- `created_at`
- `schema_version`

Niveau de confiance :

- `section_detection_confidence`
- `section_type_confidence`

Liens :

- enfant de `DocumentRecord`
- parent logique de `TextBlockRecord`, `TableRecord`, `FigureRecord`
- source de contexte pour `EvidenceRecord` et `MetricCandidateRecord`

Regle importante :

`page_end` ne doit jamais etre inferieur a `page_start`.

### 6.8 `EvidenceRecord`

Role :

Representer une preuve localisee reutilisable par un moteur d'extraction ESG.

Champs obligatoires :

- `evidence_id`
- `document_id`
- `page_id`
- `page_number`
- `evidence_type`
- `quote`
- `bbox`

Types possibles :

- `text`
- `table_cell`
- `table_row`
- `figure_caption`
- `section_context`

Champs de tracabilite :

- `section_id`
- `text_block_id`
- `table_id`
- `cell_id`
- `figure_id`
- `source_url`
- `created_at`
- `schema_version`

Niveau de confiance :

- `evidence_confidence`
- `localization_confidence`

Liens :

- pointe vers un element source ;
- peut etre referencee par `MetricCandidateRecord`.

### 6.9 `MetricCandidateRecord`

Role :

Representer un candidat metrique ESG extrait automatiquement.

Ce record n'est pas un indicateur valide.

Champs obligatoires :

- `metric_candidate_id`
- `metric_id`
- `metric_name`
- `document_id`
- `evidence_id`
- `value_raw`
- `unit_raw`
- `extraction_method`

Champs de tracabilite :

- `company_slug`
- `fiscal_year`
- `official_doc_type`
- `page_number`
- `section_id`
- `created_at`
- `schema_version`

Niveau de confiance :

- `confidence`
- `review_required`
- `validation_status`

Liens :

- enfant logique de `DocumentRecord`
- lie a `EvidenceRecord`
- peut utiliser `SectionRecord`, `TableCellRecord` ou `TextBlockRecord` comme contexte.

Regle importante :

Un `MetricCandidateRecord` ne doit jamais etre considere comme un indicateur ESG valide sans validation.

### 6.10 `QualityCheckRecord`

Role :

Representer un controle qualite applique a un document, une page, un bloc, une table, une section, une preuve ou un candidat metrique.

Champs obligatoires :

- `quality_check_id`
- `target_type`
- `target_id`
- `check_name`
- `status`
- `severity`

Champs de tracabilite :

- `document_id`
- `page_id`
- `created_at`
- `schema_version`

Niveau de confiance :

- `confidence`
- `review_required`

Liens :

- pointe vers l'objet controle ;
- alimente `quality_report.jsonl`.

## 7. Coordonnees et bbox

Chaque element localise doit conserver une `bbox` quand le moteur peut l'obtenir.

Format recommande :

```json
{
  "x0": 0.0,
  "y0": 0.0,
  "x1": 100.0,
  "y1": 50.0,
  "coordinate_system": "pdf_points",
  "page_number": 1
}
```

Les coordonnees servent a :

- verifier la localisation ;
- reconstruire l'ordre de lecture ;
- relier preuves et sources ;
- permettre une revue humaine future ;
- relire un extrait dans le PDF original.

## 8. Ordre de lecture

L'ordre de lecture doit etre explicite.

Chaque `TextBlockRecord`, `TableRecord` et `FigureRecord` doit avoir :

- `reading_order`;
- `page_number`;
- `bbox`;
- `parent_section_id` si connu.

Le moteur doit tenir compte :

- des colonnes ;
- des headers et footers ;
- des encadres ;
- des tableaux ;
- des legendes ;
- des notes.

L'ordre de lecture ne doit pas etre confondu avec l'ordre brut d'extraction du parser PDF.

## 9. Gestion des tableaux

Les tableaux doivent etre extraits comme objets separes.

Un tableau peut produire :

- `TableRecord`
- plusieurs `TableCellRecord`
- eventuellement des `EvidenceRecord`
- eventuellement des `MetricCandidateRecord`

Le moteur doit distinguer :

- tableau detecte mais non parse ;
- tableau parse avec faible confiance ;
- tableau parse avec structure fiable.

Les donnees issues de tableaux doivent conserver :

- ligne ;
- colonne ;
- texte brut ;
- bbox ;
- relation avec le tableau parent.

## 10. Gestion des figures et graphiques

Les figures doivent etre detectees mais pas interpretees comme donnees chiffrees en v0.

Le moteur peut extraire :

- presence d'une figure ;
- type probable ;
- bbox ;
- legende ;
- page ;
- section rattachee.

L'interpretation des graphiques visuels doit etre repoussee a une phase ulterieure.

## 11. Sections

Une section est une structure logique construite a partir :

- des titres ;
- de l'ordre de lecture ;
- des pages ;
- des elements suivants jusqu'au prochain titre compatible.

La detection de section doit eviter :

- les lignes de table des matieres ;
- les headers/footers ;
- les numeros de page ;
- les titres dupliques ;
- les sous-titres orphelins.

Une section doit avoir :

- un debut clair ;
- une fin logique ;
- un niveau de confiance ;
- une relation parent/enfant si possible.

## 12. Preuves localisees

Une preuve localisee est un extrait qui peut justifier une extraction future.

Elle peut venir :

- d'un bloc de texte ;
- d'une cellule ;
- d'une ligne de tableau ;
- d'une legende ;
- d'un titre de section.

Elle doit toujours pointer vers sa source :

```text
EvidenceRecord
→ document_id
→ page_id
→ section_id optionnel
→ text_block_id/table_id/cell_id/figure_id optionnel
→ bbox
```

Une preuve n'est pas une conclusion.

## 13. Controle qualite minimal

Le moteur documentaire PDF doit produire des controles qualite sur :

- PDF lisible ;
- nombre de pages ;
- pages sans texte ;
- pages avec texte tres faible ;
- extraction de layout disponible ;
- tables detectees ;
- tables non parsees ;
- figures detectees ;
- sections invalides ;
- ordre de lecture incertain ;
- absence de bbox ;
- erreurs parser.

Chaque controle doit etre trace dans `quality_report.jsonl`.

## 14. Regles de securite et de non-destruction

Le moteur doit respecter ces regles :

1. Lire les PDFs en lecture seule.
2. Ne jamais modifier `ESGFinalCorpus`.
3. Ne jamais modifier les manifests originaux.
4. Ne jamais supprimer ou deplacer un fichier source.
5. Ecrire uniquement dans `ESGInformationExtraction/outputs/<run_id>/`.
6. Ne pas lancer d'OCR massif par defaut.
7. Ne pas produire de scoring ESG.
8. Ne pas considerer les candidats comme valides.

## 15. Conclusion

La prochaine etape avant toute extraction ESG est de stabiliser un moteur documentaire PDF.

Ce moteur doit produire une representation structuree, localisee et traçable du PDF. Cette representation doit separer clairement :

- structure documentaire brute ;
- preuves localisees ;
- candidats ESG ;
- indicateurs valides futurs.

Tant que cette separation n'est pas stable, toute extraction ESG doit rester experimentale.

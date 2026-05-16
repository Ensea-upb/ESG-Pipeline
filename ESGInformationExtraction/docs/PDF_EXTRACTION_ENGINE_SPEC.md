# PDF Extraction Engine — Technical Specification v0

## 1. Objectif technique

Le moteur PDF v0 doit transformer un fichier PDF en objets documentaires structures, localises et exploitables par les couches aval.

Il doit produire les objets suivants :

- `DocumentRecord`
- `PageRecord`
- `TextBlockRecord`
- `TableRecord`
- `TableCellRecord`
- `FigureRecord`
- `SectionRecord`
- `EvidenceRecord`
- `QualityCheckRecord`

`MetricCandidateRecord` n'appartient pas au coeur du moteur PDF. Il appartient a la couche ESG, qui interprete ensuite les objets documentaires pour proposer des candidats metriques. Le moteur PDF ne valide aucun indicateur ESG et ne produit aucun scoring.

Le moteur PDF doit etre :

- non destructif ;
- reproductible ;
- traçable ;
- limite a un PDF a la fois en v0 ;
- capable de produire des sorties partielles avec statuts explicites.

## 2. Ordre d'implementation recommande

### Phase 1 — Document loading

Objectif :

- ouvrir le PDF en lecture seule ;
- verifier que le fichier existe ;
- verifier que le header est compatible PDF ;
- calculer les metadonnees techniques initiales ;
- creer `document_record.json`.

### Phase 2 — Page extraction

Objectif :

- compter les pages ;
- creer un `PageRecord` par page ;
- collecter dimensions, rotation, statut d'extraction et metadonnees.

### Phase 3 — Text block extraction

Objectif :

- extraire le texte brut ;
- decouper le texte en blocs ;
- attribuer un type initial : `title`, `subtitle`, `paragraph`, `list_item`, `note`, `header`, `footer`, `caption`, `unknown`.

### Phase 4 — Layout and bbox extraction

Objectif :

- associer des coordonnees `bbox` aux pages et blocs ;
- conserver le systeme de coordonnees ;
- signaler les blocs sans bbox.

### Phase 5 — Reading order

Objectif :

- ordonner les blocs, tableaux, figures et captions ;
- gerer les colonnes et zones hors flux ;
- produire `reading_order` et `reading_order_confidence`.

### Phase 6 — Table detection and extraction

Objectif :

- detecter les tableaux ;
- extraire cellules, lignes et colonnes quand possible ;
- attribuer un statut explicite a chaque tableau.

### Phase 7 — Figure detection

Objectif :

- detecter figures, images, graphiques et schemas ;
- extraire bbox, type probable, caption et texte voisin ;
- ne pas lire les valeurs numeriques des graphiques en v0.

### Phase 8 — Section detection

Objectif :

- construire les sections a partir des `TextBlockRecord` de type `title` ou `subtitle` ;
- utiliser l'ordre de lecture ;
- eviter les titres de table des matieres, headers et footers ;
- garantir `page_start <= page_end`.

### Phase 9 — Evidence building

Objectif :

- construire des preuves localisees reutilisables ;
- relier chaque preuve a une source documentaire explicite ;
- ne pas tirer de conclusion ESG.

### Phase 10 — Quality checks

Objectif :

- produire les controles qualite minimaux ;
- signaler les erreurs et sorties partielles ;
- rendre l'extraction auditable.

### Phase 11 — Extraction summary

Objectif :

- produire `extraction_summary.json` ;
- decrire les compteurs, statuts, erreurs, options et duree d'execution.

## 3. Contrats de sortie

Toutes les sorties doivent etre ecrites dans :

```text
ESGInformationExtraction/outputs/<run_id>/
```

Aucune sortie ne doit etre ecrite dans `ESGFinalCorpus`.

### 3.1 `document_record.json`

Granularite :

- un fichier par PDF traite.

Champs obligatoires :

- `schema_version`: string
- `document_id`: string non vide
- `sha256`: string ou null si indisponible
- `document_path`: string
- `file_name`: string
- `page_count`: integer
- `loading_status`: string
- `created_at`: string ISO-8601

Champs optionnels :

- `canonical_document_id`: string
- `company_name`: string
- `company_slug`: string
- `fiscal_year`: integer
- `official_doc_type`: string
- `manifest_path`: string
- `references_path`: string
- `source_url`: string
- `source_title`: string

Exemple minimal :

```json
{
  "schema_version": "1.0.0",
  "document_id": "doc_001",
  "sha256": "abc123",
  "document_path": "/data/document.pdf",
  "file_name": "document.pdf",
  "page_count": 120,
  "loading_status": "readable",
  "created_at": "2026-05-10T08:00:00Z"
}
```

### 3.2 `page_index.jsonl`

Granularite :

- une ligne par page.

Champs obligatoires :

- `schema_version`: string
- `page_id`: string unique
- `document_id`: string
- `page_number`: integer, commence a 1
- `width`: number ou null
- `height`: number ou null
- `rotation`: integer ou null
- `extraction_status`: string

Champs optionnels :

- `text_char_count`: integer
- `has_text`: boolean
- `has_tables`: boolean
- `has_figures`: boolean
- `page_label`: string

Exemple minimal :

```json
{"schema_version":"1.0.0","page_id":"page_001","document_id":"doc_001","page_number":1,"width":595.0,"height":842.0,"rotation":0,"extraction_status":"ok"}
```

### 3.3 `text_blocks.jsonl`

Granularite :

- une ligne par bloc de texte.

Champs obligatoires :

- `schema_version`: string
- `text_block_id`: string unique
- `document_id`: string
- `page_id`: string
- `page_number`: integer
- `block_type`: string
- `text`: string
- `bbox`: object ou null
- `reading_order`: integer

Champs optionnels :

- `font_size`: number
- `font_name`: string
- `is_bold`: boolean
- `is_italic`: boolean
- `language`: string
- `block_type_confidence`: number
- `reading_order_confidence`: number

Exemple minimal :

```json
{"schema_version":"1.0.0","text_block_id":"tb_001","document_id":"doc_001","page_id":"page_001","page_number":1,"block_type":"title","text":"Climate strategy","bbox":{"x0":72,"y0":80,"x1":300,"y1":105,"coordinate_system":"pdf_points","page_number":1},"reading_order":1}
```

### 3.4 `table_index.jsonl`

Granularite :

- une ligne par tableau detecte.

Champs obligatoires :

- `schema_version`: string
- `table_id`: string unique
- `document_id`: string
- `page_id`: string
- `page_number`: integer
- `bbox`: object ou null
- `row_count`: integer ou null
- `column_count`: integer ou null
- `extraction_status`: string

Statuts autorises :

- `parsed`
- `detected_not_parsed`
- `failed`
- `empty`
- `low_confidence`

Champs optionnels :

- `caption_text`: string
- `structure_confidence`: number
- `table_detection_confidence`: number
- `is_multi_page`: boolean
- `continued_from_table_id`: string

Exemple minimal :

```json
{"schema_version":"1.0.0","table_id":"tbl_001","document_id":"doc_001","page_id":"page_010","page_number":10,"bbox":{"x0":40,"y0":120,"x1":550,"y1":400,"coordinate_system":"pdf_points","page_number":10},"row_count":8,"column_count":5,"extraction_status":"parsed"}
```

### 3.5 `table_cells.jsonl`

Granularite :

- une ligne par cellule de tableau.

Champs obligatoires :

- `schema_version`: string
- `cell_id`: string unique
- `table_id`: string
- `document_id`: string
- `page_id`: string
- `row_index`: integer
- `column_index`: integer
- `text`: string
- `bbox`: object ou null

Champs optionnels :

- `row_span`: integer
- `column_span`: integer
- `is_header`: boolean
- `cell_confidence`: number

Exemple minimal :

```json
{"schema_version":"1.0.0","cell_id":"cell_001","table_id":"tbl_001","document_id":"doc_001","page_id":"page_010","row_index":0,"column_index":0,"text":"Scope 1","bbox":{"x0":50,"y0":130,"x1":150,"y1":150,"coordinate_system":"pdf_points","page_number":10}}
```

### 3.6 `figure_index.jsonl`

Granularite :

- une ligne par figure, image, graphique ou schema detecte.

Champs obligatoires :

- `schema_version`: string
- `figure_id`: string unique
- `document_id`: string
- `page_id`: string
- `page_number`: integer
- `figure_type`: string
- `bbox`: object ou null
- `extraction_status`: string
- `needs_review`: boolean

Champs optionnels :

- `caption_text`: string
- `surrounding_text`: string
- `figure_detection_confidence`: number
- `figure_type_confidence`: number

Exemple minimal :

```json
{"schema_version":"1.0.0","figure_id":"fig_001","document_id":"doc_001","page_id":"page_012","page_number":12,"figure_type":"chart","bbox":{"x0":60,"y0":160,"x1":520,"y1":500,"coordinate_system":"pdf_points","page_number":12},"extraction_status":"detected","needs_review":true}
```

### 3.7 `section_index.jsonl`

Granularite :

- une ligne par section documentaire.

Champs obligatoires :

- `schema_version`: string
- `section_id`: string unique
- `document_id`: string
- `section_title`: string
- `section_type`: string
- `page_start`: integer
- `page_end`: integer
- `start_element_id`: string
- `end_element_id`: string ou null

Champs optionnels :

- `parent_section_id`: string
- `source_heading_block_id`: string
- `section_detection_confidence`: number
- `section_type_confidence`: number

Exemple minimal :

```json
{"schema_version":"1.0.0","section_id":"sec_001","document_id":"doc_001","section_title":"Climate strategy","section_type":"climate","page_start":12,"page_end":18,"start_element_id":"tb_120","end_element_id":"tb_189","section_detection_confidence":0.72}
```

### 3.8 `evidence_store.jsonl`

Granularite :

- une ligne par preuve localisee.

Champs obligatoires :

- `schema_version`: string
- `evidence_id`: string unique
- `document_id`: string
- `page_id`: string
- `page_number`: integer
- `evidence_type`: string
- `quote`: string
- `bbox`: object ou null

Champs optionnels :

- `section_id`: string
- `text_block_id`: string
- `table_id`: string
- `cell_id`: string
- `figure_id`: string
- `evidence_confidence`: number
- `localization_confidence`: number

Exemple minimal :

```json
{"schema_version":"1.0.0","evidence_id":"ev_001","document_id":"doc_001","page_id":"page_012","page_number":12,"evidence_type":"text","quote":"Scope 1 emissions decreased by 5%.","bbox":{"x0":70,"y0":240,"x1":420,"y1":255,"coordinate_system":"pdf_points","page_number":12},"text_block_id":"tb_145"}
```

### 3.9 `quality_report.jsonl`

Granularite :

- une ligne par controle qualite.

Champs obligatoires :

- `schema_version`: string
- `quality_check_id`: string unique
- `target_type`: string
- `target_id`: string
- `check_name`: string
- `status`: string
- `severity`: string

Champs optionnels :

- `document_id`: string
- `page_id`: string
- `message`: string
- `review_required`: boolean
- `created_at`: string

Exemple minimal :

```json
{"schema_version":"1.0.0","quality_check_id":"qc_001","target_type":"section","target_id":"sec_001","check_name":"section_range_valid","status":"pass","severity":"major","message":"page_start <= page_end"}
```

### 3.10 `extraction_summary.json`

Granularite :

- un fichier par execution du moteur sur un PDF.

Champs obligatoires :

- `schema_version`: string
- `document_id`: string
- `pdf_path`: string
- `output_dir`: string
- `started_at`: string
- `finished_at`: string
- `status`: string
- `page_count`: integer
- `pages_processed`: integer
- `text_blocks_count`: integer
- `tables_count`: integer
- `table_cells_count`: integer
- `figures_count`: integer
- `sections_count`: integer
- `evidence_count`: integer
- `quality_checks_count`: integer
- `errors_count`: integer
- `warnings_count`: integer

Champs optionnels :

- `engine_version`: string
- `parser_name`: string
- `parser_version`: string
- `options`: object
- `errors`: array
- `warnings`: array

Exemple minimal :

```json
{
  "schema_version": "1.0.0",
  "document_id": "doc_001",
  "pdf_path": "/data/document.pdf",
  "output_dir": "ESGInformationExtraction/outputs/run_001",
  "started_at": "2026-05-10T08:00:00Z",
  "finished_at": "2026-05-10T08:01:00Z",
  "status": "success",
  "page_count": 120,
  "pages_processed": 120,
  "text_blocks_count": 3200,
  "tables_count": 18,
  "table_cells_count": 540,
  "figures_count": 12,
  "sections_count": 80,
  "evidence_count": 0,
  "quality_checks_count": 240,
  "errors_count": 0,
  "warnings_count": 5
}
```

## 4. Invariants obligatoires

Les invariants suivants doivent toujours etre respectes :

- `document_id` non vide.
- `page_number` commence a 1.
- `page_id` unique dans `page_index.jsonl`.
- `text_block_id` unique dans `text_blocks.jsonl`.
- `table_id` unique dans `table_index.jsonl`.
- `cell_id` unique dans `table_cells.jsonl`.
- `figure_id` unique dans `figure_index.jsonl`.
- `section_id` unique dans `section_index.jsonl`.
- `evidence_id` unique dans `evidence_store.jsonl`.
- `page_start <= page_end` pour toute section.
- Chaque `EvidenceRecord` doit pointer vers au moins une source : `text_block_id`, `table_id`, `cell_id`, `figure_id` ou `section_id`.
- Aucune ecriture dans `ESGFinalCorpus`.
- Aucune modification du PDF source.
- Aucune modification du manifest source.
- Toutes les sorties sont ecrites dans `ESGInformationExtraction/outputs/<run_id>/`.
- Les erreurs partielles doivent etre encodees en statuts et controles qualite, pas provoquer une perte silencieuse.

## 5. Strategie texte

La v0 doit extraire le texte en plusieurs niveaux.

### 5.1 Texte brut

Le texte brut doit etre conserve tel que renvoye par le parser, avec normalisation minimale :

- conservation des accents ;
- conservation des retours ligne utiles ;
- suppression optionnelle des caracteres de controle ;
- normalisation des espaces seulement si necessaire.

Le texte brut ne doit pas etre transforme en interpretation ESG.

### 5.2 Blocs

Les blocs doivent etre construits a partir du layout quand disponible.

Chaque bloc doit avoir :

- page ;
- bbox ;
- texte ;
- type initial ;
- ordre de lecture ;
- niveau de confiance.

### 5.3 Titres

Les titres doivent etre detectes par combinaison de signaux :

- taille de police ;
- style ;
- position ;
- longueur ;
- numerotation ;
- mots-cles ;
- isolement visuel.

Ils doivent devenir des `TextBlockRecord` avec `block_type = "title"` ou `block_type = "subtitle"`.

### 5.4 Paragraphes

Les paragraphes doivent conserver le texte brut et la bbox.

Ils ne doivent pas etre fusionnes agressivement en v0.

### 5.5 Listes

Les listes doivent etre detectees par :

- puces ;
- numerotation ;
- indentation ;
- repetition visuelle.

Chaque item peut etre un `TextBlockRecord` de type `list_item`.

### 5.6 Notes

Les notes doivent etre detectees par :

- position basse de page ;
- taille de police inferieure ;
- marqueurs de note ;
- separation visuelle.

### 5.7 Headers et footers

Les headers et footers doivent etre detectes et marques, afin d'eviter leur usage dans les sections et evidences.

### 5.8 Captions

Les captions doivent etre rattachees si possible a :

- une figure ;
- un tableau ;
- un graphique.

## 6. Strategie tableaux

La v0 doit gerer plusieurs cas.

### 6.1 Tableau avec lignes visibles

Le moteur peut utiliser les lignes graphiques pour reconstruire lignes, colonnes et cellules.

Statut attendu :

- `parsed` si la structure est fiable ;
- `low_confidence` si la structure est incertaine.

### 6.2 Tableau sans lignes visibles

Le moteur doit utiliser :

- alignements de texte ;
- espaces ;
- colonnes implicites ;
- repetition de motifs.

Statut attendu :

- `parsed` si les colonnes sont fiables ;
- `low_confidence` si ambigu ;
- `detected_not_parsed` si seule la zone est detectee.

### 6.3 Tableau multi-pages

Le moteur doit detecter les continuations possibles :

- meme titre ;
- meme header ;
- page consecutive ;
- structure similaire.

Champs utiles :

- `is_multi_page`
- `continued_from_table_id`

### 6.4 Tableau detecte mais non parsable

Le moteur doit produire un `TableRecord` avec :

- bbox ;
- page ;
- statut `detected_not_parsed` ;
- message dans `quality_report.jsonl`.

### 6.5 Tableau ambigu

Le moteur doit produire :

- statut `low_confidence` ;
- `structure_confidence` faible ;
- `review_required = true` dans un controle qualite.

## 7. Strategie figures et graphiques

La v0 ne lit pas les valeurs numeriques des graphiques.

Elle doit seulement produire :

- `FigureRecord` ;
- `bbox` ;
- `figure_type` ;
- `caption_text` ;
- `surrounding_text` ;
- `extraction_status` ;
- `needs_review`.

Types minimum :

- `image`
- `chart`
- `diagram`
- `logo`
- `map`
- `unknown`

Les graphiques doivent etre marques `needs_review = true` si une future extraction de valeurs visuelles est envisagee.

## 8. Strategie ordre de lecture

Le moteur doit ordonner :

- blocs de texte ;
- tableaux ;
- figures ;
- captions.

L'ordre de lecture doit etre construit par page puis consolide au niveau document.

Regles v0 :

1. Trier par zones visuelles principales.
2. Detecter les colonnes si possible.
3. Exclure ou degrader headers et footers.
4. Rattacher captions aux objets proches.
5. Donner un `reading_order_confidence`.

Champs attendus :

- `reading_order`
- `reading_order_confidence`
- `reading_order_method`

L'ordre brut du parser PDF ne doit pas etre considere fiable par defaut.

## 9. Strategie sections

Probleme deja observe :

Des sections peuvent avoir `page_end < page_start` quand plusieurs titres sont detectes sur la meme page et que `page_end` est calcule comme `page_start du titre suivant - 1`.

Regle obligatoire :

```text
page_end >= page_start
```

Les sections doivent etre construites a partir des `TextBlockRecord` de type `title` ou `subtitle`, pas seulement a partir du texte page par page.

La construction des sections doit utiliser :

- `start_element_id` ;
- `end_element_id` ;
- `reading_order` ;
- `page_start` ;
- `page_end`.

Cas a gerer :

- suppression des titres de table des matieres ;
- suppression des headers et footers ;
- plusieurs titres sur une meme page ;
- sous-sections ;
- titres repetes ;
- titres sans contenu ;
- section finale du document.

Pour plusieurs titres sur une meme page :

- `page_start` peut etre identique ;
- `page_end` ne doit pas etre decremente sous `page_start` ;
- `end_element_id` doit etre utilise pour delimiter la section dans l'ordre de lecture.

## 10. Strategie `EvidenceRecord`

Une preuve doit toujours pointer vers au moins une source :

- `text_block_id` ;
- ou `table_id` / `cell_id` ;
- ou `figure_id` ;
- ou `section_id`.

Une preuve n'est pas une conclusion.

Elle doit contenir :

- quote ;
- page ;
- bbox si disponible ;
- lien source ;
- confiance de localisation ;
- methode de construction.

Une preuve peut servir a une extraction ESG future, mais elle ne doit pas etre interpretee comme un indicateur valide.

## 11. Controles qualite

Checks minimaux v0 :

### `pdf_readable`

Verifie que le PDF peut etre ouvert.

### `page_count_valid`

Verifie que le nombre de pages est superieur a 0.

### `page_has_text`

Verifie qu'une page contient du texte extractible.

### `bbox_available`

Verifie que les objets localises disposent d'une bbox quand attendu.

### `table_parsing_status`

Verifie que chaque tableau a un statut explicite.

### `figure_detection_status`

Verifie que chaque figure a un statut explicite.

### `section_range_valid`

Verifie que `page_start <= page_end`.

### `evidence_source_exists`

Verifie que chaque evidence pointe vers une source existante.

### `output_file_not_empty`

Verifie que les fichiers obligatoires ne sont pas vides.

### `extraction_summary_exists`

Verifie que `extraction_summary.json` existe et contient les compteurs attendus.

Chaque check doit produire un `QualityCheckRecord`.

## 12. CLI cible

Script cible :

```text
ESGInformationExtraction/run_pdf_extraction.py
```

La v0 traite un seul PDF a la fois.

Arguments :

```bash
python ESGInformationExtraction/run_pdf_extraction.py \
  --pdf-path /path/to/document.pdf \
  --document-id doc_001 \
  --output-dir ESGInformationExtraction/outputs/run_001 \
  --max-pages 50 \
  --extract-tables \
  --extract-figures \
  --overwrite
```

### `--pdf-path`

Chemin du PDF a lire en lecture seule.

### `--document-id`

Identifiant du document. Obligatoire en v0 pour garantir la stabilite des liens.

### `--output-dir`

Dossier de sortie. Doit etre dans `ESGInformationExtraction/outputs/<run_id>/`.

### `--max-pages`

Limite optionnelle de pages a traiter.

### `--extract-tables`

Active la detection/extraction des tableaux.

### `--extract-figures`

Active la detection des figures.

### `--overwrite`

Autorise l'ecrasement controle des sorties existantes dans `output_dir`.

Sans `--overwrite`, le script doit refuser d'ecrire si les fichiers de sortie existent deja.

## 13. Criteres de reussite v0

La v0 est reussie si, pour un PDF donne, elle produit au minimum :

- `document_record.json` ;
- `page_index.jsonl` ;
- `text_blocks.jsonl` ;
- `quality_report.jsonl` ;
- `extraction_summary.json`.

Les tableaux, figures et sections peuvent etre partiels en v0, mais doivent avoir des statuts explicites.

Critere supplementaire :

- aucune ecriture dans le dossier source ;
- aucun crash sur PDF lisible ;
- erreurs partielles reportees dans `quality_report.jsonl` ;
- `extraction_summary.json` coherent avec les fichiers produits.

## 14. Ce qui est hors perimetre v0

Sont explicitement exclus de la v0 :

- OCR massif ;
- extraction fiable des valeurs de graphiques ;
- scoring ESG ;
- RAG ;
- base vectorielle ;
- validation automatique finale des indicateurs ESG ;
- extraction massive sur tout `ESGFinalCorpus` ;
- interpretation metier definitive ;
- modification des PDFs ;
- modification des manifests ;
- branchement a `ESGOrchestrator`.

## 15. Notes d'implementation

Priorite absolue :

1. Stabiliser les contrats de sortie.
2. Garantir les invariants.
3. Produire des diagnostics utiles.
4. Rester sur un PDF a la fois.
5. Ne pas confondre extraction documentaire et extraction ESG.

La couche ESG pourra ensuite consommer ces sorties pour produire des `MetricCandidateRecord`, mais cette etape doit rester separee.

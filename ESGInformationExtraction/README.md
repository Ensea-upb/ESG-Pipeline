# ESGInformationExtraction

## Documentation v1.5

- [Release notes v1.5](docs/RELEASE_NOTES_V1_5.md)
- [Validation commands v1.5](docs/VALIDATION_COMMANDS_V1_5.md)
- [Module usage map v1.5](docs/MODULE_USAGE_MAP_V1_5.md)
- [Config usage v1.5](docs/CONFIG_USAGE_V1_5.md)
- [Output contract notes v1.5](docs/OUTPUT_CONTRACT_NOTES_V1_5.md)
- [ADR-002 schema architecture hygiene v1.5](docs/ADR_002_SCHEMA_ARCHITECTURE_HYGIENE_V1_5.md)

## v1.5 - Schema and architecture hygiene

La v1.5 est une release de durcissement leger. Elle ne change pas la logique
d'extraction, ne change pas les 23 fichiers de sortie, et ne change pas le
contrat v1.0.

Elle aligne les schemas de support avec les outputs reels, documente
`run_pdf_extraction.py` comme moteur actif, clarifie les modules legacy ou
experimentaux, et ajoute un audit d'architecture non destructif.

Commande d'audit :

```bash
python ESGInformationExtraction/tools/audit_engine_architecture.py \
  --project-root "." \
  --output-dir "ESGInformationExtraction/outputs/architecture_hygiene_v15" \
  --overwrite
```

## Documentation v1.4

- [Release notes v1.4](docs/RELEASE_NOTES_V1_4.md)
- [Architecture overview v1.4](docs/ARCHITECTURE_OVERVIEW_V1_4.md)
- [Validation commands v1.4](docs/VALIDATION_COMMANDS_V1_4.md)

## v1.4 - Batch execution checklist

La v1.4 transforme le plan de remediation batch en checklist d'execution humaine.

Le remediation plan explique quelle action minimale est recommandee pour chaque output. L'execution checklist ordonne ces actions par priorite et fournit, pour chaque output, une commande proposee, une instruction manuelle, une commande de verification et des criteres de completion.

Commande :

```bash
python ESGInformationExtraction/tools/batch_check_outputs.py \
  --outputs-root "ESGInformationExtraction/outputs" \
  --contract-path "ESGInformationExtraction/contracts/output_contract_v1.json" \
  --write-report \
  --write-remediation-plan \
  --write-execution-checklist \
  --overwrite
```

La checklist produit :

- `batch_execution_checklist.json`
- `batch_execution_checklist.csv`
- `batch_execution_checklist.md`

Elle ne lance aucune commande automatiquement. L'execution reste humaine : l'utilisateur choisit, verifie et lance manuellement les commandes proposees.

Cette version ne modifie pas les outputs scannes, ne reparse aucun PDF et ne fait aucune extraction ESG : pas de metrique, pas d'indicateur, pas de score, pas de RAG, pas de base vectorielle et pas d'OCR.

## v1.3 - Batch remediation plan

La v1.3 ajoute un plan de remediation batch pour transformer les resultats de compatibilite en actions minimales recommandees.

La compatibilite repond a la question : "dans quel etat est cet output par rapport au contrat v1.0 ?". La remediation repond a la question suivante : "quelle est l'action la plus petite et la moins risquee pour corriger ou rapprocher cet output du contrat ?".

Commande :

```bash
python ESGInformationExtraction/tools/batch_check_outputs.py \
  --outputs-root "ESGInformationExtraction/outputs" \
  --contract-path "ESGInformationExtraction/contracts/output_contract_v1.json" \
  --write-report \
  --write-remediation-plan \
  --overwrite
```

Avec `--write-remediation-plan`, le scanner produit :

- `batch_remediation_plan.json`
- `batch_remediation_plan.csv`
- `batch_remediation_plan.md`

Actions recommandees possibles :

- `no_action_needed`
- `annotate_summary_only`
- `rerun_audit_standalone`
- `rerun_contract_validation`
- `regenerate_with_current_engine`
- `manual_review_required`

Le plan ne corrige rien automatiquement. Il ne lance aucune commande, n'annote aucun summary et ne regenere aucun output. Les commandes proposees sont indicatives et doivent etre executees manuellement apres verification.

Cette version ne reparse pas les PDFs et ne fait aucune extraction ESG : pas de metrique, pas d'indicateur, pas de score, pas de RAG, pas de base vectorielle et pas d'OCR.

## v1.2 - Batch compatibility scanner

La v1.2 ajoute un scanner batch non destructif pour verifier plusieurs dossiers d'outputs avec le contrat v1.0.

`check_output_compatibility.py` analyse un seul dossier. `batch_check_outputs.py` parcourt un dossier racine, detecte les sous-dossiers qui ressemblent a des outputs `ESGInformationExtraction`, puis applique la meme logique de compatibilite a chacun.

Commande :

```bash
python ESGInformationExtraction/tools/batch_check_outputs.py \
  --outputs-root "ESGInformationExtraction/outputs" \
  --contract-path "ESGInformationExtraction/contracts/output_contract_v1.json" \
  --write-report \
  --overwrite
```

Le batch detecte un output si le dossier contient au moins un fichier marqueur comme `extraction_summary.json`, `document_record.json`, `evidence_store.jsonl` ou `document_inventory.json`.

Avec `--write-report`, il produit uniquement :

- `ESGInformationExtraction/outputs/batch_compatibility_report/batch_compatibility_summary.json`
- `ESGInformationExtraction/outputs/batch_compatibility_report/batch_compatibility_table.csv`
- `ESGInformationExtraction/outputs/batch_compatibility_report/batch_compatibility_report.md`

Sans `--overwrite`, le CLI refuse de remplacer des rapports batch deja presents. Avec `--overwrite`, il reecrit seulement ces trois rapports batch.

Le scanner ne modifie jamais les dossiers d'outputs scannes et ne fait aucune extraction ESG : pas de metrique, pas d'indicateur, pas de score, pas de RAG, pas de base vectorielle et pas de relecture PDF.

## v1.1 - Compatibilite des anciens outputs

La v1.1 ajoute un outil non destructif pour diagnostiquer les dossiers d'outputs produits avant le contrat v1.0.

Commande :

```bash
python ESGInformationExtraction/tools/check_output_compatibility.py \
  --output-dir "ESGInformationExtraction/outputs/pdf_v08_example" \
  --contract-path "ESGInformationExtraction/contracts/output_contract_v1.json"
```

Par defaut, le CLI lit les fichiers existants et affiche seulement un JSON console. Il ne modifie aucun fichier.

Options :

- `--write-report` : ecrit `compatibility_report.json`, `compatibility_findings.jsonl`, `compatibility_report.md` ;
- `--overwrite` : autorise a remplacer un rapport de compatibilite existant ;
- `--annotate-summary` : ajoute explicitement des champs de compatibilite dans `extraction_summary.json` uniquement.

Statuts possibles :

- `compatible` : conforme au contrat v1.0 ;
- `compatible_with_warnings` : utilisable, par exemple ancien output sans `engine_contract_version` ;
- `migration_required` : outputs documentaires presents mais audit a regenerer ;
- `incompatible` : fichiers documentaires essentiels manquants.

Cet outil ne reparse pas le PDF, ne modifie pas les PDFs, ne modifie pas `ESGFinalCorpus`, et ne fait aucune extraction ESG.

## v1.0 - Contrat stable du moteur documentaire PDF

La v1.0 fige les schemas de sortie du moteur documentaire PDF afin de preparer une future couche ESG separee.

Le moteur documentaire PDF produit des objets de structure : pages, blocs, sections, evidences documentaires, tableaux, cellules, figures, inventaire multimodal et audits. La future couche ESG devra lire ces sorties, mais elle n'est pas incluse ici.

Fichiers de contrat :

- `ESGInformationExtraction/docs/OUTPUT_CONTRACT_V1.md` : documentation humaine du contrat ;
- `ESGInformationExtraction/contracts/output_contract_v1.json` : contrat machine-readable ;
- `ESGInformationExtraction/tools/validate_output_contract.py` : validation des fichiers produits.

Commande :

```bash
python ESGInformationExtraction/tools/validate_output_contract.py \
  --output-dir "ESGInformationExtraction/outputs/pdf_v09_example" \
  --contract-path "ESGInformationExtraction/contracts/output_contract_v1.json"
```

Cette etape protege les futures extractions ESG en stabilisant les noms de fichiers, champs, valeurs autorisees et invariants inter-fichiers.

Aucune metrique ESG, aucun indicateur, aucun score, aucun RAG, aucune base vectorielle, aucun LLM et aucun OCR ne sont produits.

## v0.9 - CLI d'audit documentaire standalone

La v0.9 permet de regenerer l'audit documentaire sans reextraire le PDF.

Le CLI lit un dossier d'outputs existant et reecrit uniquement :

- `consistency_report.json`
- `audit_findings.jsonl`
- `document_audit_report.md`

Il ne relit pas le PDF, n'extrait pas de texte, ne detecte pas de tableaux ou figures, et ne modifie pas `evidence_store.jsonl`, `table_index.jsonl`, `figure_index.jsonl`, `text_blocks.jsonl` ou `section_index.jsonl`.

Commande :

```bash
python ESGInformationExtraction/tools/run_document_audit.py \
  --output-dir "ESGInformationExtraction/outputs/pdf_v08_example" \
  --overwrite
```

Sans `--overwrite`, le CLI refuse d'ecraser des fichiers d'audit deja presents. Avec `--overwrite`, il reecrit seulement les trois fichiers d'audit.

Difference avec l'extraction PDF : `run_pdf_extraction.py` construit les objets documentaires depuis le PDF ; `run_document_audit.py` relit seulement les objets deja produits pour refaire le rapport de coherence.

Aucune extraction ESG n'est faite : aucune metrique, aucun indicateur, aucun score, aucun RAG, aucune base vectorielle.

## v0.8 - Audit documentaire inter-fichiers

La v0.8 ajoute un audit de coherence entre tous les fichiers produits par le moteur PDF.

Nouveaux fichiers :

- `consistency_report.json` : synthese machine-readable de la coherence inter-fichiers ;
- `audit_findings.jsonl` : une ligne par finding d'audit, avec severite, categorie et recommandation ;
- `document_audit_report.md` : rapport humain lisible pour inspection avant toute extraction ESG.

Cet audit verifie notamment :

- la presence des fichiers attendus ;
- la coherence des compteurs entre `evidence_store.jsonl` et `multimodal_evidence_index.jsonl` ;
- la validite des references vers `text_block_id`, `table_id`, `figure_id` et `section_id` ;
- les politiques qui empechent les evidences `quarantine` ou `review_required` d'etre utilisees automatiquement.

Le rapport humain est necessaire avant une future extraction ESG parce qu'il explique les zones fragiles : sections suspectes, tableaux ambigus, figures visuelles, evidences a revue humaine.

La readiness documentaire n'est pas une validation ESG. Elle indique seulement si les sorties documentaires semblent propres pour une future experimentation separee.

Cette version ne produit aucune metrique ESG, aucun indicateur et aucun score.

## v0.7 - Inventaire documentaire multimodal

La v0.7 consolide les evidences texte, tableaux et figures dans une couche d'audit commune.

Nouveaux fichiers :

- `document_inventory.json` : resume documentaire global du PDF ;
- `multimodal_evidence_index.jsonl` : index normalise de toutes les evidences ;
- `multimodal_statistics.json` : compteurs globaux par modalite, type, section et politique.

`evidence_store.jsonl` reste la source des evidences produites par les couches texte/table/figure. `multimodal_evidence_index.jsonl` ajoute une vue commune avec `source_modality`, `object_quality_flags`, `object_confidence` et `downstream_use_policy`.

`downstream_use_policy` sert uniquement a proteger les futures extractions :

- `eligible_for_future_extraction` : evidence documentaire normale, exploitable plus tard a titre experimental ;
- `review_before_extraction` : evidence conservee mais a verifier ;
- `exclude_from_automatic_extraction` : evidence conservee mais a exclure des traitements automatiques.

Une evidence `quarantine` ou `review_required` ne peut jamais etre `eligible_for_future_extraction`.

Ce statut n'est pas une validation ESG. Il ne valide aucune metrique, aucun indicateur et aucun score. Il indique seulement si l'objet documentaire semble suffisamment propre pour une future phase d'extraction separee.

## v0.4 - Evidence store documentaire non metier

La v0.4 ajoute un `evidence_store.jsonl` documentaire, construit uniquement a partir de `section_index.jsonl` et `text_blocks.jsonl`.

Une evidence documentaire est un extrait localise du PDF : titre de section ou paragraphe rattache a une section. Ce n'est pas une metrique ESG, ce n'est pas une conclusion et ce n'est pas un indicateur valide.

Sorties ajoutees :

- `evidence_store.jsonl` : une ligne par preuve documentaire localisee ;
- `evidence_statistics.json` : repartitions, compteurs et exemples limites.

La v0.4 produit surtout deux types de preuves :

- `section_heading` pour chaque section acceptee ;
- `paragraph` pour les paragraphes utiles rattaches a une section.

Les blocs structurels sont exclus en v0.4 :

- `toc_entry`
- `header`
- `footer`
- `footnote`
- `caption`
- `unknown`
- blocs vides, trop courts ou purement numeriques.

Le rattachement aux sections utilise d'abord les bornes `start_element_id` / `end_element_id`, puis les pages couvertes par la section. Une preuve avec bbox et section valide obtient une confiance plus elevee ; une preuve courte ou sans bbox est marquee `review_required`.

Ce fichier servira plus tard a l'extraction ESG, mais il ne fait pas encore cette extraction : aucune valeur ESG n'est lue, aucune base vectorielle n'est creee, aucun RAG et aucun scoring ne sont produits.

Commande d'exemple :

```bash
python ESGInformationExtraction/run_pdf_extraction.py \
  --pdf-path /path/to/document.pdf \
  --document-id doc_example_001 \
  --output-dir ESGInformationExtraction/outputs/pdf_v04_example \
  --max-pages 10 \
  --overwrite
```

## v0.4.1 - Stabilisation de l'evidence store documentaire

La v0.4.1 reduit la fragmentation des evidences documentaires.

Dans la v0.4, chaque bloc `paragraph` pouvait devenir une evidence separee. Sur de vrais PDFs, cela produit parfois des extraits trop courts ou des morceaux de phrase. La v0.4.1 regroupe donc certains blocs consecutifs, uniquement quand ils appartiennent a la meme section et que la fusion reste courte et auditable.

Regles principales :

- fusion conservative des paragraphes consecutifs d'une meme section ;
- limite de quote a 800 caracteres ;
- pas de fusion des `section_heading`, `toc_entry`, `header`, `footer`, `footnote`, `caption` ou `unknown` ;
- filtrage des evidences paragraph trop courtes ;
- evidences entre 30 et 60 caracteres marquees `review_required`.

Nouveaux champs dans `evidence_store.jsonl` :

- `source_text_block_ids`
- `merged_blocks_count`
- `was_merged_evidence`
- `merge_method`

La v0.4.1 ajoute aussi des diagnostics sur les sections suspectes :

- sections de front matter recevant beaucoup d'evidences ;
- sections concentrant une part tres elevee des evidences ;
- mismatch simple entre un titre de section de type certification/assurance et les premiers paragraphes rattaches.

Ces alertes ne suppriment aucune section et ne valident aucune information ESG. Une evidence reste une preuve documentaire localisee, pas un indicateur, pas une metrique et pas un score.

## v0.4.2 - Isolation des sections suspectes

La v0.4.2 marque les sections dont la qualite documentaire est fragile, sans les supprimer.

Certaines sections peuvent etre suspectes parce que le titre vient du front matter, du sommaire, ou parce que le titre annonce un contenu qui ne correspond pas aux premieres evidences rattachees. Exemple typique : une section de certification dont les premiers paragraphes parlent de traduction, d'historique ou de marques.

Chaque section recoit maintenant :

- `section_quality_score`
- `is_suspicious_section`
- `suspicion_reasons`
- `evidence_policy`

Les politiques possibles sont :

- `normal` : la section peut etre utilisee plus tard avec prudence normale ;
- `review_required` : la section est conservee mais demande une verification ;
- `quarantine` : la section et ses evidences sont conservees, mais ne doivent pas etre utilisees automatiquement pour une future extraction ESG.

`quarantine` ne signifie jamais suppression. Les sections suspectes sont aussi ecrites dans `suspicious_sections.jsonl` avec des citations exemples pour audit.

Les evidences heritent de la qualite de leur section via :

- `section_quality_score`
- `section_is_suspicious`
- `section_suspicion_reasons`
- `evidence_policy`
- `is_quarantined_evidence`

Cette etape protege les futures extractions ESG : elle evite d'utiliser automatiquement des passages mal rattaches ou ambigus. Elle ne produit toujours aucune metrique, aucun indicateur et aucun score ESG.

## v0.6.1 — Stabilisation des figures et pages visuelles

La v0.6.1 distingue les vraies figures exploitables des pages visuelles ou pages de séparation détectées par heuristique.

Problème traité : en v0.6, les pages LVMH avec peu de texte (couverture, séparateurs) étaient signalées comme figures avec le même statut que des figures réelles. La v0.6.1 introduit un niveau d'objet visuel (`visual_object_level`) pour qualifier chaque détection.

Nouveau champ `visual_object_level` :

| Valeur | Signification |
|--------|---------------|
| `embedded_object` | Image native détectée par `page.images` de pdfplumber |
| `captioned_region` | Visuel inféré depuis une caption textuelle (sans image native) |
| `page_level_visual` | Page entière signalée visuellement — pas une figure localisée |
| `unknown` | Niveau indéterminé |

Nouveaux champs booléens par figure :

- `is_page_level_visual` : vrai si `page_visual_heuristic`
- `is_embedded_visual` : vrai si `pdfplumber_image`
- `is_captioned_figure` : vrai si `caption_heuristic`
- `is_visual_page_candidate` : vrai si la figure est une page visuelle candidate

Règles de qualité renforcées :

- `page_visual_heuristic` → `figure_confidence <= 0.35` et `review_required = True` toujours
- Page 1 ou `is_low_text` ou `is_possible_visual` → flag `possible_cover_or_separator_page`
- `page_visual_heuristic` → flags `page_level_visual_candidate`, `weak_visual_detection`, `not_interpretable_visual`
- Toujours : `no_bbox_available` si bbox null, `no_caption_detected` si caption null

Evidence de type `figure` pour les pages visuelles :

- Quote non interprétative : `"Page-level visual candidate detected on page X; not interpreted."`
- `review_required = True` toujours
- Confiance héritée de la figure (≤ 0.35)
- Aucune valeur lue, aucun indicateur ESG produit

Pourquoi une page visuelle n'est pas une figure exploitable : la détection par heuristique de page (`is_possible_visual`) indique seulement que la page a peu de texte extrait. Cela peut correspondre à une page de couverture, une page de séparation, ou un graphique dont les éléments ne sont pas exposés en tant qu'objets pdfplumber. Sans image native ni caption, il est impossible de localiser ou caractériser la figure.

Nouveaux compteurs dans `figure_statistics.json` et `extraction_summary.json` :

- `page_level_visual_count`, `embedded_visual_count`, `captioned_figure_count`
- `visual_page_candidates_count`, `figures_without_bbox_count`, `weak_visual_detections_count`
- `possible_cover_or_separator_figures_count`, `figure_object_level_distribution`

Nouveaux checks dans `quality_report.jsonl` :

- `page_level_visual_detected`, `figure_without_bbox_warning`, `weak_visual_detection_warning`
- `visual_page_candidate_warning`, `figure_object_level_assigned`

Test LVMH (20 pages) : 3 figures détectées — toutes `page_level_visual`, toutes `weak_visual_detection`, `failed_figures_count = 0`. Les pages 1, 6, 10 sont correctement identifiées comme pages visuelles candidates, pas comme figures interprétables.

## v0.6 — Détection documentaire des figures et graphiques

La v0.6 ajoute une première détection des objets visuels dans les PDFs ESG. Elle détecte, localise et audite les figures, images, graphiques et zones visuelles, sans en interpréter le contenu.

Aucune valeur n'est lue dans les graphiques. Aucun indicateur ESG n'est produit. Aucun modèle vision n'est appelé. Aucun pixel n'est extrait.

Nouvelles sorties :

| Fichier | Contenu |
|---------|---------|
| `figure_index.jsonl` | Un enregistrement par figure détectée ou suspecte |
| `figure_statistics.json` | Compteurs, distributions, échantillons |

Types de figures (`figure_type`) :

| Valeur | Signification |
|--------|---------------|
| `image` | Image native détectée par pdfplumber (objet PDF image) |
| `chart` | Graphique inféré à partir d'une caption « chart » ou « graph » |
| `diagram` | Diagramme inféré à partir d'une caption « diagram » ou « schéma » |
| `map` | Carte inférée à partir d'une caption « map » ou « carte » |
| `logo` | Image native de petite surface (< 5000 pt²) — probablement un logo |
| `unknown_visual` | Visuel détecté sans type identifiable |

Statuts d'extraction (`extraction_status`) :

- `detected` : image native détectée via `page.images` de pdfplumber ;
- `low_confidence` : figure inférée à partir d'une caption sans image native ;
- `detected_not_interpreted` : page visuellement dense sans image ni caption ;
- `failed` : erreur d'extraction inattendue.

Stratégies de détection (ordre de priorité) :

1. `pdfplumber_image` — images PDF natives via `page.images` ;
2. `caption_heuristic` — blocs caption contenant `Figure N`, `Chart N`, `Graphique N`, etc. sans image native ;
3. `page_visual_heuristic` — pages avec peu de texte (`is_possible_visual`) sans image ni caption.

Chaque figure reçoit :
- `figure_bbox` (si disponible via pdfplumber) ou null ;
- `nearby_caption_text` : texte de caption associé ;
- `nearby_text_block_ids` : identifiants des blocs proches ;
- `figure_confidence` et `localization_confidence` ;
- `figure_quality_flags` : raisons d'un manque de qualité (`no_bbox_available`, `no_caption_detected`, etc.) ;
- `source_page_diagnostic_flags` : diagnostics de la page source.

Rattachement aux sections :

Chaque figure est rattachée à la première section dont `page_start <= page_number <= page_end`. Les champs de qualité de section sont propagés :
- `section_quality_score`, `section_is_suspicious`, `section_suspicion_reasons`
- `evidence_policy`, `is_quarantined_figure`

Une figure liée à une section quarantinée reçoit `is_quarantined_figure = true` et l'evidence associée reçoit `is_quarantined_evidence = true`.

Evidences documentaires de type `figure` :

Une evidence est créée pour chaque figure avec `extraction_status` dans `{detected, low_confidence, detected_not_interpreted}`. La quote est la caption si disponible, sinon une description du type de visuel. Aucune valeur ESG n'est lue.

Test LVMH (20 pages) : 3 pages visuelles détectées via heuristique de page (`detected_not_interpreted`), 0 failed — 3 evidences documentaires produites. Les images natives ne sont pas détectées car pdfplumber ne les expose pas comme objets `page.images` sur ce PDF.

Limites v0.6 :

- Pas de lecture des valeurs dans les graphiques.
- Pas d'OCR des zones visuelles.
- Pas d'appel à un modèle vision.
- Les images complexes (SVG embedded, graphiques vectoriels) ne sont pas détectées par `page.images`.
- La `figure_bbox` n'est disponible que pour les images natives (`pdfplumber_image`).
- Aucune déduplication des figures entre pages.

## v0.5.2 — Stabilisation qualité des tableaux

La v0.5.2 renforce la fiabilite de l'extraction des tableaux introduite en v0.5. Elle detecte et signale les tableaux artéfacts sans les supprimer, et enrichit chaque enregistrement avec des metriques de qualite cellulaire.

Problèmes traités :

- Tableaux sur les pages de sommaire ou de front matter classés `parsed` a tort.
- Tableaux entierement vides (`all_cells_empty`) non distingues des tableaux réels.
- Tableaux d'une seule ligne ou colonne confondus avec des tableaux valides.
- Cellules fragmentées (1–3 caractères) faussant la confiance.
- Tableaux minuscules (≤ 3 cellules) produits comme evidences sans justification.

Nouvelles regles de qualite (`table_quality_flags`) :

| Flag | Condition |
|------|-----------|
| `all_cells_empty` | Toutes les cellules sont vides |
| `mostly_empty_cells` | > 80 % de cellules vides |
| `high_empty_cells_ratio` | > 50 % de cellules vides |
| `single_row_table` | 1 seule ligne |
| `single_column_table` | 1 seule colonne |
| `tiny_table_artifact` | ≤ 3 cellules au total |
| `front_matter_or_toc_table_like` | Page identifiee comme sommaire ou front matter |
| `fragmented_cells_detected` | > 20 % de cellules fragmentees (≤ 3 chars) |
| `high_fragmented_cells_ratio` | > 30 % de cellules fragmentees |
| `low_numeric_density` | Tableau sans cellule numerique |
| `table_artifact_suspected` | Combinaison de flags suggerant un artefact |

Regles de déclassement (`parsed` → `low_confidence`) :

- `mostly_empty_cells` : > 80 % de cellules vides
- `front_matter_or_toc_table_like` : page de sommaire ou front matter
- `high_fragmented_cells_ratio` : > 30 % de cellules fragmentees
- `single_row_table` ou `single_column_table`

Politiques d'evidence :

- `empty_table` : aucune evidence produite
- `tiny_table_artifact` sans `page_looks_table_like` : aucune evidence produite
- Toutes les evidences `low_confidence` sont marquees `review_required=True`

Nouvelles metriques par tableau dans `table_index.jsonl` :

- `non_empty_cells_count`, `empty_cells_ratio`, `average_cell_text_length`
- `fragmented_cells_count`, `numeric_cells_count`, `numeric_cells_ratio`

Nouveaux compteurs dans `table_statistics.json` :

- `mostly_empty_tables_count`, `tiny_table_artifacts_count`, `front_matter_or_toc_tables_count`
- `fragmented_tables_count`, `table_artifact_suspected_count`
- `average_empty_cells_ratio`, `average_numeric_cells_ratio`
- `sample_empty_tables`, `sample_tiny_table_artifacts`, `sample_front_matter_or_toc_tables`, `sample_fragmented_tables`

Nouveaux champs dans `extraction_summary.json` :

- `empty_tables_count`, `mostly_empty_tables_count`, `tiny_table_artifacts_count`
- `front_matter_or_toc_tables_count`, `fragmented_tables_count`, `table_artifact_suspected_count`
- `table_evidence_count`

Nouveaux controles dans `quality_report.jsonl` :

- `empty_table_detected`, `mostly_empty_table_warning`, `tiny_table_artifact_warning`
- `front_matter_or_toc_table_warning`, `fragmented_table_warning`
- `table_artifact_suspected_warning`, `table_evidence_policy_consistency_check`

Test LVMH (20 pages) : 28 tableaux, 8 parsed, 13 low_confidence, 7 empty_table, 0 failed — 20 evidences documentaires produites, 11 tableaux de front matter signales, 8 artefacts minuscules supprimes des evidences.

## v0.5 — Moteur d'extraction de tableaux

La v0.5 ajoute un moteur d'extraction de tableaux via pdfplumber. Chaque page est analysee a la recherche de tableaux structures.

Nouvelles sorties :

| Fichier | Contenu |
|---------|---------|
| `table_index.jsonl` | Un enregistrement par tableau detecte ou suspecte |
| `table_cells.jsonl` | Une ligne par cellule de tableau (parsed ou low_confidence) |
| `table_statistics.json` | Compteurs, distribution des statuts, echantillons |

Statuts d'extraction (`extraction_status`) :

- `parsed` : tableau detecte avec au moins 2 lignes et 2 colonnes ;
- `low_confidence` : tableau detecte mais avec peu de lignes ou de colonnes ;
- `empty_table` : tableau detecte mais toutes les cellules sont vides ;
- `detected_not_parsed` : page heuristiquement identifiee comme table-like mais pdfplumber n'a rien extrait ;
- `failed` : erreur d'extraction inattendue.

Les pages `detected_not_parsed` ne sont jamais ignorees silencieusement : elles produisent un enregistrement dans `table_index.jsonl` avec `review_required=True`.

L'extraction suit un ordre de priorite :

1. Strategie lignes (`extract_tables()`) — detection de bordures ;
2. Strategie texte (`TABLE_TEXT_STRATEGY_SETTINGS`) si (1) echoue — colonnes par alignement ;
3. Heuristique textuelle (`_looks_table_like`) si (2) n'extrait rien — marque `detected_not_parsed`.

Les cellules (`table_cells.jsonl`) ne sont produites que pour les tableaux `parsed` ou `low_confidence`. Un tableau `detected_not_parsed` n'a aucune cellule.

Chaque tableau produit une evidence documentaire de type `table` dans `evidence_store.jsonl`. Ce n'est pas une extraction ESG : le contenu des cellules n'est pas interprete, aucune metrique n'est deduite.

Les compteurs `tables_count` et `table_cells_count` dans `extraction_summary.json` refletent maintenant les vrais nombres.

Test LVMH (20 pages) : 28 tableaux detectes, 4725 cellules, statuts `parsed` et `low_confidence`.

## PDF extraction engine v0

Le moteur PDF v0 transforme **un seul PDF** en sorties documentaires structurees.

Il ne fait pas d'extraction ESG, ne produit pas d'indicateur valide et ne produit pas de score ESG.

Commande d'exemple :

```bash
python ESGInformationExtraction/run_pdf_extraction.py \
  --pdf-path /path/to/document.pdf \
  --document-id doc_example_001 \
  --output-dir ESGInformationExtraction/outputs/pdf_v0_example \
  --max-pages 5 \
  --overwrite
```

Sorties produites :

| Fichier | Contenu |
|---------|---------|
| `document_record.json` | Metadonnees techniques du PDF et sha256 |
| `page_index.jsonl` | Une ligne par page traitee |
| `text_blocks.jsonl` | Une ligne par bloc de texte extrait |
| `quality_report.jsonl` | Controles qualite minimaux |
| `extraction_summary.json` | Resume d'execution et compteurs |

Garanties v0 :

- lecture seule du PDF source ;
- aucune ecriture dans `ESGFinalCorpus` ;
- aucune modification des manifests ;
- IDs stables pour les pages et blocs ;
- pas d'append silencieux ;
- refus d'ecraser les sorties sans `--overwrite` ;
- traitement limite a un PDF a la fois.

Limites v0 :

- pas d'OCR ;
- pas d'extraction de tableaux ;
- pas d'extraction de figures ;
- pas de detection de sections ;
- pas d'extraction ESG ;
- pas de scoring ESG ;
- pas d'extraction massive sur tout `ESGFinalCorpus`.

## v0.1 — Diagnostics qualite documentaire

La v0.1 renforce le moteur PDF avec des diagnostics sur la qualite textuelle des pages et des blocs extraits.

Ajouts principaux :

- detection des pages avec peu de texte (`page_low_text_warning`) ;
- detection des pages probablement visuelles, image-heavy ou pages separatrices (`possible_visual_page`) ;
- detection simple des pages de sommaire (`possible_table_of_contents_page`) ;
- detection des pages avec densite elevee de titres (`high_title_density_warning`) ;
- ajout de compteurs diagnostics dans `extraction_summary.json` ;
- production de `text_block_statistics.json`.

Les pages faibles en texte sont signalees parce qu'elles peuvent correspondre a :

- une page image ;
- une page de separation ;
- une page scannee ;
- une page dont le texte est mal extrait ;
- une page fortement graphique.

Les sommaires sont detectes parce qu'ils produisent souvent beaucoup de blocs courts classes comme titres. Ces blocs ne doivent pas etre confondus plus tard avec des sections reelles du document.

Cette v0.1 ne fait toujours pas d'extraction ESG. Elle ne valide aucun indicateur, ne produit aucun score et ne lit pas les valeurs des graphiques.

Commande d'exemple :

```bash
python ESGInformationExtraction/run_pdf_extraction.py \
  --pdf-path /path/to/document.pdf \
  --document-id doc_example_001 \
  --output-dir ESGInformationExtraction/outputs/pdf_v01_example \
  --max-pages 10 \
  --overwrite
```

Audit independant des blocs de texte deja produits :

```bash
python ESGInformationExtraction/tools/audit_text_blocks.py \
  --text-blocks-path ESGInformationExtraction/outputs/pdf_v01_example/text_blocks.jsonl \
  --page-index-path ESGInformationExtraction/outputs/pdf_v01_example/page_index.jsonl \
  --output-path ESGInformationExtraction/outputs/pdf_v01_example/text_block_statistics.json
```

## v0.2 — Classification documentaire des blocs

La v0.2 ameliore la classification des blocs de texte pour preparer une future detection de sections plus robuste.

Nouveaux `block_type` possibles :

- `header`
- `footer`
- `caption`
- `list_item`
- `toc_entry`
- `title`
- `paragraph`
- `unknown`

Cette etape sert a distinguer les vrais contenus documentaires des elements repetitifs ou structurels.

`toc_entry` est important parce que les sommaires produisent beaucoup de titres courts avec numeros de page. Sans detection explicite, une future detection de sections pourrait confondre le sommaire avec le corps du document.

Les headers et footers doivent etre identifies parce qu'ils sont repetes, souvent courts, et peuvent polluer les sections, les preuves et les statistiques de contenu.

Champs ajoutes dans `text_blocks.jsonl` :

- `is_header`
- `is_footer`
- `is_toc_entry`
- `block_type_confidence`
- `classification_reason`

Diagnostics ajoutes dans `quality_report.jsonl` :

- `header_footer_detected`
- `toc_entries_detected`
- `excessive_unknown_blocks_warning`
- `repeated_header_footer_warning`

Cette v0.2 ne fait toujours pas d'extraction ESG. Elle ne produit pas de metriques, pas de score, pas de RAG et pas de base vectorielle.

Commande d'exemple :

```bash
python ESGInformationExtraction/run_pdf_extraction.py \
  --pdf-path /path/to/document.pdf \
  --document-id doc_example_001 \
  --output-dir ESGInformationExtraction/outputs/pdf_v02_example \
  --max-pages 10 \
  --overwrite
```

Commande de test :

```bash
python -m pytest ESGInformationExtraction/tests --basetemp "$env:TEMP/pytest_esg_v02"
```

## v0.2.1 — Raffinement footer / footnote

La v0.2.1 stabilise la classification des textes situes en bas de page.

Elle existe parce que la v0.2 pouvait classer trop agressivement comme `footer` des lignes utiles, par exemple des elements de chronologie, des notes explicatives ou du contenu documentaire place en bas de page.

Difference entre les types :

- `footer` : element structurel court, en bas de page, avec pattern documentaire recurrent ou explicite.
- `footnote` : note de bas de page avec marqueur comme `(1)`, `(a)` ou `*`, contenant une phrase explicative.
- contenu documentaire : ligne informative non recurrente, a conserver plutot en `paragraph` ou `unknown` si le moteur hesite.

Regle de prudence :

Un bloc ne doit pas devenir `footer` seulement parce qu'il est en bas de page. Il faut plusieurs signaux : zone basse, texte court, pattern de pagination ou libelle recurrent du document.

Ce raffinement est necessaire avant la detection de sections, car les footers et notes ne doivent pas ouvrir de fausses sections ni polluer le corps du document.

Cette etape ne fait toujours pas d'extraction ESG, ne valide aucune metrique et ne produit aucun score.

## v0.3 — Détection conservatrice des sections

La v0.3 ajoute une premiere detection de sections a partir des `TextBlockRecord`.

Les sections sont construites apres la classification des blocs parce que tous les blocs `title` ne sont pas de vrais titres de section. Les sommaires, footers, footnotes, captions, listes et chronologies peuvent produire de faux titres.

Blocs exclus explicitement de la creation de sections :

- `toc_entry`
- `header`
- `footer`
- `footnote`
- `caption`
- `list_item`

Le moteur produit deux fichiers :

- `section_candidates.jsonl` : tous les titres ou blocs structurels analyses, y compris les rejets ;
- `section_index.jsonl` : uniquement les sections acceptees.

Cette separation permet d'auditer pourquoi un bloc a ete accepte ou rejete avant de faire une detection de sections plus avancee.

La detection reste conservative :

- rejet des lignes de chronologie avec plusieurs annees ;
- rejet des blocs trop numeriques ;
- rejet des titres trop courts ;
- garantie `page_start <= page_end` ;
- classification simple du `section_type` par mots-cles.

Cette v0.3 ne fait toujours pas d'extraction ESG. Elle ne produit pas de metriques, ne valide aucun indicateur et ne produit aucun scoring.

## v0.3.1 — Stabilisation des titres de section

La v0.3.1 durcit la selection des vrais titres de section.

Elle existe parce que certains blocs classes `title` peuvent etre des titres de couverture, des entrees de sommaire, des lignes de chronologie ou des valeurs numeriques. Ces blocs sont utiles dans le document, mais ils ne doivent pas ouvrir de sections.

Rejets ajoutes ou renforces :

- titres de couverture et document title ;
- `CONTENTS`, `TABLE OF CONTENTS`, `SOMMAIRE`, `TABLE DES MATIERES` ;
- lignes de chronologie de marque avec annees ;
- blocs purement ou quasi numeriques ;
- front matter comme `FISCAL YEAR ENDED ...`.

La classification `section_type` utilise des mots-cles plus stricts avec frontieres de mots afin d'eviter les faux positifs de sous-chaine. Par exemple, `eau` ne doit pas matcher dans `Chateau`.

Cette etape reste avant l'extraction ESG. Elle ne produit pas de metriques, ne valide aucun indicateur et ne produit aucun scoring.

## v0.3.2 — Réduction des faux titres de section

La v0.3.2 reduit les faux positifs avant la creation d'un evidence store documentaire.

Elle existe parce que certains blocs ressemblent visuellement a des titres mais ne doivent pas ouvrir de section :

- fragments de titres multi-lignes ;
- organigrammes ;
- diagrammes ;
- lignes de quasi-tableaux ;
- phrases accidentellement classees comme `title`.

Le moteur peut fusionner certains headings consecutifs simples, par exemple :

```text
BUSINESS OVERVIEW,
HIGHLIGHTS AND OUTLOOK
```

devient :

```text
BUSINESS OVERVIEW, HIGHLIGHTS AND OUTLOOK
```

Les candidats gardent l'audit complet dans `section_candidates.jsonl` :

- `normalized_heading_text`
- `source_heading_block_ids`
- `was_merged_heading`
- `candidate_score`
- `rejection_rule`
- `accepted_rule`

Cette etape reste conservative. En cas de doute, un bloc est rejete comme candidat de section plutot que de creer une section fragile.

Ce n'est toujours pas une extraction ESG : aucune metrique, aucun indicateur valide, aucun score.

## Rôle

Ce module prépare le terrain pour l'extraction d'informations ESG à partir des documents du corpus.

Il est **isolé** : il lit le corpus en lecture seule et écrit uniquement dans son propre dossier `outputs/`.
Il ne touche jamais aux fichiers sources dans `ESGFinalCorpus/`.

---

## Isolation et contraintes

- **Lecture seule** sur `ESGFinalCorpus/` — aucune écriture, aucune suppression, aucune modification.
- **Outputs séparés** — tous les fichiers produits vont dans `outputs/<run_id>/`.
- **Pas de dépendance vers les retrievers** — ce module est indépendant du pipeline d'ingestion.
- **Candidats, pas d'indicateurs validés** — les métriques extraites sont des candidats bruts à faible confiance.

---

## Structure

```
ESGInformationExtraction/
├── schemas/                   # Modèles Pydantic (6 schemas)
│   ├── document_record.py     # Document source (entrée immuable)
│   ├── page_record.py         # Page extraite
│   ├── section_record.py      # Section détectée
│   ├── metric_record.py       # Candidat métrique (non validé)
│   ├── evidence_record.py     # Extrait de texte justificatif
│   └── quality_check_record.py
├── config/
│   ├── extraction_config.yaml # Paramètres du pipeline
│   ├── metric_catalog_v0.yaml # 18 métriques ESG (FR+EN)
│   └── section_taxonomy_v0.yaml # 18 types de sections (FR+EN)
├── document_base/
│   └── build_document_base.py # Scan du corpus → DocumentRecord[]
├── parsing/
│   ├── pdf_text_parser.py     # Extraction texte via pdfplumber
│   └── page_index_builder.py  # Pages brutes → PageRecord[]
├── section_detection/
│   ├── heading_detector.py    # Détection de titres par règles
│   └── section_index_builder.py # Headings → SectionRecord[]
├── extraction/
│   ├── metric_candidate_extractor.py  # Mots-clés + regex → candidats
│   └── unit_normalizer.py     # Normalisation des unités
├── evidence/
│   └── evidence_store.py      # Candidats → EvidenceRecord[]
├── quality_control/
│   └── quality_checks.py      # 5 contrôles qualité
├── outputs/                   # Fichiers produits (gitignored sauf .gitkeep)
└── tests/
    └── test_schemas.py        # Tests d'instanciation des 6 schemas
```

---

## Inputs

- `ESGFinalCorpus/<company_slug>/<fiscal_year>/<doc_type>/` — PDFs + manifests JSON
- `config/section_taxonomy_v0.yaml` — mots-clés de section
- `config/metric_catalog_v0.yaml` — mots-clés de métriques ESG

## Outputs (dans `outputs/<run_id>/`)

| Fichier | Contenu |
|---------|---------|
| `document_base.jsonl` | Un `DocumentRecord` par document scanné |
| `page_index.jsonl` | Un `PageRecord` par page extraite |
| `section_index.jsonl` | Un `SectionRecord` par section détectée |
| `evidence_store.jsonl` | Un `EvidenceRecord` par extrait de preuve |
| `quality_report.jsonl` | Un `QualityCheckRecord` par contrôle effectué |

---

## Dépendances

```
pydantic>=2.0
pdfplumber       # extraction PDF (pip install pdfplumber)
pyyaml           # lecture des configs
```

---

## Limites actuelles (v0)

- Détection de titres par heuristiques simples (longueur, casse, mots-clés).
- Extraction de métriques par mots-clés et regex — **pas de LLM, pas de NLP avancé**.
- Les valeurs extraites sont des **candidats bruts** : `confidence` toujours < 0.4.
- Aucun système de déduplication des métriques inter-documents.
- Tableaux detectes et localises (v0.5) mais contenu non interprete pour les metriques ESG.

---

## Plan d'évolution (futur)

1. Intégration d'un modèle NLP léger pour la classification de sections.
2. Extraction de valeurs dans les tableaux (pdfplumber table extraction).
3. Pipeline de validation humaine des `MetricRecord` (`review_required=True`).
4. Scoring ESG agrégé par entreprise et par exercice fiscal.

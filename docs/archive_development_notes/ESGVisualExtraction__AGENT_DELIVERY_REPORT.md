# ESGVisualExtraction - Agent Delivery Report

## Phase 0 - Inspection

Inputs reels inspectes dans :

```text
ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test
```

Fichiers fiables consommes :

- `document_inventory.json`
- `extraction_summary.json`
- `figure_index.jsonl`
- `figure_statistics.json`
- `multimodal_evidence_index.jsonl`

Observation LVMH :

- `figures_count`: 3
- `page_level_visual_count`: 3
- `figures_without_bbox_count`: 3
- `figure_type`: `unknown_visual`

## Versions Realisees

### v0.1 - Loader visuel

Statut : passed.

Sorties :

- `visual_input_inventory.json`
- `visual_items.jsonl`
- `visual_extraction_summary.json`

Garantie : `figure_index.jsonl` est obligatoire et tous les items sont `review_required=true`.

### v0.2 - Crop non destructif

Statut : passed.

Sorties :

- `visual_crops_index.jsonl`
- `crops/`

Le PDF est lu en lecture seule. Si le rendu echoue, un placeholder image est produit avec statut explicite.

### v0.3 - OCR image

Statut : passed.

Tesseract OCR 5.4.0 a ete installe depuis l'installateur Windows UB Mannheim, reference par la documentation officielle Tesseract. Le module utilise le binaire CLI si le wrapper Python `pytesseract` n'est pas installe.

### v0.4 - Classification visuelle

Statut : passed.

Types autorises :

- `logo_or_cover`
- `illustrative_photo`
- `chart`
- `scanned_table`
- `diagram`
- `org_chart`
- `map`
- `unknown_visual`

### v0.5 - Candidats visuels ESG

Statut : passed.

Sorties :

- `visual_candidates.csv`
- `visual_candidates.jsonl`

Regles :

- `review_required=true`
- `extraction_status=candidate_only`
- `confidence <= 0.5`
- aucun score
- aucun indicateur valide

### v0.6 - Audit visuel

Statut : passed avec warning OCR.

Sorties :

- `visual_audit_summary.json`
- `visual_audit_findings.jsonl`
- `visual_audit_samples.csv`

### v0.7 - Contrat de sortie visuel

Statut : passed.

Sorties :

- `contracts/visual_output_contract_v0.json`
- `docs/VISUAL_OUTPUT_CONTRACT_V0.md`
- `scripts/validate_visual_outputs.py`

### v1.0 - Release stable

Statut : passed avec warnings metier.

Docs :

- `docs/RELEASE_NOTES_V1_0.md`
- `docs/ARCHITECTURE_OVERVIEW_V1_0.md`
- `docs/VALIDATION_COMMANDS_V1_0.md`

## Tests Executes

- `python -m compileall -q ESGVisualExtraction ESGCSVExtraction ESGInformationExtraction` : passed.
- `python -m pytest ESGVisualExtraction/tests --basetemp <tmp>` : 14 passed, 1 warning cache pytest.
- `python -m pytest ESGCSVExtraction/tests --basetemp <tmp>` : 31 passed, 1 warning cache pytest.
- `python -m pytest ESGInformationExtraction/tests --basetemp <tmp>` : 228 passed, 1 warning cache pytest.

## Test Manuel LVMH

Input :

```text
ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test
```

Output :

```text
ESGVisualExtraction/outputs/lvmh_visual_v10_test
```

Resultats :

- `visual_items_count`: 3
- `crops_count`: 3
- `ocr_outputs_count`: 3
- `visual_candidates_count`: 3
- `audit_errors_count`: 0
- `audit_warnings_count`: 1

Distribution `information_type` :

```text
visual_context_evidence: 3
```

Distribution `visual_type` :

```text
logo_or_cover: 3
```

OCR initial avant installation Tesseract :

```text
ocr_unavailable: 3
```

OCR apres installation Tesseract :

```text
success: 3
ocr_engine: tesseract_cli
```

Validation contrat :

```text
status: success
contract_version: 0.7.0
checks_count: 16
errors_count: 0
warnings_count: 0
```

## Preuve Non Destructive

Input documentaire :

```text
files_hashed: 23
digest_before: 0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee
digest_after:  0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee
```

PDF source :

```text
digest_before: 4e67ffaaae7f880fd24e837c30f10c08b0a087ca1b4314dade86e7b5d32c12cb
digest_after:  4e67ffaaae7f880fd24e837c30f10c08b0a087ca1b4314dade86e7b5d32c12cb
```

## Warnings

- `quality_warning=true`
- `real_world_visual_audit_pending=true`
- OCR reel disponible via `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- Les figures LVMH disponibles sont surtout des pages visuelles faibles, sans bbox ni caption.

## Decision

v1.0 est validee techniquement. La prochaine etape doit etre une revue sur un corpus avec vrais graphiques, captions et images embarquees.

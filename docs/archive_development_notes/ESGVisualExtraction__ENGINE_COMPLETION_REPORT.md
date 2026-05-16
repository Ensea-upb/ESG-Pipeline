# ESGVisualExtraction - Engine Completion Report

## Version Finale Atteinte

Version finale : v1.0.

Statut : passed avec warnings metier.

## Versions Validees

- v0.1 : loader visuel.
- v0.2 : crops non destructifs.
- v0.3 : OCR optionnel avec fallback.
- v0.4 : classification visuelle.
- v0.5 : candidats visuels ESG.
- v0.6 : audit visuel.
- v0.7 : contrat de sortie visuel.
- v1.0 : release stable documentee.

## Fichiers Produits

- `visual_input_inventory.json`
- `visual_items.jsonl`
- `visual_crops_index.jsonl`
- `visual_ocr_outputs.jsonl`
- `visual_ocr_summary.json`
- `visual_classification.jsonl`
- `visual_classification_summary.json`
- `visual_candidates.csv`
- `visual_candidates.jsonl`
- `visual_audit_summary.json`
- `visual_audit_findings.jsonl`
- `visual_audit_samples.csv`
- `visual_extraction_summary.json`

## Tests Executes

- `compileall` : OK.
- `ESGVisualExtraction/tests` : 14 passed, 0 failed, 0 errors.
- `ESGCSVExtraction/tests` : 31 passed, 0 failed, 0 errors.
- `ESGInformationExtraction/tests` : 228 passed, 0 failed, 0 errors.

Warnings pytest : cache `.pytest_cache` inaccessible uniquement.

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

## Crops Produits

3 crops PNG produits dans :

```text
ESGVisualExtraction/outputs/lvmh_visual_v10_test/crops/
```

Les 3 crops sont issus du PDF source lu en lecture seule.

## OCR Status

```text
success: 3
```

Tesseract OCR 5.4.0 est installe dans :

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Le module utilise le CLI `tesseract` si le wrapper Python `pytesseract` n'est pas disponible.

## Visual Type Distribution

```text
logo_or_cover: 3
```

## Visual Candidates

```text
visual_context_evidence: 3
```

Tous les candidats :

- `review_required=true`
- `extraction_status=candidate_only`
- `confidence <= 0.5`

## Validation Contrat

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

## Limites Restantes

- OCR reel disponible, mais qualite a auditer sur un corpus plus riche.
- Les figures LVMH disponibles sont page-level, sans bbox ni caption.
- Classification visuelle volontairement simple.
- Les valeurs extraites depuis image restent candidates faibles.
- Aucun indicateur ESG n'est valide.

## Recommandation

Prochaine version recommandee : v1.1 avec test sur documents contenant de vrais graphiques ESG captionnes, activation optionnelle de Tesseract si disponible, et revue humaine des crops.

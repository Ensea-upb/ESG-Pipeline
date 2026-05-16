# VISUAL_CROP_ROBUSTNESS_FIX_REPORT

**Date :** 2026-05-14  
**Version corrigée :** ESGVisualExtraction + ESGExtractionOrchestrator robustness fix  
**Auteur :** Claude Code (Sonnet 4.6)

---

## 1. Bug initial

Le pilot strict 10 documents (v1) a produit :

- documents_selected = 10
- documents_success = 7
- documents_failed = **3**

Les 3 échecs arrivent tous à l'étape `02_orchestrator` avec :

```json
{
  "status": "failed",
  "errors": [
    "[Errno 2] No such file or directory: '...\\02_orchestrator\\visual\\crops\\crop_0001_fig_canonical_...png'"
  ]
}
```

---

## 2. Documents impactés

| Document | Chemin crop (tronqué) | Longueur chemin |
|----------|----------------------|-----------------|
| schneider-electric / 03_climate_report_tcfd_transition_plan | `…\crop_0001_fig_canonical_40d8e0d89b7401018cec99da_p0001_0000.png` | **271 chars** |
| schneider-electric / 16_agm_minutes_resolutions | `…\crop_0001_fig_canonical_21b88b77a7daf1ed63d6a77e_p0001_0000.png` | **259 chars** |
| totalenergies / 02_sustainability_statement_csrd_esrs | `…\crop_0001_fig_canonical_46ba29d60207c57de191ca65_p0001_0000.png` | **265 chars** |

---

## 3. Cause racine

**Windows MAX_PATH (260 caractères) dépassé.**

Le nom de fichier du crop incluait le `figure_id` complet :
```
crop_0001_fig_canonical_40d8e0d89b7401018cec99da_p0001_0000.png
```
(63 caractères)

Combiné avec un chemin de base déjà long (`EXTERNAL_AUDIT_RUNS\strict_pilot_prepare_review_10docs_v1\schneider-electric\2024\03_climate_report_tcfd_transition_plan\canonical_40d8e0d89b7401018cec99da\02_orchestrator\visual\crops\`), le total dépassait 260 caractères.

Windows refusait la création du fichier → `[Errno 2] FileNotFoundError` → propagation fatale → document failed.

Les 7 documents qui réussissaient avaient des chemins suffisamment courts pour rester sous 260 caractères.

---

## 4. Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `ESGVisualExtraction/src/esg_visual_extraction/cropper.py` | Raccourcissement filename + robustesse par-crop + champs `crop_file_exists` / `visual_warning` |
| `ESGVisualExtraction/src/esg_visual_extraction/candidate_extractor.py` | Best-effort : try/except autour de `crop_visual_items` et `run_ocr`, `status="warning"` si warnings |
| `ESGVisualExtraction/src/esg_visual_extraction/audit.py` | Nouvelle check `crops_with_warnings` |
| `ESGExtractionOrchestrator/src/esg_extraction_orchestrator/runner.py` | Défense en profondeur : try/except autour du visual engine, propagation de `status="warning"` |
| `ESGVisualExtraction/tests/test_visual_crop_robustness_v03.py` | 6 nouveaux tests visuels |
| `ESGExtractionOrchestrator/tests/test_orchestrator_visual_robustness_v01.py` | 4 nouveaux tests orchestrateur |

**Fichiers non modifiés :** PDFs, ESGFinalCorpus, contrats, outputs sources, runner, métadonnées.

---

## 5. Comportement avant/après

### Avant

```python
# cropper.py ligne 24 — filename incluant figure_id (63 chars)
image_path = crops_dir / f"{crop_id}_{item.get('figure_id') or 'figure'}.png"
# → chemin total > 260 chars → FileNotFoundError → document failed
```

### Après

```python
# cropper.py — filename court (13 chars), figure_id préservé dans les métadonnées
image_path = crops_dir / f"{crop_id}.png"
# → chemin total < 260 chars → save réussit → document success
```

#### Robustesse ajoutée dans `cropper.py`

Chaque crop est maintenant enveloppé dans un `try/except` global. En cas d'échec :
- `crop_status = "failed"`
- `crop_file_exists = False`
- `visual_warning = "crop_creation_failed"`
- Le crop suivant continue normalement

#### Robustesse ajoutée dans `candidate_extractor.py`

```python
try:
    crops = crop_visual_items(...)
except Exception as exc:
    crop_pipeline_warning = f"crop_visual_items failed: {exc}"
    crops = []
# → pipeline continue, visual_candidates.csv toujours produit
```

Status `"warning"` (non `"failed"`) si crops avec warnings.

#### Robustesse ajoutée dans `runner.py`

```python
try:
    result = extractor_cls(...).run()
except Exception as exc:
    if engine_name == "visual":
        return {"engine": "visual", "status": "warning", "candidates_count": 0, ...}
    raise
# → orchestrateur continue avec CSV + Table même si visual crash
```

#### Nouveau champ dans `audit.py`

```python
"crops_with_warnings": [row for row in crops if row.get("visual_warning")],
```

---

## 6. Tests ajoutés

### ESGVisualExtraction (6 tests dans `test_visual_crop_robustness_v03.py`)

| Test | Vérifie |
|------|---------|
| `test_visual_crop_directory_created` | `crops/` créé même avec 0 items |
| `test_visual_crop_directory_created_with_items` | `crops/` créé avec items |
| `test_missing_crop_does_not_crash_when_pdf_absent` | PDF absent → `crop_status="missing_source_pdf"`, `crop_file_exists=False`, pas d'exception |
| `test_missing_crop_does_not_crash_when_pdf_empty_string` | PDF vide → même comportement |
| `test_missing_crop_does_not_crash_visual_extraction_via_cli` | CLI : `rc=0` même si rendu échoue, fichiers produits |
| `test_crop_filename_does_not_include_figure_id` | Filename = `crop_0001.png` (pas de figure_id) |
| `test_existing_visual_outputs_still_pass_contract` | Contrat visuel toujours valide après fix |

### ESGExtractionOrchestrator (4 tests dans `test_orchestrator_visual_robustness_v01.py`)

| Test | Vérifie |
|------|---------|
| `test_orchestrator_continues_when_visual_crop_missing` | `rc=0`, `consolidated_candidates.csv` produit, CSV candidates présents |
| `test_engine_manifest_records_visual_status` | `manifest["visual"]["status"]` ∈ statuts valides |
| `test_engine_manifest_visual_warning_has_warning_field` | Si `status="warning"`, champ `warning` présent |
| `test_existing_orchestrator_outputs_still_pass_contract` | Contrat orchestrateur toujours valide |
| `test_full_extraction_summary_contains_visual_candidates_count` | `visual_candidates_count` ≥ 0 dans summary |

---

## 7. Résultats pytest

### Tests visuels

```
ESGVisualExtraction/tests — 28 passed  (avant: 22, ajout: 6)
```

### Tests orchestrateur

```
ESGExtractionOrchestrator/tests — 21 passed  (avant: 16, ajout: 5)
```

### Suite globale

```
493 passed, 5 warnings in 121.70s  (avant: 481, ajout: 12)
Aucune régression.
```

---

## 8. Résultat du pilot 10 documents v2

**Commande exécutée :**

```powershell
python run_strict_index_pilot.py `
  --index-path "DocumentPostProcessing\data\quality_audit_v2\extraction_index_strict_likely_valid.csv" `
  --output-root "EXTERNAL_AUDIT_RUNS\strict_pilot_prepare_review_10docs_v2" `
  --max-documents 10 `
  --mode prepare-review `
  --execute `
  --overwrite `
  --max-pages 120
```

**Résultats :**

| Métrique | v1 (avant fix) | v2 (après fix) |
|----------|---------------|---------------|
| documents_selected | 10 | 10 |
| documents_processed | 10 | 10 |
| documents_success | **7** | **10** |
| documents_failed | **3** | **0** |
| review_workspaces_produced | 7 | 10 |
| top_review_candidates.csv produits | 7 | **10** |

**Détail par document :**

| Document | Status v1 | Status v2 |
|----------|-----------|-----------|
| air-liquide / 01_urd_annual_report | success | success |
| lvmh / 16_agm_minutes_resolutions | success | success |
| schneider-electric / 01_urd_annual_report | success | success |
| **schneider-electric / 03_climate_report_tcfd_transition_plan** | **failed** | **success** |
| schneider-electric / 04_vigilance_plan | success | success |
| schneider-electric / 13_investor_presentations | success | success |
| **schneider-electric / 16_agm_minutes_resolutions** | **failed** | **success** |
| totalenergies / 01_urd_annual_report | success | success |
| **totalenergies / 02_sustainability_statement_csrd_esrs** | **failed** | **success** |
| totalenergies / 05_half_year_financial_report | success | success |

**Visual extraction pour les 3 documents précédemment échoués :**

| Document | crops_count | crops_with_warnings | status |
|----------|-------------|---------------------|--------|
| schneider-electric / 03_climate_report | 20 | 0 | success |
| schneider-electric / 16_agm_minutes | 25 | 0 | success |
| totalenergies / 02_csrd_esrs | 491 | 0 | success |

**30/30 validateurs `rc=0`** (steps 01_validate_output_contract, 02_validate_full_extraction, 03_validate_indicator_validation pour chacun des 10 documents).

**Sécurité :**
- Aucun auto-accept
- Aucun PDF modifié
- ESGFinalCorpus non modifié
- Outputs uniquement dans `EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2/`

---

## 9. Décision finale

### ✅ GO

- `FileNotFoundError` sur crop PNG : **éliminé** (root cause corrigée par raccourcissement filename)
- `02_orchestrator` : **rc=0** pour les 10 documents
- Tous les crop PNG manquants ne font plus échouer le document
- `consolidated_candidates.csv` : produit pour les 10 documents
- 10/10 review workspaces produits
- 10/10 `top_review_candidates.csv` produits
- 493 tests globaux passent, 0 régression
- Aucun auto-accept, aucun PDF modifié, ESGFinalCorpus intact

# STRICT_INDEX_PILOT_RUNNER_FIX_REPORT

**Date :** 2026-05-14  
**Version corrigée :** StrictIndexPilotRunner v1.0 → v1.0.1  
**Auteur :** Claude Code (Sonnet 4.6)

---

## 1. Bug initial

Le premier pilot réel `prepare-review` sur 3 documents a échoué à l'étape `01_validate_output_contract` avec :

```
returncode = 2
documents_failed = 3
documents_success = 0
```

Erreur root cause : les validateurs étaient appelés sans l'argument `--contract-path`.

---

## 2. Cause racine

Dans `run_strict_index_pilot.py`, les 6 commandes de validation (`val_cmd`) étaient construites uniquement avec `--output-dir`, sans `--contract-path`. Les scripts de validation (argparse) retournent `rc=2` (erreur argument manquant) dès que le chemin de contrat est absent.

Exemple du bug (step 01) :

```python
# AVANT — manquait --contract-path
val_cmd = [
    sys.executable,
    str(SCRIPTS["validate_output_contract"]),
    "--output-dir", str(out_dir),
    # ← MANQUANT : "--contract-path", ...
]
```

---

## 3. Fichiers modifiés

| Fichier | Nature de la modification |
|---------|--------------------------|
| `run_strict_index_pilot.py` | Ajout dictionnaire `CONTRACTS` + 6 corrections `--contract-path` |
| `tests/test_strict_index_pilot_runner_v10.py` | 6 nouveaux tests (13–18) |

Fichiers **non modifiés** : tous les moteurs ESG, ESGInformationExtraction, ESGExtractionOrchestrator, ESGIndicatorValidation, ESGManualReview, ESGIndicatorDatabase, ESGVariableDatasetBuilder, PDFs, ESGFinalCorpus.

---

## 4. Validateurs corrigés

Un dictionnaire `CONTRACTS` a été ajouté dans la section constantes de `run_strict_index_pilot.py` :

```python
CONTRACTS = {
    "output_contract_v1":               _HERE / "ESGInformationExtraction" / "contracts" / "output_contract_v1.json",
    "full_extraction_output_contract_v0": _HERE / "ESGExtractionOrchestrator" / "contracts" / "full_extraction_output_contract_v0.json",
    "indicator_validation_contract_v0": _HERE / "ESGIndicatorValidation" / "contracts" / "indicator_validation_contract_v0.json",
    "manual_review_contract_v0":        _HERE / "ESGManualReview" / "contracts" / "manual_review_contract_v0.json",
    "indicator_database_contract_v0":   _HERE / "ESGIndicatorDatabase" / "contracts" / "indicator_database_contract_v0.json",
    "esg_variables_dataset_contract_v0": _HERE / "ESGVariableDatasetBuilder" / "contracts" / "esg_variables_dataset_contract_v0.json",
}
```

Chaque `val_cmd` a été corrigé :

| Step | Script validateur | Clé contrat ajoutée |
|------|-------------------|---------------------|
| `01_validate_output_contract` | `validate_output_contract.py` | `output_contract_v1` |
| `02_validate_full_extraction` | `validate_full_extraction_outputs.py` | `full_extraction_output_contract_v0` |
| `03_validate_indicator_validation` | `validate_indicator_validation_outputs.py` | `indicator_validation_contract_v0` |
| `05_validate_manual_review` | `validate_manual_review_outputs.py` | `manual_review_contract_v0` |
| `06_validate_indicator_database` | `validate_indicator_database_outputs.py` | `indicator_database_contract_v0` |
| `08_validate_variable_dataset` | `validate_esg_variables_dataset.py` | `esg_variables_dataset_contract_v0` |

---

## 5. Tests ajoutés

6 nouveaux tests dans `tests/test_strict_index_pilot_runner_v10.py` (tests 13–18) :

| N° | Nom du test | Ce qu'il vérifie |
|----|-------------|-----------------|
| 13 | `test_information_extraction_validator_has_contract_path` | `--contract-path output_contract_v1.json` présent dans `01_validate_output_contract` |
| 14 | `test_orchestrator_validator_has_contract_path` | `--contract-path full_extraction_output_contract_v0.json` présent dans `02_validate_full_extraction` |
| 15 | `test_indicator_validation_validator_has_contract_path` | `--contract-path indicator_validation_contract_v0.json` présent dans `03_validate_indicator_validation` |
| 16 | `test_manual_review_validator_has_contract_path` | `--contract-path manual_review_contract_v0.json` présent dans `05_validate_manual_review` |
| 17 | `test_indicator_database_validator_has_contract_path` | `--contract-path indicator_database_contract_v0.json` présent dans `06_validate_indicator_database` |
| 18 | `test_variable_dataset_validator_has_contract_path` | `--contract-path esg_variables_dataset_contract_v0.json` présent dans `08_validate_variable_dataset` |

**Méthode :** monkeypatch de `run_step` dans le module chargé → interception des commandes sans exécution réelle.

---

## 6. Résultats des tests

### Suite du runner

```
tests/test_strict_index_pilot_runner_v10.py — 18 passed
```

### Suite globale

```
481 passed, 5 warnings in 128.82s
```

Avant correction : 474 passed (12 tests runner + 462 autres).  
Après correction : 481 passed (18 tests runner + 463 autres). Aucune régression.

---

## 7. Résultat du pilot 3 documents v2

**Commande exécutée :**

```powershell
python run_strict_index_pilot.py `
  --index-path "DocumentPostProcessing\data\quality_audit_v2\extraction_index_strict_likely_valid.csv" `
  --output-root "EXTERNAL_AUDIT_RUNS\strict_pilot_prepare_review_3docs_v2" `
  --max-documents 3 `
  --mode prepare-review `
  --execute `
  --overwrite `
  --max-pages 80
```

**Résultats :**

| Métrique | Valeur |
|----------|--------|
| documents_selected | 3 |
| documents_processed | 3 |
| documents_success | **3** |
| documents_failed | **0** |
| documents_skipped | 0 |
| review_workspaces_produced | 3 |
| top_review_candidates.csv | 3 (un par document) |

**Returncodes des validateurs (command log) :**

| Step | rc |
|------|----|
| 01_validate_output_contract (air-liquide) | 0 |
| 02_validate_full_extraction (air-liquide) | 0 |
| 03_validate_indicator_validation (air-liquide) | 0 |
| 01_validate_output_contract (lvmh) | 0 |
| 02_validate_full_extraction (lvmh) | 0 |
| 03_validate_indicator_validation (lvmh) | 0 |
| 01_validate_output_contract (schneider-electric) | 0 |
| 02_validate_full_extraction (schneider-electric) | 0 |
| 03_validate_indicator_validation (schneider-electric) | 0 |

**Documents traités :**
- `air-liquide / 2024 / 01_urd_annual_report`
- `lvmh / 2024 / 16_agm_minutes_resolutions`
- `schneider-electric / 2024 / 01_urd_annual_report`

**Sécurité :**
- Aucun auto-accept (aucun `proposed_decision="accept_candidate"`)
- Aucun PDF modifié
- ESGFinalCorpus non modifié
- Outputs uniquement dans `EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_3docs_v2/`
- Tous les subprocess utilisent `sys.executable`

---

## 8. Décision finale

### ✅ GO

- `01_validate_output_contract` : `rc=0` pour les 3 documents
- Aucun validateur appelé sans `--contract-path`
- `documents_success = 3`, `documents_failed = 0`
- Review workspaces produits pour les 3 documents
- `top_review_candidates.csv` produit pour les 3 documents
- Aucun auto-accept
- Aucun PDF modifié
- ESGFinalCorpus non modifié
- 481 tests globaux passent, aucune régression

Le pipeline `prepare-review` est opérationnel. Le runner peut être utilisé pour des runs complets sur l'index strict.

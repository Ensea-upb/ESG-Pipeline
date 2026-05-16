# CONTROL_CENTER_V2_REPORT

**Date :** 2026-05-14  
**Phase :** ESGPilotControlCenter v2.0  
**Auteur :** Claude Code (Sonnet 4.6)  
**Décision finale :** GO — interface v2.0 opérationnelle

---

## 1. Objectif

Refondre l'interface Streamlit existante (v1 : pilotage technique module par module) en un **outil de pilotage métier** centré sur les questions réelles du porteur de projet :

1. Où en est le projet ?
2. Quels runs ont réussi ou échoué ?
3. Quels documents produisent du bruit ?
4. Quels candidats semblent réellement utiles ?
5. Quelles erreurs reviennent souvent ?
6. Quelle est la charge de revue humaine ?
7. Peut-on décider GO / GO_WITH_FIXES / NO_GO ?
8. Que doit-on améliorer dans Extraction V2 ?

---

## 2. Limites de l'ancienne interface (v1)

| Problème v1 | Impact |
|-------------|--------|
| Organisée par modules techniques (ESGExtractionOrchestrator, etc.) | L'utilisateur ne comprend pas ce qu'il regarde |
| Permet de relancer le pipeline | Risque de modification accidentelle des outputs sources |
| Pas de vue par document | Impossible de comparer deux documents |
| Pas de décision GO/NO_GO visible | Le porteur de projet ne peut pas décider |
| Pas de file de revue prioritaire | La revue humaine n'est pas guidée |
| Pas de baseline manuelle | Impossible de mesurer la précision V1 |

---

## 3. Architecture v2.0

### Nouvelle structure

```
ESGProductionControlCenter/
│
├── app.py                          # Home page v2.0 (+ backward compat SAFETY_TEXT / render_app)
│
├── pages/
│   ├── 01_Project_Cockpit.py       # Vue 30 secondes — KPI globaux
│   ├── 02_Run_Monitoring.py        # Suivi des runs et documents
│   ├── 03_Document_Inspector.py    # Inspecter un document précis
│   ├── 04_Candidate_Explorer.py    # Explorer et filtrer les candidats
│   ├── 05_Human_Review_Desk.py     # File de revue prioritaire
│   ├── 06_Manual_Baseline.py       # Baseline manuelle Schneider TCFD
│   ├── 07_V1_vs_V2_Benchmark.py    # Préparer la comparaison V2
│   └── 08_Quality_Decision_Board.py # Décision GO / GO_WITH_FIXES / NO_GO
│
├── src/
│   └── esg_production_control_center/
│       ├── data_loader.py          # Chargement données pilot (lecture seule)
│       ├── metrics.py              # Calcul KPI (fonctions pures)
│       ├── decision_rules.py       # Logique GO / GO_WITH_FIXES / NO_GO
│       ├── filters.py              # Filtrage DataFrames
│       ├── export_utils.py         # Exports sécurisés (jamais vers sources)
│       ├── run_registry.py         # Découverte des runs disponibles
│       └── ui_components.py        # Composants Streamlit réutilisables
│
└── tests/
    ├── test_data_loader_v20.py      (11 tests)
    ├── test_metrics_v20.py          (14 tests)
    ├── test_decision_rules_v20.py   (12 tests)
    ├── test_read_only_safety_v20.py  (4 tests)
    └── test_exports_v20.py           (7 tests)
```

### Inputs lus (lecture seule)

| Fichier | Source |
|---------|--------|
| `pilot_run_summary.json` | Run pilot v2 |
| `selected_documents.csv` | Run pilot v2 |
| `_review_quality_audit/pilot_review_quality_summary.json` | PilotReviewQualityAudit v1.0 |
| `_review_quality_audit/candidate_counts_by_document.csv` | PilotReviewQualityAudit v1.0 |
| `_review_quality_audit/candidate_counts_by_family.csv` | PilotReviewQualityAudit v1.0 |
| `_review_quality_audit/top_possible_indicators_all_docs.csv` | PilotReviewQualityAudit v1.0 |
| `_review_quality_audit/false_positive_risk_samples.csv` | PilotReviewQualityAudit v1.0 |
| `{company}/{year}/{doc_type}/{doc_id}/04_review_workspace/manual_review_workspace.csv` | Pilot per-document |

### Outputs produits (sécurisés)

Tous les exports vont dans :
- `<run_root>/_control_center_exports/`
- `ESGProductionControlCenter/outputs/control_center_reports/`

Aucun fichier source n'est jamais modifié.

---

## 4. Pages créées

### Page 1 — Project Cockpit
- Phases projet (7 statuts GO/GO_WITH_FIXES/En préparation)
- KPI en 3 lignes : documents, candidats, qualité
- Décision GO_WITH_FIXES avec explication
- Critères évalués (tableau)
- Prochaines étapes recommandées

### Page 2 — Run Monitoring
- Métriques run (selected/success/failed)
- Table per-document filtrable
- Détail document (étapes complétées, erreur, log)
- Pilot command log (pilot_command_log.jsonl)

### Page 3 — Document Inspector
- Sélecteurs : company / year / doc_type / document_id
- 5 onglets : Résumé, Candidats utiles, Candidats à risque, Distribution par page, Logs

### Page 4 — Candidate Explorer
- Filtres : statut, famille, entreprise, moteur, année, has_value, has_quote, texte
- Vues rapides : 5 presets (utiles, à vérifier, bruit, GHG, unknown/boundary)
- Téléchargement CSV de la vue filtrée
- Distribution par famille et statut

### Page 5 — Human Review Desk
- File prioritaire (possible_indicator + valeur + quote + famille non-bruyante)
- Filtres supplémentaires
- Export `_control_center_exports/review_queue_export.csv`
- Actions futures préparées (v2.1)

### Page 6 — Manual Baseline
- 23 indicateurs Schneider TCFD 2023 (lecture manuelle réelle)
- Métriques de précision V1 estimée (~50-55%)
- 6 types d'erreurs V1 identifiés
- Export template `manual_baseline_template.csv`

### Page 7 — V1 vs V2 Benchmark
- Métriques V1 actuelles
- Erreurs V1 connues + correction V2 proposée
- Emplacements réservés pour fichiers V2
- Architecture V2 prévue (top-down, variable-driven)

### Page 8 — Quality Decision Board
- Bannière de décision GO_WITH_FIXES
- Critères évalués avec ✅/❌
- KPI qui ont déterminé la décision
- Règles de décision expliquées
- Export `quality_decision_report.md`

---

## 5. Termes humains utilisés

| Terme technique | Terme humain |
|-----------------|--------------|
| `possible_indicator` | Probablement utile |
| `needs_review` | À vérifier |
| `reject_candidate` | Probablement bruit |
| `manual_review_workspace.csv` | Table de revue humaine |
| `ESGExtractionOrchestrator` | Candidats consolidés |
| `indicator_family = unknown` | Famille inconnue |
| `indicator_family = boundary` | Limite système |

---

## 6. Sécurité lecture seule

- **Aucun pipeline relancé** depuis l'interface
- **Aucun PDF modifié**
- **ESGFinalCorpus non modifié**
- **Outputs pilot v2 non modifiés**
- Les exports vont uniquement dans `_control_center_exports/`
- Test `test_read_only_no_source_modification` vérifie que load_all_review_workspaces ne modifie aucun fichier

---

## 7. Tests exécutés

### Nouveaux tests v2.0

| Fichier | Tests | Résultat |
|---------|-------|----------|
| `test_data_loader_v20.py` | 11 | ✅ PASSED |
| `test_metrics_v20.py` | 14 | ✅ PASSED |
| `test_decision_rules_v20.py` | 12 | ✅ PASSED |
| `test_read_only_safety_v20.py` | 4 | ✅ PASSED |
| `test_exports_v20.py` | 7 | ✅ PASSED |
| **Total nouveaux** | **48** | **✅ 48/48** |

### Tests ESGProductionControlCenter (total)

```
75 passed, 1 warning
```

(27 anciens + 48 nouveaux — 0 régression)

### Suite globale

```
552 passed, 5 warnings in 107.99s
```

**Avant v2.0 :** 504 tests  
**Après v2.0 :** 552 tests (+48, 0 régression)

### Smoke test données réelles

| Métrique | Valeur calculée | Valeur attendue |
|----------|-----------------|-----------------|
| Documents | 10/10 | 10/10 ✅ |
| Candidats | 6 027 | 6 027 ✅ |
| possible_indicator | 1 020 | 1 020 ✅ |
| Valeurs manquantes | 52,3 % | 52,3 % ✅ |
| Bruit familial | 62,3 % | 62,2 % ✅ |
| Charge de revue | 127,5 h | 127,5 h ✅ |
| Décision | GO_WITH_FIXES | GO_WITH_FIXES ✅ |

---

## 8. Résultat

### Interface opérationnelle

```
streamlit run ESGProductionControlCenter/app.py
```

- 8 pages disponibles dans la navigation gauche
- Run root configurable depuis chaque page (sidebar)
- Données réelles du pilot 10 documents chargées correctement
- Décision GO_WITH_FIXES affichée correctement
- Exports disponibles (review queue, decision report, baseline template)

---

## 9. Décision finale

### GO

- L'interface démarre
- Les 8 pages existent
- L'utilisateur peut charger le run pilot 10 docs
- Les KPI s'affichent correctement
- Les documents sont inspectables
- Les candidats sont filtrables
- La file de revue prioritaire est visible
- La décision GO_WITH_FIXES est affichée
- Aucun fichier source n'est modifié
- Tests module : 75/75 passent
- Tests globaux : 552 passent
- 0 régression

---

## 10. Prochaine étape recommandée

### Option A : Lancer l'interface et inspecter manuellement le pilot
```powershell
streamlit run ESGProductionControlCenter/app.py
```

### Option B : Corriger les erreurs V1 pour GO
1. Filtrer les numéros de section → faux positifs immédiats
2. Forcer famille=ghg_emissions quand unité CO2
3. Implémenter filtre auto pour needs_review unknown/boundary sans valeur

### Option C : Démarrer l'Extraction V2
1. Créer le catalogue YAML de 30-50 variables ESG prioritaires
2. Implémenter le PatternMatcher (Layer 1 — regex déterministe)
3. Tester sur Schneider TCFD (ground truth disponible dans Page 6)
4. Comparer précision/recall V1 vs V2 (Page 7)

---

## Sécurité

- Aucun auto-accept
- Aucun PDF modifié
- ESGFinalCorpus non modifié
- Outputs du pilot v2 non modifiés
- Exports uniquement dans `_control_center_exports/`

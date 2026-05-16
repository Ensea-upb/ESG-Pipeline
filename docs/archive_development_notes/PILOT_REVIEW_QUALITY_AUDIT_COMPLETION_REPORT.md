# PILOT_REVIEW_QUALITY_AUDIT_COMPLETION_REPORT

**Date :** 2026-05-14  
**Phase :** PilotReviewQualityAudit v1.0  
**Auteur :** Claude Code (Sonnet 4.6)  
**Décision finale :** GO_WITH_FIXES

---

## 1. Fichiers créés

| Fichier | Description |
|---------|-------------|
| `tools/audit_pilot_review_quality.py` | Script principal d'audit (CLI) |
| `tests/test_pilot_review_quality_audit_v10.py` | 11 tests unitaires (fixtures synthétiques) |
| `EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2/_review_quality_audit/pilot_review_quality_summary.json` | Résumé global JSON |
| `_review_quality_audit/candidate_counts_by_document.csv` | Stats par document (10 lignes) |
| `_review_quality_audit/candidate_counts_by_family.csv` | Stats par famille ESG (13 lignes) |
| `_review_quality_audit/candidate_counts_by_status.csv` | Distribution des statuts (3 lignes) |
| `_review_quality_audit/top_possible_indicators_all_docs.csv` | Meilleurs candidats (200 lignes) |
| `_review_quality_audit/false_positive_risk_samples.csv` | Candidats à risque de faux positif (603 lignes) |
| `_review_quality_audit/review_burden_report.md` | Rapport lisible — charge de revue |
| `_review_quality_audit/PILOT_REVIEW_QUALITY_AUDIT_REPORT.md` | Rapport de décision projet |

**Fichiers non modifiés :**
- PDFs, ESGFinalCorpus, tous les outputs du pilot v2 (lecture seule respectée).

---

## 2. Tests exécutés

### Tests spécifiques au module d'audit

```
tests/test_pilot_review_quality_audit_v10.py — 11 passed
```

| Test | Résultat |
|------|----------|
| `test_audit_script_exists` | PASSED |
| `test_finds_review_workspaces` | PASSED |
| `test_counts_candidates_by_document` | PASSED |
| `test_counts_candidates_by_family` | PASSED |
| `test_detects_missing_quotes` | PASSED |
| `test_detects_false_positive_footnote` | PASSED |
| `test_detects_year_mismatch` | PASSED |
| `test_top_possible_indicators_limit` | PASSED |
| `test_outputs_are_created` | PASSED |
| `test_audit_is_read_only` | PASSED |
| `test_summary_has_decision_field` | PASSED |

### Suite globale

```
504 passed, 5 warnings in 128.33s
```

**Avant cette phase :** 493 tests.  
**Après :** 504 tests (+11, 0 régression).

---

## 3. Résultats globaux

| Métrique | Valeur |
|----------|--------|
| Workspaces audités | 10 / 10 |
| Workspaces manquants | 0 |
| Total candidats | 6 027 |
| possible_indicator | 1 020 (16,9%) |
| needs_review | 4 412 (73,2%) |
| reject_candidate | 595 (9,9%) |
| Quotes manquantes | 0 (0,0%) — excellent |
| Valeurs manquantes | 3 150 (52,3%) — problématique |
| Unités manquantes | 5 174 (85,8%) — élevé |
| Années manquantes | 0 (0,0%) — excellent |
| Company manquante | 0 (0,0%) — excellent |
| Fiscal year manquant | 0 (0,0%) — excellent |

---

## 4. Nombre de workspaces audités

**10 / 10** workspaces trouvés et audités sans erreur critique.

| Document | Candidats | possible | needs | reject | Charge (min) | Niveau |
|----------|-----------|----------|-------|--------|-------------|--------|
| totalenergies / 01_urd_annual_report | 1 481 | 248 | 1 116 | 117 | 1 900 | excessive |
| air-liquide / 01_urd_annual_report | 720 | 155 | 524 | 41 | 1 007 | excessive |
| schneider-electric / 01_urd_annual_report | 596 | 124 | 422 | 50 | 836 | excessive |
| totalenergies / 02_sustainability_csrd_esrs | 490 | 88 | 358 | 44 | 688 | excessive |
| totalenergies / 05_half_year_financial | 441 | 64 | 332 | 45 | 584 | excessive |
| schneider-electric / 13_investor_presentations | 410 | 86 | 295 | 29 | 580 | excessive |
| schneider-electric / 04_vigilance_plan | 297 | 53 | 221 | 23 | 415 | excessive |
| schneider-electric / 03_climate_report | 218 | 67 | 130 | 21 | 342 | excessive |
| schneider-electric / 16_agm_minutes | 258 | 101 | 120 | 37 | 450 | excessive |
| lvmh / 16_agm_minutes | 167 | 34 | 114 | 19 | 280 | excessive |

---

## 5. Nombre total de candidats

**6 027 candidats** répartis sur 10 documents.

- Moyenne par document : **602,7**
- Médiane : **334,5**
- Maximum : **1 481** (totalenergies / 01_urd)

---

## 6. Top familles ESG

| Famille | Candidats | share | possible |
|---------|-----------|-------|----------|
| unknown | 2 768 | 45,9% | 174 |
| boundary | 984 | 16,3% | 233 |
| ghg_emissions | 610 | 10,1% | 170 |
| policy | 468 | 7,8% | 47 |
| energy | 422 | 7,0% | 145 |
| risk | 244 | 4,0% | 27 |
| methodology | 227 | 3,8% | 102 |
| workforce | 144 | 2,4% | 85 |
| water | 60 | 1,0% | 30 |
| governance | 58 | 1,0% | 4 |

**Observation clé :** 62,2% des candidats appartiennent aux familles `unknown` ou `boundary`, qui sont à fort bruit. Ce ratio élevé explique la décision GO_WITH_FIXES.

---

## 7. Taux de faux positifs probables

| Niveau | Nombre | Taux |
|--------|--------|------|
| high   | 4      | 0,07% |
| medium | 599    | 9,9% |

- Faux positifs à haut risque : **très faible** (4/6027).
- Faux positifs à risque moyen : principalement des **year_mismatch** (candidats avec données historiques) et **missing_page_number**.
- La détection de faux positifs confirme que le pipeline est sain — peu de candidats clairement erronés.

**Raisons les plus fréquentes dans les 603 FP détectés :**
- `year_mismatch` : années historiques (2015–2022) dans documents fiscal_year=2024.
- `missing_page_number` : candidats sans page_number (principalement familles `unknown`/`boundary`).
- `unit_family_mismatch` : unités incohérentes (ex. `hours` pour `ghg_emissions`).

---

## 8. Estimation de charge de revue

| Hypothèse | Valeur |
|-----------|--------|
| Barème possible_indicator | 3 min/candidat |
| Barème needs_review | 1 min/candidat |
| Barème reject_candidate | 0,3 min/candidat |
| **Total estimé** | **7 650 min = 127,5 heures** |
| Moyenne/document | 765 min = 12,8 heures |

La charge totale brute est **excessive** pour une revue complète.

**Cependant :** en pratique, la revue humaine porterait uniquement sur les `possible_indicator` (1 020), soit **51 heures** — plus réaliste mais encore élevé pour 10 documents.

**Voie d'amélioration :** filtrer automatiquement les `needs_review` appartenant aux familles `unknown` et `boundary` (représentent 46% du corpus) réduirait la charge de ~60%.

---

## 9. Décision finale

### GO_WITH_FIXES

**Critères évalués :**

| Critère | Résultat |
|---------|----------|
| 10 workspaces trouvés | ✅ |
| 0 workspaces manquants | ✅ |
| Quotes présentes pour possible_indicator | ✅ 100% |
| company/fiscal_year présents | ✅ 100% |
| Valeurs manquantes < 30% | ❌ 52,3% |
| Familles bruit < 50% | ❌ 62,2% (unknown + boundary) |
| Charge ≤ 120 min/doc | ❌ 765 min/doc |
| Faux positifs hauts-risque < 10% | ✅ 0,07% |

**Conclusion :** Le pilot est techniquement complet et lisible. Les workspaces sont exploitables. Mais la proportion élevée de candidats `unknown`/`boundary` (bruit) et la charge de revue excessive empêchent un GO direct pour 20 documents.

---

## 10. Recommandation pour la suite

### Avant de passer à 20 documents

1. **Réduire le bruit `unknown`/`boundary`**
   - Investiguer pourquoi 62,2% des candidats ont une famille non reconnue.
   - Améliorer le classifieur de familles dans `ESGCSVExtraction` ou `ESGIndicatorValidation`.
   - Target : réduire à < 30%.

2. **Corriger les valeurs manquantes**
   - 52,3% des candidats n'ont pas de `raw_value` — acceptable pour les familles `policy`/`risk`/`methodology` mais problématique pour `ghg_emissions`/`energy`/`water`.
   - Séparer les candidats qualitatifs (policy, risk) des quantitatifs (GHG, energy) et appliquer des règles de validation différentes.

3. **Implémenter un filtre automatique**
   - Auto-rejeter les candidats `needs_review` de familles `unknown`/`boundary` sans valeur ni unité.
   - Réduirait la charge de revue de ~60%.

4. **Valider manuellement un échantillon**
   - Revoir manuellement 20-30 `possible_indicator` des familles `ghg_emissions`, `energy`, `water`, `workforce` pour évaluer la précision réelle.

5. **Relancer l'audit qualité v2** après corrections → si GO, lancer pilot 20 documents.

### Ne pas annoncer GO pour 20 documents tant que :
- La précision des `possible_indicator` n'a pas été estimée par revue manuelle.
- Le taux de bruit familial reste > 50%.
- La charge de revue dépasse 120 min/doc en moyenne.

---

## Sécurité

- Aucun auto-accept.
- Aucun PDF modifié.
- ESGFinalCorpus non modifié.
- Outputs du pilot v2 non modifiés (lecture seule respectée).
- Outputs uniquement dans `_review_quality_audit/`.

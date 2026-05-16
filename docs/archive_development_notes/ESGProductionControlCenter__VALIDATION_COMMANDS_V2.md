# VALIDATION_COMMANDS_V2

## Lancer l'interface

```powershell
# Depuis la racine ESG
streamlit run ESGProductionControlCenter/app.py
```

L'interface s'ouvre sur la page d'accueil.  
La navigation à gauche donne accès aux 8 pages.

---

## Tests du module ESGProductionControlCenter

```powershell
python -m pytest ESGProductionControlCenter/tests/ -q
```

Résultat attendu : `75 passed, 1 warning`

### Tests v2.0 uniquement

```powershell
python -m pytest ESGProductionControlCenter/tests/test_data_loader_v20.py `
               ESGProductionControlCenter/tests/test_metrics_v20.py `
               ESGProductionControlCenter/tests/test_decision_rules_v20.py `
               ESGProductionControlCenter/tests/test_read_only_safety_v20.py `
               ESGProductionControlCenter/tests/test_exports_v20.py `
               -v
```

Résultat attendu : `48 passed`

---

## Suite globale (no régression)

```powershell
python -m pytest -q
```

Résultat attendu : `552 passed, 5 warnings`

---

## Smoke test données réelles

```powershell
python -c "
import sys; sys.path.insert(0, '.')
from pathlib import Path
from ESGProductionControlCenter.src.esg_production_control_center.data_loader import (
    load_pilot_summary, build_candidate_table, load_false_positive_risks
)
from ESGProductionControlCenter.src.esg_production_control_center.metrics import compute_all_metrics
from ESGProductionControlCenter.src.esg_production_control_center.decision_rules import compute_decision

run_root = Path('EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2')
ps = load_pilot_summary(run_root)
df = build_candidate_table(run_root)
fp = load_false_positive_risks(run_root)
m = compute_all_metrics(ps, df, fp)
d = compute_decision(m)
print('Documents:', m['documents_success'], '/', m['documents_selected'])
print('Candidats:', m['candidate_count_total'])
print('Décision:', d)
"
```

Résultat attendu :
```
Documents: 10 / 10
Candidats: 6027
Décision: GO_WITH_FIXES
```

---

## Vérifier lecture seule (aucun fichier source modifié)

```powershell
python -m pytest ESGProductionControlCenter/tests/test_read_only_safety_v20.py -v
```

---

## Validation projet globale

```powershell
python tools/run_project_validation.py --project-root . --full
```

---

## Pages disponibles

| Page | URL (local) |
|------|------------|
| Home | http://localhost:8501 |
| Project Cockpit | http://localhost:8501/Project_Cockpit |
| Run Monitoring | http://localhost:8501/Run_Monitoring |
| Document Inspector | http://localhost:8501/Document_Inspector |
| Candidate Explorer | http://localhost:8501/Candidate_Explorer |
| Human Review Desk | http://localhost:8501/Human_Review_Desk |
| Manual Baseline | http://localhost:8501/Manual_Baseline |
| V1 vs V2 Benchmark | http://localhost:8501/V1_vs_V2_Benchmark |
| Quality Decision Board | http://localhost:8501/Quality_Decision_Board |

---

## Configurer le dossier de run

Dans la sidebar de chaque page, modifier le champ **Dossier de run** :

```
EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2
```

Le path est relatif à la racine du projet ESG.

---

## Exporter des outputs (lecture seule respectée)

Les exports sont disponibles dans chaque page :

- **Page 5 — Human Review Desk** : `_control_center_exports/review_queue_export.csv`
- **Page 6 — Manual Baseline** : `_control_center_exports/manual_baseline_template.csv`
- **Page 8 — Quality Decision Board** : `_control_center_exports/quality_decision_report.md`

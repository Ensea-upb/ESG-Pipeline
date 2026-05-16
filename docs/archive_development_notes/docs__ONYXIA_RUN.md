# Exécuter le pipeline ESG sur Onyxia

Ce guide décrit uniquement la construction du corpus documentaire ESG :

```text
ingestion documentaire
-> post-processing
-> déduplication
-> registre canonique
-> organisation taxonomique
-> validation documentaire légère
-> sélection finale
-> ESGFinalCorpus isolé par run_id
```

Il ne couvre pas l'extraction d'indicateurs ESG, le RAG, les bases vectorielles, les LLM ou le scoring ESG.

## 1. Copier Ou Cloner Le Projet

Sur Onyxia, placer le projet dans un dossier de travail, par exemple :

```bash
cd /home/onyxia/work
git clone <url-du-repo> ESG
```

Si le projet est transféré manuellement, conserver la structure des dossiers :

```text
ESG/
├── ESGOrchestrator/
├── DocumentPostProcessing/
├── AnnualReportRetriever/
├── SustainabilityReportRetriever/
├── ClimateReportRetriever/
├── CorporatePolicyRetriever/
└── ...
```

## 2. Définir La Racine Projet

```bash
export ESG_PROJECT_ROOT=/home/onyxia/work/ESG
```

En local Windows, l'équivalent est :

```powershell
$env:ESG_PROJECT_ROOT="C:\Users\hp\Desktop\ESG"
```

## 3. Installer Les Dépendances

Le fichier global est :

```text
requirements_all.txt
```

Installation manuelle :

```bash
cd "$ESG_PROJECT_ROOT"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements_all.txt
```

## 4. Lancer Le Pilot Onyxia

Commande recommandée :

```bash
cd /home/onyxia/work/ESG
bash scripts/run_onyxia_pipeline.sh
```

Par défaut, ce script lance :

```text
profile: onyxia_pilot_5x2
companies: LVMH, TotalEnergies, Schneider Electric, Air Liquide, BNP Paribas
years: 2024, 2025
```

Pour faire un dry-run :

```bash
DRY_RUN=1 bash scripts/run_onyxia_pipeline.sh
```

Pour forcer un run_id :

```bash
RUN_ID=onyxia_pilot_test_001 bash scripts/run_onyxia_pipeline.sh
```

## 5. Inspecter Les Logs Et Sorties

Les sorties sont isolées par run :

```text
ESGOrchestrator/runs/<run_id>/
├── run_state.json
├── task_log.csv
├── coverage_matrix.csv
├── final_summary.json
├── postprocessing/
├── ESGCorpus/
├── ESGCorpusTaxonomy/
└── ESGFinalCorpus/
```

Fichiers utiles :

```bash
cat ESGOrchestrator/runs/<run_id>/final_summary.json
head ESGOrchestrator/runs/<run_id>/task_log.csv
```

Le corpus final du run est ici :

```text
ESGOrchestrator/runs/<run_id>/ESGFinalCorpus/
```

## 6. Reprendre Un Run Interrompu

Le profil active `resume: true`, et les sorties sont isolées par `run_id`.

Relancer avec le même `run_id` :

```bash
cd "$ESG_PROJECT_ROOT/ESGOrchestrator"
python scripts/run_pipeline.py --profile onyxia_pilot_5x2 --run-id <run_id>
```

Note : le mécanisme de reprise est encore minimal. Vérifier `task_log.csv` avant relance longue.

## 7. Lancer Le CAC40 Complet Après Validation

Ne lancer cette commande qu'après validation du pilot :

```bash
cd /home/onyxia/work/ESG/ESGOrchestrator
python scripts/run_pipeline.py --profile onyxia_cac40_5y
```

Le profil complet cible :

```text
CAC40 x 2021, 2022, 2023, 2024, 2025
```

## 8. Variables Utiles

```bash
export ESG_PROJECT_ROOT=/home/onyxia/work/ESG
export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=1
```

Pendant un run orchestré, le post-processing reçoit automatiquement :

```text
ESG_POSTPROCESS_INPUT_ROOT=$ESG_PROJECT_ROOT/data/dossier_ingestion_0
ESG_POSTPROCESS_OUTPUT_ROOT=$ESG_PROJECT_ROOT/ESGOrchestrator/runs/<run_id>/postprocessing
```

## 9. Limites Actuelles

- Ne pas lancer le profil complet avant validation du pilot.
- Le projet construit le corpus documentaire, mais ne fait pas encore l'extraction ESG.
- `max_workers` est configuré, mais l'exécution reste prudente et essentiellement séquentielle.
- La reprise longue doit être vérifiée avec `task_log.csv` et `final_summary.json`.

# ClimateReportRetriever

**Version : v0.1**

Moteur d'ingestion documentaire pour les rapports climat, TCFD, plans de transition et rapports carbone.

---

## Objectif

Ce moteur recherche, score, télécharge et stocke des candidats documents de type :

- Climate Report
- TCFD Report / TCFD Index
- Climate Transition Plan / Transition Plan
- Net Zero Transition Plan / Net Zero Report
- Carbon Report / GHG Emissions Report
- CDP Climate Response
- Bilan carbone / Rapport climat
- Plan de transition / Rapport TCFD
- Stratégie climat / Rapport émissions carbone

Il ne valide pas définitivement les documents. Son rôle est de constituer un corpus de candidats plausibles pour une analyse ESG aval.

---

## Architecture

```
ClimateReportRetriever/
├── src/climate_report_retriever/
│   ├── __init__.py
│   ├── models.py          — Dataclasses : Company, ClimateReportRequest, SearchCandidate, ScoredCandidate, DownloadResult
│   ├── utils.py           — Utilitaires texte et fichier (slugify, normalize, sha256, ...)
│   ├── search.py          — ClimateReportSearch : requêtes Tavily multi-terminologie
│   ├── scorer.py          — ClimateReportScorer : scoring multi-signaux + classification
│   ├── downloader.py      — PDFDownloader : téléchargement robuste avec retry
│   ├── html_resolver.py   — HTMLToPDFLinkResolver : extraction de liens PDF depuis pages HTML
│   ├── storage.py         — ClimateReportStorage : stockage + manifests JSON
│   └── retriever.py       — ClimateReportRetriever : orchestrateur principal
├── scripts/
│   ├── run_download_all.py   — CLI pour une seule entreprise
│   └── run_benchmark.py      — Benchmark multi-entreprises
├── requirements.txt
└── README.md
```

---

## Pipeline d'ingestion

```
Requêtes Tavily (17 requêtes par défaut)
    ↓
SearchCandidate[]
    ↓
Scoring multi-signaux (ClimateReportScorer)
    ↓
ScoredCandidate[] (triés par score décroissant)
    ↓
Filtre seuil (score >= min_score, défaut : 80)
    ↓
Pour chaque candidat :
    ├─ PDF direct → téléchargement
    └─ Page HTML → résolution HTML→PDF → rescoring → téléchargement
    ↓
Filtre temporel (fiscal_year et fiscal_year - 1)
    ↓
Déduplication par URL
    ↓
PDFDownloader (3 stratégies × variantes d'URL × 2 retries)
    ↓
ClimateReportStorage
    ↓
data/dossier_ingestion_0/climate_reports/<entreprise>/<année>/candidates/
    candidate_001_score_85_0.pdf
    candidate_001_manifest.json
    ↓
data/dossier_ingestion_0/registry/climate_reports_registry.jsonl
```

---

## Système de scoring

Le scorer attribue un score de 0 à 100 à chaque candidat via des signaux positifs et négatifs.

### Signaux positifs

| Signal | Points |
|---|---|
| Année fiscale trouvée dans le texte/URL | +25 |
| Mots-clés forts climat (climate report, TCFD, transition plan, net zero, ...) | +35 |
| Mots-clés TCFD/CDP (tcfd index, carbon disclosure project, science based targets, ...) | +35 |
| Mots-clés faibles climat (climate, carbon, ghg, emissions, ...) | +18 |
| Nom de l'entreprise détecté | +20 |
| Domaine officiel | +20 |
| URL PDF directe | +10 |
| Nom de fichier compatible (climatereport, tcfd, transitionplan, ...) | +15 |
| Signal plan de transition avec contexte climat | +5 |
| Rapport annuel/URD contenant signaux climat | +8 |
| CDN asset plausible + PDF + nom fichier + entreprise | +5 |
| Agrégateur documentaire tiers | +3 |

### Pénalités

| Signal | Points |
|---|---|
| Document financier sans signal climat | -45 |
| Présentation / slides | -40 |
| Document assemblée générale / gouvernance | -60 |
| Document périodique (Q1, Q2, ...) | -30 |
| Communiqué de presse | -35 |
| Domaine de communiqué financier | -30 |
| Domaine de faible confiance (Scribd, Slideshare, ...) | -45 |
| Années détectées mais pas l'année cible | -15 |
| Aucun signal climat fort | -25 |
| Nom entreprise absent | -25 |
| URL non PDF | -8 |

### Classes documentaires

| Classe | Décision |
|---|---|
| `standalone_climate_report` | auto_download |
| `tcfd_cdp_disclosure` | auto_download |
| `climate_transition_plan` | auto_download |
| `annual_report_with_climate_content` | auto_download |
| `html_landing_page` | pdf_resolution_required |
| `financial_only_document` | reject (plafond 50) |
| `presentation` | reject (plafond 50) |
| `periodic_report` | reject (plafond 55) |
| `press_release` | reject (plafond 55) |
| `low_trust_copy` | reject (plafond 59) |
| `governance_meeting_document` | reject (plafond 40) |
| `unknown` | reject (plafond 59) |

---

## Dossier de stockage

```
data/dossier_ingestion_0/
├── climate_reports/
│   └── <company_slug>/
│       └── <fiscal_year>/
│           └── candidates/
│               ├── candidate_001_score_92_0.pdf
│               ├── candidate_001_manifest.json
│               ├── candidate_002_score_85_5.pdf
│               └── candidate_002_manifest.json
├── registry/
│   ├── climate_reports_registry.jsonl
│   ├── download_all_climate_<company>_<year>.json
│   └── benchmark_climate_report_<year>_<timestamp>.json
└── tmp/
    └── (fichiers temporaires de téléchargement)
```

---

## Utilisation

### Prérequis

```bash
pip install -r requirements.txt
```

Créer un fichier `.env` à la racine du projet `ClimateReportRetriever/` :

```
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Télécharger pour une seule entreprise

```bash
cd ClimateReportRetriever

python scripts/run_download_all.py \
    --company-name "TotalEnergies" \
    --fiscal-year 2024 \
    --official-domain totalenergies.com \
    --ticker TTE \
    --isin FR0000120271 \
    --jurisdiction France \
    --min-score 80
```

### Benchmark multi-entreprises (LVMH, TotalEnergies, Schneider Electric)

```bash
cd ClimateReportRetriever

python scripts/run_benchmark.py \
    --fiscal-year 2024 \
    --min-score 80 \
    --sleep 1
```

### Utilisation programmatique

```python
from src.climate_report_retriever.models import Company
from src.climate_report_retriever.retriever import ClimateReportRetriever

company = Company(
    name="TotalEnergies",
    official_domain="totalenergies.com",
    ticker="TTE",
    isin="FR0000120271",
    jurisdiction="France",
)

retriever = ClimateReportRetriever(
    root_dir="data/dossier_ingestion_0",
)

result = retriever.download_high_score_candidates(
    company=company,
    fiscal_year=2024,
    min_score=80.0,
)

print(f"Téléchargés : {result.downloaded_count}")
print(f"Échecs      : {result.failed_count}")
print(f"Ignorés     : {result.skipped_count}")

for item in result.downloaded:
    print(f"  [{item['rank']}] score={item['score']} | {item['title']}")
    print(f"       local_path: {item['local_path']}")
```

---

## Paramètres du retriever

| Paramètre | Défaut | Description |
|---|---|---|
| `root_dir` | `data/dossier_ingestion_0` | Dossier racine de stockage |
| `auto_download_threshold` | `80.0` | Score minimum pour téléchargement automatique |
| `human_review_threshold` | `60.0` | Score minimum pour revue humaine |
| `min_score` (download) | `80.0` | Filtre de sélection des candidats |

---

## Contraintes

- Ce moteur ne valide pas définitivement les documents téléchargés.
- Ce moteur ne déduplique pas les documents entre moteurs différents.
- Ce moteur ne réalise pas l'extraction ESG ni le scoring ESG.
- Chaque manifest JSON contient les signaux de scoring pour audit.
- Le registre JSONL permet l'audit en temps réel de l'ingestion.

---

## Moteurs associés

| Moteur | Documents cibles |
|---|---|
| `AnnualReportRetriever` | Rapports annuels, URD, DEU |
| `SustainabilityReportRetriever` | Rapports ESG, RSE, durabilité, CSRD |
| `ClimateReportRetriever` | Rapports climat, TCFD, transition, carbone |
| `GovernanceReportRetriever` | *(à venir)* |
| `RemunerationReportRetriever` | *(à venir)* |
| `VigilancePlanRetriever` | *(à venir)* |

# GovernanceReportRetriever

**Version : v0.1**

Moteur d'ingestion documentaire pour les rapports de gouvernance d'entreprise.

---

## Objectif

Ce moteur recherche, score, télécharge et stocke des candidats documents de type :

- Corporate Governance Report
- Governance Statement / Corporate Governance Statement
- Corporate Governance Charter / Governance Charter
- Corporate Governance Framework
- Corporate Governance Code
- Board Governance Report
- Rapport de gouvernance / Rapport gouvernance d'entreprise
- Déclaration de gouvernance / Charte de gouvernance
- Code de gouvernance

**Distinction clé** : ce moteur rejette explicitement les avis de convocation
d'assemblée générale (AGM notices, proxy forms, avis de convocation), qui ne sont
pas des rapports de gouvernance.

---

## Architecture

```
GovernanceReportRetriever/
├── src/governance_report_retriever/
│   ├── __init__.py
│   ├── models.py          — Dataclasses : Company, GovernanceReportRequest, ...
│   ├── utils.py           — Utilitaires texte et fichier
│   ├── search.py          — GovernanceReportSearch : requêtes Tavily multi-terminologie
│   ├── scorer.py          — GovernanceReportScorer : scoring + classification
│   ├── downloader.py      — PDFDownloader : téléchargement robuste avec retry
│   ├── html_resolver.py   — HTMLToPDFLinkResolver : extraction liens PDF
│   ├── storage.py         — GovernanceReportStorage : stockage + manifests
│   └── retriever.py       — GovernanceReportRetriever : orchestrateur principal
├── scripts/
│   ├── run_download_all.py
│   └── run_benchmark.py
├── requirements.txt
└── README.md
```

---

## Pipeline d'ingestion

```
Requêtes Tavily (15-21 requêtes par défaut)
    ↓
SearchCandidate[]
    ↓
Scoring multi-signaux (GovernanceReportScorer)
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
GovernanceReportStorage
    ↓
data/dossier_ingestion_0/governance_reports/<entreprise>/<année>/candidates/
    ↓
data/dossier_ingestion_0/registry/governance_reports_registry.jsonl
```

---

## Système de scoring

### Signaux positifs

| Signal | Points |
|---|---|
| Année fiscale trouvée | +25 |
| Mots-clés forts gouvernance (corporate governance report, governance statement, rapport de gouvernance, ...) | +35 |
| Mots-clés divulgation (AFEP-MEDEF, board diversity, comité d'audit, ...) | +35 |
| Mots-clés faibles (governance, board of directors, conseil d'administration, ...) | +18 |
| Nom de l'entreprise détecté | +20 |
| Domaine officiel | +20 |
| URL PDF directe | +10 |
| Nom de fichier compatible (governancereport, charte-de-gouvernance, ...) | +15 |
| Rapport annuel/URD contenant signaux gouvernance | +8 |
| CDN asset plausible | +5 |
| Agrégateur tiers | +3 |

### Pénalités

| Signal | Points |
|---|---|
| Avis de convocation AGM (notice of meeting, vote instructions, ...) | -60 |
| Document financier sans signal gouvernance | -45 |
| Présentation / slides | -40 |
| Communiqué de presse | -35 |
| Domaine de communiqué | -30 |
| Document périodique (quarterly, half-year, ...) | -30 |
| Domaine de faible confiance (Scribd, ...) | -45 |
| Années non pertinentes | -15 |

### Classes documentaires

| Classe | Décision |
|---|---|
| `standalone_governance_report` | auto_download |
| `governance_disclosure` | auto_download |
| `annual_report_with_governance_section` | auto_download |
| `html_landing_page` | pdf_resolution_required |
| `agm_convocation_document` | reject (plafond 40) |
| `financial_only_document` | reject (plafond 50) |
| `presentation` | reject (plafond 50) |
| `periodic_report` | reject (plafond 55) |
| `press_release` | reject (plafond 55) |
| `low_trust_copy` | reject (plafond 59) |
| `unknown` | reject (plafond 59) |

---

## Dossier de stockage

```
data/dossier_ingestion_0/
├── governance_reports/
│   └── <company_slug>/
│       └── <fiscal_year>/
│           └── candidates/
│               ├── candidate_001_score_92_0.pdf
│               └── candidate_001_manifest.json
├── registry/
│   ├── governance_reports_registry.jsonl
│   ├── download_all_governance_<company>_<year>.json
│   └── benchmark_governance_report_<year>_<timestamp>.json
└── tmp/
```

---

## Utilisation

### Prérequis

```bash
pip install -r requirements.txt
```

Fichier `.env` à la racine de `GovernanceReportRetriever/` :

```
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### CLI mono-entreprise

```bash
cd GovernanceReportRetriever

python scripts/run_download_all.py \
    --company-name "Schneider Electric" \
    --fiscal-year 2024 \
    --official-domain se.com \
    --min-score 80
```

### Benchmark multi-entreprises

```bash
cd GovernanceReportRetriever

python scripts/run_benchmark.py \
    --fiscal-year 2024 \
    --min-score 80 \
    --sleep 1
```

### Utilisation programmatique

```python
from src.governance_report_retriever.models import Company
from src.governance_report_retriever.retriever import GovernanceReportRetriever

company = Company(
    name="Schneider Electric",
    official_domain="se.com",
    ticker="SU",
    isin="FR0000121972",
    jurisdiction="France",
)

retriever = GovernanceReportRetriever(root_dir="data/dossier_ingestion_0")

result = retriever.download_high_score_candidates(
    company=company,
    fiscal_year=2024,
    min_score=80.0,
)

print(f"Téléchargés : {result.downloaded_count}")
for item in result.downloaded:
    print(f"  [{item['rank']}] score={item['score']} | {item['title']}")
```

---

## Contraintes

- Ce moteur ne valide pas définitivement les documents téléchargés.
- Ce moteur ne déduplique pas les documents entre moteurs différents.
- Ce moteur ne réalise pas l'extraction ESG ni le scoring ESG.
- Les avis de convocation d'AG sont explicitement rejetés (classe `agm_convocation_document`).

---

## Moteurs associés

| Moteur | Documents cibles |
|---|---|
| `AnnualReportRetriever` | Rapports annuels, URD, DEU |
| `SustainabilityReportRetriever` | Rapports ESG, RSE, durabilité, CSRD |
| `ClimateReportRetriever` | Rapports climat, TCFD, transition, carbone |
| `GovernanceReportRetriever` | Rapports de gouvernance d'entreprise |
| `RemunerationReportRetriever` | *(à venir)* |
| `VigilancePlanRetriever` | *(à venir)* |

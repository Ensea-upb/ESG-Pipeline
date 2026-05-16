# RemunerationReportRetriever

Moteur d'ingestion automatique des **rapports de rémunération des dirigeants** (Remuneration Reports, Directors' Remuneration Reports, Executive Compensation Reports).

Fait partie du système ESG Document Ingestion — version **v0.1**.

---

## Documents ciblés

| Type | Exemples |
|------|---------|
| Rapport de rémunération autonome | Remuneration Report, Directors' Remuneration Report |
| Rapport exécutif de rémunération | Executive Compensation Report, Pay Report |
| Rapport say on pay | Say on Pay Report, Advisory Vote on Compensation |
| Politique de rémunération | Remuneration Policy Report, Politique de rémunération |
| Section dans rapport annuel | Annual Report — Remuneration section, URD — Rémunération |

Stocké dans : `data/dossier_ingestion_0/remuneration_reports/`

---

## Structure du module

```
RemunerationReportRetriever/
├── src/
│   └── remuneration_report_retriever/
│       ├── __init__.py
│       ├── models.py          # Dataclasses : Company, RemunerationReportRequest, ScoredCandidate, DownloadResult
│       ├── utils.py           # Utilitaires : slugify, extract_years, compute_sha256, ...
│       ├── search.py          # RemunerationReportSearch — requêtes Tavily multi-stratégies
│       ├── scorer.py          # RemunerationReportScorer — scoring multi-signaux
│       ├── downloader.py      # PDFDownloader — 3 stratégies HTTP robustes
│       ├── html_resolver.py   # HTMLToPDFLinkResolver — résolution HTML → PDF
│       ├── storage.py         # RemunerationReportStorage — stockage local + manifeste
│       └── retriever.py       # RemunerationReportRetriever — pipeline central
├── scripts/
│   ├── run_download_all.py    # CLI : télécharger pour une entreprise
│   └── run_benchmark.py       # Benchmark : LVMH, TotalEnergies, Schneider Electric
├── .env                       # TAVILY_API_KEY=...
├── requirements.txt
└── README.md
```

---

## Installation

```bash
cd RemunerationReportRetriever
pip install -r requirements.txt
```

Créer un fichier `.env` :

```
TAVILY_API_KEY=tvly-...
```

---

## Utilisation

### Télécharger pour une entreprise

```bash
python scripts/run_download_all.py \
  --company-name "TotalEnergies" \
  --fiscal-year 2024 \
  --official-domain totalenergies.com \
  --ticker TTE \
  --isin FR0000120271 \
  --jurisdiction France \
  --min-score 80.0
```

### Lancer le benchmark

```bash
python scripts/run_benchmark.py --fiscal-year 2024
```

---

## Scoring

### Signaux positifs

| Signal | Points |
|--------|--------|
| Mot-clé fort (remuneration report, directors remuneration, executive compensation…) | +35 |
| Mot-clé de divulgation (ltip, stip, say on pay, pay ratio, ceo pay ratio, actions de performance…) | +35 |
| Mot-clé faible (pay, salary, compensation…) | +18 |
| Année fiscale dans titre/URL | +25 |
| Nom de l'entreprise dans titre/URL | +20 |
| Domaine officiel de l'entreprise | +20 |
| URL PDF directe | +10 |
| Nom de fichier fort (remuneration, compensation, pay-report…) | +15 |
| CDN / asset domain | +5 |
| Archive tierce (modernslaveryregistry.org, etc.) | +3 |

### Pénalités

| Signal | Points |
|--------|--------|
| Document exclusivement financier (financial statements, earnings release…) | -45 |
| Document de présentation (investor presentation, roadshow…) | -40 |
| Convocation AGM (avis de convocation, notice of meeting, proxy form…) | -60 |
| Rapport périodique trimestriel (Q1, Q3, interim…) | -30 |
| Communiqué de presse | -35 |
| Domaine presse | -30 |
| Domaine de faible confiance | -45 |

### Classes de documents

| Classe | Score max | Décision |
|--------|-----------|----------|
| `standalone_remuneration_report` | 100 | auto_download si ≥ 80 |
| `remuneration_disclosure` | 100 | auto_download si ≥ 80 |
| `annual_report_with_remuneration_section` | 75 | human_review si ≥ 60 |
| `agm_convocation_document` | 40 | reject |
| `reject` | 0 | reject |

---

## Stockage

```
data/dossier_ingestion_0/
├── remuneration_reports/
│   └── <company_slug>/
│       └── <fiscal_year>/
│           └── candidates/
│               ├── candidate_001_score_95_0.pdf
│               ├── candidate_001_manifest.json
│               └── ...
├── registry/
│   └── remuneration_reports_registry.jsonl
└── tmp/
```

Chaque manifeste JSON contient : source URL, titre, snippet, score, signaux positifs/négatifs, sha256, taille, horodatage.

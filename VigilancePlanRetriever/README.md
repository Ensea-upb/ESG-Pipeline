# VigilancePlanRetriever

Moteur d'ingestion automatique des **plans de vigilance et rapports de devoir de vigilance** (Plan de vigilance, Modern Slavery Statement, Human Rights Due Diligence Report).

Fait partie du système ESG Document Ingestion — version **v0.1**.

---

## Documents ciblés

| Type | Exemples |
|------|---------|
| Plan de vigilance (loi FR 2017) | Plan de vigilance, Rapport devoir de vigilance |
| Modern Slavery Statement (UK/AU) | Modern Slavery Act Report, Anti-Slavery Statement |
| Rapport droits humains | Human Rights Due Diligence Report, Duty of Vigilance Plan |
| Rapport chaîne d'approvisionnement | Supply Chain Transparency Report, Responsible Sourcing Report |
| Rapport travail forcé | Forced Labour Report, Child Labour Statement |

Stocké dans : `data/dossier_ingestion_0/vigilance_plans/`

---

## Structure du module

```
VigilancePlanRetriever/
├── src/
│   └── vigilance_plan_retriever/
│       ├── __init__.py
│       ├── models.py          # Dataclasses : Company, VigilancePlanRequest, ScoredCandidate, DownloadResult
│       ├── utils.py           # Utilitaires : slugify, extract_years, compute_sha256, ...
│       ├── search.py          # VigilancePlanSearch — requêtes Tavily multi-stratégies
│       ├── scorer.py          # VigilancePlanScorer — scoring multi-signaux
│       ├── downloader.py      # PDFDownloader — 3 stratégies HTTP robustes
│       ├── html_resolver.py   # HTMLToPDFLinkResolver — résolution HTML → PDF
│       ├── storage.py         # VigilancePlanStorage — stockage local + manifeste
│       └── retriever.py       # VigilancePlanRetriever — pipeline central
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
cd VigilancePlanRetriever
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
| Mot-clé fort (plan de vigilance, devoir de vigilance, modern slavery statement, human rights due diligence…) | +35 |
| Mot-clé de divulgation (un guiding principles, ungp, csddd, child labour, travail forcé, conflict minerals…) | +35 |
| Mot-clé faible (vigilance, slavery, supply chain, due diligence…) | +18 |
| Année fiscale dans titre/URL | +25 |
| Nom de l'entreprise dans titre/URL | +20 |
| Domaine officiel de l'entreprise | +20 |
| URL PDF directe | +10 |
| Nom de fichier fort (vigilance, modern-slavery, duty-of-vigilance…) | +15 |
| CDN / asset domain | +5 |
| Archive tierce (modernslaveryregistry.org, modernslaveryscrutiny.org…) | +3 |

### Pénalités

| Signal | Points |
|--------|--------|
| Document exclusivement financier (financial statements, earnings release…) | -45 |
| Document de présentation (investor presentation, roadshow…) | -40 |
| Rapport périodique trimestriel (Q1, Q3, interim…) | -30 |
| Communiqué de presse | -35 |
| Domaine presse | -30 |
| Domaine de faible confiance | -45 |

### Classes de documents

| Classe | Score max | Décision |
|--------|-----------|----------|
| `standalone_vigilance_plan` | 100 | auto_download si ≥ 80 |
| `vigilance_disclosure` | 100 | auto_download si ≥ 80 |
| `annual_report_with_vigilance_section` | 75 | human_review si ≥ 60 |
| `reject` | 0 | reject |

---

## Registres tiers reconnus

Le scorer reconnaît `modernslaveryregistry.org` et `modernslaveryscrutiny.org` comme archives de référence pour les Modern Slavery Statements. Ces sources reçoivent +3 points (archive tierce) mais ne sont pas pénalisées comme domaine presse.

---

## Stockage

```
data/dossier_ingestion_0/
├── vigilance_plans/
│   └── <company_slug>/
│       └── <fiscal_year>/
│           └── candidates/
│               ├── candidate_001_score_95_0.pdf
│               ├── candidate_001_manifest.json
│               └── ...
├── registry/
│   └── vigilance_plans_registry.jsonl
└── tmp/
```

Chaque manifeste JSON contient : source URL, titre, snippet, score, signaux positifs/négatifs, sha256, taille, horodatage.

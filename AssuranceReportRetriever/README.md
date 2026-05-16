# AssuranceReportRetriever

Retrieves third-party assurance reports on ESG / sustainability data: ISAE 3000, ISAE 3410, AA1000, limited and reasonable assurance statements.

## Targets

- Independent Limited Assurance Statement
- Reasonable Assurance Report
- ISAE 3000 / ISAE 3410 assurance
- AA1000 assurance statement
- Commissaire aux comptes durabilité (CSRD)
- Rapport de vérification ESG

## Usage

```bash
# Download for a single company
python scripts/run_download_all.py \
  --company-name "Schneider Electric" \
  --fiscal-year 2024 \
  --official-domain se.com

# Run benchmark
python scripts/run_benchmark.py --fiscal-year 2024
```

## Scoring

| Signal | Points |
|--------|--------|
| Strong assurance keywords (ISAE 3000, AA1000, independent assurance…) | +45 |
| Secondary keywords (limited assurance, reasonable assurance…) | +20 |
| Year found | +20 |
| Official domain | +20 |
| Company name detected | +15 |
| Direct PDF URL | +10 |
| Strong filename | +15 |

## Storage

```
data/dossier_ingestion_0/assurance_reports/<company_slug>/candidates/
```

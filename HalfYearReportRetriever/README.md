# HalfYearReportRetriever

Retrieves half-year / semi-annual / interim financial reports (H1 results).

## Targets

- Half Year Report / Semi-Annual Report
- Interim Report / H1 Results
- Rapport semestriel / Résultats H1 / Premier semestre

## Usage

```bash
# Download for a single company
python scripts/run_download_all.py \
  --company-name "TotalEnergies" \
  --fiscal-year 2024 \
  --official-domain totalenergies.com \
  --min-score 80

# Run benchmark (LVMH, TotalEnergies, Schneider Electric)
python scripts/run_benchmark.py --fiscal-year 2024
```

## Scoring

| Signal | Points |
|--------|--------|
| Strong H1 keywords (rapport semestriel, half year report…) | +35 |
| Secondary H1 keywords (interim, six months…) | +20 |
| Year found | +25 |
| Company name detected | +20 |
| Official domain | +20 |
| Direct PDF URL | +10 |
| Strong filename | +15 |
| Annual report (penalty — wrong doc) | cap 50 |
| Press release | −30 |

## Storage

```
data/dossier_ingestion_0/half_year_reports/<company_slug>/candidates/
```

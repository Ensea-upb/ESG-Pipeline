# InvestorPresentationRetriever

Retrieves investor presentations: Capital Markets Days, investor days, roadshow presentations, results slides.

## Targets

- Capital Markets Day (CMD) presentation
- Investor Day / ESG Day presentation
- Annual/Full Year results presentation slides
- Roadshow presentation PDF

## Usage

```bash
# Download for a single company
python scripts/run_download_all.py \
  --company-name "TotalEnergies" \
  --fiscal-year 2024 \
  --official-domain totalenergies.com

# Run benchmark
python scripts/run_benchmark.py --fiscal-year 2024
```

## Scoring

| Signal | Points |
|--------|--------|
| Strong keywords (capital markets day, investor day, CMD…) | +40 |
| Secondary keywords (results presentation, investor relations…) | +20 |
| Year found | +20 |
| Company name detected | +20 |
| Official domain | +20 |
| Direct PDF URL | +10 |
| Strong filename (cmd-, investor-day-…) | +15 |
| Company name absent | −40 |
| Press release | −30 |

## Storage

```
data/dossier_ingestion_0/investor_presentations/<company_slug>/candidates/
```

# CDPResponseRetriever

Retrieves published CDP (Carbon Disclosure Project) questionnaire responses: Climate Change, Water Security, Forests.

## Targets

- CDP Climate Change response
- CDP Water Security response
- CDP Forests response
- CDP disclosure / questionnaire PDF

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

## Notes

Most CDP responses are locked behind the CDP platform (cdp.net). This retriever finds publicly available CDP disclosures. Full CDP responses require a CDP account.

## Scoring

| Signal | Points |
|--------|--------|
| Strong CDP keywords (cdp response, carbon disclosure project…) | +45 |
| Secondary keywords (cdp score, climate disclosure…) | +20 |
| cdp.net domain bonus | +20 |
| Year found | +20 |
| Company name detected | +15 |
| Official company domain | +15 |
| Direct PDF URL | +10 |
| Company name absent | −40 |

## Storage

```
data/dossier_ingestion_0/cdp_responses/<company_slug>/candidates/
```

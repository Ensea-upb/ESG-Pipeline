# AGMRetriever

Retrieves Annual General Meeting (AGM) documents: convocations, resolutions, vote results, minutes (PV).

## Targets

- AGM resolutions / Proxy statement
- Notice of annual general meeting / Convocation AG
- Voting results / Résultats votes assemblée générale
- Say on Climate vote
- Minutes / Procès-verbal AG

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
| Strong AGM keywords (resolutions, proxy, assemblée générale…) | +40 |
| Secondary keywords (say on climate, shareholder vote…) | +20 |
| Year found | +20 |
| Company name detected | +20 |
| Official domain | +20 |
| Direct PDF URL | +10 |
| Regulatory domain (sec.gov, amf-france.org) | +5 |
| Company name absent | −40 |

## Storage

```
data/dossier_ingestion_0/agm_documents/<company_slug>/candidates/
```

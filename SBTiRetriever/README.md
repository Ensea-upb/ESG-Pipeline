# SBTiRetriever

Retrieves Science Based Targets initiative (SBTi) validation documents: commitment letters, validated target summaries, Net-Zero Standard adherence.

## Targets

- SBTi commitment letter
- SBTi validated targets page (sciencebasedtargets.org)
- Net-Zero Standard commitment
- 1.5°C aligned target documentation

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
| Strong SBTi keywords (sbti validated, science based targets…) | +45 |
| Secondary keywords (net zero commitment, 1.5 degrees…) | +20 |
| sciencebasedtargets.org domain bonus | +20 |
| Year found | +15 |
| Company name detected | +15 |
| Official company domain | +15 |
| Direct PDF URL | +10 |
| Company name absent | −40 |

## Storage

```
data/dossier_ingestion_0/sbti_commitments/<company_slug>/candidates/
```

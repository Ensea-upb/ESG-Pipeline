# EarningsCallRetriever

Retrieves earnings call transcripts: Q1–Q4 and full-year results calls, analyst conference call transcripts.

## Targets

- Earnings call transcript (Q1/Q2/Q3/Q4/FY)
- Conference call transcript
- Analyst call transcript
- seekingalpha.com / motleyfool.com transcripts

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

Earnings call transcripts for European companies are mostly available as HTML pages (seekingalpha.com) rather than PDFs. These will be marked `pdf_resolution_required` and require a separate HTML-to-PDF conversion step.

## Scoring

| Signal | Points |
|--------|--------|
| Strong keywords (earnings call transcript, results call transcript…) | +45 |
| Secondary keywords (earnings call, conference call, analyst call…) | +20 |
| Year found | +20 |
| Company name detected | +15 |
| Official domain | +15 |
| Specialized transcript source (seekingalpha, motleyfool) | +10 |
| Company name absent | −40 |
| Press release | −25 |

## Storage

```
data/dossier_ingestion_0/earnings_calls/<company_slug>/candidates/
```

# CorporatePolicyRetriever

Retrieves corporate policy documents across 6 ESG policy types. Policies are treated as perpetual documents (not tied to a specific fiscal year).

## Policy Types

| Value | Description |
|-------|-------------|
| `code_of_conduct` | Code of conduct / Code éthique |
| `anticorruption` | Anti-corruption / Anti-bribery policy |
| `human_rights` | Human rights policy |
| `dei` | Diversity, Equity & Inclusion policy |
| `environmental` | Environmental / Climate policy |
| `supplier_code` | Supplier code of conduct |

## Usage

```bash
# Download a specific policy type
python scripts/run_download_all.py \
  --company-name "Schneider Electric" \
  --reference-year 2024 \
  --policy-type code_of_conduct \
  --official-domain se.com

# Run full benchmark (3 companies × 6 policy types)
python scripts/run_benchmark.py --reference-year 2024

# Run benchmark for specific policy types
python scripts/run_benchmark.py --reference-year 2024 --policy-types code_of_conduct anticorruption
```

## Scoring

| Signal | Points |
|--------|--------|
| Strong policy keywords (type-specific) | +35 |
| Secondary policy keywords | +20 |
| Official domain | +25 |
| Company name detected | +20 |
| Direct PDF URL | +10 |
| Document >4 years old | −20 |

## Storage

```
data/dossier_ingestion_0/corporate_policies/<policy_type>/<company_slug>/candidates/
```

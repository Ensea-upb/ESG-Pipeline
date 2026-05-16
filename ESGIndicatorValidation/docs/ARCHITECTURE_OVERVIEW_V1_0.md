# ESGIndicatorValidation v1.0 - Architecture Overview

Pipeline:

1. Loader reads `consolidated_unique_candidates.csv` or `consolidated_candidates.csv`.
2. Prevalidator applies conservative status rules.
3. Normalizer extracts candidate value, unit and year.
4. Family mapper proposes ESG families.
5. Deduplicator groups similar candidates and keeps canonical rows for review.
6. Review queue orders manual review priorities.
7. Audit and contract validation verify safety invariants.

This module prepares candidate records for future human validation. It deliberately stops before producing final ESG indicators.

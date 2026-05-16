# ESG Variable Dataset Contract V0

The dataset unit is `company x year`.

Required files:

- `esg_variables_dataset.csv`
- `esg_variables_dataset_enriched.csv`
- `esg_variables_long.csv`
- `esg_variables_evidence.csv`
- `esg_variables_quality_report.json`

The main dataset contains `company`, `year`, and the 31 required variables.
The enriched dataset contains value, unit, status, source document, page number,
and confidence for every variable.

Allowed statuses are `found`, `missing_from_corpus`, `needs_review`,
`qualitative_only`, `conflicting_values`, and `not_disclosed`.

External sources and score columns are forbidden. A `found` value must have
evidence in `esg_variables_evidence.csv`.
